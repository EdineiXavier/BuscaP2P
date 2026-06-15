"""
Cada função retorna um SearchResult com:
  - found          : bool
  - found_at       : node_id onde o recurso foi encontrado (ou None)
  - messages       : número total de mensagens trocadas
  - nodes_visited  : conjunto de nós que participaram da busca
  - path           : sequência de nós percorridos
  - cache_hit      : True se o recurso foi encontrado via cache
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from network import P2PNetwork


@dataclass
class SearchResult:
    found: bool = False
    found_at: str | None = None
    messages: int = 0
    nodes_visited: set[str] = field(default_factory=set)
    path: list[str] = field(default_factory=list)
    cache_hit: bool = False

    def summary(self) -> str:
        status = f"ENCONTRADO em '{self.found_at}'" if self.found else "NÃO ENCONTRADO"
        cache_info = " (via cache)" if self.cache_hit else ""
        return (
            f"  Resultado       : {status}{cache_info}\n"
            f"  Mensagens       : {self.messages}\n"
            f"  Nós envolvidos  : {len(self.nodes_visited)} {sorted(self.nodes_visited)}\n"
            f"  Caminho         : {' -> '.join(self.path) if self.path else 'N/A'}"
        )


# -----------------------------------------------------------------------
# Busca por Inundação (Flooding)
# -----------------------------------------------------------------------

def flooding(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    """
    Envia a requisição a TODOS os vizinhos simultaneamente (BFS em camadas).
    Cada transmissão de um nó para um vizinho conta como 1 mensagem.
    O TTL é decrementado a cada salto; quando chega a 0 a mensagem é descartada.
    Ao encontrar o recurso, envia 1 mensagem de resposta de volta ao nó origem.
    """
    result = SearchResult()

    start_node = network.get_node(start_id)
    result.nodes_visited.add(start_id)
    result.path.append(start_id)

    # Verifica localmente no nó de origem
    if start_node.has_resource(resource_id):
        result.found = True
        result.found_at = start_id
        return result

    # Fila: (current_node_id, ttl_restante, caminho_até_aqui)
    queue: deque[tuple[str, int, list[str]]] = deque()
    visited: set[str] = {start_id}

    for neighbor_id in start_node.neighbors:
        result.messages += 1
        queue.append((neighbor_id, ttl - 1, [start_id, neighbor_id]))

    while queue:
        current_id, current_ttl, current_path = queue.popleft()

        if current_id in visited:
            continue
        visited.add(current_id)
        result.nodes_visited.add(current_id)

        current_node = network.get_node(current_id)

        if current_node.has_resource(resource_id):
            result.found = True
            result.found_at = current_id
            result.path = current_path
            result.messages += 1
            _propagate_cache(network, current_path, resource_id, current_id)
            return result

        if current_ttl <= 0:
            continue

        for neighbor_id in current_node.neighbors:
            if neighbor_id not in visited:
                result.messages += 1
                queue.append((neighbor_id, current_ttl - 1, current_path + [neighbor_id]))

    return result


# -----------------------------------------------------------------------
# Busca por Passeio Aleatório (Random Walk)
# -----------------------------------------------------------------------

def random_walk(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    """
    A cada passo escolhe ALEATORIAMENTE um vizinho e envia a requisição apenas para ele.
    Continua até encontrar o recurso ou o TTL zerar.
    Cada passo (hop) conta como 1 mensagem.
    Ao encontrar, envia 1 mensagem de resposta ao nó origem.
    """
    result = SearchResult()

    current_id = start_id
    result.nodes_visited.add(current_id)
    result.path.append(current_id)

    current_node = network.get_node(current_id)

    if current_node.has_resource(resource_id):
        result.found = True
        result.found_at = current_id
        return result

    remaining_ttl = ttl

    while remaining_ttl > 0:
        current_node = network.get_node(current_id)
        neighbors = current_node.neighbors

        if not neighbors:
            break

        next_id = random.choice(neighbors)
        result.messages += 1
        result.nodes_visited.add(next_id)
        result.path.append(next_id)
        remaining_ttl -= 1

        next_node = network.get_node(next_id)

        if next_node.has_resource(resource_id):
            result.found = True
            result.found_at = next_id
            result.messages += 1
            _propagate_cache(network, result.path, resource_id, next_id)
            return result

        current_id = next_id

    return result


# -----------------------------------------------------------------------
# Busca por Inundação Informada (Informed Flooding)
# -----------------------------------------------------------------------

def informed_flooding(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    """
    Antes de iniciar a inundação, cada nó consulta seu cache local.
    Se o nó de origem já souber onde o recurso está, responde imediatamente
    com apenas 1 mensagem (consulta ao cache), sem propagar nada na rede.
    Caso contrário, durante a inundação, cada nó visitado também consulta
    seu cache antes de continuar propagando — se tiver a informação, responde
    direto sem precisar chegar ao nó que possui o recurso.
    """
    result = SearchResult()

    start_node = network.get_node(start_id)
    result.nodes_visited.add(start_id)
    result.path.append(start_id)

    # 1. Verifica recurso local
    if start_node.has_resource(resource_id):
        result.found = True
        result.found_at = start_id
        return result

    # 2. Consulta cache do nó de origem
    cached_location = start_node.get_cached_location(resource_id)
    if cached_location:
        result.found = True
        result.found_at = cached_location
        result.cache_hit = True
        result.messages += 1  # 1 mensagem: consulta ao nó cacheado
        result.nodes_visited.add(cached_location)
        result.path.append(cached_location)
        return result

    # 3. Inundação normal, mas cada nó intermediário também checa seu cache
    queue: deque[tuple[str, int, list[str]]] = deque()
    visited: set[str] = {start_id}

    for neighbor_id in start_node.neighbors:
        result.messages += 1
        queue.append((neighbor_id, ttl - 1, [start_id, neighbor_id]))

    while queue:
        current_id, current_ttl, current_path = queue.popleft()

        if current_id in visited:
            continue
        visited.add(current_id)
        result.nodes_visited.add(current_id)

        current_node = network.get_node(current_id)

        # Checa recurso local
        if current_node.has_resource(resource_id):
            result.found = True
            result.found_at = current_id
            result.path = current_path
            result.messages += 1
            _propagate_cache(network, current_path, resource_id, current_id)
            return result

        # Checa cache do nó intermediário — atalho!
        cached_location = current_node.get_cached_location(resource_id)
        if cached_location:
            result.found = True
            result.found_at = cached_location
            result.cache_hit = True
            result.path = current_path + [cached_location]
            result.messages += 1  # mensagem: current -> nó cacheado
            result.nodes_visited.add(cached_location)
            _propagate_cache(network, result.path, resource_id, cached_location)
            return result

        if current_ttl <= 0:
            continue

        for neighbor_id in current_node.neighbors:
            if neighbor_id not in visited:
                result.messages += 1
                queue.append((neighbor_id, current_ttl - 1, current_path + [neighbor_id]))

    return result


# -----------------------------------------------------------------------
# Busca por Passeio Aleatório Informado (Informed Random Walk)
# -----------------------------------------------------------------------

def informed_random_walk(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    """
    Igual ao random_walk, mas antes de cada salto o nó atual consulta seu cache.
    Se souber onde o recurso está, vai direto para lá sem continuar o passeio.
    Isso reduz significativamente o número de mensagens em buscas repetidas.
    """
    result = SearchResult()

    current_id = start_id
    result.nodes_visited.add(current_id)
    result.path.append(current_id)

    current_node = network.get_node(current_id)

    # 1. Verifica recurso local
    if current_node.has_resource(resource_id):
        result.found = True
        result.found_at = current_id
        return result

    # 2. Consulta cache do nó de origem
    cached_location = current_node.get_cached_location(resource_id)
    if cached_location:
        result.found = True
        result.found_at = cached_location
        result.cache_hit = True
        result.messages += 1
        result.nodes_visited.add(cached_location)
        result.path.append(cached_location)
        return result

    remaining_ttl = ttl

    while remaining_ttl > 0:
        current_node = network.get_node(current_id)
        neighbors = current_node.neighbors

        if not neighbors:
            break

        # Checa cache antes de cada salto
        cached_location = current_node.get_cached_location(resource_id)
        if cached_location:
            result.found = True
            result.found_at = cached_location
            result.cache_hit = True
            result.messages += 1
            result.nodes_visited.add(cached_location)
            result.path.append(cached_location)
            _propagate_cache(network, result.path, resource_id, cached_location)
            return result

        next_id = random.choice(neighbors)
        result.messages += 1
        result.nodes_visited.add(next_id)
        result.path.append(next_id)
        remaining_ttl -= 1

        next_node = network.get_node(next_id)

        if next_node.has_resource(resource_id):
            result.found = True
            result.found_at = next_id
            result.messages += 1
            _propagate_cache(network, result.path, resource_id, next_id)
            return result

        current_id = next_id

    return result


# -----------------------------------------------------------------------
# Utilitário interno: propaga cache de localização
# -----------------------------------------------------------------------

def _propagate_cache(network: "P2PNetwork", path: list[str], resource_id: str, found_at: str):
    """Atualiza o cache de todos os nós no caminho com a localização do recurso."""
    for node_id in path:
        network.get_node(node_id).update_cache(resource_id, found_at)
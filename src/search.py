"""
search.py - Algoritmos de busca em redes P2P não estruturadas
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from network import P2PNetwork


@dataclass
class HistoricoStep:
    rodada: int
    ttl_restante: int
    mensagens: list[str]
    encontrou: bool = False
    found_at: str | None = None
    cache_hit: bool = False


@dataclass
class SearchResult:
    found: bool = False
    found_at: str | None = None
    messages: int = 0
    nodes_visited: set[str] = field(default_factory=set)
    path: list[str] = field(default_factory=list)
    cache_hit: bool = False
    historico: list[HistoricoStep] = field(default_factory=list)

    def summary(self) -> str:
        linhas = ["", "  Histórico:"]
        for step in self.historico:
            ttl_str = f"TTL={step.ttl_restante}"
            if len(step.mensagens) == 1:
                msgs_str = step.mensagens[0]
            else:
                msgs_str = "{ " + ",  ".join(step.mensagens) + " }"

            sufixo = ""
            if step.encontrou:
                if step.cache_hit:
                    sufixo = f"  *** CACHE HIT → ENCONTRADO em '{step.found_at}' ***"
                else:
                    sufixo = f"  *** ENCONTRADO em '{step.found_at}' ***"

            linhas.append(f"    Rodada {step.rodada:>2} [{ttl_str}]  {msgs_str}{sufixo}")

        linhas.append("")
        if self.found:
            linhas.append(f"  Caminho até o recurso : {' -> '.join(self.path)}")
        else:
            linhas.append(f"  Caminho percorrido    : {' -> '.join(self.path) if self.path else 'N/A'}")

        status = f"ENCONTRADO em '{self.found_at}'" if self.found else "NÃO ENCONTRADO"
        cache_info = " (via cache)" if self.cache_hit else ""
        linhas += [
            "",
            f"  Resultado       : {status}{cache_info}",
            f"  Mensagens       : {self.messages}",
            f"  Nós envolvidos  : {len(self.nodes_visited)} {sorted(self.nodes_visited)}",
        ]
        return "\n".join(linhas)


# -----------------------------------------------------------------------
# Flooding — BFS por camadas (cada camada = 1 rodada paralela)
# -----------------------------------------------------------------------

def flooding(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    result     = SearchResult()
    start_node = network.get_node(start_id)
    result.nodes_visited.add(start_id)
    result.path.append(start_id)

    # Recurso está no próprio nó origem
    if start_node.has_resource(resource_id):
        result.found    = True
        result.found_at = start_id
        result.historico.append(HistoricoStep(1, ttl,
            [f"{start_id} já possui o recurso"], True, start_id))
        return result

    visited = {start_id}
    rodada  = 1

    # Camada inicial: origem envia para todos os seus vizinhos
    # Cada item: (node_id, ttl_restante, pai, caminho)
    camada = [(viz, ttl - 1, start_id, [start_id, viz])
              for viz in start_node.neighbors]

    while camada:
        msgs_rodada = []
        proxima     = []
        encontrou   = False
        found_node  = None
        found_path  = []
        ttl_camada  = camada[0][1]  # TTL desta camada

        for current_id, current_ttl, pai, current_path in camada:
            if current_id in visited:
                continue
            visited.add(current_id)
            result.nodes_visited.add(current_id)
            result.messages += 1

            msgs_rodada.append(f"{pai} -> {current_id}")

            if network.get_node(current_id).has_resource(resource_id):
                encontrou  = True
                found_node = current_id
                found_path = current_path
            elif current_ttl > 0:
                for viz in network.get_node(current_id).neighbors:
                    if viz not in visited:
                        proxima.append((viz, current_ttl - 1, current_id,
                                        current_path + [viz]))

        if msgs_rodada:
            result.historico.append(HistoricoStep(
                rodada=rodada, ttl_restante=ttl_camada,
                mensagens=msgs_rodada,
                encontrou=encontrou, found_at=found_node
            ))
            rodada += 1

        if encontrou:
            result.found    = True
            result.found_at = found_node
            result.path     = found_path
            result.messages += 1  # resposta de volta
            _propagate_cache(network, found_path, resource_id, found_node)
            return result

        camada = proxima

    return result


# -----------------------------------------------------------------------
# Random Walk — sequencial, com backtracking
# -----------------------------------------------------------------------

def random_walk(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    result     = SearchResult()
    current_id = start_id
    result.nodes_visited.add(current_id)
    result.path.append(current_id)

    if network.get_node(current_id).has_resource(resource_id):
        result.found    = True
        result.found_at = current_id
        result.historico.append(HistoricoStep(1, ttl,
            [f"{current_id} já possui o recurso"], True, current_id))
        return result

    remaining_ttl = ttl
    rodada        = 1

    while remaining_ttl > 0:
        neighbors = network.get_node(current_id).neighbors
        if not neighbors:
            break

        next_id = random.choice(neighbors)
        result.messages   += 1
        result.nodes_visited.add(next_id)
        result.path.append(next_id)
        remaining_ttl -= 1

        encontrou = network.get_node(next_id).has_resource(resource_id)
        result.historico.append(HistoricoStep(
            rodada=rodada, ttl_restante=remaining_ttl,
            mensagens=[f"{current_id} -> {next_id}"],
            encontrou=encontrou,
            found_at=next_id if encontrou else None
        ))
        rodada += 1

        if encontrou:
            result.found    = True
            result.found_at = next_id
            result.messages += 1
            _propagate_cache(network, result.path, resource_id, next_id)
            return result

        current_id = next_id

    return result


# -----------------------------------------------------------------------
# Informed Flooding
# -----------------------------------------------------------------------

def informed_flooding(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    result     = SearchResult()
    start_node = network.get_node(start_id)
    result.nodes_visited.add(start_id)
    result.path.append(start_id)

    if start_node.has_resource(resource_id):
        result.found    = True
        result.found_at = start_id
        result.historico.append(HistoricoStep(1, ttl,
            [f"{start_id} já possui o recurso"], True, start_id))
        return result

    cached = start_node.get_cached_location(resource_id)
    if cached:
        result.found     = True
        result.found_at  = cached
        result.cache_hit = True
        result.messages  = 1
        result.nodes_visited.add(cached)
        result.path.append(cached)
        result.historico.append(HistoricoStep(1, ttl,
            [f"{start_id} -> {cached} (cache hit!)"], True, cached, True))
        return result

    visited = {start_id}
    rodada  = 1

    camada = [(viz, ttl - 1, start_id, [start_id, viz])
              for viz in start_node.neighbors]

    while camada:
        msgs_rodada = []
        proxima     = []
        encontrou   = False
        found_node  = None
        found_path  = []
        cache_hit   = False
        ttl_camada  = camada[0][1]

        for current_id, current_ttl, pai, current_path in camada:
            if current_id in visited:
                continue
            visited.add(current_id)
            result.nodes_visited.add(current_id)
            result.messages += 1
            node = network.get_node(current_id)

            c = node.get_cached_location(resource_id)
            if c:
                msgs_rodada.append(f"{pai} -> {current_id} -> {c} (cache hit!)")
                result.nodes_visited.add(c)
                encontrou  = True
                found_node = c
                found_path = current_path + [c]
                cache_hit  = True
                continue

            msgs_rodada.append(f"{pai} -> {current_id}")

            if node.has_resource(resource_id):
                encontrou  = True
                found_node = current_id
                found_path = current_path
            elif current_ttl > 0:
                for viz in node.neighbors:
                    if viz not in visited:
                        proxima.append((viz, current_ttl - 1, current_id,
                                        current_path + [viz]))

        if msgs_rodada:
            result.historico.append(HistoricoStep(
                rodada=rodada, ttl_restante=ttl_camada,
                mensagens=msgs_rodada,
                encontrou=encontrou, found_at=found_node, cache_hit=cache_hit
            ))
            rodada += 1

        if encontrou:
            result.found     = True
            result.found_at  = found_node
            result.cache_hit = cache_hit
            result.path      = found_path
            result.messages += 1
            _propagate_cache(network, found_path, resource_id, found_node)
            return result

        camada = proxima

    return result


# -----------------------------------------------------------------------
# Informed Random Walk
# -----------------------------------------------------------------------

def informed_random_walk(network: "P2PNetwork", start_id: str, resource_id: str, ttl: int) -> SearchResult:
    result     = SearchResult()
    current_id = start_id
    result.nodes_visited.add(current_id)
    result.path.append(current_id)
    node = network.get_node(current_id)

    if node.has_resource(resource_id):
        result.found    = True
        result.found_at = current_id
        result.historico.append(HistoricoStep(1, ttl,
            [f"{current_id} já possui o recurso"], True, current_id))
        return result

    cached = node.get_cached_location(resource_id)
    if cached:
        result.found     = True
        result.found_at  = cached
        result.cache_hit = True
        result.messages  = 1
        result.nodes_visited.add(cached)
        result.path.append(cached)
        result.historico.append(HistoricoStep(1, ttl,
            [f"{current_id} -> {cached} (cache hit!)"], True, cached, True))
        return result

    remaining_ttl = ttl
    rodada        = 1

    while remaining_ttl > 0:
        node      = network.get_node(current_id)
        neighbors = node.neighbors
        if not neighbors:
            break

        cached = node.get_cached_location(resource_id)
        if cached:
            result.found     = True
            result.found_at  = cached
            result.cache_hit = True
            result.messages += 1
            result.nodes_visited.add(cached)
            result.path.append(cached)
            result.historico.append(HistoricoStep(rodada, remaining_ttl,
                [f"{current_id} -> {cached} (cache hit!)"], True, cached, True))
            _propagate_cache(network, result.path, resource_id, cached)
            return result

        next_id = random.choice(neighbors)
        result.messages   += 1
        result.nodes_visited.add(next_id)
        result.path.append(next_id)
        remaining_ttl -= 1

        encontrou = network.get_node(next_id).has_resource(resource_id)
        result.historico.append(HistoricoStep(
            rodada=rodada, ttl_restante=remaining_ttl,
            mensagens=[f"{current_id} -> {next_id}"],
            encontrou=encontrou,
            found_at=next_id if encontrou else None
        ))
        rodada += 1

        if encontrou:
            result.found    = True
            result.found_at = next_id
            result.messages += 1
            _propagate_cache(network, result.path, resource_id, next_id)
            return result

        current_id = next_id

    return result


# -----------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------

def _propagate_cache(network: "P2PNetwork", path: list[str], resource_id: str, found_at: str):
    for node_id in path:
        network.get_node(node_id).update_cache(resource_id, found_at)
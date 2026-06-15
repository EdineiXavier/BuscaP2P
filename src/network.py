import yaml
import json
from collections import deque


class Node:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.resources: set[str] = set()
        self.neighbors: list[str] = []
        self.cache: dict[str, str] = {}  # resource_id -> node_id (busca informada)

    def has_resource(self, resource_id: str) -> bool:
        return resource_id in self.resources

    def update_cache(self, resource_id: str, node_id: str):
        self.cache[resource_id] = node_id

    def get_cached_location(self, resource_id: str) -> str | None:
        return self.cache.get(resource_id)

    def __repr__(self):
        return f"Node({self.node_id}, resources={self.resources}, neighbors={self.neighbors})"


class P2PNetwork:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.min_neighbors: int = 0
        self.max_neighbors: int = 0


    def load_from_file(self, filepath: str):
        """Lê o arquivo de configuração (YAML ou JSON)."""
        with open(filepath, "r") as f:
            if filepath.endswith(".json"):
                data = json.load(f)
            else:
                data = yaml.safe_load(f)

        self.min_neighbors = data.get("min_neighbors", 1)
        self.max_neighbors = data.get("max_neighbors", 10)
        num_nodes = data.get("num_nodes", 0)

        resources_map: dict[str, list[str]] = data.get("resources", {})
        for node_id, res_list in resources_map.items():
            node = Node(node_id)
            if isinstance(res_list, str):
                res_list = [r.strip() for r in res_list.split(",")]
            node.resources = set(res_list)
            self.nodes[node_id] = node

        for i in range(1, num_nodes + 1):
            nid = f"n{i}"
            if nid not in self.nodes:
                self.nodes[nid] = Node(nid)

        edges = data.get("edges", [])
        for edge in edges:
            if isinstance(edge, str):
                parts = [p.strip() for p in edge.split(",")]
            else:
                parts = [str(p).strip() for p in edge]
            if len(parts) == 2:
                a, b = parts
                self._add_edge(a, b)

        self.validate()

    def _add_edge(self, a: str, b: str):
        if a not in self.nodes:
            self.nodes[a] = Node(a)
        if b not in self.nodes:
            self.nodes[b] = Node(b)
        if b not in self.nodes[a].neighbors:
            self.nodes[a].neighbors.append(b)
        if a not in self.nodes[b].neighbors:
            self.nodes[b].neighbors.append(a)


    def validate(self):
        errors = []

        # 1. Rede não pode estar particionada (verifica conectividade via BFS)
        if not self._is_connected():
            errors.append("ERRO: A rede está particionada (não totalmente conectada).")

        for node_id, node in self.nodes.items():
            # 2. Limites de vizinhos
            n = len(node.neighbors)
            if n < self.min_neighbors:
                errors.append(
                    f"ERRO: Nó '{node_id}' tem {n} vizinho(s), mínimo é {self.min_neighbors}."
                )
            if n > self.max_neighbors:
                errors.append(
                    f"ERRO: Nó '{node_id}' tem {n} vizinho(s), máximo é {self.max_neighbors}."
                )

            # 3. Nós sem recursos
            if not node.resources:
                errors.append(f"ERRO: Nó '{node_id}' não possui recursos.")

            # 4. Self-loops
            if node_id in node.neighbors:
                errors.append(f"ERRO: Nó '{node_id}' possui aresta para si mesmo.")

        if errors:
            raise ValueError("Arquivo de configuração inválido:\n" + "\n".join(errors))

    def _is_connected(self) -> bool:
        if not self.nodes:
            return True
        start = next(iter(self.nodes))
        visited = set()
        queue = deque([start])
        while queue:
            nid = queue.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            for neighbor in self.nodes[nid].neighbors:
                if neighbor not in visited:
                    queue.append(neighbor)
        return visited == set(self.nodes.keys())


    def get_node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            raise KeyError(f"Nó '{node_id}' não encontrado na rede.")
        return self.nodes[node_id]

    def summary(self) -> str:
        lines = [
            f"Rede P2P — {len(self.nodes)} nó(s)",
            f"  Vizinhos: min={self.min_neighbors}, max={self.max_neighbors}",
        ]
        for nid, node in sorted(self.nodes.items()):
            lines.append(
                f"  {nid}: recursos={sorted(node.resources)}, vizinhos={sorted(node.neighbors)}"
            )
        return "\n".join(lines)

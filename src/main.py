#!/usr/bin/env python3
"""
main.py - Interface de linha de comando para o simulador de rede P2P

Uso:
    # Modo interativo
    python src/main.py configs/rede_pequena.yaml

    # Busca direta via argumentos
    python src/main.py configs/rede_pequena.yaml --search n1 r9 10 flooding

    # Ver info da rede
    python src/main.py configs/rede_pequena.yaml --info
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network import P2PNetwork
from search import flooding, random_walk, informed_flooding, informed_random_walk, SearchResult

ALGORITHMS = {
    "flooding":             flooding,
    "random_walk":          random_walk,
    "informed_flooding":    informed_flooding,
    "informed_random_walk": informed_random_walk,
}


def run_search(network, node_id, resource_id, ttl, algo):
    fn = ALGORITHMS[algo]
    return fn(network, node_id, resource_id, ttl)


def interactive_mode(network: P2PNetwork):
    todos_nos      = sorted(network.nodes.keys())
    todos_recursos = sorted({r for node in network.nodes.values() for r in node.resources})

    print("\n" + "=" * 56)
    print("  Simulador de Busca P2P — Modo Interativo")
    print("=" * 56)
    print(f"  Nós disponíveis  : {', '.join(todos_nos)}")
    print(f"  Recursos na rede : {', '.join(todos_recursos)}")
    print(f"  Algoritmos       : {', '.join(ALGORITHMS.keys())}")
    print("  Digite 'sair' para encerrar.\n")

    while True:
        try:
            print("Nova busca:")

            node_id = input("  node_id     : ").strip()
            if node_id.lower() == "sair":
                break
            if node_id not in network.nodes:
                print(f"  ⚠ Nó '{node_id}' não existe. Tente: {todos_nos}\n")
                continue

            resource_id = input("  resource_id : ").strip()
            if resource_id not in todos_recursos:
                print(f"  ⚠ Recurso '{resource_id}' não existe. Tente: {todos_recursos}\n")
                continue

            ttl_str = input("  ttl         : ").strip()
            if not ttl_str.isdigit() or int(ttl_str) <= 0:
                print("  ⚠ TTL deve ser um número inteiro positivo.\n")
                continue
            ttl = int(ttl_str)

            algo = input("  algo        : ").strip()
            if algo not in ALGORITHMS:
                print(f"  ⚠ Algoritmo inválido. Opções: {list(ALGORITHMS.keys())}\n")
                continue

            result = run_search(network, node_id, resource_id, ttl, algo)
            print(f"\n[Busca: {algo.upper()} | nó={node_id} | recurso={resource_id} | TTL={ttl}]")
            print(result.summary())
            print()

        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Simulador de busca em redes P2P não estruturadas."
    )
    parser.add_argument("config", help="Arquivo de configuração (.yaml ou .json)")
    parser.add_argument("--info", action="store_true", help="Exibe resumo da rede e sai")
    parser.add_argument(
        "--search", nargs=4,
        metavar=("NODE_ID", "RESOURCE_ID", "TTL", "ALGO"),
        help="Executa uma busca direta: --search node_id resource_id ttl algo",
    )
    args = parser.parse_args()

    network = P2PNetwork()
    try:
        network.load_from_file(args.config)
        print(f"✔ Rede carregada com sucesso: {len(network.nodes)} nó(s).")
    except (ValueError, FileNotFoundError) as e:
        print(f"✘ {e}")
        sys.exit(1)

    if args.info:
        print(network.summary())
        sys.exit(0)

    if args.search:
        node_id, resource_id, ttl_str, algo = args.search
        if algo not in ALGORITHMS:
            print(f"✘ Algoritmo '{algo}' inválido. Opções: {list(ALGORITHMS.keys())}")
            sys.exit(1)
        if node_id not in network.nodes:
            print(f"✘ Nó '{node_id}' não existe.")
            sys.exit(1)
        ttl = int(ttl_str)
        result = run_search(network, node_id, resource_id, ttl, algo)
        print(f"\n[Busca: {algo.upper()} | nó={node_id} | recurso={resource_id} | TTL={ttl}]")
        print(result.summary())
        sys.exit(0)

    interactive_mode(network)


if __name__ == "__main__":
    main()
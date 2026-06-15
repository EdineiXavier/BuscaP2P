import sys
import os
import argparse
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network import P2PNetwork
from search import flooding, random_walk, informed_flooding, informed_random_walk

ALGORITMOS = {
    "flooding":             flooding,
    "random_walk":          random_walk,
    "informed_flooding":    informed_flooding,
    "informed_random_walk": informed_random_walk,
}

# -----------------------------------------------------------------------
# Paleta de cores
# -----------------------------------------------------------------------
COR_NO_NORMAL    = "#CBD5E1"
COR_NO_VISITADO  = "#60A5FA"
COR_NO_ENCONTROU = "#22C55E"
COR_NO_ORIGEM    = "#F59E0B"
COR_ARESTA       = "#94A3B8"
COR_ARESTA_ATIVA = "#2563EB"
COR_FUNDO        = "#F8FAFC"

# -----------------------------------------------------------------------
# Monta grafo NetworkX
# -----------------------------------------------------------------------

def montar_grafo(network: P2PNetwork):
    G = nx.Graph()
    for node_id in network.nodes:
        G.add_node(node_id)
    for node_id, node in network.nodes.items():
        for viz in node.neighbors:
            G.add_edge(node_id, viz)
    return G

# -----------------------------------------------------------------------
# Coleta passos do flooding — por CAMADA (paralelo real)
# -----------------------------------------------------------------------

def coletar_passos_flooding(network, start_id, resource_id, ttl, informada):
    passos     = []
    visitados  = {start_id}
    start_node = network.get_node(start_id)

    if start_node.has_resource(resource_id):
        passos.append((set([start_id]), [], True, start_id))
        return passos

    if informada:
        cached = start_node.get_cached_location(resource_id)
        if cached:
            passos.append(({start_id, cached}, [(start_id, cached)], True, cached))
            return passos

    camada_atual = [(viz, ttl - 1, start_id) for viz in start_node.neighbors]

    while camada_atual:
        proxima_camada = []
        arestas_camada = []
        encontrou      = False
        found_node     = None

        for current_id, current_ttl, pai in camada_atual:
            if current_id in visitados:
                continue

            visitados.add(current_id)
            arestas_camada.append((pai, current_id))
            node = network.get_node(current_id)

            if informada:
                cached = node.get_cached_location(resource_id)
                if cached:
                    passos.append((set(visitados) | {cached},
                                   arestas_camada + [(current_id, cached)],
                                   True, cached))
                    return passos

            if node.has_resource(resource_id):
                encontrou  = True
                found_node = current_id

            if current_ttl > 0:
                for viz in node.neighbors:
                    if viz not in visitados:
                        proxima_camada.append((viz, current_ttl - 1, current_id))

        passos.append((set(visitados), arestas_camada, encontrou, found_node))

        if encontrou:
            return passos

        camada_atual = proxima_camada

    return passos

# -----------------------------------------------------------------------
# Coleta passos do random walk (sequencial por natureza)
# -----------------------------------------------------------------------

def coletar_passos_random_walk(network, start_id, resource_id, ttl, informada):
    import random
    passos     = []
    current_id = start_id
    visitados  = {start_id}
    node       = network.get_node(current_id)

    if node.has_resource(resource_id):
        passos.append(({start_id}, [], True, start_id))
        return passos

    if informada:
        cached = node.get_cached_location(resource_id)
        if cached:
            passos.append(({start_id, cached}, [(start_id, cached)], True, cached))
            return passos

    for _ in range(ttl):
        node      = network.get_node(current_id)
        neighbors = node.neighbors
        if not neighbors:
            break

        if informada:
            cached = node.get_cached_location(resource_id)
            if cached:
                passos.append((set(visitados) | {cached},
                               [(current_id, cached)], True, cached))
                return passos

        next_id = random.choice(neighbors)
        visitados.add(next_id)
        passos.append((set(visitados), [(current_id, next_id)], False, None))

        if network.get_node(next_id).has_resource(resource_id):
            passos[-1] = (set(visitados), [(current_id, next_id)], True, next_id)
            return passos

        current_id = next_id

    return passos

# -----------------------------------------------------------------------
# Legenda
# -----------------------------------------------------------------------

def _legenda(ax, modo='rede'):
    itens = [
        mpatches.Patch(color=COR_NO_ORIGEM,   label="Nó origem"),
        mpatches.Patch(color=COR_NO_NORMAL,   label="Não visitado"),
    ]
    if modo == 'busca':
        itens += [
            mpatches.Patch(color=COR_NO_VISITADO,  label="Visitado"),
            mpatches.Patch(color=COR_NO_ENCONTROU, label="Recurso encontrado"),
        ]
    ax.legend(handles=itens, loc='lower left', fontsize=8,
              framealpha=0.8, edgecolor='#CBD5E1')

# -----------------------------------------------------------------------
# Desenho da rede
# -----------------------------------------------------------------------

def desenhar_rede_base(ax, G, pos, network, start_id=None,
                       nos_visitados=None, arestas_ativas=None,
                       encontrou=False, found_node=None, modo='rede'):
    ax.cla()
    ax.set_facecolor(COR_FUNDO)
    ax.axis('off')

    nos_visitados  = nos_visitados  or set()
    arestas_ativas = arestas_ativas or []

    cores_nos = []
    for nid in G.nodes():
        if nid == start_id:
            cores_nos.append(COR_NO_ORIGEM)
        elif encontrou and nid == found_node:
            cores_nos.append(COR_NO_ENCONTROU)
        elif nid in nos_visitados:
            cores_nos.append(COR_NO_VISITADO)
        else:
            cores_nos.append(COR_NO_NORMAL)

    cores_arestas, larguras = [], []
    for u, v in G.edges():
        if (u, v) in arestas_ativas or (v, u) in arestas_ativas:
            cores_arestas.append(COR_ARESTA_ATIVA)
            larguras.append(3.5)
        else:
            cores_arestas.append(COR_ARESTA)
            larguras.append(1.5)

    nx.draw_networkx_edges(G, pos, ax=ax,
                           edge_color=cores_arestas, width=larguras, alpha=0.8)
    nx.draw_networkx_nodes(G, pos, ax=ax,
                           node_color=cores_nos, node_size=950,
                           edgecolors="#334155", linewidths=1.8)
    nx.draw_networkx_labels(G, pos, ax=ax,
                            font_size=10, font_weight='bold', font_color="#1E293B")

    for nid, (x, y) in pos.items():
        recursos = ", ".join(sorted(network.nodes[nid].resources))
        ax.text(x, y - 0.13, recursos, ha='center', va='top',
                fontsize=7, color="#475569",
                bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6, ec='none'))

    _legenda(ax, modo=modo)

# -----------------------------------------------------------------------
# Separador visual no terminal
# -----------------------------------------------------------------------

def sep(char="-", n=56):
    print(char * n)

# -----------------------------------------------------------------------
# Modo interativo principal
# -----------------------------------------------------------------------

def modo_interativo(network: P2PNetwork, velocidade: float):
    G   = montar_grafo(network)
    pos = nx.spring_layout(G, seed=42, k=2.5)

    todos_nos      = sorted(network.nodes.keys())
    todos_recursos = sorted({r for node in network.nodes.values() for r in node.resources})

    plt.ion()
    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_facecolor(COR_FUNDO)

    status_ax = fig.add_axes([0.0, 0.0, 1.0, 0.07])
    status_ax.axis('off')
    status_ax.set_facecolor("#1E293B")
    status_text = status_ax.text(
        0.5, 0.5, "Digite os parâmetros no terminal para iniciar uma busca.",
        ha='center', va='center', fontsize=10, color='white',
        fontweight='bold', transform=status_ax.transAxes
    )

    def atualizar_status(msg):
        status_text.set_text(msg)
        fig.canvas.draw()
        fig.canvas.flush_events()

    desenhar_rede_base(ax, G, pos, network)
    ax.set_title("Rede P2P — aguardando busca", fontsize=12, fontweight='bold')
    fig.canvas.draw()
    plt.pause(0.1)

    print("\n" + "=" * 56)
    print("  Simulador de Busca P2P")
    print("=" * 56)
    print(f"  Nós disponíveis  : {', '.join(todos_nos)}")
    print(f"  Recursos na rede : {', '.join(todos_recursos)}")
    print(f"  Algoritmos       : {', '.join(ALGORITMOS.keys())}")
    print("  Digite 'sair' para encerrar.")
    sep()

    while True:
        try:
            print("\nNova busca:")
            node_id = input("  node_id     : ").strip()
            if node_id.lower() == "sair":
                break
            if node_id not in network.nodes:
                print(f"  ⚠ Nó '{node_id}' não existe. Tente: {todos_nos}")
                continue

            resource_id = input("  resource_id : ").strip()
            if resource_id not in todos_recursos:
                print(f"  ⚠ Recurso '{resource_id}' não existe. Tente: {todos_recursos}")
                continue

            ttl_str = input("  ttl         : ").strip()
            if not ttl_str.isdigit() or int(ttl_str) <= 0:
                print("  ⚠ TTL deve ser um número inteiro positivo.")
                continue
            ttl = int(ttl_str)

            algo = input("  algo        : ").strip()
            if algo not in ALGORITMOS:
                print(f"  ⚠ Algoritmo inválido. Opções: {list(ALGORITMOS.keys())}")
                continue

        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        # --- Coleta passos para animação ---
        informada = algo.startswith("informed_")
        if "flooding" in algo:
            passos     = coletar_passos_flooding(network, node_id, resource_id, ttl, informada)
            tipo_label = "paralelo por camada"
        else:
            passos     = coletar_passos_random_walk(network, node_id, resource_id, ttl, informada)
            tipo_label = "sequencial"

        # --- Roda também o algoritmo real para pegar o SearchResult completo ---
        fn     = ALGORITMOS[algo]
        result = fn(network, node_id, resource_id, ttl)

        atualizar_status(
            f"Iniciando: {algo} | origem={node_id} | recurso={resource_id} | TTL={ttl}"
        )

        # Estado inicial
        desenhar_rede_base(ax, G, pos, network, start_id=node_id, modo='busca')
        ax.set_title(
            f"Algoritmo: {algo.upper()}  |  Origem: {node_id}  |  "
            f"Recurso: {resource_id}  |  TTL: {ttl}\nEstado Inicial",
            fontsize=11, fontweight='bold'
        )
        fig.canvas.draw()
        plt.pause(velocidade * 1.5)

        # --- Animação ---
        nos_vis   = set()
        encontrou = False
        found_node = None
        for i, (nos_vis, arestas, encontrou, found_node) in enumerate(passos):
            desenhar_rede_base(ax, G, pos, network,
                               start_id=node_id,
                               nos_visitados=nos_vis,
                               arestas_ativas=arestas,
                               encontrou=encontrou,
                               found_node=found_node,
                               modo='busca')

            rodada_label = "Rodada" if "flooding" in algo else "Passo"
            ax.set_title(
                f"Algoritmo: {algo.upper()}  |  Origem: {node_id}  |  "
                f"Recurso: {resource_id}  |  TTL: {ttl}\n"
                f"{rodada_label} {i + 1}/{len(passos)}"
                + (f"  — {len(arestas)} mensagem(ns) simultânea(s)" if "flooding" in algo else ""),
                fontsize=11, fontweight='bold'
            )

            if encontrou:
                msg = (f"✔  ENCONTRADO em '{found_node}'  |  "
                       f"Msgs: {result.messages}  |  Nós visitados: {len(nos_vis)}")
            elif i == len(passos) - 1:
                msg = (f"✘  NÃO ENCONTRADO (TTL esgotado)  |  "
                       f"Msgs: {result.messages}  |  Nós visitados: {len(nos_vis)}")
            else:
                msg = (f"Propagando...  |  "
                       f"{rodada_label}: {i + 1}  |  Nós visitados: {len(nos_vis)}")

            atualizar_status(msg)
            plt.pause(velocidade)

            if encontrou:
                break

        # --- Resultado no terminal (igual ao main.py) ---
        sep()
        print(f"\n  [Busca: {algo.upper()} | nó={node_id} | recurso={resource_id} | TTL={ttl}]")
        print(result.summary())
        sep()

        plt.pause(1.5)
        desenhar_rede_base(ax, G, pos, network)
        ax.set_title("Rede P2P — aguardando próxima busca", fontsize=12, fontweight='bold')
        atualizar_status("Busca concluída. Digite os parâmetros no terminal para uma nova busca.")
        fig.canvas.draw()
        plt.pause(0.1)

    plt.ioff()
    plt.close()

# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Simulador visual de busca em redes P2P."
    )
    parser.add_argument("config", help="Arquivo de configuração (.yaml ou .json)")
    parser.add_argument("--velocidade", type=float, default=2.0,
                        help="Intervalo entre passos em segundos (padrão: 2.0)")
    args = parser.parse_args()

    network = P2PNetwork()
    try:
        network.load_from_file(args.config)
        print(f"✔ Rede carregada: {len(network.nodes)} nó(s).")
    except (ValueError, FileNotFoundError) as e:
        print(f"✘ {e}")
        sys.exit(1)

    modo_interativo(network, args.velocidade)


if __name__ == "__main__":
    main()
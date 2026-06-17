#!/usr/bin/env python3
"""
visualizar.py - Visualização interativa da busca em redes P2P

Uso:
    python src/visualizar.py configs/rede_pequena.yaml
    python src/visualizar.py configs/rede_media.yaml --velocidade 1.2
"""

import sys
import os
import argparse

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network import P2PNetwork
from search import (flooding, random_walk, informed_flooding,
                    informed_random_walk, SearchResult)

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
# Converte o histórico do SearchResult em passos visuais
#
# Cada passo visual é uma tupla:
#   (nos_visitados: set, arestas_ativas: list, encontrou: bool, found_node: str|None)
# -----------------------------------------------------------------------

def passos_do_historico(result: SearchResult, start_id: str):
    """
    Deriva os passos de animação diretamente do histórico do SearchResult,
    garantindo que a visualização seja 100% fiel ao que o algoritmo fez.
    """
    passos       = []
    nos_visitados = {start_id}

    for step in result.historico:
        arestas_ativas = []

        for msg in step.mensagens:
            # Extrai os nós da mensagem — formato: "nX -> nY" ou "nX <- nY (backtrack...)"
            if " -> " in msg:
                partes = msg.split(" -> ")
                origem = partes[0].strip()
                # pode ter sufixo "(cache hit!)" no último trecho
                destino = partes[-1].strip().split(" ")[0]
                nos_visitados.add(origem)
                nos_visitados.add(destino)
                arestas_ativas.append((origem, destino))
            elif " <- " in msg:
                # backtrack: "nX <- nY" significa voltou de nX para nY
                partes = msg.split(" <- ")
                origem  = partes[0].strip()
                destino = partes[1].strip().split(" ")[0]
                nos_visitados.add(origem)
                nos_visitados.add(destino)
                arestas_ativas.append((origem, destino))

        passos.append((
            set(nos_visitados),
            arestas_ativas,
            step.encontrou,
            step.found_at
        ))

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

        # --- Roda o algoritmo UMA única vez ---
        fn     = ALGORITMOS[algo]
        result = fn(network, node_id, resource_id, ttl)

        # --- Deriva os passos visuais do histórico real ---
        passos     = passos_do_historico(result, node_id)
        is_flooding = "flooding" in algo
        tipo_label  = "paralelo por camada" if is_flooding else "sequencial"

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

        # --- Animação passo a passo ---
        nos_vis    = set()
        encontrou  = False
        found_node = None

        for i, (nos_vis, arestas, encontrou, found_node) in enumerate(passos):
            desenhar_rede_base(ax, G, pos, network,
                               start_id=node_id,
                               nos_visitados=nos_vis,
                               arestas_ativas=arestas,
                               encontrou=encontrou,
                               found_node=found_node,
                               modo='busca')

            rodada_label = "Rodada" if is_flooding else "Passo"
            step         = result.historico[i]
            msg_titulo   = " | ".join(step.mensagens)

            ax.set_title(
                f"Algoritmo: {algo.upper()}  |  Origem: {node_id}  |  "
                f"Recurso: {resource_id}  |  TTL: {ttl}\n"
                f"{rodada_label} {i + 1}/{len(passos)} — {msg_titulo}",
                fontsize=10, fontweight='bold'
            )

            ja_encontrou = result.found and encontrou

            if ja_encontrou and "propagação paralela" not in " ".join(result.historico[i].mensagens):
                msg = (f"✔  ENCONTRADO em '{found_node}'  |  "
                       f"Propagação paralela em andamento...  |  Nós visitados: {len(nos_vis)}")
            elif i == len(passos) - 1:
                status_final = f"✔  ENCONTRADO em '{result.found_at}'" if result.found else "✘  NÃO ENCONTRADO"
                msg = (f"{status_final}  |  "
                       f"Msgs: {result.messages}  |  Nós visitados: {len(nos_vis)}")
            elif encontrou:
                msg = (f"✔  ENCONTRADO em '{found_node}'  |  "
                       f"Outros nós ainda propagando...  |  Nós visitados: {len(nos_vis)}")
            else:
                msg = (f"Propagando...  |  "
                       f"{rodada_label}: {i + 1}  |  Nós visitados: {len(nos_vis)}")

            atualizar_status(msg)
            plt.pause(velocidade)
            # Não para ao encontrar — continua mostrando propagação paralela

        # --- Resultado no terminal ---
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
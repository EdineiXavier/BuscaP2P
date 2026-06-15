#!/usr/bin/env python3
"""
graficos.py - Gera gráficos comparativos dos algoritmos de busca P2P

Uso:
    python tests/graficos.py

Gráficos gerados em tests/graficos/:
    1. barras_mensagens_por_rede.png
    2. linhas_efeito_ttl.png
    3. barras_efeito_cache.png
    4. linhas_escalabilidade.png
    5. linhas_taxa_sucesso.png
"""

import sys
import os
import random
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from network import P2PNetwork
from search import flooding, random_walk, informed_flooding, informed_random_walk

# -----------------------------------------------------------------------
# Configurações gerais
# -----------------------------------------------------------------------

BASE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'graficos')
REPETICOES = 30
random.seed(42)

os.makedirs(OUT_DIR, exist_ok=True)

ALGORITMOS = {
    "flooding":        flooding,
    "random_walk":     random_walk,
    "inf_flooding":    informed_flooding,
    "inf_random_walk": informed_random_walk,
}

REDES = {
    "Pequena\n(6 nós)":  ("configs/rede_pequena.yaml", "n1", "r9",  10),
    "Média\n(12 nós)":   ("configs/rede_media.yaml",   "n1", "r20", 10),
    "Grande\n(20 nós)":  ("configs/rede_grande.yaml",  "n1", "r30", 15),
}

# Paleta de cores consistente
CORES = {
    "flooding":        "#2563EB",   # azul
    "random_walk":     "#F59E0B",   # amarelo
    "inf_flooding":    "#10B981",   # verde
    "inf_random_walk": "#EF4444",   # vermelho
}

LABELS = {
    "flooding":        "Flooding",
    "random_walk":     "Random Walk",
    "inf_flooding":    "Inf. Flooding",
    "inf_random_walk": "Inf. Random Walk",
}

ESTILO = {
    "flooding":        "-o",
    "random_walk":     "--s",
    "inf_flooding":    "-^",
    "inf_random_walk": "--D",
}

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def carregar_rede(caminho: str) -> P2PNetwork:
    net = P2PNetwork()
    net.load_from_file(os.path.join(BASE_DIR, caminho))
    return net

def rodar_media(fn, caminho, node_id, resource_id, ttl):
    msgs, found = [], 0
    for _ in range(REPETICOES):
        net = carregar_rede(caminho)
        r = fn(net, node_id, resource_id, ttl)
        msgs.append(r.messages)
        if r.found:
            found += 1
    return sum(msgs) / REPETICOES, (found / REPETICOES) * 100

def estilo_grafico(ax, titulo, xlabel, ylabel):
    ax.set_title(titulo, fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    ax.legend(fontsize=9, framealpha=0.7)

# -----------------------------------------------------------------------
# Gráfico 1 — Barras agrupadas: mensagens por algoritmo e por rede
# -----------------------------------------------------------------------

def grafico1():
    print("  Gerando gráfico 1 — Mensagens por algoritmo e rede...")

    nomes_redes = list(REDES.keys())
    nomes_algos = list(ALGORITMOS.keys())
    n_redes     = len(nomes_redes)
    n_algos     = len(nomes_algos)

    dados = {a: [] for a in nomes_algos}

    for nome_rede, (caminho, node, recurso, ttl) in REDES.items():
        for nome_algo, fn in ALGORITMOS.items():
            if "random" in nome_algo:
                media, _ = rodar_media(fn, caminho, node, recurso, ttl)
                dados[nome_algo].append(media)
            else:
                net = carregar_rede(caminho)
                r = fn(net, node, recurso, ttl)
                dados[nome_algo].append(r.messages)

    fig, ax = plt.subplots(figsize=(10, 6))
    x       = np.arange(n_redes)
    largura = 0.18
    offsets = np.linspace(-(n_algos - 1) / 2, (n_algos - 1) / 2, n_algos) * largura

    for i, nome_algo in enumerate(nomes_algos):
        bars = ax.bar(
            x + offsets[i], dados[nome_algo], largura,
            label=LABELS[nome_algo],
            color=CORES[nome_algo], alpha=0.85, edgecolor='white', linewidth=0.8
        )
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                    f"{h:.1f}", ha='center', va='bottom', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(nomes_redes, fontsize=10)
    estilo_grafico(ax,
        "Mensagens Trocadas por Algoritmo e Tamanho de Rede",
        "Topologia da Rede", "Nº de Mensagens")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "1_barras_mensagens_por_rede.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"    Salvo: {path}")

# -----------------------------------------------------------------------
# Gráfico 2 — Linhas: efeito do TTL nas mensagens
# -----------------------------------------------------------------------

def grafico2():
    print("  Gerando gráfico 2 — Efeito do TTL...")

    ttls    = [2, 4, 6, 8, 10, 15]
    configs = [
        ("Pequena (6 nós)",  "configs/rede_pequena.yaml", "n1", "r9"),
        ("Média (12 nós)",   "configs/rede_media.yaml",   "n1", "r20"),
        ("Grande (20 nós)",  "configs/rede_grande.yaml",  "n1", "r30"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)

    for ax, (nome_rede, caminho, node, recurso) in zip(axes, configs):
        for nome_algo, fn in ALGORITMOS.items():
            msgs = []
            for ttl in ttls:
                if "random" in nome_algo:
                    media, _ = rodar_media(fn, caminho, node, recurso, ttl)
                    msgs.append(media)
                else:
                    net = carregar_rede(caminho)
                    r = fn(net, node, recurso, ttl)
                    msgs.append(r.messages)

            ax.plot(ttls, msgs, ESTILO[nome_algo],
                    color=CORES[nome_algo], label=LABELS[nome_algo],
                    linewidth=2, markersize=6)

        estilo_grafico(ax, nome_rede, "TTL", "Nº de Mensagens")

    fig.suptitle("Efeito do TTL no Número de Mensagens Trocadas",
                 fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "2_linhas_efeito_ttl.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"    Salvo: {path}")

# -----------------------------------------------------------------------
# Gráfico 3 — Barras duplas: efeito do cache (1ª vs 2ª busca)
# -----------------------------------------------------------------------

def grafico3():
    print("  Gerando gráfico 3 — Efeito do Cache...")

    configs = [
        ("Pequena\n(6 nós)",  "configs/rede_pequena.yaml", "n1", "r9",  10),
        ("Média\n(12 nós)",   "configs/rede_media.yaml",   "n1", "r20", 10),
        ("Grande\n(20 nós)",  "configs/rede_grande.yaml",  "n1", "r30", 15),
    ]

    pares = [
        ("Flooding",     flooding,    informed_flooding,    "flooding"),
        ("Random Walk",  random_walk, informed_random_walk, "random_walk"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))

    for ax, (nome_par, fn_base, fn_inf, chave) in zip(axes, pares):
        nomes_redes = [c[0] for c in configs]
        msgs_1a     = []
        msgs_2a     = []

        for _, caminho, node, recurso, ttl in configs:
            # 1ª busca
            if "random" in chave:
                for _ in range(50):
                    net = carregar_rede(caminho)
                    r1 = fn_base(net, node, recurso, ttl)
                    if r1.found:
                        break
            else:
                net = carregar_rede(caminho)
                r1 = fn_base(net, node, recurso, ttl)

            # 2ª busca (usa cache populado)
            r2 = fn_inf(net, node, recurso, ttl)
            msgs_1a.append(r1.messages)
            msgs_2a.append(r2.messages)

        x       = np.arange(len(nomes_redes))
        largura = 0.32

        b1 = ax.bar(x - largura / 2, msgs_1a, largura,
                    label="1ª Busca (sem cache)", color="#94A3B8", alpha=0.9, edgecolor='white')
        b2 = ax.bar(x + largura / 2, msgs_2a, largura,
                    label="2ª Busca (com cache)", color=CORES[chave], alpha=0.9, edgecolor='white')

        for bar in list(b1) + list(b2):
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.2,
                    str(int(h)), ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Anotação de redução
        for i, (m1, m2) in enumerate(zip(msgs_1a, msgs_2a)):
            reducao = int((m1 - m2) / m1 * 100)
            ax.annotate(f"-{reducao}%",
                        xy=(x[i], max(m1, m2) + 1.5),
                        ha='center', fontsize=9, color='#1E293B', fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(nomes_redes, fontsize=10)
        estilo_grafico(ax, f"{nome_par}: 1ª vs 2ª Busca",
                       "Topologia da Rede", "Nº de Mensagens")

    fig.suptitle("Impacto do Cache nas Buscas Informadas",
                 fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "3_barras_efeito_cache.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"    Salvo: {path}")

# -----------------------------------------------------------------------
# Gráfico 4 — Linhas: escalabilidade (mensagens vs tamanho da rede)
# -----------------------------------------------------------------------

def grafico4():
    print("  Gerando gráfico 4 — Escalabilidade...")

    tamanhos   = [6, 12, 20]
    configs    = [
        ("configs/rede_pequena.yaml", "n1", "r9",  15),
        ("configs/rede_media.yaml",   "n1", "r20", 15),
        ("configs/rede_grande.yaml",  "n1", "r30", 15),
    ]

    fig, ax = plt.subplots(figsize=(9, 6))

    for nome_algo, fn in ALGORITMOS.items():
        msgs = []
        for caminho, node, recurso, ttl in configs:
            if "random" in nome_algo:
                media, _ = rodar_media(fn, caminho, node, recurso, ttl)
                msgs.append(media)
            else:
                net = carregar_rede(caminho)
                r = fn(net, node, recurso, ttl)
                msgs.append(r.messages)

        ax.plot(tamanhos, msgs, ESTILO[nome_algo],
                color=CORES[nome_algo], label=LABELS[nome_algo],
                linewidth=2.5, markersize=8)

        # Anotação no último ponto
        ax.annotate(f"{msgs[-1]:.1f}",
                    xy=(tamanhos[-1], msgs[-1]),
                    xytext=(8, 0), textcoords='offset points',
                    fontsize=9, color=CORES[nome_algo], fontweight='bold')

    ax.set_xticks(tamanhos)
    ax.set_xticklabels(["6 nós", "12 nós", "20 nós"])
    estilo_grafico(ax,
        "Escalabilidade: Mensagens vs Tamanho da Rede (TTL=15)",
        "Tamanho da Rede (nº de nós)", "Nº de Mensagens")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "4_linhas_escalabilidade.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"    Salvo: {path}")

# -----------------------------------------------------------------------
# Gráfico 5 — Linhas: taxa de sucesso do random_walk por TTL
# -----------------------------------------------------------------------

def grafico5():
    print("  Gerando gráfico 5 — Taxa de sucesso do Random Walk...")

    ttls    = [2, 4, 6, 8, 10, 15, 20]
    configs = [
        ("Pequena (6 nós)",  "configs/rede_pequena.yaml", "n1", "r9"),
        ("Média (12 nós)",   "configs/rede_media.yaml",   "n1", "r20"),
        ("Grande (20 nós)",  "configs/rede_grande.yaml",  "n1", "r30"),
    ]

    pares_random = {
        "random_walk":     (random_walk,     "--s", "#F59E0B"),
        "inf_random_walk": (informed_random_walk, "-D",  "#EF4444"),
    }

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for ax, (nome_rede, caminho, node, recurso) in zip(axes, configs):
        for nome_algo, (fn, estilo, cor) in pares_random.items():
            taxas = []
            for ttl in ttls:
                _, taxa = rodar_media(fn, caminho, node, recurso, ttl)
                taxas.append(taxa)

            ax.plot(ttls, taxas, estilo, color=cor,
                    label=LABELS[nome_algo], linewidth=2, markersize=6)

        ax.axhline(100, color='gray', linestyle=':', linewidth=1, alpha=0.6)
        ax.set_ylim(0, 110)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
        estilo_grafico(ax, nome_rede, "TTL", "Taxa de Sucesso (%)")

    fig.suptitle("Taxa de Sucesso do Random Walk por TTL",
                 fontsize=14, fontweight='bold', y=1.02)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "5_linhas_taxa_sucesso.png")
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"    Salvo: {path}")

# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  Gerando gráficos comparativos...")
    print("=" * 60)

    grafico1()
    grafico2()
    grafico3()
    grafico4()
    grafico5()

    print("=" * 60)
    print(f"  Todos os gráficos salvos em: tests/graficos/")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
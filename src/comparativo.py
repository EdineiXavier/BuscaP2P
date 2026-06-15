#!/usr/bin/env python3
"""
comparativo.py - Testes comparativos entre os algoritmos de busca P2P

Roda múltiplos cenários em diferentes topologias e exibe tabelas comparativas.

Uso:
    python tests/comparativo.py
"""

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from network import P2PNetwork
from search import flooding, random_walk, informed_flooding, informed_random_walk

# -----------------------------------------------------------------------
# Configurações
# -----------------------------------------------------------------------

ALGORITMOS = {
    "flooding":         flooding,
    "random_walk":      random_walk,
    "inf_flooding":     informed_flooding,
    "inf_random_walk":  informed_random_walk,
}

REDES = {
    "Pequena (6n)":  "configs/rede_pequena.yaml",
    "Media  (12n)":  "configs/rede_media.yaml",
    "Grande (20n)":  "configs/rede_grande.yaml",
}

# Repetições para algoritmos probabilísticos
REPETICOES = 30

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

def carregar_rede(caminho: str) -> P2PNetwork:
    net = P2PNetwork()
    net.load_from_file(os.path.join(BASE_DIR, caminho))
    return net

def sep(char="=", n=80):
    print(char * n)

def titulo(txt):
    sep()
    print(f"  {txt}")
    sep()

def cab(colunas):
    print("  " + "".join(n.center(l) for n, l in colunas))
    print("  " + "-" * sum(l for _, l in colunas))

def lin(valores):
    print("  " + "".join(str(v).center(l) for v, l in valores))

def rodar(fn, net, node_id, resource_id, ttl):
    return fn(net, node_id, resource_id, ttl)

def rodar_media(fn, caminho, node_id, resource_id, ttl, n=REPETICOES):
    """Roda n vezes e retorna (média_msgs, taxa_sucesso%)."""
    msgs, found = [], 0
    for _ in range(n):
        net = carregar_rede(caminho)
        r = fn(net, node_id, resource_id, ttl)
        msgs.append(r.messages)
        if r.found:
            found += 1
    return sum(msgs) / n, (found / n) * 100

# -----------------------------------------------------------------------
# Cenário 1: Comparação direta — todos os algoritmos, mesma busca
# -----------------------------------------------------------------------

def cenario1(nome_rede, caminho, node_id, resource_id, ttl):
    titulo(f"CENÁRIO 1 — Comparação Direta | {nome_rede}")
    print(f"  nó origem={node_id}  |  recurso={resource_id}  |  TTL={ttl}")
    print(f"  (random_walk: média de {REPETICOES} execuções)\n")

    cols = [("Algoritmo", 20), ("Encontrado?", 13), ("Msgs", 8),
            ("Nós Visit.", 12), ("Cache Hit?", 12)]
    cab(cols)

    for nome, fn in ALGORITMOS.items():
        is_random = "random" in nome
        if is_random:
            media_msgs, taxa = rodar_media(fn, caminho, node_id, resource_id, ttl)
            found_str = f"SIM ({taxa:.0f}%)"
            msgs_str  = f"{media_msgs:.1f}"
            # Para nós visitados, roda uma vez
            net = carregar_rede(caminho)
            r = rodar(fn, net, node_id, resource_id, ttl)
            nos_str = str(len(r.nodes_visited))
            cache_str = "NÃO"
        else:
            net = carregar_rede(caminho)
            r = rodar(fn, net, node_id, resource_id, ttl)
            found_str = "SIM" if r.found else "NÃO"
            msgs_str  = str(r.messages)
            nos_str   = str(len(r.nodes_visited))
            cache_str = "SIM" if r.cache_hit else "NÃO"

        lin([(nome, 20), (found_str, 13), (msgs_str, 8), (nos_str, 12), (cache_str, 12)])
    print()

# -----------------------------------------------------------------------
# Cenário 2: Efeito do TTL
# -----------------------------------------------------------------------

def cenario2(nome_rede, caminho, node_id, resource_id):
    titulo(f"CENÁRIO 2 — Efeito do TTL | {nome_rede}")
    print(f"  nó origem={node_id}  |  recurso={resource_id}")
    print(f"  valores = mensagens trocadas  |  * = não encontrado em todas execuções\n")

    ttls = [2, 4, 6, 8, 10, 15]
    cols = [("TTL", 5)] + [(n, 17) for n in ALGORITMOS]
    cab(cols)

    for ttl in ttls:
        vals = [(str(ttl), 5)]
        for nome, fn in ALGORITMOS.items():
            if "random" in nome:
                media, taxa = rodar_media(fn, caminho, node_id, resource_id, ttl)
                sufixo = "" if taxa == 100 else f" ({taxa:.0f}%ok)"
                val = f"{media:.1f}{sufixo}"
            else:
                net = carregar_rede(caminho)
                r = rodar(fn, net, node_id, resource_id, ttl)
                val = str(r.messages) if r.found else f"{r.messages}*"
            vals.append((val, 17))
        lin(vals)
    print()

# -----------------------------------------------------------------------
# Cenário 3: Efeito do Cache (1ª vs 2ª busca)
# -----------------------------------------------------------------------

def cenario3(nome_rede, caminho, node_id, resource_id, ttl):
    titulo(f"CENÁRIO 3 — Efeito do Cache | {nome_rede}")
    print(f"  nó origem={node_id}  |  recurso={resource_id}  |  TTL={ttl}")
    print(f"  1ª busca com algoritmo base popula o cache; 2ª busca usa algoritmo informado\n")

    pares = [
        ("flooding",    "inf_flooding",    flooding,    informed_flooding),
        ("random_walk", "inf_random_walk", random_walk, informed_random_walk),
    ]

    cols = [("Par (base -> informado)", 32), ("1ª Busca", 10),
            ("2ª Busca", 10), ("Redução", 10), ("Cache Hit?", 12)]
    cab(cols)

    for nome_b, nome_i, fn_b, fn_i in pares:
        # 1ª busca — popula cache
        net = carregar_rede(caminho)
        if "random" in nome_b:
            # Garante que a 1ª busca encontre para popular o cache
            r1_found = None
            for _ in range(50):
                net = carregar_rede(caminho)
                r1_found = fn_b(net, node_id, resource_id, ttl)
                if r1_found.found:
                    break
            r1 = r1_found
        else:
            r1 = fn_b(net, node_id, resource_id, ttl)

        # 2ª busca — usa cache
        r2 = fn_i(net, node_id, resource_id, ttl)

        reducao = f"{(r1.messages - r2.messages) / r1.messages * 100:.0f}%" if r1.messages else "N/A"
        par = f"{nome_b} -> {nome_i}"
        lin([(par, 32), (r1.messages, 10), (r2.messages, 10),
             (reducao, 10), ("SIM" if r2.cache_hit else "NÃO", 12)])
    print()

# -----------------------------------------------------------------------
# Cenário 4: Escalabilidade — mesmo algo, redes diferentes
# -----------------------------------------------------------------------

def cenario4(recursos_por_rede, ttl):
    titulo("CENÁRIO 4 — Escalabilidade (mesmo algoritmo, redes diferentes)")
    print(f"  TTL={ttl}  |  busca de n1 pelo recurso mais distante de cada rede\n")

    cols = [("Algoritmo", 18)] + [(nome, 16) for nome in REDES]
    cab(cols)

    for nome_algo, fn in ALGORITMOS.items():
        vals = [(nome_algo, 18)]
        for nome_rede, caminho in REDES.items():
            resource_id = recursos_por_rede[nome_rede]
            if "random" in nome_algo:
                media, taxa = rodar_media(fn, caminho, "n1", resource_id, ttl)
                sufixo = "" if taxa >= 90 else f"({taxa:.0f}%)"
                val = f"{media:.1f} {sufixo}"
            else:
                net = carregar_rede(caminho)
                r = rodar(fn, net, "n1", resource_id, ttl)
                val = str(r.messages) if r.found else f"{r.messages}*"
            vals.append((val, 16))
        lin(vals)

    print(f"\n  random_walk = média de {REPETICOES} execuções\n")

# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    random.seed(42)
    print()
    titulo("TESTES COMPARATIVOS — Algoritmos de Busca em Redes P2P")
    print()

    configs = [
        ("Pequena (6n)",  "configs/rede_pequena.yaml", "n1", "r9",  10),
        ("Media  (12n)",  "configs/rede_media.yaml",   "n1", "r20", 10),
        ("Grande (20n)",  "configs/rede_grande.yaml",  "n1", "r30", 15),
    ]

    for nome, caminho, node, recurso, ttl in configs:
        cenario1(nome, caminho, node, recurso, ttl)
        cenario2(nome, caminho, node, recurso)
        cenario3(nome, caminho, node, recurso, ttl)

    cenario4(
        recursos_por_rede={
            "Pequena (6n)": "r9",
            "Media  (12n)": "r20",
            "Grande (20n)": "r30",
        },
        ttl=15
    )

    sep()
    print("  Testes concluídos.")
    sep()
    print()

if __name__ == "__main__":
    main()
import sys
import os
import matplotlib.pyplot as plt
import networkx as nx

TOTAL_BOTS = 40
VALID = {0: 0, 4: 10, 10: 25, 20: 50}   # nº infiltrados -> %
OUTPUT_DIR = "results/figures"

# Nivel de infiltración (nº de nodos) como argumento; por defecto 10
if len(sys.argv) > 1:
    INFILTRATED = int(sys.argv[1])
else:
    INFILTRATED = 10

if INFILTRATED not in VALID:
    print(f"Valor de infiltrados no válido: {INFILTRATED}. Usa 0, 4, 10 o 20.")
    sys.exit(1)

RATIO = VALID[INFILTRATED]


def build_graph():
    G = nx.Graph()

    c2 = "C2"
    G.add_node(c2, role="c2")

    infiltrated_nodes = [f"B{i}" for i in range(1, INFILTRATED + 1)]
    normal_nodes = [f"B{i}" for i in range(INFILTRATED + 1, TOTAL_BOTS + 1)]

    for node in normal_nodes:
        G.add_node(node, role="normal")
        G.add_edge(c2, node)

    for node in infiltrated_nodes:
        G.add_node(node, role="infiltrated")
        G.add_edge(c2, node)

    return G, c2, normal_nodes, infiltrated_nodes


def draw_graph():
    G, c2, normal_nodes, infiltrated_nodes = build_graph()

    pos = {}
    pos[c2] = (0, 0)

    normal_pos = nx.circular_layout(normal_nodes, scale=2.8)
    infil_pos = nx.circular_layout(infiltrated_nodes, scale=4.0) if infiltrated_nodes else {}

    for node, p in normal_pos.items():
        pos[node] = p

    for idx, node in enumerate(infiltrated_nodes):
        p = infil_pos[node]
        pos[node] = (p[0] * 1.15, p[1] * 1.15)

    plt.figure(figsize=(10, 10))

    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.6)

    nx.draw_networkx_nodes(G, pos, nodelist=[c2], node_size=2200)
    nx.draw_networkx_nodes(G, pos, nodelist=normal_nodes, node_size=900)

    if infiltrated_nodes:
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=infiltrated_nodes,
            node_size=1100,
            node_shape="s"
        )

    labels = {node: node for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

    plt.title(f"Topología centralizada ({TOTAL_BOTS} bots, {INFILTRATED} infiltrados, {RATIO}%)")
    plt.axis("off")
    plt.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, f"topologia_centralizada_inf{INFILTRATED}.png")
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] Imagen guardada en: {out}")


if __name__ == "__main__":
    draw_graph()

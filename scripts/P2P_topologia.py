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

    infiltrated_nodes = [f"B{i}" for i in range(1, INFILTRATED + 1)]
    normal_nodes = [f"B{i}" for i in range(INFILTRATED + 1, TOTAL_BOTS + 1)]
    all_nodes = [f"B{i}" for i in range(1, TOTAL_BOTS + 1)]

    for node in all_nodes:
        role = "infiltrated" if node in infiltrated_nodes else "normal"
        G.add_node(node, role=role)

    # Patrón de vecindad coherente con el experimento: i+1, i+2, i+3
    for i in range(TOTAL_BOTS):
        current_node = all_nodes[i]
        n1 = all_nodes[(i + 1) % TOTAL_BOTS]
        n2 = all_nodes[(i + 2) % TOTAL_BOTS]
        n3 = all_nodes[(i + 3) % TOTAL_BOTS]

        G.add_edge(current_node, n1)
        G.add_edge(current_node, n2)
        G.add_edge(current_node, n3)

    return G, normal_nodes, infiltrated_nodes, all_nodes


def draw_graph():
    G, normal_nodes, infiltrated_nodes, all_nodes = build_graph()

    pos = nx.circular_layout(all_nodes, scale=3.2)

    plt.figure(figsize=(11, 11))

    nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.45)

    nx.draw_networkx_nodes(G, pos, nodelist=normal_nodes, node_size=850)

    if infiltrated_nodes:
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=infiltrated_nodes,
            node_size=1050,
            node_shape="s"
        )

    labels = {node: node for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

    plt.title(f"Topología P2P ({TOTAL_BOTS} bots, {INFILTRATED} infiltrados, {RATIO}%)")
    plt.axis("off")
    plt.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, f"topologia_p2p_inf{INFILTRATED}.png")
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] Imagen guardada en: {out}")


if __name__ == "__main__":
    draw_graph()

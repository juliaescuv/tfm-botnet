import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import defaultdict
import statistics as st
os.makedirs("results/figures", exist_ok=True)

rows = [r for r in csv.DictReader(open("results/csv/metrics_summary.csv")) if r["status"]=="ok"]
def num(x):
    try: return float(x)
    except: return None

g = defaultdict(list)
for r in rows:
    g[(r["architecture"], int(r["infiltration_ratio"]))].append(r)

levels = [0,10,25,50]
def series(arch, metric):
    means, sds, pts = [], [], []
    for lv in levels:
        vals = [num(r[metric]) for r in g[(arch,lv)] if num(r[metric]) is not None]
        means.append(st.mean(vals))
        sds.append(st.pstdev(vals) if len(vals)>1 else 0)
        pts.append(vals)
    return means, sds, pts

COL = {"centralized":"#185FA5", "p2p":"#D85A30"}
LAB = {"centralized":"Centralizada", "p2p":"P2P"}

def plot_metric(metric, ylabel, title, fname, logy=False):
    plt.figure(figsize=(8,5))
    for arch in ["centralized","p2p"]:
        means, sds, pts = series(arch, metric)
        plt.errorbar(levels, means, yerr=sds, marker="o", capsize=4,
                     color=COL[arch], label=LAB[arch], linewidth=2, zorder=3)
        for i, lv in enumerate(levels):
            plt.scatter([lv]*len(pts[i]), pts[i], color=COL[arch],
                        alpha=0.35, s=25, zorder=2)
    plt.xlabel("Porcentaje de infiltración (%)")
    plt.ylabel(ylabel)
    plt.title(title)
    if logy: plt.yscale("log")
    plt.xticks(levels)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.figtext(0.99, 0.01, "n=3 por nivel", ha="right", fontsize=8, style="italic")
    plt.tight_layout()
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  generada: {fname}")

print("Generando figuras...")
plot_metric("latency_ms", "Latencia media (ms)", "Latencia vs infiltración", "fig_latencia.png")
plot_metric("throughput_mbps", "Throughput (Mbps)", "Throughput vs infiltración", "fig_throughput.png")
plot_metric("stability_cv", "Estabilidad (CV)", "Estabilidad (coef. variación) vs infiltración", "fig_estabilidad.png")
plot_metric("bytes_per_second", "Bytes por segundo", "Volumen de tráfico vs infiltración", "fig_volumen.png", logy=True)
print("OK")

# ---- Gráfica de BARRAS: bytes/s por arquitectura y nivel ----
import numpy as np
def plot_barras_bytes():
    plt.figure(figsize=(8,5))
    x = np.arange(len(levels))
    w = 0.35
    for j, arch in enumerate(["centralized","p2p"]):
        means, sds, pts = series(arch, "bytes_per_second")
        plt.bar(x + (j-0.5)*w, means, w, yerr=sds, capsize=4,
                color=COL[arch], label=LAB[arch], alpha=0.85)
    plt.xlabel("Porcentaje de infiltración (%)")
    plt.ylabel("Bytes por segundo (media)")
    plt.title("Tasa de bytes por segundo por arquitectura y nivel")
    plt.yscale("log")
    plt.xticks(x, [str(l) for l in levels])
    plt.legend()
    plt.grid(True, axis="y", alpha=0.3)
    plt.figtext(0.99, 0.01, "n=3 por nivel", ha="right", fontsize=8, style="italic")
    plt.tight_layout()
    plt.savefig("results/figures/fig_barras_bytes.png", dpi=150)
    plt.close()
    print("  generada: fig_barras_bytes.png")

# ---- Flujos únicos vs infiltración (líneas planas) ----
def plot_flujos():
    plt.figure(figsize=(8,5))
    for arch in ["centralized","p2p"]:
        means, sds, pts = series(arch, "unique_flows")
        plt.plot(levels, means, marker="s", color=COL[arch], label=LAB[arch], linewidth=2)
    plt.xlabel("Porcentaje de infiltración (%)")
    plt.ylabel("Flujos únicos observados")
    plt.title("Flujos únicos frente al porcentaje de infiltración")
    plt.xticks(levels)
    plt.ylim(0, 90)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.figtext(0.99, 0.01, "n=3 por nivel", ha="right", fontsize=8, style="italic")
    plt.tight_layout()
    plt.savefig("results/figures/fig_flujos.png", dpi=150)
    plt.close()
    print("  generada: fig_flujos.png")

plot_barras_bytes()
plot_flujos()

# ---- Gráfica estilo entrega 3: agrupada por ARQUITECTURA, una barra por nivel ----
def plot_barras_por_arquitectura(logy=False, suffix=""):
    plt.figure(figsize=(9,5.5))
    archs = ["centralized","p2p"]
    x = np.arange(len(archs))
    w = 0.2
    nivel_col = {0:"#1f77b4", 10:"#ff7f0e", 25:"#2ca02c", 50:"#d62728"}
    for k, lv in enumerate(levels):
        medias, sds = [], []
        for arch in archs:
            vals = [num(r["bytes_per_second"]) for r in g[(arch,lv)] if num(r["bytes_per_second"]) is not None]
            medias.append(st.mean(vals))
            sds.append(st.pstdev(vals) if len(vals)>1 else 0)
        plt.bar(x + (k-1.5)*w, medias, w, yerr=sds, capsize=3,
                color=nivel_col[lv], label=f"{lv}%")
    plt.xlabel("Arquitectura")
    plt.ylabel("Bytes por segundo (media)")
    plt.title("Tasa de bytes por segundo por arquitectura y nivel de infiltración")
    plt.xticks(x, ["centralizada","p2p"])
    if logy:
        plt.yscale("log")
    plt.legend(title="Infiltración")
    plt.grid(True, axis="y", alpha=0.3)
    plt.figtext(0.99, 0.01, "Barras de error = ±1 desviación estándar (n=3 por nivel)",
                ha="right", fontsize=8, style="italic")
    plt.tight_layout()
    fname = f"fig_bytes_por_arquitectura{suffix}.png"
    plt.savefig(fname, dpi=150)
    plt.close()
    print(f"  generada: {fname}")

plot_barras_por_arquitectura(logy=False, suffix="_lineal")
plot_barras_por_arquitectura(logy=True, suffix="_log")

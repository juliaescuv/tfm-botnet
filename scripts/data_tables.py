"""
Genera las dos tablas de resultados a partir de results/csv/metrics_summary.csv:
  - results/csv/tabla1_resumen.csv  : media +/- desviacion estandar por arquitectura y nivel.
  - results/csv/tabla2_detalle.csv  : las 24 ejecuciones individuales (las 5 metricas + volumen).
Marca con (*) las ejecuciones P2P en las que el punto de captura no observo el flood
(volumen de tipo baseline pese a haber infiltrados).

Uso:
    python3 scripts/generar_tablas.py
"""
import csv
import os
import statistics as st
from collections import defaultdict

INPUT = "results/csv/metrics_summary.csv"
OUT1 = "results/csv/tabla1_resumen.csv"
OUT2 = "results/csv/tabla2_detalle.csv"

LEVELS = [0, 10, 25, 50]
ARCHS = ["centralized", "p2p"]
ARCH_LABEL = {"centralized": "Centralizada", "p2p": "P2P"}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fmt(x, dec=2):
    """Formatea con separador de millar (espacio) y 'dec' decimales."""
    if x is None:
        return ""
    s = f"{x:,.{dec}f}".replace(",", " ")
    return s


def load_rows():
    if not os.path.exists(INPUT):
        raise SystemExit(f"No se encuentra {INPUT}. Ejecuta antes extract_metrics.py.")
    return [r for r in csv.DictReader(open(INPUT, encoding="utf-8")) if r.get("status") == "ok"]


def is_anomala(r):
    """
    Ejecucion P2P con infiltrados pero volumen de tipo baseline:
    el sniffer (b1) no capturo el flood. Umbral: bytes/s < 10 000 con infiltracion > 0.
    """
    if r["architecture"] != "p2p":
        return False
    ratio = int(r["infiltration_ratio"])
    bps = num(r["bytes_per_second"]) or 0
    return ratio > 0 and bps < 10000


def tabla1_resumen(rows):
    g = defaultdict(list)
    for r in rows:
        g[(r["architecture"], int(r["infiltration_ratio"]))].append(r)

    metricas = [
        ("latency_ms", "Latencia (ms)", 2),
        ("throughput_mbps", "Throughput (Mbps)", 2),
        ("stability_cv", "Estabilidad (CV)", 3),
        ("bytes_per_second", "Bytes/s", 0),
        ("total_packets", "Paquetes totales", 0),
    ]

    header = ["Arquitectura", "Infiltracion (%)", "n"] + [m[1] for m in metricas] + ["Nota"]
    out_rows = [header]

    for arch in ARCHS:
        for lv in LEVELS:
            items = g.get((arch, lv), [])
            if not items:
                continue
            n = len(items)
            # hay anomalas en este grupo?
            anom = any(is_anomala(r) for r in items)
            celdas = []
            for key, _, dec in metricas:
                vals = [num(r[key]) for r in items if num(r[key]) is not None]
                if not vals:
                    celdas.append("")
                    continue
                media = st.mean(vals)
                sigma = st.pstdev(vals) if len(vals) > 1 else 0.0
                celdas.append(f"{fmt(media, dec)} +/- {fmt(sigma, dec)}")
            nota = "volumen afectado por efecto posicion" if anom else ""
            out_rows.append([ARCH_LABEL[arch], str(lv), str(n)] + celdas + [nota])

    return out_rows


def tabla2_detalle(rows):
    header = ["Arquitectura", "Run", "Infiltracion (%)", "Latencia (ms)",
              "Throughput (Mbps)", "Perdida (%)", "Estabilidad (CV)",
              "Bytes/s", "Paquetes totales", "Anomala"]
    out_rows = [header]

    # ordenar por arquitectura, run, nivel
    def keyf(r):
        return (r["architecture"], r["run_id"], int(r["infiltration_ratio"]))

    for r in sorted(rows, key=keyf):
        out_rows.append([
            ARCH_LABEL[r["architecture"]],
            r["run_id"],
            r["infiltration_ratio"],
            fmt(num(r["latency_ms"]), 2),
            fmt(num(r["throughput_mbps"]), 2),
            fmt(num(r["packet_loss_pct"]), 1),
            fmt(num(r["stability_cv"]), 3),
            fmt(num(r["bytes_per_second"]), 0),
            fmt(num(r["total_packets"]), 0),
            "SI" if is_anomala(r) else "",
        ])
    return out_rows


def escribir(path, filas):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(filas)
    print(f"[OK] {path}  ({len(filas)-1} filas de datos)")


def main():
    rows = load_rows()
    escribir(OUT1, tabla1_resumen(rows))
    escribir(OUT2, tabla2_detalle(rows))
    print("\nTablas generadas. Las ejecuciones marcadas (columna 'Anomala' = SI / nota en "
          "Tabla 1) son aquellas en que el sniffer P2P no capturo el flood (efecto posicion).")


if __name__ == "__main__":
    main()

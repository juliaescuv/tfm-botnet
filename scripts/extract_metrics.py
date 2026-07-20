import os
import re
import csv
import subprocess
from pathlib import Path

CAPTURE_DIRS = ["captures/centralized", "captures/p2p"]
OUTPUT_CSV = "results/csv/metrics_summary.csv"
TOTAL_BOTS = 40

INFILTRATION_MAP = {
    0: 0,
    4: 10,
    10: 25,
    20: 50,
}

# Directorios de logs por arquitectura (para ping e iperf)
LOG_DIRS = {"centralized": "logs/centralized", "p2p": "logs/p2p"}


def run_tshark_fields(pcap_file: str):
    """
    Extrae por paquete: timestamp, ip origen, ip destino, longitud de trama.
    Excluye el tráfico de iperf (puerto 5201) para no contaminar las métricas
    de volumen y estabilidad con la ráfaga de medición de throughput.
    """
    cmd = [
        "tshark",
        "-r", pcap_file,
        "-Y", "not tcp.port==5201 and not udp.port==5201",
        "-T", "fields",
        "-e", "frame.time_epoch",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "frame.len",
        "-E", "header=n",
        "-E", "separator=,",
        "-E", "quote=n",
        "-E", "occurrence=f",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Error ejecutando tshark sobre {pcap_file}: {result.stderr.strip()}")

    rows = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 4:
            continue
        rows.append(parts[:4])

    return rows


def parse_filename(filename: str, architecture: str):
    """
    Espera nombres como: run1_inf0.pcap, run2_inf4.pcap, run3_inf10.pcap, run1_inf20.pcap
    """
    pattern = r"(?P<run_id>.+?)_inf(?P<inf>\d+)\.pcap$"
    match = re.match(pattern, filename)

    if match:
        run_id = match.group("run_id")
        infiltrated_count = int(match.group("inf"))
    else:
        run_id = Path(filename).stem
        infiltrated_count = -1

    infiltration_ratio = INFILTRATION_MAP.get(infiltrated_count, -1)

    if infiltrated_count == 0:
        scenario_type = "baseline"
    elif infiltrated_count > 0:
        scenario_type = "infiltrated"
    else:
        scenario_type = "unknown"

    normal_count = TOTAL_BOTS - infiltrated_count if infiltrated_count >= 0 else -1

    return {
        "architecture": architecture,
        "run_id": run_id,
        "infiltrated_count": infiltrated_count,
        "normal_count": normal_count,
        "total_bot_nodes": TOTAL_BOTS,
        "infiltration_ratio": infiltration_ratio,
        "scenario_type": scenario_type,
    }


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def compute_metrics(rows):
    if not rows:
        return {
            "total_packets": 0,
            "total_bytes": 0,
            "duration_seconds": 0.0,
            "packets_per_second": 0.0,
            "bytes_per_second": 0.0,
            "unique_src_ips": 0,
            "unique_dst_ips": 0,
            "unique_flows": 0,
            "avg_packet_size_bytes": 0.0,
            "stability_cv": 0.0,
        }

    timestamps = []
    total_bytes = 0
    src_ips = set()
    dst_ips = set()
    flows = set()

    for timestamp, src_ip, dst_ip, frame_len in rows:
        ts = safe_float(timestamp, None)
        if ts is not None:
            timestamps.append(ts)

        if src_ip:
            src_ips.add(src_ip)
        if dst_ip:
            dst_ips.add(dst_ip)
        if src_ip and dst_ip:
            flows.add((src_ip, dst_ip))

        total_bytes += safe_int(frame_len, 0)

    total_packets = len(rows)

    if timestamps:
        start_time = min(timestamps)
        end_time = max(timestamps)
        duration_seconds = max(end_time - start_time, 0.0)
    else:
        duration_seconds = 0.0

    if duration_seconds > 0:
        packets_per_second = total_packets / duration_seconds
        bytes_per_second = total_bytes / duration_seconds
    else:
        packets_per_second = 0.0
        bytes_per_second = 0.0

    avg_packet_size_bytes = total_bytes / total_packets if total_packets > 0 else 0.0

    # Estabilidad de la comunicación: coeficiente de variación (std/media) del
    # número de paquetes por segundo. CV bajo = flujo estable; CV alto = irregular.
    stability_cv = 0.0
    if timestamps and duration_seconds > 0:
        start = min(timestamps)
        buckets = {}
        for ts in timestamps:
            sec = int(ts - start)
            buckets[sec] = buckets.get(sec, 0) + 1
        counts = list(buckets.values())
        if counts:
            mean = sum(counts) / len(counts)
            if mean > 0:
                var = sum((c - mean) ** 2 for c in counts) / len(counts)
                stability_cv = (var ** 0.5) / mean

    return {
        "total_packets": total_packets,
        "total_bytes": total_bytes,
        "duration_seconds": round(duration_seconds, 4),
        "packets_per_second": round(packets_per_second, 4),
        "bytes_per_second": round(bytes_per_second, 4),
        "unique_src_ips": len(src_ips),
        "unique_dst_ips": len(dst_ips),
        "unique_flows": len(flows),
        "avg_packet_size_bytes": round(avg_packet_size_bytes, 4),
        "stability_cv": round(stability_cv, 4),
    }


def parse_ping(log_path):
    """
    Devuelve (latencia_media_ms, perdida_pct) del log de ping.
    """
    if not os.path.exists(log_path):
        return None, None

    text = open(log_path, errors="ignore").read()

    loss = None
    m = re.search(r"(\d+(?:\.\d+)?)% packet loss", text)
    if m:
        loss = safe_float(m.group(1), None)

    latency = None
    m = re.search(r"rtt [^=]*=\s*[\d.]+/([\d.]+)/", text)
    if m:
        latency = safe_float(m.group(1), None)

    return latency, loss


def parse_iperf(log_path):
    """
    Devuelve el throughput en Mbit/s del log de iperf3 (línea receiver, o sender).
    """
    if not os.path.exists(log_path):
        return None

    text = open(log_path, errors="ignore").read()

    receiver = None
    sender = None
    for line in text.splitlines():
        m = re.search(r"([\d.]+)\s*([KMG]?)bits/sec", line)
        if not m:
            continue
        val = safe_float(m.group(1), None)
        unit = m.group(2)
        if val is None:
            continue
        if unit == "G":
            val *= 1000.0
        elif unit == "K":
            val /= 1000.0
        elif unit == "":
            val /= 1_000_000.0
        if "receiver" in line:
            receiver = val
        elif "sender" in line:
            sender = val

    return receiver if receiver is not None else sender


def collect_pcaps():
    pcaps = []
    for capture_dir in CAPTURE_DIRS:
        path = Path(capture_dir)
        if not path.exists():
            continue
        architecture = path.name
        for pcap_file in sorted(path.glob("*.pcap")):
            pcaps.append((architecture, str(pcap_file), pcap_file.name))
    return pcaps


def ensure_output_dir():
    Path(OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)


def main():
    ensure_output_dir()
    pcaps = collect_pcaps()

    if not pcaps:
        print("No se encontraron archivos .pcap en los directorios de capturas.")
        return

    output_rows = []

    for architecture, pcap_path, filename in pcaps:
        print(f"[+] Procesando {pcap_path}")

        metadata = parse_filename(filename, architecture)
        run_id = metadata["run_id"]
        inf_count = metadata["infiltrated_count"]
        log_dir = LOG_DIRS.get(architecture, "")

        # Logs de ping/iperf de ESTA ejecución: varios pares (_p0, _p1, ...).
        # Se promedian latencia, pérdida y throughput sobre todos los pares.
        import glob
        ping_logs = sorted(glob.glob(os.path.join(log_dir, f"ping_{run_id}_inf{inf_count}_p*.log")))
        iperf_logs = sorted(glob.glob(os.path.join(log_dir, f"iperf_{run_id}_inf{inf_count}_p*.log")))
        # compatibilidad con el formato antiguo (sin _p): un solo log
        if not ping_logs:
            legacy = os.path.join(log_dir, f"ping_{run_id}_inf{inf_count}.log")
            if os.path.exists(legacy):
                ping_logs = [legacy]
        if not iperf_logs:
            legacy = os.path.join(log_dir, f"iperf_{run_id}_inf{inf_count}.log")
            if os.path.exists(legacy):
                iperf_logs = [legacy]

        lat_vals, loss_vals = [], []
        for lg in ping_logs:
            la, lo = parse_ping(lg)
            if la is not None:
                lat_vals.append(la)
            if lo is not None:
                loss_vals.append(lo)
        thr_vals = []
        for ig in iperf_logs:
            th = parse_iperf(ig)
            if th is not None:
                thr_vals.append(th)

        latency = sum(lat_vals) / len(lat_vals) if lat_vals else None
        loss = sum(loss_vals) / len(loss_vals) if loss_vals else None
        throughput = sum(thr_vals) / len(thr_vals) if thr_vals else None

        try:
            rows = run_tshark_fields(pcap_path)
            metrics = compute_metrics(rows)

            row = {
                "file_name": filename,
                "file_path": pcap_path,
                "architecture": metadata["architecture"],
                "run_id": metadata["run_id"],
                "scenario_type": metadata["scenario_type"],
                "total_bot_nodes": metadata["total_bot_nodes"],
                "normal_count": metadata["normal_count"],
                "infiltrated_count": metadata["infiltrated_count"],
                "infiltration_ratio": metadata["infiltration_ratio"],
                **metrics,
                "latency_ms": round(latency, 4) if latency is not None else "",
                "packet_loss_pct": round(loss, 4) if loss is not None else "",
                "throughput_mbps": round(throughput, 2) if throughput is not None else "",
                "status": "ok",
                "error_message": "",
            }

        except Exception as e:
            row = {
                "file_name": filename,
                "file_path": pcap_path,
                "architecture": metadata["architecture"],
                "run_id": metadata["run_id"],
                "scenario_type": metadata["scenario_type"],
                "total_bot_nodes": metadata["total_bot_nodes"],
                "normal_count": metadata["normal_count"],
                "infiltrated_count": metadata["infiltrated_count"],
                "infiltration_ratio": metadata["infiltration_ratio"],
                "total_packets": 0,
                "total_bytes": 0,
                "duration_seconds": 0.0,
                "packets_per_second": 0.0,
                "bytes_per_second": 0.0,
                "unique_src_ips": 0,
                "unique_dst_ips": 0,
                "unique_flows": 0,
                "avg_packet_size_bytes": 0.0,
                "stability_cv": 0.0,
                "latency_ms": round(latency, 4) if latency is not None else "",
                "packet_loss_pct": round(loss, 4) if loss is not None else "",
                "throughput_mbps": round(throughput, 2) if throughput is not None else "",
                "status": "error",
                "error_message": str(e),
            }

        output_rows.append(row)

    fieldnames = [
        "file_name",
        "file_path",
        "architecture",
        "run_id",
        "scenario_type",
        "total_bot_nodes",
        "normal_count",
        "infiltrated_count",
        "infiltration_ratio",
        "total_packets",
        "total_bytes",
        "duration_seconds",
        "packets_per_second",
        "bytes_per_second",
        "unique_src_ips",
        "unique_dst_ips",
        "unique_flows",
        "avg_packet_size_bytes",
        "latency_ms",
        "packet_loss_pct",
        "throughput_mbps",
        "stability_cv",
        "status",
        "error_message",
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\n[OK] CSV generado en: {OUTPUT_CSV}")
    print(f"[OK] Archivos procesados: {len(output_rows)}")
    print("\nResumen (arch, run, infiltr.%, latencia ms, pérdida %, throughput Mbps, estabilidad CV):")
    for r in output_rows:
        print(f"  {r['architecture']:11s} {r['run_id']:6s} "
              f"{str(r['infiltration_ratio']):>3}%  "
              f"lat={str(r['latency_ms']) or '-':>8}  "
              f"loss={str(r['packet_loss_pct']) or '-':>6}  "
              f"thr={str(r['throughput_mbps']) or '-':>8}  "
              f"cv={r['stability_cv']}")


if __name__ == "__main__":
    main()

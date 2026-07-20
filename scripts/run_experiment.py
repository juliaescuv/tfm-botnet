import os
import sys
import time
import random
import signal
from pathlib import Path

from mininet.clean import cleanup

TOTAL_BOTS = 40
BASE_PORT = 10000
VALID_INFILTRATED = {0: 0, 4: 10, 10: 25, 20: 50}


def ensure_dirs():
    Path("captures/centralized").mkdir(parents=True, exist_ok=True)
    Path("captures/p2p").mkdir(parents=True, exist_ok=True)
    Path("logs/centralized").mkdir(parents=True, exist_ok=True)
    Path("logs/p2p").mkdir(parents=True, exist_ok=True)
    Path("results/csv").mkdir(parents=True, exist_ok=True)
    Path("results/figures").mkdir(parents=True, exist_ok=True)


def get_bot_hosts(net):
    return [net.get(f"b{i}") for i in range(1, TOTAL_BOTS + 1)]


def choose_infiltrated_hosts(bot_hosts, infiltrated_count, seed=42):
    rng = random.Random(seed)
    chosen = rng.sample(bot_hosts, infiltrated_count) if infiltrated_count > 0 else []
    chosen_names = sorted([h.name for h in chosen], key=lambda x: int(x[1:]))
    return set(chosen_names)


def start_tcpdump(net, arch, runid, infiltrated_count):
    pcap_file = f"captures/{arch}/{runid}_inf{infiltrated_count}.pcap"
    log_file = f"logs/{arch}/tcpdump_{runid}.log"

    # Capturamos en c2 para centralizada y en b1 para p2p como aproximación simple
    sniff_host = net.get("c2") if arch == "centralized" else net.get("b1")

    # -s 96: snaplen, captura solo los primeros 96 bytes de cada paquete (cabeceras).
    # Las métricas (conteo, IPs, timestamps, longitud real de trama) se conservan,
    # pero el pcap pesa una fracción al no guardar el payload de relleno de 4 KB.
    cmd = f"tcpdump -i any -s 96 -w {pcap_file} > {log_file} 2>&1 & echo $!"
    pid = sniff_host.cmd(cmd).strip()

    return pcap_file, log_file, sniff_host, pid


def stop_background_process(host, pid):
    if pid:
        host.cmd(f"kill {pid} >/dev/null 2>&1")


# ----------------------------------------------------------------------------
# Medición de métricas adicionales: latencia y pérdida (ping), throughput (iperf)
# ----------------------------------------------------------------------------

# Puertos del servidor iperf (se filtran luego del cálculo de volumen)
IPERF_PORT = 5201

# Nº de nodos desde los que se mide latencia/throughput para promediar
N_MEASURE = 5


def choose_measure_pairs(net, arch, infiltrated_names):
    """
    Devuelve una lista de N_MEASURE pares (origen, destino) para medir y promediar.
    - Centralizada: N bots NORMALES distintos  ->  C2 (todos cruzan el cuello del C2).
    - P2P: N pares de bots de zonas opuestas del anillo (cruzan los troncales).
    """
    pairs = []
    if arch == "centralized":
        c2 = net.get("c2")
        count = 0
        for i in range(1, TOTAL_BOTS + 1):
            if f"b{i}" not in infiltrated_names:
                pairs.append((net.get(f"b{i}"), c2))
                count += 1
                if count >= N_MEASURE:
                    break
    else:
        # P2P: pares que CRUCEN los troncales limitados. Con la regla
        # switch = (i-1) % 4, elegimos pares cuyo origen y destino caigan en
        # switches ALEJADOS (s1 <-> s4) para que el tráfico atraviese los
        # enlaces troncales (el cuello de botella). Pares prefijados:
        #   b1 (s0) <-> b4 (s3), b5 (s0) <-> b8 (s3), b9 (s0) <-> b12 (s3), ...
        candidate_pairs = []
        i = 1
        while i + 3 <= TOTAL_BOTS and len(candidate_pairs) < TOTAL_BOTS:
            # b_i en switch (i-1)%4 == 0  ;  b_(i+3) en switch (i+2)%4 == 3
            candidate_pairs.append((f"b{i}", f"b{i+3}"))
            i += 4

        # preferir pares de bots normales (medir efecto sobre legítimos)
        count = 0
        for src_name, dst_name in candidate_pairs:
            if src_name not in infiltrated_names and dst_name not in infiltrated_names:
                pairs.append((net.get(src_name), net.get(dst_name)))
                count += 1
                if count >= N_MEASURE:
                    break
        # si no hay suficientes pares normales, rellenar con los primeros que crucen
        if count < N_MEASURE:
            for src_name, dst_name in candidate_pairs:
                pair = (net.get(src_name), net.get(dst_name))
                if pair not in pairs:
                    pairs.append(pair)
                    if len(pairs) >= N_MEASURE:
                        break
    return pairs[:N_MEASURE]


def start_ping_multi(pairs, arch, runid, infiltrated_count, duration):
    """
    Lanza ping EN PARALELO desde cada par durante la ventana. Un log por par:
    ping_<runid>_inf<N>_p<k>.log. Devuelve lista de (src, pid).
    """
    count = max(duration, 1)
    procs = []
    for k, (src, dst) in enumerate(pairs):
        ping_log = f"logs/{arch}/ping_{runid}_inf{infiltrated_count}_p{k}.log"
        cmd = f"ping -c {count} -i 1 {dst.IP()} > {ping_log} 2>&1 & echo $!"
        pid = src.cmd(cmd).strip()
        procs.append((src, pid))
    return procs


def run_iperf_multi(pairs, arch, runid, infiltrated_count, iperf_seconds=10):
    """
    Mide throughput con iperf3 en cada par, de forma secuencial al final de la
    ventana. Un log por par: iperf_<runid>_inf<N>_p<k>.log.
    """
    for k, (src, dst) in enumerate(pairs):
        iperf_log = f"logs/{arch}/iperf_{runid}_inf{infiltrated_count}_p{k}.log"
        dst.cmd(f"iperf3 -s -p {IPERF_PORT} > /dev/null 2>&1 &")
        time.sleep(1)
        src.cmd(f"iperf3 -c {dst.IP()} -p {IPERF_PORT} -t {iperf_seconds} > {iperf_log} 2>&1")
        dst.cmd("pkill -f 'iperf3 -s' >/dev/null 2>&1")
        time.sleep(0.5)


def import_topology(arch):
    if arch == "centralized":
        from topology_centralized import build_network
        return build_network
    elif arch == "p2p":
        from topology_p2p import build_network
        return build_network
    else:
        raise ValueError(f"Arquitectura no válida: {arch}")


def launch_centralized(net, infiltrated_names, runid):
    processes = []

    c2 = net.get("c2")
    c2_log = f"logs/centralized/c2_{runid}.log"
    c2_proc = c2.popen(["python3", "scripts/c2_server.py"], stdout=open(c2_log, "w"), stderr=open(c2_log, "a"))
    processes.append(c2_proc)

    time.sleep(2)

    for i in range(1, TOTAL_BOTS + 1):
        bot = net.get(f"b{i}")
        bot_log = f"logs/centralized/{bot.name}_{runid}.log"

        if bot.name in infiltrated_names:
            proc = bot.popen(
                ["python3", "scripts/infiltrated_bot_centralized.py", "10.0.0.100", "9000"],
                stdout=open(bot_log, "w"),
                stderr=open(bot_log, "a"),
            )
        else:
            proc = bot.popen(
                ["python3", "scripts/normal_bot_centralized.py", "10.0.0.100", "9000"],
                stdout=open(bot_log, "w"),
                stderr=open(bot_log, "a"),
            )

        processes.append(proc)

    return processes


def build_neighbors(i):
    n1 = (i % TOTAL_BOTS) + 1
    n2 = ((i + 1) % TOTAL_BOTS) + 1
    n3 = ((i + 2) % TOTAL_BOTS) + 1

    return [
        f"10.0.0.{n1}:{BASE_PORT + n1}",
        f"10.0.0.{n2}:{BASE_PORT + n2}",
        f"10.0.0.{n3}:{BASE_PORT + n3}",
    ]


def launch_p2p(net, infiltrated_names, runid):
    processes = []

    for i in range(1, TOTAL_BOTS + 1):
        bot = net.get(f"b{i}")
        port = str(BASE_PORT + i)
        neighbors = build_neighbors(i)
        bot_log = f"logs/p2p/{bot.name}_{runid}.log"

        if bot.name in infiltrated_names:
            proc = bot.popen(
                ["python3", "scripts/infiltrated_bot_p2p.py", bot.IP(), port] + neighbors,
                stdout=open(bot_log, "w"),
                stderr=open(bot_log, "a"),
            )
        else:
            proc = bot.popen(
                ["python3", "scripts/normal_bot_p2p.py", bot.IP(), port] + neighbors,
                stdout=open(bot_log, "w"),
                stderr=open(bot_log, "a"),
            )

        processes.append(proc)

    return processes


def terminate_processes(processes):
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass

    time.sleep(2)

    for proc in processes:
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass


def main():
    if len(sys.argv) < 4:
        print("Uso: sudo python3 scripts/run_experiment.py <centralized|p2p> <0|4|10|20> <runid> [duration] [seed]")
        sys.exit(1)

    arch = sys.argv[1]
    infiltrated_count = int(sys.argv[2])
    runid = sys.argv[3]
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 180
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 42

    if infiltrated_count not in VALID_INFILTRATED:
        print("Valor de infiltrados no válido. Usa 0, 4, 10 o 20.")
        sys.exit(1)

    ensure_dirs()
    cleanup()

    build_network = import_topology(arch)
    net = build_network()
    net.start()

    try:
        bot_hosts = get_bot_hosts(net)
        infiltrated_names = choose_infiltrated_hosts(bot_hosts, infiltrated_count, seed=seed)
        normal_count = TOTAL_BOTS - infiltrated_count
        ratio = VALID_INFILTRATED[infiltrated_count]

        print(f"Arquitectura: {arch}")
        print(f"Normales: {normal_count}")
        print(f"Infiltrados: {infiltrated_count}")
        print(f"Porcentaje: {ratio}%")
        print(f"Nodos infiltrados: {sorted(infiltrated_names, key=lambda x: int(x[1:]))}")

        pcap_file, _, sniff_host, tcpdump_pid = start_tcpdump(net, arch, runid, infiltrated_count)
        time.sleep(2)

        if arch == "centralized":
            processes = launch_centralized(net, infiltrated_names, runid)
        else:
            processes = launch_p2p(net, infiltrated_names, runid)

        # Pares de nodos para medir latencia/throughput (varios, para promediar)
        m_pairs = choose_measure_pairs(net, arch, infiltrated_names)
        pares_txt = ", ".join(f"{s.name}->{d.name}" for s, d in m_pairs)
        print(f"Midiendo latencia/throughput en {len(m_pairs)} pares: {pares_txt}")

        # Latencia + pérdida con ping EN PARALELO durante toda la ventana
        ping_procs = start_ping_multi(m_pairs, arch, runid, infiltrated_count, duration)

        print(f"Capturando en: {pcap_file}")
        print(f"Ejecutando durante {duration} segundos...")
        time.sleep(duration)

        # Throughput con iperf: ráfaga corta al final de la ventana, por cada par
        print("Midiendo throughput con iperf...")
        run_iperf_multi(m_pairs, arch, runid, infiltrated_count, iperf_seconds=10)

        for src, pid in ping_procs:
            stop_background_process(src, pid)
        terminate_processes(processes)
        stop_background_process(sniff_host, tcpdump_pid)
        time.sleep(2)

    finally:
        net.stop()
        cleanup()


if __name__ == "__main__":
    main()

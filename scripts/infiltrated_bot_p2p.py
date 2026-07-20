import socket
import threading
import time
import sys
import random

MY_IP = sys.argv[1]
MY_PORT = int(sys.argv[2])
NEIGHBORS = sys.argv[3:]

RUNNING = True

# Payload de relleno (benigno) para saturar la comunicación entre pares.
PAYLOAD_SIZE = 4096
BASE_MESSAGES = [
    "peer_hello", "peer_status", "routing_update", "keepalive",
    "peer_sync", "topology_refresh", "control_resend", "neighbor_probe",
]


def build_message():
    base = random.choice(BASE_MESSAGES)
    padding = "X" * (PAYLOAD_SIZE - len(base))
    return (base + ":" + padding).encode()


def listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((MY_IP, MY_PORT))
    server.listen(50)

    while RUNNING:
        try:
            conn, addr = server.accept()
            conn.recv(8192)
            conn.close()
        except Exception:
            pass


def flood_neighbors():
    # Flood continuo a los vecinos: satura la comunicación entre pares.
    while RUNNING:
        for neighbor in NEIGHBORS:
            try:
                ip, port = neighbor.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((ip, int(port)))
                # varias ráfagas grandes por conexión
                for _ in range(10):
                    sock.sendall(build_message())
                sock.close()
            except Exception:
                pass


def main():
    threading.Thread(target=listener, daemon=True).start()
    # varios hilos de flood para más agresividad
    for _ in range(3):
        threading.Thread(target=flood_neighbors, daemon=True).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()

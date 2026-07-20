import socket
import time
import sys
import random

C2_IP = sys.argv[1]
C2_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9000

def main():
    messages = [
        "heartbeat",
        "status_ok",
        "sync_request"
    ]

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((C2_IP, C2_PORT))

            while True:
                sock.sendall(random.choice(messages).encode())
                time.sleep(2)
        except Exception:
            time.sleep(1)

if __name__ == "__main__":
    main()
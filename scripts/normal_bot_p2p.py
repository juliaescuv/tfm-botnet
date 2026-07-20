import socket
import threading
import time
import sys
import random

MY_IP = sys.argv[1]
MY_PORT = int(sys.argv[2])
NEIGHBORS = sys.argv[3:]

RUNNING = True

def listener():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((MY_IP, MY_PORT))
    server.listen(20)

    while RUNNING:
        try:
            conn, addr = server.accept()
            conn.recv(8192)
            conn.close()
        except Exception:
            pass

def talk_to_neighbors():
    messages = [
        "peer_hello",
        "peer_status",
        "routing_update",
        "keepalive"
    ]

    while RUNNING:
        for neighbor in NEIGHBORS:
            try:
                ip, port = neighbor.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((ip, int(port)))
                sock.sendall(random.choice(messages).encode())
                sock.close()
            except Exception:
                pass
        time.sleep(2)

def main():
    threading.Thread(target=listener, daemon=True).start()
    threading.Thread(target=talk_to_neighbors, daemon=True).start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()

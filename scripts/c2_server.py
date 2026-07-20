import socket
import threading

HOST = "0.0.0.0"
PORT = 9000

# Buffer de recepción grande para drenar rápido el tráfico de los bots
# (incluido el flood de los infiltrados). NO se imprime cada mensaje: con el
# flood de 4 KB continuo, imprimir saturaría el C2 por CPU/disco y desviaría
# el cuello de botella de la red al procesamiento. El C2 solo recibe y descarta.
RECV_SIZE = 65536


def handle_client(conn, addr):
    try:
        while True:
            data = conn.recv(RECV_SIZE)
            if not data:
                break
            # se descarta el contenido (mensajes sintéticos benignos)
    except Exception:
        pass
    finally:
        conn.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(200)
    print(f"[C2] Escuchando en {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()

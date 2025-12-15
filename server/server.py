import socket
import threading
import json
import time
import random

TCP_PORT = 50000
DISCOVERY_PORT = 50001


def room_code():
    return ''.join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(4))


class RoomServer:
    def __init__(self):
        self.code = room_code()
        self.clients = {}
        self.running = True

    def start(self):
        print(f"[SERVER] Room created. Code: {self.code}")
        threading.Thread(target=self.discovery_loop, daemon=True).start()
        threading.Thread(target=self.tcp_loop, daemon=True).start()
        self.game_loop()

    def discovery_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))

        while self.running:
            try:
                msg, addr = sock.recvfrom(1024)
                if msg.decode() == "DISCOVER_ROOM":
                    reply = {
                        "type": "room",
                        "room_code": self.code,
                        "host": socket.gethostbyname(socket.gethostname()),
                        "tcp_port": TCP_PORT,
                    }
                    sock.sendto(json.dumps(reply).encode(), addr)
            except:
                pass

    def tcp_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("", TCP_PORT))
        srv.listen(8)

        while self.running:
            conn, addr = srv.accept()
            pid = f"P{len(self.clients)+1}"
            self.clients[conn] = {"id": pid, "x": 500, "y": 350}
            conn.sendall(json.dumps({"type": "welcome", "id": pid}).encode() + b"\n")
            threading.Thread(target=self.client_receiver, args=(conn,), daemon=True).start()

    def client_receiver(self, conn):
        buf = b""
        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = json.loads(line.decode())
                    player = self.clients[conn]
                    player["x"] += msg.get("dx", 0)
                    player["y"] += msg.get("dy", 0)
            except:
                break

        del self.clients[conn]
        conn.close()

    def game_loop(self):
        while self.running:
            state = {
                "type": "state",
                "players": list(self.clients.values())
            }
            data = json.dumps(state).encode() + b"\n"

            for conn in list(self.clients.keys()):
                try:
                    conn.sendall(data)
                except:
                    del self.clients[conn]
                    conn.close()

            time.sleep(1 / 20)


# 🔹 NEW: server entry function
def run_server():
    RoomServer().start()


if __name__ == "__main__":
    run_server()

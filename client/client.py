import socket
import threading
import json
import pygame
import time
import sys
import os

DISCOVERY_PORT = 50001
TCP_PORT = 50000

# 🔹 Import server runner
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server")))
from server import run_server


def discover_rooms(timeout=1.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.4)

    found = []
    start = time.time()

    while time.time() - start < timeout:
        sock.sendto(b"DISCOVER_ROOM", ("<broadcast>", DISCOVERY_PORT))
        try:
            data, addr = sock.recvfrom(1024)
            found.append(json.loads(data.decode()))
        except:
            pass

    return found


class Client:
    def __init__(self):
        self.sock = None
        self.players = []
        self.running = True

    def connect(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, TCP_PORT))
        threading.Thread(target=self.recv_loop, daemon=True).start()

    def recv_loop(self):
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    print("Disconnected from server")
                    self.running = False
                    self.sock.close()
                    break

                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = json.loads(line.decode())
                    if msg["type"] == "welcome":
                        self.id = msg["id"]
                    elif msg["type"] == "state":
                        self.players = msg["players"]

            except (ConnectionResetError, ConnectionAbortedError, OSError):
                print("Disconnected from server")
                self.running = False
                try:
                    self.sock.close()
                except:
                    pass
                break

    def send_input(self, dx, dy):
        try:
            msg = json.dumps({"dx": dx, "dy": dy}) + "\n"
            self.sock.sendall(msg.encode())
        except:
            pass


# ---------------------- GAME START ----------------------
pygame.init()
screen = pygame.display.set_mode((1000, 700))
clock = pygame.time.Clock()

client = Client()

# 🔹 HOST MODE (set to False to join instead)
HOST_GAME = True

if HOST_GAME:
    print("Hosting game...")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)  # allow server to start
    client.connect("127.0.0.1")
else:
    rooms = discover_rooms()
    if rooms:
        print("Found rooms:", rooms)
        client.connect(rooms[0]["host"])
    else:
        print("No rooms found.")

running = True
while running and client.running:
    dx = dy = 0
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: dx = -5
    if keys[pygame.K_RIGHT]: dx = 5
    if keys[pygame.K_UP]: dy = -5
    if keys[pygame.K_DOWN]: dy = 5

    client.send_input(dx, dy)

    screen.fill((30, 30, 30))
    for p in client.players:
        pygame.draw.rect(screen, (0, 255, 0), (p["x"], p["y"], 40, 40))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
client.running = False

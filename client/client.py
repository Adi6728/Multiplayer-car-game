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


# ---------------- ROAD CONFIG ----------------
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700

ROAD_WIDTH = 600
ROAD_X = (SCREEN_WIDTH - ROAD_WIDTH) // 2

LANE_COUNT = 3
LANE_WIDTH = ROAD_WIDTH // LANE_COUNT


# ---------------- LOAD ASSETS ----------------
ASSET_PATH = os.path.join(os.path.dirname(__file__), "assets")

CAR_IMAGES = [
    pygame.image.load(os.path.join(ASSET_PATH, "car_red.png")),
    pygame.image.load(os.path.join(ASSET_PATH, "car_blue.png")),
    pygame.image.load(os.path.join(ASSET_PATH, "car_green.png")),
    pygame.image.load(os.path.join(ASSET_PATH, "car_yellow.png")),
]

CAR_IMAGES = [pygame.transform.scale(img, (40, 40)) for img in CAR_IMAGES]


def draw_road(surface):
    # Draw road
    pygame.draw.rect(
        surface,
        (50, 50, 50),
        (ROAD_X, 0, ROAD_WIDTH, SCREEN_HEIGHT)
    )

    # Draw lane dividers
    for i in range(1, LANE_COUNT):
        x = ROAD_X + i * LANE_WIDTH
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(
                surface,
                (255, 255, 255),
                (x, y),
                (x, y + 20),
                4
            )


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
        self.id = None

        self.player_skins = {}
        self.player_angles = {}

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
                        self.player_skins[self.id] = CAR_IMAGES[len(self.player_skins) % len(CAR_IMAGES)]
                        self.player_angles[self.id] = 0

                    elif msg["type"] == "state":
                        for p in msg["players"]:
                            pid = p["id"]
                            if pid not in self.player_skins:
                                self.player_skins[pid] = CAR_IMAGES[len(self.player_skins) % len(CAR_IMAGES)]
                                self.player_angles[pid] = 0
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


# ---------------- GAME START ----------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

client = Client()

HOST_GAME = True

if HOST_GAME:
    print("Hosting game...")
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(1)
    client.connect("127.0.0.1")
else:
    rooms = discover_rooms()
    if rooms:
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
    if client.id:
        if keys[pygame.K_LEFT]:
            dx = -5
            client.player_angles[client.id] = 90
        if keys[pygame.K_RIGHT]:
            dx = 5
            client.player_angles[client.id] = -90
        if keys[pygame.K_UP]:
            dy = -5
            client.player_angles[client.id] = 0
        if keys[pygame.K_DOWN]:
            dy = 5
            client.player_angles[client.id] = 180

    client.send_input(dx, dy)

    screen.fill((0, 120, 0))
    draw_road(screen)

    lane_centers = [
        ROAD_X + LANE_WIDTH // 2,
        ROAD_X + LANE_WIDTH + LANE_WIDTH // 2,
        ROAD_X + 2 * LANE_WIDTH + LANE_WIDTH // 2
    ]

    for index, p in enumerate(client.players):
        pid = p["id"]
        sprite = client.player_skins.get(pid)
        angle = client.player_angles.get(pid, 0)

        if sprite:
            lane_x = lane_centers[index % LANE_COUNT] - 20
            rotated = pygame.transform.rotate(sprite, angle)
            screen.blit(rotated, (lane_x, p["y"]))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
client.running = False

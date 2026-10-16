"""
Car Racing Game - Python + tkinter (no installation needed)

You (blue car) race against the computer (red car).
The computer car drives by itself: its speed and steering change randomly.
Both cars have a top speed of 100 km/h. First to the finish line wins!

Controls:
    Up / W        accelerate
    Down / S      brake
    Left / A      steer left
    Right / D     steer right
    P             pause / resume
    R             restart
    Esc           quit

Tips:
    * Driving on the grass slows you down (max 40 km/h).
    * Hitting the other car slows the car that hit from behind.
"""

import math
import random
import time
import tkinter as tk

# ---------------- Settings ----------------
W, H = 460, 640               # game canvas size
PANEL_W = 150                 # side panel width
ROAD_L, ROAD_R = 80, 380      # road edges (x)
LANES = 3
PLAYER_Y = 500                # fixed screen y of the player's car
PX_PER_M = 10                 # pixels per metre
RACE_M = 1500                 # race length in metres
MAX_KMH = 100                 # top speed of BOTH cars
OFFROAD_MAX_KMH = 40
CAR_W, CAR_H = 36, 64

KMH_TO_MPS = 1000 / 3600

GRASS = "#2e7d32"
GRASS_DARK = "#276b2b"
ROAD = "#3a3a3f"
PANEL_BG = "#15151f"
TEXT = "#e6e6f0"
PLAYER_COLOR = ("#1e88e5", "#0d47a1")
CPU_COLOR = ("#e53935", "#7f1d1d")


class Car:
    def __init__(self, name, body, roof):
        self.name = name
        self.body = body
        self.roof = roof
        self.x = 0.0
        self.dist = 0.0       # metres travelled
        self.speed = 0.0      # km/h


class RacingGame:
    def __init__(self, root):
        self.root = root
        root.title("Car Racing Game")
        root.resizable(False, False)

        frame = tk.Frame(root, bg=PANEL_BG)
        frame.pack()
        self.canvas = tk.Canvas(frame, width=W, height=H, bg=GRASS, highlightthickness=0)
        self.canvas.pack(side="left")
        self.panel = tk.Canvas(frame, width=PANEL_W, height=H, bg=PANEL_BG, highlightthickness=0)
        self.panel.pack(side="left")

        self.player = Car("You", *PLAYER_COLOR)
        self.cpu = Car("Computer", *CPU_COLOR)

        self.keys = set()
        root.bind("<KeyPress>", self.on_press)
        root.bind("<KeyRelease>", self.on_release)

        self.reset()
        self.last = time.perf_counter()
        self.loop()

    # ---------------- State ----------------
    def reset(self):
        lane_w = (ROAD_R - ROAD_L) / LANES
        self.cpu.x = ROAD_L + lane_w * 0.5
        self.player.x = ROAD_L + lane_w * 2.5
        for car in (self.player, self.cpu):
            car.dist = 0.0
            car.speed = 0.0

        self.state = "countdown"      # countdown -> race -> over
        self.countdown = 3.0
        self.race_time = 0.0
        self.paused = False
        self.winner = None
        self.result_text = ""

        # computer driver "brain"
        self.cpu_target_speed = 80.0
        self.cpu_speed_timer = 0.0
        self.cpu_target_x = self.cpu.x
        self.cpu_lat_timer = 0.0

    # ---------------- Input ----------------
    def on_press(self, event):
        key = event.keysym.lower()
        if key == "escape":
            self.root.destroy()
            return
        if key == "r":
            self.reset()
            return
        if key == "p" and self.state == "race":
            self.paused = not self.paused
            return
        self.keys.add(key)

    def on_release(self, event):
        self.keys.discard(event.keysym.lower())

    def held(self, *names):
        return any(n in self.keys for n in names)

    # ---------------- Game loop ----------------
    def loop(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        if not self.paused:
            self.update(dt)
        self.draw()
        self.root.after(16, self.loop)

    def update(self, dt):
        if self.state == "countdown":
            self.countdown -= dt
            if self.countdown <= 0:
                self.state = "race"
                self.race_time = 0.0
            return
        if self.state != "race":
            return

        self.race_time += dt
        self.update_player(dt)
        self.update_cpu(dt)
        self.handle_collision()
        self.check_finish()

    def on_road(self, x):
        return ROAD_L <= x <= ROAD_R

    def update_player(self, dt):
        p = self.player
        if self.held("up", "w"):
            p.speed += 32 * dt
        elif self.held("down", "s"):
            p.speed -= 70 * dt
        else:
            p.speed -= 12 * dt          # natural slow-down

        cap = MAX_KMH if self.on_road(p.x) else OFFROAD_MAX_KMH
        if p.speed > cap:
            p.speed = max(cap, p.speed - 60 * dt)
        p.speed = max(0.0, min(MAX_KMH, p.speed))

        steer = (1 if self.held("right", "d") else 0) - (1 if self.held("left", "a") else 0)
        grip = min(1.0, p.speed / 20)   # can't steer when stopped
        p.x += steer * (120 + 1.2 * p.speed) * grip * dt
        p.x = max(ROAD_L - 25, min(ROAD_R + 25, p.x))

        p.dist += p.speed * KMH_TO_MPS * dt

    def update_cpu(self, dt):
        c = self.cpu

        # pick a new random speed now and then
        self.cpu_speed_timer -= dt
        if self.cpu_speed_timer <= 0:
            if random.random() < 0.12:
                self.cpu_target_speed = random.uniform(35, 55)     # little "mistake"
            else:
                self.cpu_target_speed = random.uniform(60, MAX_KMH)
            self.cpu_speed_timer = random.uniform(1.0, 3.0)

        if c.speed < self.cpu_target_speed:
            c.speed += 25 * dt
        else:
            c.speed -= 40 * dt
        c.speed = max(0.0, min(MAX_KMH, c.speed))

        # pick a new random place on the road now and then
        self.cpu_lat_timer -= dt
        if self.cpu_lat_timer <= 0:
            self.cpu_target_x = random.uniform(ROAD_L + 25, ROAD_R - 25)
            self.cpu_lat_timer = random.uniform(0.8, 2.2)

        diff = self.cpu_target_x - c.x
        move = (90 * (0.3 + c.speed / MAX_KMH)) * dt
        if abs(diff) <= move:
            c.x = self.cpu_target_x
        else:
            c.x += move if diff > 0 else -move

        c.dist += c.speed * KMH_TO_MPS * dt

    def handle_collision(self):
        p, c = self.player, self.cpu
        dx = p.x - c.x
        ddist_px = (p.dist - c.dist) * PX_PER_M
        if abs(dx) < CAR_W - 2 and abs(ddist_px) < CAR_H - 4:
            if abs(dx) >= CAR_W * 0.55:
                # side swipe: push the cars apart sideways
                push = (CAR_W - abs(dx)) / 2 + 1
                sign = 1 if dx >= 0 else -1
                p.x += sign * push
                c.x -= sign * push
                p.speed *= 0.97
                c.speed *= 0.97
            else:
                # rear-end: the car behind loses speed and is held back
                rear, front = (p, c) if p.dist < c.dist else (c, p)
                rear.speed = min(rear.speed, front.speed * 0.8)
                rear.dist = min(rear.dist, front.dist - (CAR_H - 4) / PX_PER_M)

    def check_finish(self):
        p, c = self.player, self.cpu
        if p.dist >= RACE_M or c.dist >= RACE_M:
            self.state = "over"
            if p.dist >= c.dist:
                self.winner = "player"
                self.result_text = f"Your time: {self.race_time:.1f} s"
            else:
                self.winner = "cpu"
                gap = c.dist - p.dist
                self.result_text = f"You finished {gap:.0f} m behind"

    # ---------------- Drawing ----------------
    def draw(self):
        c = self.canvas
        c.delete("all")
        p, cpu = self.player, self.cpu
        scroll = (p.dist * PX_PER_M)

        # grass stripes
        off = scroll % 120
        for y0 in range(-120, H + 120, 120):
            y = y0 + off
            c.create_rectangle(0, y, W, y + 60, fill=GRASS_DARK, outline="")

        # road
        c.create_rectangle(ROAD_L, 0, ROAD_R, H, fill=ROAD, outline="")
        c.create_line(ROAD_L, 0, ROAD_L, H, fill="white", width=4)
        c.create_line(ROAD_R, 0, ROAD_R, H, fill="white", width=4)

        # lane dashes
        lane_w = (ROAD_R - ROAD_L) / LANES
        off = scroll % 80
        for i in range(1, LANES):
            x = ROAD_L + lane_w * i
            for y0 in range(-80, H + 80, 80):
                y = y0 + off
                c.create_line(x, y, x, y + 40, fill="#d8d8d8", width=3)

        # start line
        y_start = PLAYER_Y + p.dist * PX_PER_M
        if y_start < H + 20:
            c.create_rectangle(ROAD_L, y_start - 3, ROAD_R, y_start + 3, fill="white", outline="")

        # finish line (checkered)
        y_fin = PLAYER_Y - (RACE_M - p.dist) * PX_PER_M
        if -60 < y_fin < H + 60:
            size = 20
            cols = int((ROAD_R - ROAD_L) / size)
            for row in range(2):
                for col in range(cols):
                    color = "white" if (row + col) % 2 == 0 else "black"
                    x1 = ROAD_L + col * size
                    y1 = y_fin - size + row * size
                    c.create_rectangle(x1, y1, x1 + size, y1 + size, fill=color, outline="")
            c.create_text(W // 2, y_fin - 40, text="FINISH", fill="white",
                          font=("Consolas", 16, "bold"))

        # computer car (position relative to the player)
        cpu_y = PLAYER_Y - (cpu.dist - p.dist) * PX_PER_M
        if -CAR_H < cpu_y < H + CAR_H:
            self.draw_car(c, cpu.x, cpu_y, cpu.body, cpu.roof)
        elif cpu_y <= -CAR_H:
            c.create_text(cpu.x, 22, text="▲ CPU", fill="#ff8a80", font=("Consolas", 12, "bold"))
        else:
            c.create_text(cpu.x, H - 20, text="▼ CPU", fill="#ff8a80", font=("Consolas", 12, "bold"))

        # player car
        self.draw_car(c, p.x, PLAYER_Y, p.body, p.roof)

        # messages
        if self.state == "countdown":
            n = math.ceil(self.countdown)
            self.big_text(str(n), "Get ready!")
        elif self.state == "race" and self.race_time < 0.7:
            self.big_text("GO!", "")
        if self.paused:
            self.big_text("PAUSED", "Press P to resume")
        if self.state == "over":
            title = "YOU WIN! 🏆" if self.winner == "player" else "COMPUTER WINS"
            self.big_text(title, f"{self.result_text}\nPress R to race again")

        self.draw_panel()

    def big_text(self, title, subtitle):
        c = self.canvas
        c.create_rectangle(40, H // 2 - 80, W - 40, H // 2 + 80, fill="#000000",
                           stipple="gray50", outline="")
        c.create_text(W // 2, H // 2 - 25, text=title, fill="white",
                      font=("Consolas", 34, "bold"))
        if subtitle:
            c.create_text(W // 2, H // 2 + 35, text=subtitle, fill="white",
                          font=("Consolas", 13), justify="center")

    @staticmethod
    def draw_car(c, x, y, body, roof):
        hw, hh = CAR_W / 2, CAR_H / 2
        # wheels
        for wy in (y - hh + 8, y + hh - 22):
            c.create_rectangle(x - hw - 3, wy, x - hw + 3, wy + 14, fill="#111", outline="")
            c.create_rectangle(x + hw - 3, wy, x + hw + 3, wy + 14, fill="#111", outline="")
        # body
        c.create_rectangle(x - hw, y - hh, x + hw, y + hh, fill=body, outline="#111", width=1)
        # windows + roof
        c.create_rectangle(x - hw + 5, y - hh + 16, x + hw - 5, y - hh + 28, fill="#9ad7ff", outline="")
        c.create_rectangle(x - hw + 6, y - hh + 28, x + hw - 6, y + hh - 18, fill=roof, outline="")
        c.create_rectangle(x - hw + 5, y + hh - 18, x + hw - 5, y + hh - 10, fill="#9ad7ff", outline="")
        # lights
        c.create_rectangle(x - hw + 3, y - hh, x - hw + 10, y - hh + 5, fill="#fff59d", outline="")
        c.create_rectangle(x + hw - 10, y - hh, x + hw - 3, y - hh + 5, fill="#fff59d", outline="")
        c.create_rectangle(x - hw + 3, y + hh - 4, x - hw + 10, y + hh, fill="#ff1744", outline="")
        c.create_rectangle(x + hw - 10, y + hh - 4, x + hw - 3, y + hh, fill="#ff1744", outline="")

    def draw_panel(self):
        s = self.panel
        s.delete("all")
        p, cpu = self.player, self.cpu

        s.create_text(PANEL_W // 2, 28, text="SPEED", fill="#9aa0b5", font=("Consolas", 12, "bold"))
        s.create_text(PANEL_W // 2, 70, text=f"{p.speed:3.0f}", fill=TEXT, font=("Consolas", 40, "bold"))
        s.create_text(PANEL_W // 2, 105, text="km/h", fill="#9aa0b5", font=("Consolas", 12))

        # speed bar
        bx1, bx2, by = 20, PANEL_W - 20, 125
        s.create_rectangle(bx1, by, bx2, by + 12, outline="#444", fill="#222")
        frac = p.speed / MAX_KMH
        color = "#66bb6a" if frac < 0.7 else "#ffca28" if frac < 0.9 else "#ef5350"
        s.create_rectangle(bx1, by, bx1 + (bx2 - bx1) * frac, by + 12, outline="", fill=color)
        s.create_text(PANEL_W // 2, by + 28, text=f"max {MAX_KMH} km/h", fill="#6c7089",
                      font=("Consolas", 10))

        # race progress track
        top, bottom = 200, 480
        tx = PANEL_W // 2
        s.create_text(tx, top - 22, text="RACE", fill="#9aa0b5", font=("Consolas", 12, "bold"))
        s.create_line(tx, top, tx, bottom, fill="#444", width=6)
        s.create_text(tx + 38, top, text="FIN", fill="white", font=("Consolas", 10, "bold"))
        s.create_text(tx + 38, bottom, text="START", fill="#6c7089", font=("Consolas", 9))
        for car, col, label, dx in ((cpu, "#ef5350", "CPU", 14), (p, "#42a5f5", "YOU", -14)):
            f = max(0.0, min(1.0, car.dist / RACE_M))
            y = bottom - (bottom - top) * f
            s.create_oval(tx - 8 + dx, y - 8, tx + 8 + dx, y + 8, fill=col, outline="")
            anchor = "e" if dx < 0 else "w"
            s.create_text(tx + dx + (-12 if dx < 0 else 12), y, text=label, fill=col,
                          font=("Consolas", 9, "bold"), anchor=anchor)

        left = max(0, RACE_M - p.dist)
        s.create_text(PANEL_W // 2, 510, text=f"{left:,.0f} m to go", fill=TEXT, font=("Consolas", 12))
        s.create_text(PANEL_W // 2, 534, text=f"Time {self.race_time:5.1f} s", fill="#9aa0b5",
                      font=("Consolas", 11))

        s.create_text(PANEL_W // 2, 590,
                      text="↑/W go   ↓/S brake\n←/A →/D steer\nP pause   R restart",
                      fill="#6c7089", font=("Consolas", 10), justify="center")


def main():
    root = tk.Tk()
    RacingGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()

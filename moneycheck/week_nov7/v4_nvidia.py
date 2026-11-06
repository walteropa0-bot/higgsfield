"""TUE - Nvidia: nearly -$1.4 trillion since its Oct 2026 record. 2022: -66% (Nov 2021 -> Oct 2022 closes).
Then +1,100% in 20 months (Oct 2022 -> Jun 2024). Objective history, no prediction, no recommendation."""
import math
import sys

import numpy as np

import eng14 as E
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, partial, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, NAVY, RED,
                   RED_HI, DARKCARD, kline, kwords, topic, footnote, follow, figure, rays, rain)
from PIL import Image

DUR = 25.0
NF = int(DUR * FPS)
NAME = "tue_nvidia_rollercoaster"


def jag(p0, p1, n, amp, seed):
    rng = np.random.default_rng(seed)
    pts = [p0]
    for i in range(1, n):
        u = i / n
        pts.append((lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u) + float(rng.uniform(-amp, amp))))
    pts.append(p1)
    return pts


CRASH_NOW = jag((150, 760), (930, 1150), 16, 26, 3)
DOWN22 = jag((150, 650), (520, 1130), 14, 30, 7)
UP24 = jag((520, 1130), (930, 650), 16, 34, 11)


def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.0))
    kline(f, 540, 410, "NVIDIA JUST LOST", 70, WHITE, lt, -1, a)
    kline(f, 540, 505, "NEARLY $1.4 TRILLION", 82, RED_HI, lt, -1, a)
    kline(f, 540, 580, "SINCE ITS OCTOBER RECORD", 28, MUTED, lt, 0.3, a, w="xb", track=0.2)
    f.dash(120, 1180, 960, 1180, MUTED, 0.4 * a)
    f.line(CRASH_NOW, RED, a, 7)
    hx, hy = CRASH_NOW[-1]
    f.halo(hx, hy, 90 + 20 * math.sin(t * 6), RED, 0.85 * a)
    f.circ(hx, hy, 11, RED_HI, a)
    for i in range(6):
        u = (lt * 0.55 + i / 6) % 1.0
        f.bill(300 + i * 95 + 40 * math.sin(u * 6 + i), 1080 - 330 * u, 0.7, a * 0.8 * math.sin(math.pi * u), ang=u * 3 + i)


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 520, "THIS ISN'T NEW.", 92, WHITE, lt, 0.05, a)
    yr = 2026 - int(round(5 * eio(prog(lt, 0.6, 1.6))))
    p = prog(lt, 0.5, 0.3)
    f.pill(540, 660, f"BACK TO {yr}", 44, a * eo(p), fill=GOLD, tc=NAVY, track=0.2)
    for i in range(10):
        u = (lt * 1.6 + i / 10) % 1.0
        y = 800 + i * 50
        f.line([(1000 - u * 900, y), (1000 - u * 900 + 120, y)], WHITE, 0.18 * a, 3)
    figure(f, 540, 1250, 110, a, spot=0.6)


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "NOV 2021 → OCT 2022", 34, MUTED, lt, 0.0, a, w="xb", track=0.15)
    v = 66 * eio(prog(lt, 0.3, 1.8))
    f.text(540, 520, f"−{round(v)}%", 150, RED_HI, a * eo(prog(lt, 0.2, 0.3)), "black")
    f.dash(120, 1180, 960, 1180, MUTED, 0.4 * a)
    pts = partial(DOWN22, max(0.002, eio(prog(lt, 0.3, 1.8))))
    f.line(pts, RED, a, 7)
    hx, hy = pts[-1]
    f.halo(hx, hy, 80, RED, 0.8 * a)
    for i in range(4):
        tl = 1.4 + 0.18 * i
        mv = eio(prog(lt, tl, 1.0))
        x = 620 + i * 90 + mv * 500
        f.pawn(x, 1170, 80, mixc(WHITE, RED, 0.6), a * (1 - prog(lt, tl + 0.8, 0.3)), abs(math.sin(lt * 12)) * 5 * (mv > 0))
        if lt > tl:
            f.pill(x, 1060, "SOLD", 14, a * (1 - prog(lt, tl + 0.8, 0.3)), fill=RED, tc=WHITE, padx=11, pady=6)


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "THEN: OCT 2022 → JUN 2024", 34, MUTED, lt, 0.0, a, w="xb", track=0.15)
    v = 1100 * eio(prog(lt, 0.3, 2.0))
    f.text(540, 520, "+" + format(int(round(v / 10) * 10), ",") + "%", 140, GREEN_HI, a * eo(prog(lt, 0.2, 0.3)), "black")
    f.dash(120, 1180, 960, 1180, MUTED, 0.4 * a)
    f.line(DOWN22, RED, 0.35 * a, 5)
    pts = partial(UP24, max(0.002, eio(prog(lt, 0.3, 2.0))))
    f.line(pts, GREEN, a, 7)
    hx, hy = pts[-1]
    rays(f, hx, hy, t, a * eo(prog(lt, 2.2, 0.4)), GREEN)
    f.halo(hx, hy, 90, GREEN, 0.85 * a)
    f.pawn(hx, hy - 4, 90, WHITE, a)
    f.burst(hx, hy - 20, prog(lt, 2.3, 1.4), seed=6, n=20, spread=420, a=a)
    kline(f, 540, 1290, "IN ABOUT 20 MONTHS", 26, WHITE, lt, 2.4, a, w="xb", track=0.2)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 430, "EVEN THE BIGGEST WINNERS", 52, WHITE, lt, 0.05, a)
    kline(f, 540, 530, "CRASH. HARD.", 104, RED_HI, lt, 0.5, a)
    sx = lambda pts, k: [(lerp(150, 930, (x - 150) / 780 * k), y) for x, y in pts]
    full = [(150 + (x - 150) * 0.42, 650 + (y - 650) * 0.7) for x, y in DOWN22] + \
           [(150 + (520 - 150) * 0.42 + (x - 520) * 0.8, 650 + (y - 650) * 0.7) for x, y in UP24[1:]]
    last = full[-1]
    full += jag(last, (930, 900), 6, 18, 5)[1:]
    p = eio(prog(lt, 0.3, 2.4))
    pts = partial(full, max(0.002, p))
    cols = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cols.append(RED if y1 > y0 else GREEN)
    f.cline(pts, cols, a, 6)
    hx, hy = pts[-1]
    f.pawn(hx, hy - 4, 80, WHITE, a, abs(math.sin(lt * 9)) * 4)


def b5(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.4))
    kline(f, 540, 480, "VOLATILITY IS", 70, WHITE, lt, 0.05, a)
    kline(f, 540, 575, "THE PRICE OF GROWTH.", 64, GOLD_HI, lt, 0.5, a)
    kline(f, 540, 665, "NOT A PREDICTION — JUST HISTORY.", 26, MUTED, lt, 1.0, a, w="xb", track=0.15)
    figure(f, 540, 1200, 140, a, ring=1.0, spot=0.9)
    follow(f, lt, 1.5, a)


BEATS = [(0.0, 4.0, b0), (4.0, 7.2, b1), (7.2, 11.6, b2), (11.6, 16.4, b3), (16.4, 20.6, b4), (20.6, DUR, b5)]
SHAKES = [(9.3, 0.4, 7), (14.0, 0.45, 9)]
FLASHES = [(13.95, 0.22, 0.3)]


def tint(t):
    k = max(0.2 * (1 - prog(t, 3.0, 0.8)), 0.18 * prog(t, 7.6, 0.4) * (1 - prog(t, 11.3, 0.4)))
    return (RED, k) if k > 0.01 else None


def persistent(f, t):
    topic(f, "NVIDIA")
    footnote(f, "NVDA CLOSING PRICES, SPLIT-ADJUSTED · VALUE LOSS AS OF NOV 5, 2026 · FACTS, NOT A RECOMMENDATION")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES, tint).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES, tint).resize((360, 640), Image.LANCZOS)


def cover():
    f = E.compose(1.5, BEATS, DUR, persistent)
    E.post(f.img, 0.0, tint=(RED, 0.18)).save(f"cover_{NAME}.png")


EVENTS = [(0.0, "impact", 0.55), (0.0, "bass", 0.5), (0.05, "sweep_down", 0.5), (0.35, "pop", 0.4),
          (4.0, "whoosh", 0.5), (4.1, "pop", 0.45), (4.5, "swoosh_up", 0.4)] + [(4.6 + 0.16 * i, "tick", 0.25) for i in range(10)] + [
          (7.2, "whoosh", 0.5), (7.3, "pop", 0.4), (7.5, "sweep_down", 0.55), (9.3, "impact", 0.55), (9.3, "bass", 0.45)] + [
          (8.6 + 0.18 * i, "pop", 0.25) for i in range(4)] + [
          (11.6, "whoosh", 0.5), (11.7, "pop", 0.4), (11.9, "riser", 0.5), (13.95, "cash", 0.6), (14.0, "impact", 0.5),
          (14.0, "sparkle", 0.45)] + [(14.1 + 0.12 * i, "coin_p", 0.4, 2093 + 140 * i) for i in range(7)] + [
          (16.4, "whoosh", 0.5), (16.5, "pop", 0.4), (16.9, "bass", 0.5), (16.9, "impact", 0.4)] + [
          (17.0 + 0.3 * i, "tick", 0.2) for i in range(7)] + [
          (20.6, "whoosh", 0.5), (20.7, "pop", 0.4), (21.1, "ding", 0.45), (21.6, "pop", 0.35), (22.1, "pop", 0.35),
          (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)

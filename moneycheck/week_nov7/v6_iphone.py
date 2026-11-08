"""THU - First iPhone ($599, June 29, 2007) or $599 of Apple stock? $4.36 (split-adjusted close) -> $344.17 (Nov 5, 2026 close)
= 79x -> about $47,299 (price only, no dividends). Objective history, no recommendation."""
import math
import sys

import numpy as np

import eng14 as E
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, partial, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, NAVY, RED,
                   RED_HI, DARKCARD, kline, kwords, topic, footnote, follow, figure, rays, rain, phone, money)
from PIL import Image

DUR = 24.0
NF = int(DUR * FPS)
NAME = "thu_iphone_vs_apple_stock"
VAL = 599 / (122.04 / 28) * 344.17


def chart_icon(f, x, y, s, a, c=GREEN):
    f.rect(x - 120 * s, y - 120 * s, x + 120 * s, y + 120 * s, DARKCARD, a, r=24 * s)
    f.rect(x - 120 * s, y - 120 * s, x + 120 * s, y + 120 * s, c, a, r=24 * s, w=4 * s)
    pts = [(x - 85 * s, y + 60 * s), (x - 40 * s, y + 25 * s), (x - 5 * s, y + 40 * s), (x + 30 * s, y - 15 * s),
           (x + 55 * s, y - 5 * s), (x + 85 * s, y - 70 * s)]
    f.line(pts, c, a, 7 * s)
    f.poly([(x + 85 * s, y - 92 * s), (x + 100 * s, y - 60 * s), (x + 66 * s, y - 64 * s)], c, a)


def apple_path():
    rng = np.random.default_rng(14)
    pts = []
    dips = [(0.07, 0.55), (0.3, 0.3), (0.45, 0.25), (0.58, 0.32), (0.7, 0.3), (0.82, 0.25)]
    for i in range(61):
        u = i / 60
        v = (u ** 2.2) * 0.98 + 0.02
        for c, d in dips:
            v *= 1 - d * math.exp(-((u - c) / 0.025) ** 2)
        pts.append((150 + 780 * u, 1150 - 560 * v + float(rng.uniform(-6, 6))))
    return pts


AP = apple_path()


def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.2))
    kline(f, 540, 410, "2007: THE FIRST IPHONE", 64, WHITE, lt, -1, a)
    kline(f, 540, 500, "COST $599.", 86, GOLD_HI, lt, -1, a)
    kwords(f, 540, 590, [("WHAT IF YOU BOUGHT", WHITE), ("APPLE STOCK", GREEN_HI), ("INSTEAD?", WHITE)], 40, lt, 0.4, a)
    phone(f, 300, 920, 1.0, a)
    f.text(300, 1110, "$599", 44, WHITE, a, "black")
    f.text(540, 920, "VS", 64, GOLD_HI, a * eo(prog(lt, 0.9, 0.3)), "black")
    pc = eo(prog(lt, 1.1, 0.4))
    chart_icon(f, 780, 920, 1.0, a * (0.35 + 0.65 * pc))
    f.text(780, 1110, "$599", 44, GREEN_HI, a * (0.35 + 0.65 * pc), "black")


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 430, "THE PHONE:", 64, WHITE, lt, 0.05, a)
    kline(f, 540, 520, "OUTDATED FOR YEARS.", 58, MUTED, lt, 0.5, a)
    g = eo(prog(lt, 0.8, 1.2))
    phone(f, 540, 900, 1.3, a, c=mixc(WHITE, (110, 120, 140), g), screen=mixc((30, 48, 86), (14, 20, 34), g))
    bx, by = 540, 870
    f.rect(bx - 48, by - 22, bx + 40, by + 22, mixc(WHITE, MUTED, g), a, r=5, w=4)
    f.rect(bx + 40, by - 9, bx + 50, by + 9, mixc(WHITE, MUTED, g), a, r=2)
    f.rect(bx - 42, by - 16, bx - 42 + 76 * (1 - g * 0.9), by + 16, mixc(GREEN, RED, g), a, r=3)
    pp = prog(lt, 1.8, 0.4)
    f.pill(540, 1170, "NO MORE UPDATES", 26 * (0.8 + 0.2 * eback(pp)), a * eo(pp), fill=None, outline=RED, tc=RED_HI, track=0.18)


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "THE STOCK:", 52, WHITE, lt, 0.05, a)
    g = eio(prog(lt, 0.5, 3.4))
    v = 599 * (1 + (VAL / 599 - 1) * g)
    f.text(540, 510, money(v), 120, GREEN_HI if g > 0.98 else WHITE, a * eo(prog(lt, 0.3, 0.3)), "black")
    f.dash(120, 1170, 960, 1170, MUTED, 0.4 * a)
    pts = partial(AP, max(0.002, g))
    f.line(pts, GREEN, a, 6)
    hx, hy = pts[-1]
    f.halo(hx, hy, 80, GREEN, 0.8 * a)
    f.pawn(hx, hy - 4, 80, WHITE, a, abs(math.sin(lt * 9)) * 4 * (g < 1))
    f.text(160, 1215, "2007", 26, WHITE, a, "black")
    f.text(920, 1215, "2026", 26, WHITE if g > 0.98 else MUTED, a, "black")
    kline(f, 540, 1290, "$4.36 → $344.17 PER SHARE", 26, MUTED, lt, 1.2, a, w="xb", track=0.12)


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.6))
    rays(f, 540, 820, t, a * eo(prog(lt, 0.2, 0.4)), GREEN)
    kline(f, 540, 520, "THAT'S 79×", 132, GOLD_HI, lt, 0.05, a)
    kline(f, 540, 640, "YOUR MONEY.", 66, WHITE, lt, 0.5, a)
    f.burst(540, 900, prog(lt, 0.3, 1.5), seed=8, n=22, spread=460, a=a)
    rain(f, lt, 0.6, a * 0.7, n=14)
    kline(f, 540, 1230, "(IF YOU NEVER SOLD)", 28, MUTED, lt, 1.0, a, w="xb", track=0.18)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 470, "EVERY PURCHASE HAS", 58, WHITE, lt, 0.05, a)
    kline(f, 540, 560, "A HIDDEN PRICE TAG.", 64, GOLD_HI, lt, 0.5, a)
    kline(f, 540, 650, "IT'S CALLED OPPORTUNITY COST.", 28, MUTED, lt, 1.0, a, w="xb", track=0.12)
    x, y = 540, 950
    p = eo(prog(lt, 0.8, 0.5))
    sw = 0.08 * math.sin(t * 3)
    c, s_ = math.cos(sw), math.sin(sw)
    R = lambda px, py: (x + px * c - py * s_, y + px * s_ + py * c)
    f.line([(x, y - 200), R(-100, -40)], WHITE, a * p, 3)
    f.poly([R(-140, -40), R(100, -40), R(150, 20), R(100, 80), R(-140, 80)], GOLD, a * p)
    f.circ(*R(85, 20), 12, NAVY, a * p)
    f.text(*R(-25, 20), "?", 90, NAVY, a * p, "black")


def b5(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.0))
    kline(f, 540, 480, "WHAT WOULD YOU", 72, WHITE, lt, 0.05, a)
    kline(f, 540, 575, "HAVE PICKED?", 84, GOLD_HI, lt, 0.4, a)
    phone(f, 330, 920, 0.9, a)
    f.text(540, 920, "OR", 48, MUTED, a, "black")
    chart_icon(f, 750, 920, 0.85, a)
    follow(f, lt, 1.0, a)


BEATS = [(0.0, 4.2, b0), (4.2, 8.0, b1), (8.0, 13.2, b2), (13.2, 16.8, b3), (16.8, 21.0, b4), (21.0, DUR, b5)]
SHAKES = [(13.25, 0.35, 8)]
FLASHES = [(13.2, 0.22, 0.3)]


def persistent(f, t):
    topic(f, "IPHONE VS APPLE STOCK")
    footnote(f, "PRICE ONLY, NO DIVIDENDS · SPLIT-ADJUSTED · JUN 29, 2007 → NOV 5, 2026 CLOSE · PAST ≠ FUTURE")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES).resize((360, 640), Image.LANCZOS)


def cover():
    f = E.compose(2.6, BEATS, DUR, persistent)
    E.post(f.img, 0.0).save(f"cover_{NAME}.png")


EVENTS = [(0.0, "bass", 0.55), (0.05, "pop", 0.45), (0.45, "pop", 0.4), (0.9, "pop", 0.45), (1.1, "coin", 0.45),
          (4.2, "whoosh", 0.5), (4.25, "pop", 0.4), (4.7, "pop", 0.4), (5.0, "sweep_down", 0.45), (6.0, "alert", 0.35),
          (8.0, "whoosh", 0.5), (8.05, "pop", 0.4), (8.4, "riser", 0.5)] + [
          (8.6 + 0.25 * i, "coin_p", 0.28, 1700 + 60 * i) for i in range(13)] + [(11.9, "ding", 0.55),
          (13.2, "impact", 0.55), (13.2, "cash", 0.65), (13.25, "sparkle", 0.5), (13.3, "bass", 0.45)] + [
          (13.35 + 0.12 * i, "coin_p", 0.4, 2093 + 140 * i) for i in range(7)] + [
          (16.8, "whoosh", 0.5), (16.9, "pop", 0.4), (17.3, "pop", 0.4), (17.6, "ding", 0.4), (17.8, "pop", 0.35),
          (21.0, "whoosh", 0.5), (21.1, "pop", 0.45), (21.45, "pop", 0.45), (22.0, "pop", 0.35),
          (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)

"""WED - A 1% fee can cost you $316,661: $500/month for 40 years at 7% ($1,312,407) vs 6% after a 1% fee ($995,745)."""
import math
import sys

import eng14 as E
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, NAVY, RED, RED_HI,
                   DARKCARD, kline, kwords, topic, footnote, follow, figure, bar, money)
from PIL import Image

DUR = 24.0
NF = int(DUR * FPS)
NAME = "wed_one_percent_fee"
A, B = 1312407, 995745


def tower(f, x, base, h, a, c=(30, 146, 82), leak=0.0, t=0.0):
    n = max(1, int(h / 22))
    for j in range(n):
        yy = base - 11 - j * 22
        f.rect(x - 90, yy - 9, x + 90, yy + 9, c, a * 0.95, r=4)
        f.rect(x - 16, yy - 9, x + 16, yy + 9, GOLD, a * 0.8)
    if leak > 0:
        f.pill(x + 150, base - h * 0.5, "1% FEE", 22, a * leak, fill=RED, tc=WHITE, track=0.12)
        for i in range(5):
            u = (t * 1.3 + i / 5) % 1.0
            f.coin(x + 110 + 20 * math.sin(i), base - h * 0.5 + 40 + u * 360, 13, a * leak * (1 - u), spin=t * 8 + i)


def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.2))
    kwords(f, 540, 420, [("THIS", WHITE), ("1% FEE", RED_HI)], 90, lt, -1, a)
    kline(f, 540, 520, "CAN COST YOU", 52, WHITE, lt, -1, a)
    kline(f, 540, 615, "$316,661", 104, GOLD_HI, lt, -1, a)
    tower(f, 470, 1230, 440, a, leak=1.0, t=t)


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "SAME PLAN FOR BOTH:", 34, MUTED, lt, 0.0, a, w="xb", track=0.2)
    for i, s in enumerate(("$500 EVERY MONTH", "FOR 40 YEARS", "7% A YEAR BEFORE FEES")):
        p = prog(lt, 0.35 + 0.4 * i, 0.35)
        f.pill(540, 500 + 95 * i, s, 34 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=None, outline=WHITE, tc=WHITE, track=0.14)
    figure(f, 330, 1210, 130, a, ring=1.0, spot=0.6)
    figure(f, 750, 1210, 130, a, spot=0.6)
    f.text(330, 1265, "NO FEE", 26, GREEN_HI, a * eo(prog(lt, 1.6, 0.3)), "black", track=0.15)
    f.text(750, 1265, "1% FEE", 26, RED_HI, a * eo(prog(lt, 1.8, 0.3)), "black", track=0.15)


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 380, "AFTER 40 YEARS", 30, MUTED, lt, 0.0, a, w="xb", track=0.25)
    g = eio(prog(lt, 0.4, 2.6))
    base = 1170
    h1, h2 = 600 * g, 600 * B / A * g
    bar(f, 330, base, 230, h1, GREEN, a)
    bar(f, 750, base, 230, h2, GOLD_HI, a)
    f.text(330, base - h1 - 50, money(A * g), 54, GREEN_HI, a * eo(prog(lt, 0.4, 0.3)), "black")
    f.text(750, base - h2 - 50, money(B * g), 54, GOLD_HI, a * eo(prog(lt, 0.4, 0.3)), "black")
    f.line([(180, base), (900, base)], MUTED, 0.5 * a, 2)
    f.text(330, base + 46, "NO FEE", 26, GREEN_HI, a, "black", track=0.15)
    f.text(750, base + 46, "1% FEE", 26, RED_HI, a, "black", track=0.15)


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 410, "$316,661 GONE.", 92, RED_HI, lt, 0.05, a)
    kline(f, 540, 500, "THAT'S 24% OF YOUR MONEY.", 44, WHITE, lt, 0.5, a)
    base = 1180
    h1, h2 = 600, 600 * B / A
    bar(f, 330, base, 230, h1, GREEN, a)
    bar(f, 750, base, 230, h2, GOLD_HI, a)
    gp = eo(prog(lt, 0.8, 0.5))
    f.rect(640, base - h1, 860, base - h2 - 8, RED, 0.18 * a * gp, r=10)
    f.dash(640, base - h1, 860, base - h1, RED_HI, a * gp, w=3)
    f.dash(640, base - h1, 640, base - h2 - 8, RED_HI, a * gp, w=3)
    f.dash(860, base - h1, 860, base - h2 - 8, RED_HI, a * gp, w=3)
    f.text(750, base - (h1 + h2) / 2, "FEES", 34, RED_HI, a * gp, "black", track=0.2)
    for i in range(6):
        u = (lt * 1.1 + i / 6) % 1.0
        f.coin(750 + 60 * math.sin(i * 2.1), base - h1 + 30 + u * 140, 14, a * gp * (1 - u), spin=lt * 9 + i)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kwords(f, 540, 520, [("SAME MONEY.", WHITE), ("SAME MARKET.", WHITE)], 58, lt, 0.05, a)
    kline(f, 540, 640, "JUST A 1% FEE.", 84, RED_HI, lt, 0.8, a)
    tower(f, 540, 1230, 360 * (1 - 0.24 * eio(prog(lt, 1.0, 1.5))), a, leak=eo(prog(lt, 1.0, 0.4)), t=t)


def b5(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.0))
    kline(f, 540, 520, "CHECK WHAT", 84, WHITE, lt, 0.05, a)
    kline(f, 540, 625, "YOU PAY.", 104, GOLD_HI, lt, 0.4, a)
    x, y = 540, 930
    p = eo(prog(lt, 0.7, 0.5))
    f.circ(x - 30, y - 30, 100 * p, GOLD_HI, a * p, w=12)
    f.line([(x + 42, y + 42), (x + 130, y + 130)], GOLD_HI, a * p, 22)
    f.text(x - 30, y - 30, "%", 90 * p, WHITE, a * p, "black")
    follow(f, lt, 1.0, a)


BEATS = [(0.0, 4.2, b0), (4.2, 8.0, b1), (8.0, 13.2, b2), (13.2, 17.2, b3), (17.2, 21.0, b4), (21.0, DUR, b5)]
SHAKES = [(13.25, 0.35, 7)]
FLASHES = []


def tint(t):
    k = 0.16 * prog(t, 13.2, 0.4) * (1 - prog(t, 16.9, 0.4))
    return (RED, k) if k > 0.01 else None


def persistent(f, t):
    topic(f, "INVESTING FEES")
    footnote(f, "$500/MONTH · 40 YEARS · 7% VS 6% NET RETURN · ILLUSTRATION · NOT GUARANTEED")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES, tint).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES, tint).resize((360, 640), Image.LANCZOS)


def cover():
    f = E.compose(1.0, BEATS, DUR, persistent)
    E.post(f.img, 0.0).save(f"cover_{NAME}.png")


EVENTS = [(0.0, "bass", 0.55), (0.0, "alert", 0.4)] + [(0.3 + 0.45 * i, "coin_p", 0.25, 1500 + 80 * i) for i in range(8)] + [
          (4.2, "whoosh", 0.5), (4.3, "pop", 0.4), (4.55, "pop", 0.45), (4.95, "pop", 0.45), (5.35, "pop", 0.45),
          (5.8, "pop", 0.35), (6.0, "pop", 0.35), (8.0, "whoosh", 0.5), (8.1, "pop", 0.4), (8.4, "riser", 0.55)] + [
          (8.6 + 0.2 * i, "coin_p", 0.25, 1800 + 70 * i) for i in range(11)] + [(11.0, "ding", 0.5),
          (13.2, "whoosh", 0.5), (13.25, "impact", 0.55), (13.3, "sweep_down", 0.5), (13.8, "alert", 0.35)] + [
          (14.1 + 0.25 * i, "coin_p", 0.25, 1700 - 60 * i) for i in range(6)] + [
          (17.2, "whoosh", 0.5), (17.3, "pop", 0.4), (17.6, "pop", 0.4), (18.0, "bass", 0.45), (18.2, "sweep_down", 0.4),
          (21.0, "whoosh", 0.5), (21.1, "pop", 0.45), (21.45, "ding", 0.45), (21.8, "pop", 0.35), (22.1, "pop", 0.35),
          (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)

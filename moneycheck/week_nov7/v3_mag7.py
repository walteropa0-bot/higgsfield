"""MON - Buy the S&P 500 and ~1/3 of your money goes into 7 companies (~35%, late Oct 2026). Objective, no recommendation."""
import math
import sys

import eng14 as E
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, ca, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, NAVY, RED, RED_HI,
                   DARKCARD, kline, kwords, topic, footnote, follow, figure)
from PIL import Image

DUR = 24.0
NF = int(DUR * FPS)
NAME = "mon_magnificent_7"
SEVEN = ["NVIDIA", "MICROSOFT", "APPLE", "ALPHABET", "AMAZON", "META", "TESLA"]
OTHERS = (172, 186, 214)


def donut(f, cx, cy, r, w, share, a, c7=GOLD, crack=0.0):
    box = (f.X(cx - r), f.Y(cy - r), f.X(cx + r), f.Y(cy + r))
    f.d.arc(box, 0, 360, fill=ca(OTHERS, 0.55 * a), width=f.wpx(w))
    if share > 0.002:
        f.d.arc(box, -90, -90 + 360 * share, fill=ca(mixc(c7, RED, crack), a), width=f.wpx(w))


def waffle(f, x0, y0, cell, a, n7=35, t=0.0, fall=0.0, appear=1.0):
    for i in range(100):
        cx, cy = i % 10, i // 10
        x = x0 + cx * cell
        y = y0 + cy * cell
        gold = i < n7
        pa = eo(prog(appear * 100, i * 0.6, 8))
        if pa <= 0:
            continue
        c = mixc(GOLD, RED, fall) if gold else OTHERS
        yy = y + (fall * fall * 260 * ((i * 37) % 7 + 3) / 9 if gold else 0)
        f.rect(x + 3, yy + 3, x + cell - 3, yy + cell - 3, c, a * pa * (0.95 if gold else 0.45), r=5)


def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.2))
    kline(f, 540, 410, "BUY THE S&P 500...", 70, WHITE, lt, -1, a)
    kwords(f, 540, 505, [("AND ~1/3 OF YOUR MONEY", WHITE)], 52, lt, 0.25, a)
    kwords(f, 540, 572, [("GOES INTO JUST", WHITE), ("7 COMPANIES.", GOLD_HI)], 52, lt, 0.75, a)
    share = 0.35 * eio(prog(lt, 1.2, 1.4))
    donut(f, 540, 960, 250, 80, share, a)
    f.text(540, 935, "500", 96, WHITE, a * (1 - eo(prog(lt, 2.3, 0.3))), "black")
    f.text(540, 1010, "COMPANIES", 24, MUTED, a * (1 - eo(prog(lt, 2.3, 0.3))), "xb", track=0.25)
    p = prog(lt, 2.4, 0.4)
    f.text(540, 935, "7 = 35%", 68 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    f.text(540, 1010, "OF THE WHOLE INDEX", 22, WHITE, a * eo(p), "xb", track=0.2)


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 420, "THE MAGNIFICENT 7", 70, GOLD_HI, lt, 0.0, a)
    for i, nm in enumerate(SEVEN):
        p = prog(lt, 0.45 + 0.42 * i, 0.35)
        col, row = (i % 2, i // 2) if i < 6 else (0.5, 3)
        x = 330 + col * 420
        y = 600 + row * 150
        f.pill(x, y, nm, 34 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=DARKCARD, tc=WHITE, outline=GOLD, track=0.12)


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "IF THE S&P 500 WERE 100 SQUARES:", 34, WHITE, lt, 0.0, a, w="xb", track=0.05)
    waffle(f, 290, 470, 50, a, appear=prog(lt, 0.2, 1.6))
    p1, p2 = prog(lt, 1.9, 0.4), prog(lt, 2.4, 0.4)
    f.pill(330, 1040, "7 COMPANIES ≈ 35%", 26 * (0.8 + 0.2 * eback(p1)), a * eo(p1), fill=GOLD, tc=NAVY, track=0.12)
    f.pill(750, 1040, "OTHER 493 ≈ 65%", 26 * (0.8 + 0.2 * eback(p2)), a * eo(p2), fill=None, outline=OTHERS, tc=WHITE, track=0.12)


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "WHEN THEY FALL,", 66, WHITE, lt, 0.0, a)
    kline(f, 540, 480, "YOUR \"DIVERSIFIED\" FUND FALLS TOO.", 40, RED_HI, lt, 0.4, a)
    fall = eio(prog(lt, 1.0, 1.4))
    waffle(f, 290, 560, 50, a, fall=fall)
    pp = prog(lt, 2.2, 0.4)
    f.pill(540, 1150, "NOV 5, 2026: NASDAQ −5.5% IN ONE DAY", 24 * (0.8 + 0.2 * eback(pp)), a * eo(pp), fill=None,
           outline=RED, tc=RED_HI, track=0.08)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.0))
    kline(f, 540, 480, "NOT GOOD. NOT BAD.", 68, WHITE, lt, 0.05, a)
    kline(f, 540, 575, "JUST KNOW WHAT YOU OWN.", 58, GOLD_HI, lt, 0.6, a)
    x, y = 540, 900
    p = eo(prog(lt, 0.9, 0.5))
    f.circ(x - 30, y - 30, 110 * p, GOLD_HI, a * p, w=12)
    f.line([(x + 50, y + 50), (x + 140, y + 140)], GOLD_HI, a * p, 22)
    donut(f, x - 30, y - 30, 60 * p, 22, 0.35, a * p)
    figure(f, 540, 1240, 120, a, spot=0.7)
    follow(f, lt, 1.6, a)


BEATS = [(0.0, 4.2, b0), (4.2, 8.4, b1), (8.4, 12.8, b2), (12.8, 17.4, b3), (17.4, DUR, b4)]
SHAKES = [(13.9, 0.45, 8)]
FLASHES = []


def tint(t):
    k = 0.18 * prog(t, 13.8, 0.4) * (1 - prog(t, 17.0, 0.4))
    return (RED, k) if k > 0.01 else None


def persistent(f, t):
    topic(f, "S&P 500")
    footnote(f, "WEIGHTS ≈ LATE OCT 2026 (INDEX FUND HOLDINGS) · FACTS, NOT A RECOMMENDATION")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES, tint).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES, tint).resize((360, 640), Image.LANCZOS)


def cover():
    f = E.compose(3.6, BEATS, DUR, persistent)
    E.post(f.img, 0.0).save(f"cover_{NAME}.png")


EVENTS = [(0.0, "bass", 0.55), (0.3, "pop", 0.45), (0.8, "pop", 0.45), (1.2, "swoosh_up", 0.5), (2.6, "ding", 0.5),
          (2.65, "coin", 0.4), (4.2, "whoosh", 0.5), (4.25, "pop", 0.45)] + [
          (4.65 + 0.42 * i, "pop", 0.45) for i in range(7)] + [(7.6, "ding", 0.35),
          (8.4, "whoosh", 0.5), (8.45, "pop", 0.4)] + [(8.6 + 0.16 * i, "tick", 0.22) for i in range(10)] + [
          (10.3, "pop", 0.5), (10.8, "pop", 0.45), (12.8, "whoosh", 0.5), (12.85, "pop", 0.4), (13.2, "pop", 0.4),
          (13.8, "sweep_down", 0.55), (13.9, "impact", 0.6), (14.0, "bass", 0.45), (15.0, "alert", 0.4),
          (17.4, "whoosh", 0.5), (17.5, "pop", 0.45), (18.0, "pop", 0.45), (18.4, "ding", 0.45), (19.0, "pop", 0.35),
          (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)

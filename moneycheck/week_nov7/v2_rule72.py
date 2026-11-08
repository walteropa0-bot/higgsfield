"""SUN - The Rule of 72: how fast does your money double? (savings 1% -> 72 y, stocks ~7% -> ~10 y, credit card 24% -> 3 y)."""
import math
import sys

import eng14 as E
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, NAVY, RED, RED_HI,
                   DARKCARD, kline, kwords, topic, footnote, follow, figure, rays)
from PIL import Image

DUR = 24.0
NF = int(DUR * FPS)
NAME = "sun_rule_of_72"


def coins_double(f, cx, cy, lt, a, t0=0.6, step=0.75, levels=3):
    k = 0
    for i in range(levels):
        if lt >= t0 + i * step:
            k = i + 1
    n = 2 ** k
    p = eo(prog(lt, t0 + (k - 1) * step, 0.45)) if k else 1.0
    cols = min(n, 4)
    rows = (n + cols - 1) // cols
    r = 62 if n <= 2 else 50
    for j in range(n):
        gx, gy = j % cols, j // cols
        tx = cx + (gx - (cols - 1) / 2) * (r * 2.4)
        ty = cy + (gy - (rows - 1) / 2) * (r * 2.4)
        src = j // 2 if k else 0
        sx = cx + ((src % max(1, cols // 2 if n > 2 else 1)) - 0) * 0
        x, y = lerp(cx, tx, p), lerp(cy, ty, p)
        f.halo(x, y, r * 1.5, GOLD, 0.35 * a)
        f.coin(x, y, r, a, spin=0.0)
    if k:
        q = prog(lt, t0 + (k - 1) * step, 0.5)
        f.text(cx + 250, cy - 170, "×2", 70 * (0.8 + 0.2 * eback(q)), GREEN_HI, a * eo(q) * (1 - prog(lt, t0 + k * step - 0.1, 0.2) * (k < levels)), "black")


def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.8))
    kline(f, 540, 430, "HOW FAST DOES", 76, WHITE, lt, -1, a)
    kline(f, 540, 525, "YOUR MONEY DOUBLE?", 76, GOLD_HI, lt, -1, a)
    coins_double(f, 540, 930, lt, a)


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    p = prog(lt, 0.05, 0.4)
    f.text(390, 600, "72", 190 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    kline(f, 680, 600, "÷ RATE", 96, WHITE, lt, 0.35, a)
    kline(f, 540, 760, "= YEARS UNTIL", 62, WHITE, lt, 0.8, a)
    kline(f, 540, 840, "YOUR MONEY DOUBLES", 62, GREEN_HI, lt, 1.1, a)
    f.ring(540, 640, prog(lt, 0.1, 1.2), GOLD_HI, 0.7 * a, rmax=380)
    figure(f, 540, 1230, 120, a * eo(prog(lt, 1.4, 0.4)), spot=0.6)


def example(f, lt, a, label, lc, eq, ec):
    f.pill(540, 430, label, 28, a * eo(prog(lt, 0.05, 0.35)), fill=None, outline=lc, tc=lc, track=0.18)
    kline(f, 540, 545, eq, 84, ec, lt, 0.3, a)


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0)
    example(f, lt, a, "SAVINGS ACCOUNT AT 1%", MUTED, "72 ÷ 1 = 72 YEARS", WHITE)
    x0, x1, y = 150, 930, 980
    f.dash(x0, y, x1, y, MUTED, 0.5 * a)
    p = prog(lt, 0.6, 2.8) * 0.35
    f.line([(x0, y), (lerp(x0, x1, p), y)], MUTED, a, 6)
    for i, yr in enumerate((0, 24, 48, 72)):
        x = x0 + (x1 - x0) * yr / 72
        f.text(x, y + 50, f"{yr}Y", 24, WHITE if yr == 72 else MUTED, a, "black")
    figure(f, lerp(x0, x1, p), y - 4, 100, a, bob=abs(math.sin(lt * 5)) * 3)
    kline(f, 540, 1150, "THAT'S MOST OF A LIFETIME.", 30, MUTED, lt, 1.6, a, w="xb", track=0.12)


def stacks(f, lt, a, vals, labels, c, base=1180, x0=200, dx=225, t0=0.6, step=0.55, scale=0.0075):
    for i, (v, lab) in enumerate(zip(vals, labels)):
        p = eo(prog(lt, t0 + i * step, 0.45))
        if p <= 0:
            continue
        x = x0 + i * dx
        h = v * scale * p
        n = max(1, int(h / 22))
        for j in range(n):
            yy = base - 11 - j * 22
            f.rect(x - 70, yy - 9, x + 70, yy + 9, c, a * 0.95, r=4)
            f.rect(x - 14, yy - 9, x + 14, yy + 9, GOLD if c != GOLD else WHITE, a * 0.8)
        f.text(x, base - n * 22 - 40, lab, 34, WHITE, a * p, "black")


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0)
    example(f, lt, a, "STOCK MARKET AT ~7%", GREEN_HI, "72 ÷ 7 ≈ 10 YEARS", GREEN_HI)
    stacks(f, lt, a, [10, 20, 40, 80], ["$10K", "$20K", "$40K", "$80K"], (30, 146, 82), scale=6.0)
    for i, s in enumerate(("TODAY", "10 Y", "20 Y", "30 Y")):
        f.text(200 + i * 225, 1225, s, 24, MUTED, a * eo(prog(lt, 0.6 + i * 0.55, 0.4)), "xb", track=0.15)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "BUT IT WORKS AGAINST YOU TOO.", 44, RED_HI, lt, 0.0, a)
    f.pill(540, 485, "CREDIT CARD AT 24%", 28, a * eo(prog(lt, 0.4, 0.35)), fill=RED, tc=WHITE, track=0.16)
    kline(f, 540, 600, "72 ÷ 24 = 3 YEARS", 84, RED_HI, lt, 0.7, a)
    stacks(f, lt, a, [5, 10, 20, 40], ["$5K", "$10K", "$20K", "$40K"], (176, 52, 52), t0=1.1, step=0.45, scale=9.0)
    for i, s in enumerate(("TODAY", "3 Y", "6 Y", "9 Y")):
        f.text(200 + i * 225, 1225, s, 24, MUTED, a * eo(prog(lt, 1.1 + i * 0.45, 0.4)), "xb", track=0.15)
    f.halo(540, 900, 600, RED, 0.12 * a * (0.5 + 0.5 * math.sin(t * 8)) * prog(lt, 1.1, 0.4))
    kline(f, 540, 1290, "IF YOU DON'T PAY IT DOWN", 22, MUTED, lt, 1.8, a, w="xb", track=0.15)


def b5(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.4))
    rays(f, 540, 930, t, a * eo(prog(lt, 0.3, 0.5)), GOLD)
    kwords(f, 540, 470, [("MAKE", WHITE), ("72", GOLD_HI), ("WORK", WHITE)], 76, lt, 0.05, a)
    kline(f, 540, 580, "FOR YOU.", 110, GREEN_HI, lt, 0.5, a)
    f.text(540, 930, "72", 300 * (0.85 + 0.15 * eback(prog(lt, 0.3, 0.5))), GOLD_HI, a * eo(prog(lt, 0.3, 0.5)), "black")
    f.text(540, 1140, "NOT AGAINST YOU.", 36, RED_HI, a * eo(prog(lt, 1.0, 0.4)), "black", track=0.1)
    follow(f, lt, 1.5, a)


BEATS = [(0.0, 3.8, b0), (3.8, 7.6, b1), (7.6, 11.4, b2), (11.4, 15.4, b3), (15.4, 19.6, b4), (19.6, DUR, b5)]
SHAKES = [(16.1, 0.35, 7)]
FLASHES = []


def tint(t):
    k = 0.2 * prog(t, 15.9, 0.4) * (1 - prog(t, 19.3, 0.4))
    return (RED, k) if k > 0.01 else None


def persistent(f, t):
    topic(f, "THE RULE OF 72")
    footnote(f, "RULE OF THUMB · EXAMPLE RATES · RETURNS ARE NOT GUARANTEED · BEFORE TAXES & FEES")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES, tint).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES, tint).resize((360, 640), Image.LANCZOS)


def cover():
    f = E.compose(2.4, BEATS, DUR, persistent)
    E.post(f.img, 0.0).save(f"cover_{NAME}.png")


EVENTS = [(0.0, "bass", 0.55), (0.6, "coin", 0.55), (1.35, "coin_p", 0.5, 2093), (1.4, "coin_p", 0.45, 2637),
          (2.1, "coin_p", 0.5, 2349), (2.15, "coin_p", 0.45, 2960), (3.8, "whoosh", 0.5), (3.85, "pop", 0.55),
          (4.15, "pop", 0.45), (4.6, "ding", 0.45), (4.9, "pop", 0.4), (7.6, "whoosh", 0.5), (7.7, "pop", 0.45),
          (7.9, "pop", 0.45)] + [(8.3 + 0.35 * i, "tick", 0.25) for i in range(8)] + [
          (11.4, "whoosh", 0.5), (11.45, "pop", 0.45), (11.7, "pop", 0.45)] + [
          (12.0 + 0.55 * i, "coin_p", 0.45, 1800 + 300 * i) for i in range(4)] + [
          (15.4, "whoosh", 0.5), (15.45, "sweep_down", 0.45), (15.8, "alert", 0.5), (16.1, "impact", 0.55)] + [
          (16.5 + 0.45 * i, "bass", 0.35) for i in range(4)] + [
          (19.6, "whoosh", 0.5), (19.7, "pop", 0.45), (19.9, "swoosh_up", 0.45), (20.1, "ding", 0.5), (20.1, "sparkle", 0.45),
          (20.6, "pop", 0.35), (21.1, "pop", 0.35), (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)

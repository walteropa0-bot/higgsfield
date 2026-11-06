"""Moneycheck Short #9 - "Chip stocks just crashed. Before you buy the dip... dig deeper."
Market news of Nov 5, 2026 (facts only, no recommendations) + a 5-layer checklist shown as a mine.
Female voice (Samara X), no subtitles. 1080x1920, 30 fps. Anchors = exact word times (words.json).

Usage:  python3 render11.py stills 1.0 6.5 ...   |   python3 render11.py sheet out.png 1 2 3 ...
        python3 render11.py cover                |   python3 render11.py video
"""
import json
import math
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from lib10 import (W, H, FPS, F, post, font, clamp, prog, eo, eio, eback, lerp, mixc, qmix, partial, ca,
                   NAVY, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, RED, RED_HI, MINUS)

WORDS = json.load(open("words.json"))


def _n(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def at(word, k=1, end=False):
    n = 0
    for w in WORDS:
        if _n(w["text"]) == _n(word):
            n += 1
            if n == k:
                return float(w["end"] if end else w["start"])
    raise KeyError((word, k))


DUR = round(WORDS[-1]["end"] + 1.82, 2)
NF = int(round(DUR * FPS))
G = 1250
ND = "–"
DARKCARD = (20, 34, 62)


# ------------------------------------------------------------------ 1 hook: trillions vanished
def _stack_bills():
    rng = np.random.default_rng(3)
    return [(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(28)]


SB = _stack_bills()


def hook(f, t):
    tv = at("vanished")
    f.cam(540, 960, 1.0 + 0.04 * eio(t / 5.0))
    f.text(540, 340, "STOCK MARKET VALUE", 24, MUTED, 1, "sb", track=0.3)
    red = prog(t, tv, 0.4)
    f.text(540, 450, "TRILLIONS", 128 * (1 + 0.04 * math.sin(math.pi * prog(t, tv, 0.5))), mixc(WHITE, RED, red), 1, "black")
    pp = prog(t, at("single"), 0.35)
    f.pill(540, 565, "GONE IN ONE DAY", 26 * (0.8 + 0.2 * eback(pp)), eo(pp), fill=RED, tc=WHITE, track=0.2)
    n, x0, base = 14, 680, G
    f.halo(x0, base - 180, 260, GREEN, 0.25 * (1 - red))
    gone = 0
    for i in range(n):
        y = base - 13 - i * 26
        ti = tv + 0.06 * (n - 1 - i)
        u = prog(t, ti, 0.9)
        if u <= 0:
            f.rect(x0 - 150, y - 11, x0 + 150, y + 11, (30, 146, 82), 1, r=3)
            f.rect(x0 - 150, y - 11, x0 + 150, y - 7, GREEN_HI, 0.5, r=2)
            f.rect(x0 - 22, y - 11, x0 + 22, y + 11, GOLD, 0.9)
            continue
        gone += 1
        for j in range(2):
            a1, a2, a3 = SB[(2 * i + j) % len(SB)]
            x = x0 + a1 * 120 + (260 + 160 * a2) * u * (1 if j else -1) * 0.8
            yy = y - (520 + 200 * a3) * eo(u) + 260 * u * u
            f.bill(x, yy, 0.95, (1 - u) * 0.95, ang=a3 + u * 4 * (1 if j else -1))
    if gone:
        ea = eo(prog(t, tv + 0.5, 0.5))
        f.dash(x0 - 150, base - 14 * 26 - 4, x0 + 150, base - 14 * 26 - 4, MUTED, 0.5 * ea)
        f.dash(x0 - 150, base - 14 * 26 - 4, x0 - 150, base, MUTED, 0.5 * ea)
        f.dash(x0 + 150, base - 14 * 26 - 4, x0 + 150, base, MUTED, 0.5 * ea)
    f.dash(40, base + 2, 1040, base + 2, MUTED, 0.35)
    f.spot(330, base - 520, base + 16, 470, 0.8)
    f.halo(330, base + 2, 130, (130, 150, 200), 0.5, sy=0.15)
    f.pawn(330, base, 160, WHITE, 1)


# ------------------------------------------------------------------ 2 under pressure / buy the dip?
TILES = [((110, 600, 520, 860), "CHIPS", 1.0), ((530, 600, 760, 860), "AI CLOUD", 0.9), ((770, 600, 970, 860), "BIG TECH", 0.65),
         ((110, 870, 330, 1130), "BANKS", 0.3), ((340, 870, 520, 1130), "ENERGY", 0.25), ((530, 870, 700, 1130), "HEALTH", 0.25),
         ((710, 870, 850, 1130), "STAPLES", 0.2), ((860, 870, 970, 1130), "UTIL.", 0.2)]


def question(f, t):
    t0, tu, tb, td = at("so"), at("under"), at("buy", 1), at("dip", 1)
    f.cam(540, 960 + 90 * eio(prog(t, tb - 0.2, 0.6)), 1.0)
    pu = prog(t, tu, 0.35)
    f.pill(540, 420, "UNDER PRESSURE", 30 * (0.8 + 0.2 * eback(pu)), eo(pu), fill=None, outline=RED, tc=RED, track=0.22)
    for i, ((x0, y0, x1, y1), name, k) in enumerate(TILES):
        pa = eo(prog(t, t0 + 0.08 * i, 0.3))
        if pa <= 0:
            continue
        pulse = 0.1 * k * (0.5 + 0.5 * math.sin(t * 6 + i)) * prog(t, tu, 0.3)
        c = mixc((60, 24, 34), RED, 0.25 + 0.65 * k)
        f.rect(x0, y0, x1, y1, c, pa * (0.55 + 0.35 * k + pulse), r=14)
        f.rect(x0, y0, x1, y1, RED_HI, pa * 0.35 * k, r=14, w=2)
        size = 30 if (x1 - x0) > 300 else 20 if (x1 - x0) > 160 else 15
        f.text((x0 + x1) / 2, (y0 + y1) / 2, name, size, WHITE, pa * 0.95, "xb", track=0.12)
        cx_, cy_, s_ = (x0 + x1) / 2, (y0 + y1) / 2 + size + 10, size * 0.8
        f.poly([(cx_ - s_ * 0.45, cy_ - s_ * 0.3), (cx_ + s_ * 0.45, cy_ - s_ * 0.3), (cx_, cy_ + s_ * 0.4)], RED_HI, pa * (0.4 + 0.6 * k))
    f.text(540, 1180, "ALL 11 S&P 500 SECTORS FELL · NOV 5, 2026", 18, MUTED, eo(prog(t, tu, 0.4)), "sb", track=0.12)
    q = prog(t, tb, 0.35)
    if q > 0:
        f.pill(540, 1290, "BUY THE DIP?", 34 * (0.75 + 0.25 * eback(q)), eo(q), fill=GOLD, tc=NAVY, track=0.18)
        f.halo(540, 1452, 120, (130, 150, 200), 0.5 * eo(q), sy=0.15)
        f.pawn(540, 1450, 105, WHITE, eo(q))
        qq = prog(t, td, 0.3)
        f.text(612, 1350, "?", 64 * (0.8 + 0.2 * eback(qq)), GOLD_HI, eo(qq), "black")


# ------------------------------------------------------------------ 3 Nasdaq -5.5%, correction
def _nas():
    rng = np.random.default_rng(9)
    pts = [(110, 640)]
    n = 20
    for i in range(1, n + 1):
        u = i / n
        y = 640 + (822 - 640) * u + (0.0 if i == n else float(rng.uniform(-22, 22)))
        pts.append((110 + (820 - 110) * u, y))
    return pts


NAS = _nas()
NAS_END = [(820, 822), (868, 880), (902, 868), (950, 1000)]


def nasdaq(f, t):
    t0, tf, tpc, tsl, tco = at("on", 1), at("fell"), at("percent", end=True), at("slipped"), at("correction")
    f.cam(540, 920, 1.0 + 0.04 * eio(prog(t, t0, 5.4)))
    pp = prog(t, t0, 0.35)
    f.pill(540, 330, "NASDAQ · NOV 5, 2026", 26 * (0.8 + 0.2 * eback(pp)), eo(pp), track=0.14)
    v = 5.5 * eo(prog(t, tf, tpc - tf))
    f.text(540, 462, (MINUS if v > 0.04 else "") + f"{v:.1f}%", 150, mixc(WHITE, RED, v / 1.5), eo(prog(t, tf - 0.15, 0.25)), "black")
    f.dash(96, 1060, 984, 1060, MUTED, 0.4)
    f.text(110, 1100, "OCT 6", 20, MUTED, 0.95, "sb", track=0.22)
    f.text(950, 1100, "NOV 5", 20, MUTED, 0.95 * prog(t, tf, 0.3), "sb", track=0.22)
    f.pill(210, 596, "RECORD HIGH", 18, eo(prog(t, t0 + 0.2, 0.4)), fill=None, outline=GOLD, tc=GOLD_HI, track=0.2)
    p1 = eio(prog(t, t0 + 0.05, 1.3))
    f.line(partial(NAS, max(0.002, p1)), mixc(WHITE, (255, 200, 195), 0.4), 1, 5)
    p2 = eio(prog(t, tf - 0.05, tpc - tf + 0.2))
    if p2 > 0.002:
        pts = partial(NAS_END, p2)
        f.line(pts, RED, 1, 7)
        hx, hy = pts[-1]
        f.halo(hx, hy, 80, RED, 0.9)
        f.circ(hx, hy, 10, RED_HI)
    ca_ = eo(prog(t, tsl, 0.4))
    f.dash(96, 980, 984, 980, RED, 0.75 * ca_, w=3)
    f.text(100, 952, MINUS + "10% = CORRECTION", 18, RED_HI, ca_, "xb", anchor="lm", track=0.15)
    pc = prog(t, tco, 0.35)
    if pc > 0:
        f.ring(950, 1000, prog(t, tco, 0.9), RED_HI, 0.9, rmax=220)
        f.pill(760, 1180, "CORRECTION", 34 * (0.75 + 0.25 * eback(pc)), eo(pc), fill=RED, tc=WHITE, track=0.2)


# ------------------------------------------------------------------ 4 chip stocks: worst day since March 2020
CRACKS = [[(540, 860), (500, 820), (470, 835), (420, 770)], [(540, 860), (600, 900), (590, 940), (650, 990)],
          [(540, 860), (580, 800), (630, 780)], [(540, 860), (490, 910), (450, 905), (430, 960)]]


def chip_icon(f, x, y, s, a, crack=0.0):
    c = mixc(WHITE, RED_HI, crack)
    f.halo(x, y, 260 * s, RED, 0.6 * crack * a)
    for i in range(7):
        o = (i - 3) * 38 * s
        for (x0, y0, x1, y1) in ((x + o, y - 180 * s, x + o, y - 150 * s), (x + o, y + 150 * s, x + o, y + 180 * s),
                                 (x - 180 * s, y + o, x - 150 * s, y + o), (x + 150 * s, y + o, x + 180 * s, y + o)):
            f.line([(x0, y0), (x1, y1)], c, a, 8 * s)
    f.rect(x - 150 * s, y - 150 * s, x + 150 * s, y + 150 * s, DARKCARD, a, r=26 * s)
    f.rect(x - 150 * s, y - 150 * s, x + 150 * s, y + 150 * s, c, a, r=26 * s, w=6 * s)
    f.rect(x - 80 * s, y - 80 * s, x + 80 * s, y + 80 * s, mixc(GOLD, RED, crack), a, r=12 * s, w=4 * s)
    f.text(x, y, "AI", 70 * s, mixc(WHITE, RED_HI, crack), a, "black")
    if crack > 0:
        for cr in CRACKS:
            pts = [(x + (px - 540) * s, y + (py - 860) * s) for px, py in cr]
            f.line(partial(pts, crack), RED_HI, a, 5 * s)


def chips(f, t):
    t0, tw, ts = at("chip"), at("worst"), at("since")
    f.cam(540, 920, 1.0 + 0.05 * eio(prog(t, t0, 3.6)))
    f.text(540, 330, "SEMICONDUCTOR INDEX", 24, MUTED, eo(prog(t, t0, 0.35)), "sb", track=0.3)
    pw = prog(t, tw, 0.35)
    f.text(540, 445, MINUS + "12%", 150 * (0.85 + 0.15 * eback(pw)), RED, eo(pw), "black")
    chip_icon(f, 540, 860, 1.0, eo(prog(t, t0 - 0.05, 0.35)), crack=eo(prog(t, tw, 0.5)))
    if t > tw:
        rng = np.random.default_rng(4)
        for i in range(10):
            u = prog(t, tw + 0.05 * i, 1.4)
            if 0 < u < 1:
                x = 540 + float(rng.uniform(-170, 170))
                y = 1000 + 500 * u * u
                f.rect(x - 7, y - 7, x + 7, y + 7, RED_HI, 1 - u, r=2)
    pp = prog(t, ts, 0.35)
    f.pill(540, 1150, "WORST DAY SINCE MARCH 2020", 26 * (0.8 + 0.2 * eback(pp)), eo(pp), fill=None, outline=RED, tc=RED_HI, track=0.14)


# ------------------------------------------------------------------ 5 the names
CARDS = [("NVIDIA", 9, "nvidia"), ("AMD", 17, "amd"), ("ARM", 13, "arm"), ("QUALCOMM", 9, "qualcomm")]


def names(f, t):
    tc = at("crushed")
    f.cam(540, 920, 1.0)
    f.pill(540, 360, "CHIP STOCKS · NOV 5", 24, eo(prog(t, at("nvidia") - 0.1, 0.35)), fill=None, outline=RED, tc=RED_HI, track=0.18)
    hit = prog(t, tc, 0.3)
    for i, (name, pct, word) in enumerate(CARDS):
        ti = at(word)
        pa = prog(t, ti, 0.35)
        if pa <= 0:
            continue
        y = 540 + i * 175 + 30 * (1 - eo(pa)) + 14 * math.sin(math.pi * hit) * (1 if i % 2 else -1)
        sh = 8 * math.sin(t * 60) * (1 - hit) * (hit > 0)
        x = 540 + sh
        a = eo(pa)
        f.rect(x - 380, y - 70, x + 380, y + 70, DARKCARD, 0.92 * a, r=24)
        f.rect(x - 380, y - 70, x + 380, y + 70, mixc(MUTED, RED, hit), (0.35 + 0.5 * hit) * a, r=24, w=3)
        f.text(x - 340, y, name, 40, WHITE, a, "black", anchor="lm")
        spark = [(x - 20 + k * 20, y - 30 + (k * 9 if k < 6 else 54 + (k - 6) * 9) + (8 if k % 2 else 0)) for k in range(9)]
        f.line(partial(spark, eo(prog(t, ti + 0.1, 0.5))), RED, a, 4)
        f.text(x + 345, y, MINUS + f"{pct}%", 56, RED, a, "black", anchor="rm")
    if hit > 0:
        f.halo(540, 820, 520, RED, 0.25 * (1 - prog(t, tc + 0.3, 0.8)))
    f.text(540, 1270, "NOV 5, 2026 · DAILY CLOSE · ROUNDED", 17, MUTED, 0.75, "sb", track=0.12)


# ------------------------------------------------------------------ 6 the fear: midterms, data centers, weak forecasts
def ballot(f, x, y, a, p):
    f.rect(x - 90, y - 60, x + 90, y + 80, DARKCARD, a, r=10)
    f.rect(x - 90, y - 60, x + 90, y + 80, WHITE, a, r=10, w=5)
    f.line([(x - 45, y - 60), (x + 45, y - 60)], NAVY, a, 9)
    py = y - 140 + 90 * eio(p)
    if p < 1:
        f.rect(x - 34, py - 40, x + 34, py + 20, WHITE, a, r=4)
        f.line([(x - 18, py - 18), (x - 6, py - 6), (x + 18, py - 30)], GOLD, a, 5)
    f.text(x, y + 20, "VOTE", 26, WHITE, a, "black")


def datacenter(f, x, y, a, t, alarm=0.0):
    f.halo(x, y, 260, mixc(GOLD, RED, alarm), 0.25 * a)
    for i in range(3):
        rx = x - 150 + i * 110
        f.rect(rx, y - 160, rx + 90, y + 120, DARKCARD, a, r=8)
        f.rect(rx, y - 160, rx + 90, y + 120, WHITE, a, r=8, w=4)
        for j in range(6):
            yy = y - 135 + j * 42
            f.line([(rx + 14, yy), (rx + 58, yy)], MUTED, a * 0.8, 4)
            blink = 0.5 + 0.5 * math.sin(t * 9 + i * 2.1 + j * 1.3)
            f.circ(rx + 72, yy, 5, mixc(GREEN_HI, RED_HI, alarm), a * (0.4 + 0.6 * blink))
    f.text(x, y - 200, "AI", 34, GOLD_HI, a, "black")


def barrier(f, x, y, a, p):
    f.rect(x - 14, y - 120, x + 14, y + 10, WHITE, a, r=4)
    ang = -1.35 * (1 - eio(p))
    L = 330
    ex, ey = x + L * math.cos(ang), y - 110 + L * math.sin(ang)
    for k in range(6):
        u0, u1 = k / 6, (k + 1) / 6
        f.line([(x + (ex - x) * u0, y - 110 + (ey - y + 110) * u0), (x + (ex - x) * u1, y - 110 + (ey - y + 110) * u1)],
               RED if k % 2 == 0 else WHITE, a, 22)


def forecast_card(f, x, y, name, a):
    f.rect(x - 360, y - 62, x + 360, y + 62, DARKCARD, 0.92 * a, r=22)
    f.rect(x - 360, y - 62, x + 360, y + 62, RED, 0.6 * a, r=22, w=3)
    f.text(x - 320, y - 14, name, 40, WHITE, a, "black", anchor="lm")
    f.text(x - 320, y + 30, "WEAK FORECAST", 18, RED_HI, a, "xb", anchor="lm", track=0.2)
    f.poly([(x + 300, y + 34), (x + 270, y - 6), (x + 288, y - 6), (x + 288, y - 40), (x + 312, y - 40), (x + 312, y - 6), (x + 330, y - 6)], RED, a)


def why(f, t):
    tf, tm, ti, tl, tai, tp, tq, tin = (at("fear", 1), at("midterms"), at("investors"), at("limits"), at("ai"), at("plus"),
                                         at("qualcomm", 2), at("intel"))
    k = eio(prog(t, tp - 0.15, 0.7))
    f.cam(540, 960 + 560 * k, 1.0)
    pf = prog(t, tf, 0.35)
    f.pill(540, 330, "THE FEAR", 30 * (0.8 + 0.2 * eback(pf)), eo(pf), fill=None, outline=RED, tc=RED, track=0.3)
    up = 1 - 0.9 * k
    pb = prog(t, tm - 0.2, 0.35)
    if pb > 0:
        ballot(f, 250, 800, eo(pb) * up, prog(t, tm, 0.6))
        f.text(250, 930, "MIDTERMS", 20, MUTED, eo(pb) * up, "xb", track=0.25)
    pd = prog(t, ti, 0.4)
    if pd > 0:
        alarm = eo(prog(t, tl, 0.4))
        datacenter(f, 730, 820, eo(pd) * up, t, alarm)
        f.text(730, 990, "AI DATA CENTERS", 20, MUTED, eo(pd) * up, "xb", track=0.2)
        if alarm > 0:
            barrier(f, 520, 1000, eo(alarm) * up, prog(t, tl, 0.6))
            f.pill(730, 515, "NEW LIMITS?", 30 * (0.75 + 0.25 * eback(alarm)), alarm * up, fill=RED, tc=WHITE, track=0.18)
    pw = prog(t, ti, 0.35)
    f.halo(540, 1302, 120, (130, 150, 200), 0.5 * eo(pw), sy=0.15)
    f.pawn(540, 1300, 120, WHITE, eo(pw), abs(math.sin(t * 7)) * 3)
    f.text(540, 1345, "INVESTORS", 18, MUTED, eo(pw), "xb", track=0.25)
    f.text(610, 1150, "?", 56, GOLD_HI, eo(prog(t, at("worry"), 0.3)), "black")
    for nm, tt, yy in (("QUALCOMM", tq, 1560), ("INTEL", tin, 1720)):
        pc = prog(t, tt - 0.15, 0.35)
        if pc > 0:
            forecast_card(f, 540 + 60 * (1 - eo(pc)), yy, nm, eo(pc))


# ------------------------------------------------------------------ 7 a falling price is not a bargain
FALL = [(120, 720), (180, 700), (230, 760), (280, 745), (330, 840), (380, 820), (440, 960)]


def diamond(f, x, y, s, c, a=1.0, glow=1.0):
    if a <= 0.01:
        return
    P = lambda u, v: (x + u * s, y + v * s)
    f.halo(x, y, 1.4 * s, c, 0.55 * glow * a)
    f.poly([P(-0.5, -0.15), P(-0.28, -0.45), P(0.28, -0.45), P(0.5, -0.15), P(0, 0.55)], c, 0.28 * a)
    f.line([P(-0.5, -0.15), P(-0.28, -0.45), P(0.28, -0.45), P(0.5, -0.15), P(0, 0.55), P(-0.5, -0.15)], WHITE, a, max(2, 0.05 * s))
    f.line([P(-0.5, -0.15), P(0.5, -0.15)], WHITE, a * 0.8, max(2, 0.035 * s))
    f.line([P(-0.28, -0.45), P(-0.12, -0.15), P(0, 0.55), P(0.12, -0.15), P(0.28, -0.45)], WHITE, a * 0.8, max(2, 0.035 * s))
    f.line([P(-0.12, -0.15), P(0, -0.45), P(0.12, -0.15)], WHITE, a * 0.8, max(2, 0.035 * s))


def bargain(f, t):
    t0, tp, ti, tb = at("but"), at("price"), at("isnt"), at("bargain")
    f.cam(540, 920, 1.0)
    pa = eo(prog(t, t0, 0.4))
    f.text(280, 600, "FALLING PRICE", 24, RED, pa, "xb", track=0.22)
    pts = partial(FALL, max(0.002, eio(prog(t, t0, 1.2))))
    f.line(pts, RED, pa, 6)
    hx, hy = pts[-1]
    f.halo(hx, hy, 60, RED, 0.7 * pa)
    sw = 0.25 * math.sin(t * 3)
    tx, ty = hx + 30 * math.sin(sw), hy + 80
    f.line([(hx, hy), (tx, ty - 34)], WHITE, pa * eo(prog(t, tp, 0.3)), 3)
    ta = eo(prog(t, tp, 0.35))
    if ta > 0:
        f.poly([(tx - 70, ty - 34), (tx + 50, ty - 34), (tx + 80, ty), (tx + 50, ty + 34), (tx - 70, ty + 34)], GOLD, ta)
        f.circ(tx + 46, ty, 8, NAVY, ta)
        f.text(tx - 12, ty, "SALE", 28, NAVY, ta, "black")
    pn = prog(t, ti, 0.35)
    f.text(540, 850, "≠", 170 * (0.8 + 0.2 * eback(pn)), GOLD_HI, eo(pn), "black")
    pb = prog(t, tb - 0.35, 0.4)
    f.text(800, 600, "BARGAIN", 24, GREEN, eo(pb), "xb", track=0.22)
    diamond(f, 800, 840, 170, GREEN, eo(pb), glow=eo(pb))
    f.text(800, 840, "?", 90, WHITE, eo(prog(t, tb, 0.3)), "black")
    f.halo(540, 1302, 120, (130, 150, 200), 0.5, sy=0.15)
    f.pawn(540, 1300, 120, WHITE, 1)


# ------------------------------------------------------------------ 8 the mine: dig deeper (layers 1-5), headline, diamonds
SURF, SX, SW = 560, 300, 170
LTOP = [SURF + 30 + k * 270 for k in range(5)]
CAV = LTOP[4] + 270
LCOL = [(24, 40, 72), (21, 35, 64), (18, 31, 57), (16, 27, 51), (14, 24, 45)]
TITLE = ["WHY DID IT FALL?", "SALES & PROFITS", "DEBT", "VALUATION", "DIVERSIFY"]
CAVE = [(200, 1975), (420, 1955), (700, 1962), (950, 1990), (985, 2160), (935, 2335), (650, 2400), (330, 2380), (175, 2260),
        (165, 2090)]
GEMS = [(640, 2200, 92, GREEN), (520, 2250, 70, GOLD), (770, 2255, 66, GREEN), (610, 2330, 56, GOLD), (850, 2190, 54, GOLD),
        (440, 2320, 50, GREEN), (720, 2335, 60, GOLD)]


def _rocks():
    rng = np.random.default_rng(12)
    out = []
    for k in range(6):
        y0 = LTOP[k] if k < 5 else CAV
        for _ in range(30):
            out.append((float(rng.uniform(-560, 1640)), float(rng.uniform(y0 + 16, y0 + 254)),
                        float(rng.uniform(9, 26)), float(rng.uniform(6, 15))))
    return out


ROCKS = _rocks()


def TL(k):
    return at("layer", k + 1)


def layer_end(k):
    return TL(k + 1) - 0.3 if k < 4 else at("most") - 0.3


def depth(t):
    td = at("dig")
    if t < td:
        return SURF
    if t < TL(0):
        return SURF + 30 * eio(prog(t, td, TL(0) - td))
    for k in range(5):
        if t < (TL(k + 1) if k < 4 else 1e9):
            return LTOP[k] + 270 * prog(t, TL(k) + 0.2, layer_end(k) - TL(k) - 0.2)
    return CAV


def digging(t):
    td = at("dig")
    if td <= t < TL(0):
        return td
    for k in range(5):
        if TL(k) + 0.2 <= t < layer_end(k):
            return TL(k) + 0.2
    tk = at("keep")
    if tk - 0.45 <= t < tk + 0.35:
        return tk - 0.45
    return None


def swing(t, t0):
    ph = (t - t0) * 2.2
    u = ph - math.floor(ph)
    s = eo(u / 0.28) if u < 0.28 else 1 - eio((u - 0.28) / 0.72)
    k = math.floor(ph) if u >= 0.28 else math.floor(ph) - 1
    return lerp(-2.1, 0.95, s), (t0 + (k + 0.28) / 2.2 if k >= 0 else None)


def miner(f, x, y, h, t, t0=None, a=1.0, c=WHITE):
    hy = y - 0.7975 * h
    lx, ly = x + 0.15 * h, hy - 0.11 * h
    f.poly([(lx, ly - 4), (lx + 1.3 * h, ly + 0.5 * h), (lx + 1.0 * h, ly + 1.0 * h)], GOLD_HI, 0.06 * a)
    f.pawn(x, y, h, c, a)
    X0, Y0, X1, Y1 = f.X(x - 0.235 * h), f.Y(hy - 0.235 * h), f.X(x + 0.235 * h), f.Y(hy + 0.1 * h)
    f.d.chord((X0, Y0, X1, Y1), 180, 360, fill=ca(GOLD, a))
    f.line([(x - 0.27 * h, hy - 0.07 * h), (x + 0.3 * h, hy - 0.07 * h)], GOLD, a, 0.05 * h)
    f.halo(lx, ly, 0.28 * h, GOLD_HI, 0.6 * a)
    f.circ(lx, ly, 0.045 * h, GOLD_HI, a)
    ang, th = swing(t, t0) if t0 is not None else (-1.25, None)
    sx, sy = x + 0.1 * h, y - 0.55 * h
    hx, hy2 = sx + 0.22 * h * math.cos(ang), sy + 0.22 * h * math.sin(ang)
    f.line([(sx, sy), (hx, hy2)], c, a, 0.12 * h)
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    ex, ey = hx + 0.62 * h * dx, hy2 + 0.62 * h * dy
    f.line([(hx - 0.1 * h * dx, hy2 - 0.1 * h * dy), (ex, ey)], (196, 156, 72), a, 0.065 * h)
    f.line([(ex + 0.27 * h * nx - 0.07 * h * dx, ey + 0.27 * h * ny - 0.07 * h * dy), (ex + 0.04 * h * dx, ey + 0.04 * h * dy),
            (ex - 0.27 * h * nx - 0.07 * h * dx, ey - 0.27 * h * ny - 0.07 * h * dy)], (215, 222, 235), a, 0.075 * h)
    if th is not None and 0 <= t - th < 0.45:
        age = t - th
        rng = np.random.default_rng(int(th * 100))
        for i in range(8):
            vx, vy = float(rng.uniform(-280, 280)), float(rng.uniform(-430, -170))
            f.circ(x + 0.48 * h + vx * age, y - 4 + vy * age + 1000 * age * age, float(rng.uniform(3, 7)), (150, 165, 196),
                   a * (1 - age / 0.45))
        if age < 0.3:
            f.sparkle(x + 0.48 * h, y - 10, 24 * (1 - age / 0.3), GOLD_HI, a * (1 - age / 0.3))


def mine_world(f, t, D):
    f.rect(-800, SURF, 1900, LTOP[0], (27, 44, 78))
    for k in range(5):
        f.rect(-800, LTOP[k], 1900, LTOP[k] + 270, LCOL[k])
    f.rect(-800, CAV, 1900, 2700, (10, 18, 36))
    for x, y, rx, ry in ROCKS:
        f.ell(x, y, rx, ry, WHITE, 0.08, w=2)
    for k in range(5):
        f.dash(-800, LTOP[k], 1900, LTOP[k], MUTED, 0.3)
    f.dash(-800, CAV, 1900, CAV, MUTED, 0.3)
    f.line([(-800, SURF), (1900, SURF)], WHITE, 0.8, 4)
    open_ = prog(t, at("keep") + 0.2, 0.3)
    if open_ > 0:
        f.poly(CAVE, (6, 11, 22))
        f.line(CAVE + [CAVE[0]], WHITE, 0.45 * open_, 3)
    if D > SURF + 1:
        f.rect(SX - SW / 2, SURF - 2, SX + SW / 2, D, (7, 12, 24))
        f.line([(SX - SW / 2, SURF), (SX - SW / 2, D)], WHITE, 0.45, 3)
        f.line([(SX + SW / 2, SURF), (SX + SW / 2, D)], WHITE, 0.45, 3)


def layer_info(f, t, k):
    t0, yk = TL(k), LTOP[k]
    pa = prog(t, t0, 0.35)
    cx = 660
    if pa <= 0:
        f.pill(cx, yk + 46, f"LAYER {k + 1}", 16, 0.22, fill=None, outline=MUTED, tc=MUTED, track=0.25)
        f.text(cx, yk + 150, "?", 90, MUTED, 0.16, "black")
        return
    d1 = 0.65 * prog(t, TL(k + 1) - 0.3, 0.5) if k < 4 else 0.0
    d2 = 0.35 * prog(t, TL(k + 2) - 0.3, 0.5) if k < 3 else 0.0
    dim = lerp(1 - d1 - d2, 0.85, prog(t, at("most") - 0.2, 0.6)) * (1 - prog(t, at("the", 8), 0.6))
    a = eo(pa) * dim
    f.pill(cx, yk + 46, f"LAYER {k + 1}", 16, a, fill=None, outline=GOLD, tc=GOLD_HI, track=0.25)
    f.text(cx, yk + 104, TITLE[k], (44 if k else 38) * (0.85 + 0.15 * eback(pa)), WHITE, a, "black")
    if k == 0:
        p1, p2 = prog(t, at("fear", 2), 0.3), prog(t, at("real"), 0.3)
        f.pill(515, yk + 200, "FEAR?", 24 * (0.75 + 0.25 * eback(p1)), eo(p1) * dim, fill=None, outline=GOLD, tc=GOLD_HI, track=0.18)
        f.text(593, yk + 200, "OR", 18, MUTED, eo(p2) * dim, "xb", track=0.2)
        f.pill(745, yk + 200, "REAL PROBLEM?", 22 * (0.75 + 0.25 * eback(p2)), eo(p2) * dim, fill=RED, tc=WHITE, track=0.1)
    elif k == 1:
        for i, (hh, tt) in enumerate(((44, at("sales")), (74, at("sales") + 0.25), (104, at("profits")))):
            g = eo(prog(t, tt, 0.4))
            x = 600 + i * 62
            f.rect(x - 22, yk + 245 - hh * g, x + 22, yk + 245, GREEN, a, r=6)
        pg = eo(prog(t, at("growing"), 0.35)) * dim
        f.line([(790, yk + 230), (790, yk + 150)], GREEN_HI, pg, 6)
        f.poly([(770, yk + 160), (790, yk + 132), (810, yk + 160)], GREEN_HI, pg)
    elif k == 2:
        pd = eo(prog(t, at("debt"), 0.35)) * dim
        x, y = 590, yk + 200
        f.arc(x, y - 42, 26, 180, 360, WHITE, pd, w=8)
        f.circ(x, y, 46, DARKCARD, pd)
        f.circ(x, y, 46, RED_HI, pd, w=6)
        f.text(x, y + 2, "$", 40, RED_HI, pd, "black")
        ps = prog(t, at("storm"), 0.35)
        if ps > 0:
            cx2, cy2 = 770, yk + 170
            for ox, oy, r in ((-38, 8, 30), (0, -10, 40), (40, 8, 30)):
                f.circ(cx2 + ox, cy2 + oy, r, (190, 200, 222), eo(ps) * dim)
            f.rect(cx2 - 68, cy2 + 6, cx2 + 68, cy2 + 38, (190, 200, 222), eo(ps) * dim, r=16)
            fl = (math.sin(t * 23) > 0.2) * eo(ps) * dim
            f.line([(cx2 + 4, cy2 + 40), (cx2 - 14, cy2 + 78), (cx2 + 8, cy2 + 78), (cx2 - 10, cy2 + 118)], GOLD_HI, fl, 7)
            f.halo(cx2, cy2 + 60, 130, GOLD_HI, 0.35 * fl)
    elif k == 3:
        p1, p2 = prog(t, at("cheap"), 0.3), prog(t, at("expensive"), 0.3)
        f.pill(cx, yk + 172, "CHEAP NOW?", 24 * (0.75 + 0.25 * eback(p1)), eo(p1) * dim, fill=None, outline=GREEN, tc=GREEN_HI, track=0.15)
        f.pill(cx, yk + 232, "OR TOO EXPENSIVE BEFORE?", 21 * (0.75 + 0.25 * eback(p2)), eo(p2) * dim, fill=None, outline=RED,
               tc=RED_HI, track=0.08)
    elif k == 4:
        pp = eio(prog(t, at("never"), 1.2))
        x, y, r = 600, yk + 196, 58
        cols = [GOLD, GREEN, WHITE, MUTED, GOLD_HI]
        if pp > 0.01:
            for i in range(5):
                a0 = -90 + 72 * i
                f.d.pieslice((f.X(x - r), f.Y(y - r), f.X(x + r), f.Y(y + r)), a0, a0 + 72 * pp, fill=ca(cols[i], a))
            f.circ(x, y, r, NAVY, a * pp, w=4)
        so = eo(prog(t, at("one", 2), 0.3)) * dim
        f.text(760, yk + 182, "SPREAD", 22, GREEN_HI, so, "black")
        f.text(760, yk + 214, "IT OUT", 22, GREEN_HI, so, "black")


def surface_extras(f, t):
    pa = eo(prog(t, at("before", 1) - 0.1, 0.4))
    f.line([(780, SURF), (780, SURF - 150)], WHITE, pa, 6)
    f.rect(660, SURF - 250, 900, SURF - 140, DARKCARD, pa, r=14)
    f.rect(660, SURF - 250, 900, SURF - 140, WHITE, pa, r=14, w=4)
    f.text(780, SURF - 225, "ANY STOCK", 16, MUTED, pa, "xb", track=0.2)
    f.line([(690, SURF - 205), (740, SURF - 195), (780, SURF - 175), (820, SURF - 185), (870, SURF - 155)], RED, pa, 5)


CROWD = [620, 740, 860, 980, 1100]


def mine_cam(t):
    td, tm, to = at("before", 1) - 0.1, at("most"), at("the", 8)
    cx, cy, z = 540, lerp(700, 800, eio(prog(t, td, 1.6))), 1.0
    for k in range(5):
        e = eio(prog(t, TL(k) - 0.55, 0.75))
        cx, cy, z = lerp(cx, 590, e), lerp(cy, LTOP[k] + 150, e), lerp(z, 1.3, e)
    e = eio(prog(t, tm - 0.15, 0.9))
    cx, cy, z = lerp(cx, 600, e), lerp(cy, 1460, e), lerp(z, 0.5, e)
    e = eio(prog(t, to - 0.1, 0.9))
    cx, cy, z = lerp(cx, 580, e), lerp(cy, 2130, e), lerp(z, 0.95, e)
    return cx, cy, z


def mine(f, t):
    f.cam(*mine_cam(t))
    D = depth(t)
    mine_world(f, t, D)
    surface_extras(f, t)
    for k in range(5):
        layer_info(f, t, k)
    tm, tst, thl = at("most"), at("stop"), at("headline")
    pm = prog(t, tm - 0.1, 0.4)
    if pm > 0:
        for i, x in enumerate(CROWD):
            leave = eio(prog(t, tst + 0.12 * i, 0.9))
            a = eo(pm) * (1 - prog(t, tst + 0.12 * i + 0.6, 0.4))
            if a <= 0.01:
                continue
            f.ell(x + 40, SURF + 6, 50, 12, (7, 12, 24), a)
            miner(f, x + 380 * leave, SURF, 150, t, (tm + 0.1 * i) if t < tst + 0.12 * i else None, a, qmix(WHITE, RED, leave * 0.6))
        f.pill(860, SURF - 330, "MOST PEOPLE", 52, eo(pm) * (1 - prog(t, at("the", 8), 0.4)), fill=None, outline=MUTED, tc=WHITE,
               track=0.2)
        ph = prog(t, thl, 0.35)
        if ph > 0:
            a = eo(ph) * (1 - prog(t, at("the", 8), 0.4))
            x, y = 1060, SURF - 230
            f.rect(x - 170, y - 110, x + 170, y + 110, (232, 236, 244), a, r=10)
            f.rect(x - 145, y - 85, x + 145, y - 40, NAVY, a, r=5)
            f.text(x, y - 62, "HEADLINE", 36, WHITE, a, "black", track=0.1)
            for j in range(3):
                f.line([(x - 145, y + j * 32), (x + 145 - 60 * (j == 2), y + j * 32)], (150, 160, 180), a, 9)
            f.poly([(x + 215, y - 60), (x + 270, y - 60), (x + 270, y + 15), (x + 305, y + 15), (x + 242, y + 90), (x + 180, y + 15),
                    (x + 215, y + 15)], RED, a)
    tk, tfd, tdm = at("keep"), at("find"), at("diamonds")
    fall = prog(t, tk + 0.35, 0.5)
    y = D if fall <= 0 else lerp(CAV, 2345, fall * fall)
    if t >= tk + 0.2:
        rng = np.random.default_rng(77)
        for i in range(14):
            u = prog(t, tk + 0.2, 1.0)
            if 0 < u < 1:
                rx, ry = SX + float(rng.uniform(-80, 80)), CAV + 600 * u * u * float(rng.uniform(0.6, 1))
                f.rect(rx - 8, ry - 8, rx + 8, ry + 8, (120, 135, 165), 1 - u, r=3)
    for i, (gx, gy, gs, gc) in enumerate(GEMS):
        ga = eo(prog(t, tdm - 0.3 + 0.12 * i, 0.4))
        if ga > 0:
            diamond(f, gx, gy, gs, gc, ga, glow=ga * (0.8 + 0.2 * math.sin(t * 5 + i)))
            sa = math.sin(math.pi * prog(t, tdm + 0.12 * i, 0.7))
            f.sparkle(gx + gs * 0.6, gy - gs * 0.6, 26 * sa, GOLD_HI, sa)
    f.burst(640, 2220, prog(t, tdm + 0.1, 1.5), seed=5, n=22, spread=380)
    f.ring(640, 2220, prog(t, tdm, 1.0), GOLD_HI, 0.8, rmax=420)
    miner(f, SX if fall <= 0 else lerp(SX, 330, fall), y, 120, t, digging(t), 1.0)
    if t >= tm - 0.1:
        ya = eo(pm) * (1 - prog(t, tk, 0.3))
        f.text(SX, CAV + 80, "YOU", 60, GOLD_HI, ya, "black", track=0.3)
    f.cam(540, 960, 1.0)
    pd = prog(t, at("dig"), 0.35)
    f.pill(540, 300, "DIG DEEPER", 34 * (0.75 + 0.25 * eback(pd)), eo(pd) * (1 - prog(t, TL(0) + 1.2, 0.4)), fill=GOLD, tc=NAVY,
           track=0.22)
    pk = prog(t, tfd, 0.4)
    f.pill(540, 330, "KEEP DIGGING", 36 * (0.75 + 0.25 * eback(pk)), eo(pk), fill=GOLD, tc=NAVY, track=0.22)


def loopback(f, t):
    hook(f, 0.0)


# ------------------------------------------------------------------ timeline
SHOTS = [
    (0.0, at("so") - 0.1, hook, None),
    (at("so") - 0.1, at("on", 1) - 0.1, question, "zoom"),
    (at("on", 1) - 0.1, at("chip") - 0.1, nasdaq, "whip"),
    (at("chip") - 0.1, at("nvidia") - 0.08, chips, "flash"),
    (at("nvidia") - 0.08, at("the", 4) - 0.06, names, "zoom"),
    (at("the", 4) - 0.06, at("but") - 0.06, why, "wipe"),
    (at("but") - 0.06, at("before", 1) - 0.08, bargain, "zoom"),
    (at("before", 1) - 0.08, DUR - 0.7, mine, "fade"),
    (DUR - 0.7, DUR, loopback, "zoom"),
]
TR = 0.32
SHAKES = [(at("vanished") + 0.1, 0.45, 9), (at("fell") + 0.3, 0.45, 8), (at("worst") + 0.05, 0.5, 11), (at("crushed"), 0.35, 8),
          (at("limits"), 0.3, 5), (at("storm"), 0.3, 5), (at("keep") + 0.2, 0.4, 8)]
FLASH_C = (235, 245, 238)


def tint_at(t):
    k = 0.24 * prog(t, at("vanished"), 0.4) * (1 - prog(t, 4.6, 0.6))
    k = max(k, 0.2 * prog(t, at("fell"), 0.4) * (1 - prog(t, at("correction", end=True), 0.6)))
    k = max(k, 0.24 * prog(t, at("worst"), 0.3) * (1 - prog(t, at("nvidia") - 0.3, 0.5)))
    k = max(k, 0.18 * prog(t, at("crushed"), 0.2) * (1 - prog(t, at("crushed") + 0.6, 0.5)))
    return (RED, k) if k > 0.01 else None


def transition(kind, old, new, e):
    if kind == "zoom":
        z = 1.08 - 0.08 * eio(e)
        big = new.resize((int(W * z), int(H * z)), Image.BILINEAR)
        x0, y0 = (big.width - W) // 2, (big.height - H) // 2
        return Image.blend(old, big.crop((x0, y0, x0 + W, y0 + H)), eio(e))
    if kind == "flash":
        b = old if e < 0.5 else new
        return Image.blend(b, Image.new("RGB", (W, H), FLASH_C), 0.6 * (1 - abs(e - 0.5) / 0.5))
    if kind in ("wipe", "whip"):
        off = int(W * eio(e))
        out = Image.new("RGB", (W, H))
        out.paste(old, (-off, 0))
        out.paste(new, (W - off, 0))
        if kind == "wipe":
            ImageDraw.Draw(out).rectangle((W - off - 3, 0, W - off + 3, H), fill=GOLD)
            return out
        return out.filter(ImageFilter.BoxBlur(int(2 + 22 * math.sin(math.pi * e))))
    if kind == "fade":
        dark = Image.new("RGB", (W, H), (6, 10, 20))
        return Image.blend(old, dark, e / 0.5 * 0.85) if e < 0.5 else Image.blend(new, dark, (1 - e) / 0.5 * 0.85)
    return new


def chrome(im, t):
    d = ImageDraw.Draw(im, "RGBA")
    x0, x1, y = 90, 990, 205
    d.rounded_rectangle((x0, y, x1, y + 8), radius=4, fill=(28, 40, 68, 255))
    xe = x0 + (x1 - x0) * clamp(t / DUR)
    if xe > x0 + 8:
        d.rounded_rectangle((x0, y, xe, y + 8), radius=4, fill=GOLD + (255,))
    d.text((60, 1700), "Not financial advice · educational only", font=font("sb", 26), fill=(140, 155, 185, 190), anchor="lm")
    d.text((W - 60, 1700), "Moneycheck", font=font("sb", 32), fill=(255, 255, 255, 153), anchor="rm")


def shot_at(t):
    for k, s in enumerate(SHOTS):
        if s[0] <= t < s[1]:
            return k
    return len(SHOTS) - 1


def draw(k, t):
    f = F(t)
    SHOTS[k][2](f, t)
    return post(f.img, t, tint=tint_at(t))


def frame(i):
    t = i / FPS
    k = shot_at(t)
    im = draw(k, t)
    a, kind = SHOTS[k][0], SHOTS[k][3]
    if k > 0 and kind and t - a < TR:
        im = transition(kind, draw(k - 1, t), im, (t - a) / TR)
    for t0, dur, amp in SHAKES:
        if t0 <= t < t0 + dur:
            q = 1 - (t - t0) / dur
            im = ImageChops.offset(im, int(amp * q * math.sin(t * 71)), int(amp * 0.6 * q * math.cos(t * 53)))
    chrome(im, t)
    return im


def fb(i):
    return frame(i).tobytes()


def _thumb(ts):
    return frame(int(round(ts * FPS))).resize((360, 640), Image.LANCZOS)


def cover():
    t = at("keep") + 2.0
    f = F(t)
    f.cam(560, 916, 0.45)
    mine_world(f, t, CAV)
    for k in range(5):
        f.pill(745, LTOP[k] + 58, f"LAYER {k + 1}", 32, 0.9, fill=None, outline=GOLD, tc=GOLD_HI, track=0.25)
        f.text(745, LTOP[k] + 150, TITLE[k], 80, WHITE, 0.95, "black")
    for gx, gy, gs, gc in GEMS:
        diamond(f, gx, gy - 10, gs * 1.35, gc, 1.0)
    miner(f, 320, 2350, 210, t, None)
    f.cam(540, 960, 1.0)
    f.text(540, 235, "CHIP STOCKS \u00b7 NOV 5, 2026", 28, MUTED, 1, "sb", track=0.25)
    f.text(540, 380, MINUS + "12%", 200, RED, 1, "black")
    f.text(540, 560, "BUY THE DIP?", 96, GOLD_HI, 1, "black")
    f.text(540, 668, "DIG DEEPER FIRST.", 62, WHITE, 1, "black")
    im = post(f.img, 0.0)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((W - 60, 1700), "Moneycheck", font=font("sb", 32), fill=(255, 255, 255, 153), anchor="rm")
    im.save("cover_dig_deeper_1080x1920.png")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stills":
        for ts in sys.argv[2:]:
            frame(int(round(float(ts) * FPS))).save(f"still_{ts}.png")
    elif mode == "sheet":
        times = [float(x) for x in sys.argv[3:]]
        with Pool(4) as pool:
            th = pool.map(_thumb, times)
        cols = 6
        rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 360, rows * 640))
        d = ImageDraw.Draw(sheet)
        for i, (im, ts) in enumerate(zip(th, times)):
            sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
            d.text(((i % cols) * 360 + 8, (i // cols) * 640 + 8), f"{ts:.1f}", font=font("xb", 28), fill=(255, 255, 0))
        sheet.save(sys.argv[2])
    elif mode == "cover":
        cover()
    else:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                               "-pix_fmt", "yuv420p", "-movflags", "+faststart", "video_noaudio.mp4"], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for b in pool.imap(fb, range(NF), chunksize=4):
                ff.stdin.write(b)
        ff.stdin.close()
        ff.wait()
        print("done", ff.returncode, NF, "frames")

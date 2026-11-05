"""Moneycheck Short #8 - "Your portfolio is down 30%. What do you do?"
Premium animation (cryothum-like look in Moneycheck colours), female voice (Samara X), NO subtitles.
1080x1920, 30 fps, 65.9 s. All scene anchors come from the exact word times in words.json.

Usage:  python3 render10.py stills 1.0 6.5 ...   |   python3 render10.py sheet out.png 1 2 3 ...
        python3 render10.py cover                |   python3 render10.py video
"""
import json
import math
import re
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from lib10 import (W, H, FPS, F, post, font, clamp, prog, eo, eio, eback, lerp, mixc, qmix, partial,
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


DUR = 65.9
NF = int(round(DUR * FPS))
G = 1250
ND = "–"


def you(f, x, y, h, a=1.0, spot=0.8, label=True, ring=0.0, c=WHITE, bob=0.0):
    if spot > 0:
        f.spot(x, y - h * 3.3, y + 16, h * 3.1, spot * a)
    f.halo(x, y + 2, h * 0.8, (130, 150, 200), 0.5 * a, sy=0.15)
    if ring > 0:
        s = 0.8 + 0.2 * ring
        f.halo(x, y + 2, h * 0.9, GOLD, 0.35 * ring * a, sy=0.18)
        f.ell(x, y + 2, h * 0.62 * s, h * 0.13 * s, GOLD_HI, ring * a, w=4)
    f.pawn(x, y, h, c, a, bob)
    if label:
        f.text(x, y + 44, "YOU", 21, WHITE, 0.9 * a, "xb", track=0.32)


# ------------------------------------------------------------------ 1 hook
UP = [(120, 890), (180, 862), (240, 876), (300, 820), (360, 834), (420, 770), (480, 784), (540, 712), (600, 726),
      (660, 648), (700, 622)]
DOWN = [(700, 622), (732, 690), (758, 668), (796, 760), (826, 738), (866, 826), (900, 806), (950, 880)]


def hook(f, t):
    f.cam(540, 960, 1.0 + 0.045 * eio(t / 3.35))
    p = eio(prog(t, at("down") - 0.05, 0.95))
    f.text(540, 352, "YOUR PORTFOLIO", 24, MUTED, 1, "sb", track=0.3)
    v = int(round(30 * p))
    f.text(540, 462, (MINUS if v else "") + f"{v}%", 150, mixc(WHITE, RED, p * 4), 1, "black")
    f.poly(UP + [(700, 900), (120, 900)], WHITE, 0.045)
    f.dash(100, 900, 980, 900, MUTED, 0.35)
    f.line(UP, WHITE, 1, 5)
    if p > 0.002:
        pts = partial(DOWN, p)
        f.poly(pts + [(pts[-1][0], 900), (700, 900)], RED, 0.08)
        f.line(pts, RED, 1, 6)
        hx, hy = pts[-1]
        f.halo(hx, hy, 70, RED, 0.85)
        f.circ(hx, hy, 9, RED_HI)
    else:
        f.halo(700, 622, 55, WHITE, 0.55)
        f.circ(700, 622, 9, WHITE)
    you(f, 540, G, 170)


# ------------------------------------------------------------------ 2 everyone is selling / what do you do?
CROWD = [(445, 0), (635, 1), (350, 2), (730, 3), (250, 4), (830, 5), (150, 6), (930, 7)]


def crowd(f, t):
    te, tw = at("everyone"), at("what")
    f.cam(540, 1060, 1.14 - 0.14 * eo(prog(t, te - 0.12, 1.3)))
    f.dash(20, G + 2, 1060, G + 2, MUTED, 0.35)
    pa = eo(prog(t, te, 0.3)) * (1 - prog(t, tw - 0.25, 0.3))
    f.pill(540, 420, "SELL-OFF", 30 * (0.85 + 0.15 * eback(prog(t, te, 0.35))), pa, fill=None, outline=RED, tc=RED, track=0.22)
    for x0, k in CROWD:
        side = -1 if x0 < 540 else 1
        tk = te + 0.1 + 0.11 * k
        tl = tk + 0.55
        mv = eio(prog(t, tl, 1.0))
        a = 0.85 * (1 - prog(t, tl + 0.7, 0.3))
        if a <= 0.01:
            continue
        x = x0 + side * mv * 600
        bob = abs(math.sin((t - tl) * 13)) * 7 if t > tl else 0.0
        f.pawn(x, G, 128, qmix(WHITE, RED, prog(t, tk, 0.25)), a, bob)
        ps = prog(t, tk, 0.3)
        if ps > 0:
            f.pill(x, G - 162 - 30 * (k % 2) - bob, "SELL", 13 * (0.6 + 0.4 * eback(ps)), a * eo(ps), fill=RED, tc=WHITE, padx=11, pady=6)
        if 0.05 < mv < 0.97:
            for j in range(3):
                yy = G - 35 - 32 * j
                f.line([(x - side * (60 + 18 * j), yy), (x - side * (150 + 30 * j), yy)], WHITE, 0.22 * a, 3)
    q = prog(t, tw, 0.35)
    you(f, 540, G, 165, spot=0.55 + 0.6 * q)
    if q > 0:
        q2 = prog(t, tw + 0.18, 0.35)
        f.dash(505, 1095, 360, 1022, MUTED, 0.5 * eo(q))
        f.dash(575, 1095, 720, 1022, MUTED, 0.5 * eo(q2))
        f.pill(300, 990, "SELL", 32 * (0.7 + 0.3 * eback(q)), eo(q), fill=None, outline=RED, tc=RED, track=0.22)
        f.pill(780, 990, "HOLD", 32 * (0.7 + 0.3 * eback(q2)), eo(q2), fill=GOLD, tc=NAVY, track=0.22)
        qq = prog(t, at("do", 2), 0.3)
        f.text(540, 1000, "?", 96 * (0.8 + 0.2 * eback(qq)), GOLD_HI, eo(qq) * (0.85 + 0.15 * math.sin(t * 7)), "black")


# ------------------------------------------------------------------ 3 2020 crash
def _crash():
    rng = np.random.default_rng(20)
    pts = [(150, 640)]
    n = 22
    for i in range(1, n + 1):
        u = i / n
        y = 640 + 430 * (u ** 1.2)
        j = 0.0 if i == n else float(rng.uniform(-40, 16)) * math.sin(u * math.pi)
        pts.append((150 + 750 * u, y + j))
    return pts


CRASH = _crash()
PRE = [(96, 700), (123, 668), (150, 640)]


def crash20(f, t):
    ti, tc, td = at("in"), at("crashed"), at("days")
    f.cam(540, 920, 1.0 + 0.04 * eio(prog(t, ti, 6.0)))
    pp = prog(t, ti, 0.35)
    f.pill(540, 330, "S&P 500 · 2020", 26 * (0.8 + 0.2 * eback(pp)), eo(pp), track=0.14)
    v = int(round(34 * eo(prog(t, tc, at("percent", 2, end=True) - tc))))
    f.text(540, 462, (MINUS if v else "") + f"{v}%", 150, mixc(WHITE, RED, v / 6), 1, "black")
    f.dash(96, 640, 984, 640, MUTED, 0.22)
    f.dash(96, 1110, 984, 1110, MUTED, 0.4)
    f.text(150, 1150, "FEB 19", 20, MUTED, 0.95, "sb", track=0.22)
    f.line(PRE, WHITE, 1, 5)
    p = eio(prog(t, tc - 0.05, td - tc + 0.1))
    if p > 0.002:
        pts = partial(CRASH, p)
        f.poly(pts + [(pts[-1][0], 1110), (150, 1110)], RED, 0.07)
        f.line(pts, RED, 1, 6)
        hx, hy = pts[-1]
        f.halo(hx, hy, 75, RED, 0.85)
        f.circ(hx, hy, 10, RED_HI)
    else:
        f.halo(150, 640, 55, WHITE, 0.5)
        f.circ(150, 640, 9, WHITE)
    ra = eo(prog(t, ti + 0.3, 0.4)) * (1 - prog(t, tc + 0.2, 0.3))
    if ra > 0:
        f.ring(150, 640, (t * 0.9) % 1.0, GOLD_HI, 0.9 * ra, rmax=90, w=4)
        f.pill(330, 600, "RECORD HIGH", 20, ra, fill=None, outline=GOLD, tc=GOLD_HI, track=0.2)
        f.dash(170, 628, 236, 606, GOLD, 0.6 * ra)
    f.text(900, 1150, "MAR 23", 20, MUTED, 0.95 * eo(prog(t, td - 0.3, 0.3)), "sb", track=0.22)
    pd = prog(t, tc, at("thirtythree", end=True) - tc)
    sa = eo(prog(t, tc - 0.2, 0.35))
    f.stopwatch(400, 1300, 58, sa, ang=pd * 2 * math.pi)
    f.text(482, 1300, f"{int(round(33 * pd))} DAYS", 64, WHITE, sa, "black", anchor="lm")


# ------------------------------------------------------------------ 4 fear
FEAR = [(x, y) for y in (1030, 1180, 1330) for x in (200, 370, 540, 710, 880)]
STAY = {(370, 1030), (880, 1330), (200, 1180)}
_lo = [p for p in FEAR if p not in STAY and p != (540, 1180)]
LEAVE = {p: i for i, p in enumerate([_lo[j] for j in np.random.default_rng(4).permutation(len(_lo))])}


def fear(f, t):
    tf, te, tm, ts = at("fear"), at("everywhere"), at("many"), at("sold", 1, end=True)
    f.cam(540, 1000, 1.06 - 0.06 * eo(prog(t, tf - 0.06, 1.2)))
    pf = prog(t, tf, 0.4)
    f.pill(540, 420, "FEAR", 44 * (0.8 + 0.2 * eback(pf)), eo(pf), fill=None, outline=RED, tc=RED, track=0.35)
    for t0 in (tf, tf + 0.75, tf + 1.5, tf + 2.25):
        f.ring(540, 1180, prog(t, t0, 1.5), RED, 0.55, rmax=720, w=5)
    for x, y in FEAR:
        if (x, y) == (540, 1180):
            continue
        h = 100 if y > 1100 else 92
        red = prog(t, te - 0.35 + math.hypot(x - 540, y - 1180) / 900, 0.3)
        if (x, y) in STAY:
            back = prog(t, ts, 0.5)
            f.pawn(x, y, h, qmix(WHITE, RED, red * (1 - back)), 0.85)
            continue
        side = -1 if x < 540 else 1 if x > 540 else (-1 if y < 1180 else 1)
        tl = tm + 0.06 * LEAVE[(x, y)]
        mv = eio(prog(t, tl, 0.85))
        a = 0.85 * (1 - prog(t, tl + 0.62, 0.25))
        if a <= 0.01:
            continue
        xx = x + side * mv * 720
        bob = abs(math.sin((t - tl) * 13)) * 6 if t > tl else 0.0
        f.pawn(xx, y, h, qmix(WHITE, RED, red), a, bob)
        sp = prog(t, tl, 0.3)
        if sp > 0:
            f.pill(xx, y - h - 30 - bob, "SOLD", 14 * (0.6 + 0.4 * eback(sp)), a * eo(sp), fill=RED, tc=WHITE, padx=11, pady=6)
    you(f, 540, 1180, 112, spot=0.5, label=False, ring=eo(prog(t, ts - 0.3, 0.5)))


# ------------------------------------------------------------------ 5 recovery
CR_S = [(120 + (x - 150) * 240 / 750, y) for x, y in CRASH]
PRE_S = [(96, 690), (110, 662), (120, 640)]


def _rec():
    rng = np.random.default_rng(5)
    x0, y0 = CR_S[-1]
    pts = [(x0, y0)]
    n = 20
    for i in range(1, n + 1):
        u = i / n
        y = y0 - (y0 - 610) * (1 - (1 - u) ** 1.7)
        j = 0.0 if i == n else float(rng.uniform(-12, 24))
        pts.append((x0 + (930 - x0) * u, y + j))
    return pts


REC = _rec()
MONTHS = ["MAR", "APR", "MAY", "JUN", "JUL", "AUG"]


def recovery(f, t):
    tb, tf5, th = at("but"), at("five"), at("high")
    f.cam(520 + 40 * eio(prog(t, tb, 3.8)), 920, 1.02)
    f.pill(540, 330, "S&P 500 · 2020", 26, 1, track=0.14)
    f.dash(96, 1110, 984, 1110, MUTED, 0.4)
    f.dash(96, 640, 984, 640, GOLD, 0.55)
    f.text(100, 612, "PREVIOUS HIGH", 18, GOLD, 0.85, "sb", anchor="lm", track=0.22)
    f.text(120, 1150, "FEB", 20, MUTED, 0.95, "sb", track=0.22)
    f.line(PRE_S, WHITE, 1, 5)
    f.line(CR_S, RED, 0.9, 5)
    p = eio(prog(t, tb, th - tb + 0.15))
    pts = partial(REC, max(0.002, p))
    f.poly(pts + [(pts[-1][0], 1110), (pts[0][0], 1110)], GREEN, 0.07)
    f.line(pts, GREEN, 1, 6)
    hx, hy = pts[-1]
    f.halo(hx, hy, 75, GREEN, 0.85)
    f.circ(hx, hy, 10, GREEN_HI)
    x0b, x1b = CR_S[-1][0], 930
    for i, m in enumerate(MONTHS):
        x = x0b + i * (x1b - x0b) / 5
        lit = hx >= x - 3
        f.line([(x, 1103), (x, 1117)], MUTED, 0.7, 2)
        f.text(x, 1150, m, 20, WHITE if lit else MUTED, 1.0 if lit else 0.5, "sb", track=0.2)
    ba = eo(prog(t, tf5, 0.4))
    f.line([(x0b, 1186), (x0b, 1198), (x1b, 1198), (x1b, 1186)], GOLD, ba, 3)
    f.text((x0b + x1b) / 2, 1238, "WITHIN 5 MONTHS", 22, GOLD_HI, ba, "xb", track=0.2)
    vi = int(round(34 * clamp((hy - 640) / (1070 - 640))))
    f.text(540, 462, (MINUS if vi else "") + f"{vi}%", 150, mixc(GREEN, RED, vi / 12), 1 - prog(t, th, 0.2), "black")
    pp = prog(t, th, 0.4)
    if pp > 0:
        f.pill(540, 462, "NEW ALL-TIME HIGH", 34 * (0.8 + 0.2 * eback(pp)), eo(pp), fill=GOLD, tc=NAVY, track=0.12)
        f.flag(930, 612, eo(pp), t)
        f.ring(930, 612, prog(t, th, 0.9), GOLD_HI, 0.8, rmax=260)
        f.burst(930, 600, prog(t, th, 1.4), seed=3, n=16, spread=330)
        for i in range(5):
            sa = math.sin(math.pi * prog(t, th + 0.1 * i, 0.6))
            f.sparkle(930 + 90 * math.cos(i * 1.3), 560 + 70 * math.sin(i * 2.1), 18 * sa, GOLD_HI, sa)


# ------------------------------------------------------------------ 6 sold vs stayed
def lock(f, x, y, a, closed=1.0, c=WHITE):
    lift = (1 - closed) * 38
    cy = y - 64 - lift
    f.arc(x, cy, 40, 180, 360, c, a, w=13)
    f.line([(x - 40, cy), (x - 40, y - 44)], c, a, 13)
    f.line([(x + 40, cy), (x + 40, cy + 22 + 22 * closed)], c, a, 13)
    f.rect(x - 64, y - 50, x + 64, y + 52, c, a, r=18)
    f.circ(x, y - 6, 12, NAVY, a)
    f.rect(x - 5, y - 6, x + 5, y + 24, NAVY, a, r=3)


def split(f, t):
    t2, tl, tg = at("ones", 2), at("locked"), at("got")
    tback = at("back", 2, end=True)
    f.cam(540, 960, 1.0)
    fl = 1 - 0.6 * prog(t, t2 - 0.4, 0.4)
    fr = 0.4 + 0.6 * prog(t, t2 - 0.4, 0.4)
    f.text(540, 352, "$10,000 INVESTED · FEB 2020", 22, MUTED, 1, "sb", track=0.2)
    f.dash(540, 440, 540, 1400, MUTED, 0.35)
    f.text(270, 470, "SOLD", 28, RED, fl, "xb", track=0.32)
    f.text(810, 470, "STAYED", 28, GOLD_HI, fr, "xb", track=0.32)
    f.halo(270, 700, 150, RED, 0.6 * (1 - prog(t, tl + 0.1, 0.8)) * prog(t, tl, 0.05) * fl)
    lock(f, 270, 700, fl, closed=eback(prog(t, tl, 0.28)), c=qmix(WHITE, RED, prog(t, tl, 0.2)))
    va = eo(prog(t, at("sold", 2), 0.3))
    f.text(270, 910, "$6,600", 78, qmix(WHITE, RED, prog(t, tl, 0.3)), va * fl, "black")
    f.text(270, 978, MINUS + "$3,400 LOCKED IN", 20, RED, eo(prog(t, at("losses"), 0.3)) * fl, "xb", track=0.1)
    f.pawn(270, G, 140, mixc(WHITE, (255, 196, 190), 0.35), fl)
    for i in range(9):
        tc = tg + 0.1 * i
        pc = prog(t, tc, 0.55)
        if 0 < pc < 1:
            f.coin(810 + (i % 3 - 1) * 62 + 10 * math.sin(i), 560 + 600 * pc * pc, 19,
                   fr * (1 - prog(t, tc + 0.47, 0.08)), spin=t * 9 + i)
    pr = eio(prog(t, tg, tback - tg))
    vr = 6600 + 3400 * pr
    f.text(810, 910, "$" + format(int(round(vr / 10) * 10), ","), 78, mixc(WHITE, GREEN, pr),
           eo(prog(t, t2 - 0.3, 0.3)) * fr, "black")
    f.text(810, 978, "FULLY RECOVERED", 20, GREEN, eo(prog(t, tback, 0.3)), "xb", track=0.1)
    f.burst(810, 1080, prog(t, tback - 0.1, 1.3), seed=11, n=16, spread=330)
    hop = 26 * math.sin(math.pi * prog(t, at("back", 2), 0.45))
    f.halo(810, G + 2, 110, GOLD, 0.4 * fr, sy=0.16)
    f.pawn(810, G, 140, WHITE, fr, bob=hop)


# ------------------------------------------------------------------ 7 an average year
YEAR = [(110, 1060), (180, 1035), (250, 1045), (320, 1005), (390, 1015), (440, 985), (480, 1010), (520, 1060),
        (560, 1115), (600, 1150), (640, 1130), (690, 1080), (750, 1050), (810, 1000), (870, 1012), (930, 960), (975, 945)]
YCOL = [WHITE] * 5 + [RED] * 4 + [GREEN] * 7


def year(f, t):
    t0, t14 = at("and", 1), at("fourteen")
    f.cam(540, 960, 1.04 - 0.04 * eio(prog(t, t0, 6.0)))
    f.text(540, 352, "AN AVERAGE YEAR", 24, MUTED, eo(prog(t, t0, 0.4)), "sb", track=0.3)
    pp = prog(t, t14, 0.35)
    f.text(540, 462, MINUS + "14%", 150 * (0.85 + 0.15 * eback(pp)), RED, eo(pp), "black")
    f.dash(96, 1190, 984, 1190, MUTED, 0.35)
    f.text(110, 1230, "JAN", 20, MUTED, 0.95, "sb", track=0.22)
    f.text(975, 1230, "DEC", 20, MUTED, 0.95, "sb", track=0.22)
    p = prog(t, t0 + 0.1, at("yet") - 0.35 - t0 - 0.1)
    pts = partial(YEAR, max(0.002, p))
    f.cline(pts, YCOL, 1, 6)
    hx, hy = pts[-1]
    hc = YCOL[min(len(pts) - 2, len(YCOL) - 1)]
    f.halo(hx, hy, 60, hc if hc != WHITE else (200, 210, 240), 0.6)
    da = eo(prog(t, t14 - 0.15, 0.4))
    f.dash(440, 1150, 610, 1150, MUTED, 0.6 * da)
    f.dash(440, 985, 440, 1150, RED, 0.85 * da, w=3)
    f.text(425, 1075, MINUS + "14%", 30, RED, da, "black", anchor="rm")
    f.pawn(hx, hy - 3, 108, WHITE, 1, abs(math.sin(t * 9)) * 5 * (p < 1))
    f.text(540, 1450, "S&P 500 · AVG. INTRA-YEAR DROP 1980" + ND + "2023 · J.P. MORGAN AM", 17, MUTED, 0.75, "sb", track=0.1)


# ------------------------------------------------------------------ 8 three out of four years
def mini(cx, cy, up=True):
    pts = [(cx + (x - 540) * 0.4, cy + (y - 1050) * 0.62) for x, y in YEAR]
    if not up:
        pts = pts[:10] + [(pts[i][0], cy + 70 + (i - 10) * 3) for i in range(10, 17)]
    return pts


CARDS = [(300, 800, True), (780, 800, True), (300, 1110, False), (780, 1110, True)]


def four(f, t):
    ty, t3, t4, te = at("yet"), at("three"), at("four"), at("still")
    f.cam(540, 960, 1.0)
    p3, p4 = prog(t, t3, 0.3), prog(t, t4, 0.3)
    f.text(440, 462, "3", 150 * (0.85 + 0.15 * eback(p3)), GOLD_HI, eo(p3), "black")
    f.text(540, 462, "/", 150, MUTED, eo(p4), "black")
    f.text(640, 462, "4", 150 * (0.85 + 0.15 * eback(p4)), WHITE, eo(p4), "black")
    f.text(540, 560, "YEARS END HIGHER", 24, GREEN, eo(prog(t, at("end", 1), 0.35)), "xb", track=0.25)
    for i, (cx, cy, up) in enumerate(CARDS):
        ti = ty + 0.02 + 0.2 * i
        pa = eo(prog(t, ti, 0.3))
        if pa <= 0:
            continue
        f.rect(cx - 205, cy - 125, cx + 205, cy + 125, (20, 34, 62), 0.55 * pa, r=26)
        f.rect(cx - 205, cy - 125, cx + 205, cy + 125, MUTED, 0.3 * pa, r=26, w=2)
        f.text(cx - 180, cy - 98, f"YEAR {i + 1}", 16, MUTED, 0.9 * pa, "sb", anchor="lm", track=0.25)
        mp = mini(cx, cy, up)
        cols = YCOL if up else YCOL[:9] + [RED] * 7
        pts = partial(mp, max(0.002, prog(t, ti + 0.08, 0.6)))
        f.cline(pts, cols, pa, 4)
        ea = eo(prog(t, te + 0.12 * i, 0.3))
        if ea > 0:
            ex, ey = mp[-1]
            cc = GREEN if up else RED
            f.halo(ex, ey, 46, cc, 0.7 * ea)
            f.circ(ex, ey, 17 * (0.7 + 0.3 * eback(prog(t, te + 0.12 * i, 0.35))), cc, ea)
            if up:
                f.line([(ex - 7, ey + 1), (ex - 2, ey + 6), (ex + 8, ey - 6)], NAVY, ea, 4)
            else:
                f.line([(ex - 6, ey - 6), (ex + 6, ey + 6)], NAVY, ea, 4)
                f.line([(ex - 6, ey + 6), (ex + 6, ey - 6)], NAVY, ea, 4)
    f.text(540, 1450, "S&P 500 · POSITIVE IN 33 OF 44 YEARS · 1980" + ND + "2023", 17, MUTED, 0.75, "sb", track=0.1)


# ------------------------------------------------------------------ 9 hidden cost: the 10 best days
_r = np.random.default_rng(42)
BEST = {}
for _i, _c in enumerate([1, 4, 6, 9, 11, 13, 16, 18, 21, 23]):
    BEST[(_c, int(_r.integers(0, 12)))] = _i


def hidden(f, t):
    t0, th, tten, tyrs = at("selling", 2), at("hidden"), at("ten"), at("years", 2)
    tand, tless, thalf = at("and", 2), at("less"), at("half")
    f.cam(540, 920, 1.03 - 0.03 * eio(prog(t, t0, 8.0)))
    ph = prog(t, th, 0.35)
    f.pill(540, 340, "HIDDEN COST", 30 * (0.8 + 0.2 * eback(ph)), eo(ph), fill=None, outline=RED, tc=RED, track=0.22)
    f.text(540, 425, "20 YEARS ≈ 5,000 TRADING DAYS", 19, MUTED, eo(prog(t, t0 + 0.1, 0.4)), "sb", track=0.16)
    for c in range(25):
        ap = eo(prog(t, t0 + c * 0.04, 0.3))
        if ap <= 0:
            continue
        x = 156 + c * 32
        for r in range(12):
            y = 470 + r * 32
            i = BEST.get((c, r))
            if i is None:
                f.circ(x, y, 4, WHITE, 0.3 * ap)
                continue
            lit = eo(prog(t, tten + 0.07 * i, 0.25))
            pl = prog(t, tyrs + 0.06 * i, 0.5)
            if pl <= 0:
                f.halo(x, y, 34, GOLD, 0.75 * lit)
                f.circ(x, y, 4 + 4 * lit, mixc(WHITE, GOLD_HI, lit), ap * (0.3 + 0.7 * lit))
            else:
                yy = y - 280 * eo(pl)
                f.halo(x, yy, 34, GOLD, 0.75 * (1 - pl))
                f.circ(x, yy, 8, GOLD_HI, 1 - pl)
                f.circ(x, y, 7, MUTED, 0.55 * ap, w=2)
    missed = t >= tyrs + 0.3
    f.text(540, 870, "10 BEST DAYS MISSED" if missed else "THE 10 BEST DAYS", 24, RED if missed else GOLD_HI,
           eo(prog(t, tten, 0.3)), "xb", track=0.22)
    gb = eo(prog(t, tand, 0.55))
    if gb > 0:
        sh = eio(prog(t, tless, thalf + 0.3 - tless))
        base = 1330
        h1 = 320 * gb
        h2 = 320 * gb * (1 - 0.54 * sh)
        c2 = mixc(GOLD, RED, sh)
        for bx, hh, cc in ((360, h1, GREEN), (720, h2, c2)):
            f.rect(bx - 85, base - hh, bx + 85, base, cc, 0.32 * gb, r=12)
            f.rect(bx - 85, base - hh, bx + 85, base, cc, 0.95 * gb, r=12, w=3)
            f.rect(bx - 85, base - hh, bx + 85, base - hh + 10, cc, gb, r=5)
            f.halo(bx, base - hh, 90, cc, 0.4 * gb, sy=0.35)
        f.line([(230, base), (850, base)], MUTED, 0.5 * gb, 2)
        ha = eo(prog(t, tless, 0.3))
        f.dash(615, base - 160, 830, base - 160, MUTED, 0.7 * ha)
        f.text(840, base - 160, "HALF", 16, MUTED, ha, "sb", anchor="lm", track=0.2)
        f.text(360, base + 40, "STAYED INVESTED", 18, GREEN, gb, "xb", track=0.12)
        f.text(720, base + 40, "MISSED 10 BEST DAYS", 18, c2, gb, "xb", track=0.12)
        pp = prog(t, thalf, 0.35)
        f.pill(720, base - 232, "LESS THAN HALF", 22 * (0.8 + 0.2 * eback(pp)), eo(pp), fill=RED, tc=WHITE, track=0.12)
    f.text(540, 1450, "S&P 500 · J.P. MORGAN ASSET MANAGEMENT · 20-YEAR PERIODS", 17, MUTED,
           0.75 * eo(prog(t, tand, 0.4)), "sb", track=0.1)


# ------------------------------------------------------------------ 10 best days follow worst days
_rb = np.random.default_rng(77)
BW = [float(_rb.uniform(16, 78)) * (1 if _rb.random() < 0.55 else -1) for _ in range(34)]
BW[12], BW[13], BW[23], BW[24] = -250.0, 230.0, -205.0, 190.0
BX = [130 + i * 24.5 for i in range(34)]


def bestworst(f, t):
    t0, tb, tw = at("and", 3), at("best", 2), at("worst")
    f.cam(540, 980, 1.0)
    f.text(540, 352, "DAILY MOVES", 24, MUTED, 1, "sb", track=0.3)
    f.dash(96, 1000, 984, 1000, MUTED, 0.4)
    lb, lw = eo(prog(t, tb, 0.3)), eo(prog(t, tw, 0.3))
    for i, h in enumerate(BW):
        g = eo(prog(t, t0 + i * 0.022, 0.3))
        if g <= 0:
            continue
        x = BX[i]
        if i in (13, 24):
            c, a = mixc(WHITE, GREEN, lb), 0.55 + 0.45 * lb
        elif i in (12, 23):
            c, a = mixc(WHITE, RED, lw), 0.55 + 0.45 * lw
        else:
            c, a = (GREEN if h > 0 else RED), 0.3
        hh = h * g
        f.rect(x - 6, min(1000, 1000 - hh), x + 6, max(1000, 1000 - hh), c, a, r=4)
        if i in (13, 24):
            f.halo(x, 1000 - hh, 60, GREEN, 0.6 * lb)
        if i in (12, 23):
            f.halo(x, 1000 - hh, 60, RED, 0.6 * lw)
    f.text(575, 690, "BEST DAYS", 26, GREEN, lb, "xb", track=0.25)
    f.dash(560, 712, BX[13], 1000 - 230 - 18, GREEN, 0.6 * lb)
    f.dash(600, 712, BX[24], 1000 - 190 - 18, GREEN, 0.6 * lb)
    f.text(575, 1320, "WORST DAYS", 26, RED, lw, "xb", track=0.25)
    f.dash(560, 1296, BX[12], 1000 + 250 + 18, RED, 0.6 * lw)
    f.dash(600, 1296, BX[23], 1000 + 205 + 18, RED, 0.6 * lw)
    hp = eo(prog(t, tw + 0.35, 0.35))
    for i in (12, 23):
        f.rect(BX[i] - 22, 1000 - BW[i + 1] - 26, BX[i + 1] + 22, 1000 - BW[i] + 26, GOLD_HI, 0.9 * hp, r=18, w=3)


# ------------------------------------------------------------------ 11 don't run / focus / discipline
PH_RED = [(420, 600), (460, 640), (490, 625), (530, 700), (560, 680), (600, 790), (630, 770), (665, 880)]
PH_GRN = [(420, 900), (465, 865), (505, 880), (550, 800), (590, 815), (630, 720), (665, 640)]


def phone(f, x, y, w, h, a, pr=0.0, lit=1.0, pg=0.0):
    if a <= 0.01:
        return
    f.halo(x, y, w * 0.95, RED, 0.45 * a * pr * lit)
    f.halo(x, y, w * 0.95, GREEN, 0.3 * a * pg)
    f.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, (12, 20, 40), a, r=46)
    sx0, sy0, sx1, sy1 = x - w / 2 + 16, y - h / 2 + 56, x + w / 2 - 16, y + h / 2 - 26
    if pr > 0 and lit > 0.01:
        f.rect(sx0, sy0, sx1, sy1, RED, 0.15 * pr * lit * a, r=30)
        f.text(x, sy0 + 74, MINUS + "30%", 64, RED, a * lit * eo(pr * 2), "black")
        f.line(partial(PH_RED, pr), RED, a * lit, 5)
    if pg > 0:
        f.rect(sx0, sy0, sx1, sy1, GREEN, 0.07 * pg * a, r=30)
        pts = partial(PH_GRN, pg)
        f.line(pts, GREEN, a, 5)
        f.halo(pts[-1][0], pts[-1][1], 50, GREEN, 0.7 * a)
        f.circ(pts[-1][0], pts[-1][1], 8, GREEN_HI, a)
    f.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, WHITE, a, r=46, w=5)
    f.rect(x - 38, y - h / 2 + 20, x + 38, y - h / 2 + 34, WHITE, 0.55 * a, r=7)


def hero(f, t):
    t0, ts, tr, tdr, tst, tk = at("so"), at("screen"), at("red", 1), at("dont"), at("stay"), at("keep")
    f.cam(540, 960, 1.0 + 0.05 * eio(prog(t, t0, 6.2)))
    phone(f, 540, 700, 330, 600, eo(prog(t, ts - 0.35, 0.4)), eio(prog(t, tr - 0.1, 0.7)),
          1 - eo(prog(t, tst + 0.15, 0.4)), eio(prog(t, tk + 0.45, 1.3)))
    for i in range(4):
        u = prog(t, tdr - 0.1 + 0.17 * i, 0.95)
        if 0 < u < 1:
            x = -120 + u * 1320
            y = 1225 - (i % 2) * 18
            f.pawn(x, y, 104 + (i % 2) * 10, qmix(WHITE, RED, 0.6), 0.6, abs(math.sin(u * 26)) * 8)
            for j in range(3):
                yy = y - 30 - 30 * j
                f.line([(x - 60 - 15 * j, yy), (x - 170 - 25 * j, yy)], WHITE, 0.2, 3)
    focus = eo(prog(t, tst, 0.45))
    you(f, 540, 1290, 160, spot=0.35 + 0.95 * focus, label=False, ring=eo(prog(t, tdr + 0.15, 0.4)))
    pf = prog(t, tst, 0.35)
    f.pill(300, 1105, "FOCUS", 30 * (0.75 + 0.25 * eback(pf)), eo(pf), fill=GOLD, tc=NAVY, track=0.22)
    pd = prog(t, tk, 0.35)
    f.pill(780, 1105, "DISCIPLINE", 30 * (0.75 + 0.25 * eback(pd)), eo(pd), fill=WHITE, tc=NAVY, track=0.18)
    for i in range(4):
        tc = tk + 0.1 + 0.32 * i
        u = prog(t, tc, 0.45)
        if 0 < u < 1:
            f.coin(540 + 40 * math.sin(u * math.pi) * (1 if i % 2 else -1), 1150 - 330 * eio(u) - 120 * math.sin(math.pi * u),
                   21, 1, spin=t * 10 + i)
        sp = math.sin(math.pi * prog(t, tc + 0.42, 0.45))
        if sp > 0:
            f.sparkle(540 + 30 * (i - 1.5), 840 - 14 * i, 26 * sp, GOLD_HI, sp)


# ------------------------------------------------------------------ 12 smartest vs most patient
ZIG = [(110, 1190), (150, 1080), (190, 1210), (230, 1050), (270, 1180), (310, 1020), (350, 1160), (390, 1060),
       (430, 1200), (470, 1130)]
STEADY = [(600, 1270), (660, 1235), (720, 1190), (770, 1206), (815, 1150), (860, 1080), (900, 990), (930, 900)]
SCOL = [GOLD, GOLD, RED, GREEN, GREEN, GREEN, GREEN]


def bulb(f, x, y, a, glow=0.0):
    if a <= 0.01:
        return
    f.halo(x, y, 90, GOLD_HI, 0.5 * glow * a)
    for i in range(7):
        q = math.pi * (0.75 + 0.25 * i)
        f.line([(x + math.cos(q) * 48, y + math.sin(q) * 48), (x + math.cos(q) * 62, y + math.sin(q) * 62)], GOLD_HI, a * glow, 4)
    f.circ(x, y, 34, mixc(WHITE, GOLD_HI, glow), a, w=5)
    f.rect(x - 17, y + 30, x + 17, y + 52, WHITE, a, r=4, w=4)
    f.line([(x - 11, y + 62), (x + 11, y + 62)], WHITE, a, 4)


def hourglass(f, x, y, a, p):
    if a <= 0.01:
        return
    f.line([(x - 36, y - 52), (x + 36, y - 52)], WHITE, a, 5)
    f.line([(x - 36, y + 52), (x + 36, y + 52)], WHITE, a, 5)
    f.line([(x - 28, y - 50), (x - 4, y - 4), (x - 4, y + 4), (x - 28, y + 50)], WHITE, a, 4)
    f.line([(x + 28, y - 50), (x + 4, y - 4), (x + 4, y + 4), (x + 28, y + 50)], WHITE, a, 4)
    q = 1 - clamp(p)
    if q > 0.02:
        f.poly([(x - 22 * q, y - 6 - 36 * q), (x + 22 * q, y - 6 - 36 * q), (x, y - 4)], GOLD_HI, a)
    if 0 < p < 1:
        f.line([(x, y), (x, y + 44)], GOLD_HI, a, 2)
    k = clamp(p * 1.4)
    if k > 0.02:
        f.poly([(x - 22 * k, y + 46), (x + 22 * k, y + 46), (x, y + 46 - 32 * clamp(p))], GOLD_HI, a)


def patient(f, t):
    t0, tsm, trw, tpt = at("the", 10), at("smartest"), at("rewards"), at("patient")
    tend = at("ones", 4, end=True)
    f.cam(540, 960, 1.0)
    f.dash(540, 440, 540, 1400, MUTED, 0.35)
    la = 1 - 0.55 * prog(t, trw - 0.2, 0.4)
    ra = 0.45 + 0.55 * prog(t, trw - 0.2, 0.4)
    sa = eo(prog(t, tsm, 0.35))
    f.text(270, 470, "SMARTEST", 28, WHITE, sa * la, "xb", track=0.3)
    bulb(f, 270, 610, sa * la, glow=sa * la)
    pa = eo(prog(t, tpt, 0.35))
    f.text(780, 470, "MOST PATIENT", 28, GOLD_HI, pa, "xb", track=0.3)
    hourglass(f, 780, 610, pa, prog(t, tpt, 1.6))
    pz = prog(t, t0 + 0.1, trw - 0.35 - t0 - 0.1)
    pts = partial(ZIG, max(0.002, pz))
    f.line(pts, WHITE, 0.9 * la, 5)
    hx, hy = pts[-1]
    f.pawn(hx, hy - 3, 100, WHITE, la, abs(math.sin(t * 11)) * 14 * (pz < 1))
    ps = eio(prog(t, trw, tend - trw - 0.2))
    spts = partial(STEADY, max(0.002, ps))
    f.cline(spts, SCOL, ra, 6)
    sx, sy = spts[-1]
    f.halo(sx, sy, 60, GREEN, 0.5 * ra)
    pf = prog(t, tend - 0.2, 0.4)
    if pf > 0:
        f.flag(930, 900, eo(pf), t, c=GOLD, h=130, fw=80)
        f.ring(930, 900, prog(t, tend - 0.2, 0.9), GREEN_HI, 0.8, rmax=240)
    f.pawn(sx, sy - 3, 100, WHITE, ra, abs(math.sin(t * 8)) * 4 * (ps < 1))
    f.burst(900, 900, prog(t, tend - 0.2, 1.3), seed=21, n=14, spread=300)


# ------------------------------------------------------------------ 13 red days -> green years
DIPS = [(12, 60, 3.0), (27, 95, 4.0), (41, 55, 3.0), (55, 140, 5.0), (68, 70, 3.5), (80, 85, 4.0)]


def _long():
    rng = np.random.default_rng(8)
    pts = []
    for i in range(91):
        u = i / 90
        trend = 1370 - 620 * (u ** 1.6)
        dip = sum(dp * math.exp(-((i - c) / wd) ** 2) for c, dp, wd in DIPS)
        pts.append((110 + 820 * u, trend + dip + float(rng.uniform(-7, 7))))
    return pts


LONG = _long()
LDOWN = [LONG[i + 1][1] - LONG[i][1] > 5 for i in range(90)]


def finale(f, t):
    tr2, tg = at("red", 2), at("green")
    tfol = at("years", 3, end=True) + 0.27
    k = eio(prog(t, tr2 + 0.3, tg - tr2 - 0.4))
    c0 = (LONG[27][0], LONG[27][1] - 40, 2.2)
    f.cam(lerp(c0[0], 540, k), lerp(c0[1], 900, k), math.exp(lerp(math.log(c0[2]), 0.0, k)))
    p = 0.2 + 0.8 * eio(prog(t, tr2 - 0.1, tg - tr2 - 0.05))
    pts = partial(LONG, p)
    cols = [RED if LDOWN[i] else mixc(WHITE, GREEN, prog(t, tg + 0.5 * i / 90, 0.15)) for i in range(len(pts) - 1)]
    f.cline(pts, cols, 1, 5)
    rd = math.sin(math.pi * prog(t, tr2, 1.4))
    if rd > 0:
        for c, _, _ in DIPS:
            if c < len(pts) - 1:
                f.halo(LONG[c][0], LONG[c][1], 60, RED, 0.5 * rd)
    hx, hy = pts[-1]
    f.halo(hx, hy, 70, GREEN if t >= tg else (200, 210, 240), 0.6)
    pf = prog(t, tg + 0.2, 0.4)
    if pf > 0:
        f.flag(hx, hy, eo(pf), t, c=GOLD, h=120, fw=76)
    f.pawn(hx, hy - 3, 76, WHITE, 1, abs(math.sin(t * 9)) * 4 * (p < 1))
    f.ring(hx, hy, prog(t, tg + 0.05, 1.0), GREEN_HI, 0.8, rmax=380)
    f.burst(hx - 40, hy - 10, prog(t, tg + 0.1, 1.5), seed=31, n=22, spread=300, grav=1100)
    for i in range(6):
        sa = math.sin(math.pi * prog(t, tg + 0.15 + 0.12 * i, 0.6))
        f.sparkle(hx - 160 + 60 * i, hy - 120 - 40 * math.sin(i * 1.7), 22 * sa, GOLD_HI, sa)
    f.cam(540, 960, 1.0)
    p1 = prog(t, tr2, 0.35)
    f.text(540, 380, "RED DAYS", 104 * (0.85 + 0.15 * eback(p1)), RED, eo(p1), "black")
    p2 = prog(t, tg, 0.35)
    f.text(540, 500, "GREEN YEARS", 104 * (0.85 + 0.15 * eback(p2)), GREEN, eo(p2), "black")
    p3 = prog(t, tfol, 0.4)
    f.pill(540, 1440, "FOLLOW FOR MORE", 26 * (0.8 + 0.2 * eback(p3)), eo(p3), fill=None, outline=GOLD, tc=GOLD_HI, track=0.2)


def loopback(f, t):
    hook(f, 0.0)


# ------------------------------------------------------------------ timeline
SHOTS = [
    (0.0, at("everyone") - 0.12, hook, None),
    (at("everyone") - 0.12, at("in") - 0.1, crowd, "zoom"),
    (at("in") - 0.1, at("fear") - 0.06, crash20, "flash"),
    (at("fear") - 0.06, at("but") - 0.06, fear, "whip"),
    (at("but") - 0.06, at("the", 2) - 0.06, recovery, "zoom"),
    (at("the", 2) - 0.06, at("and", 1) - 0.06, split, "wipe"),
    (at("and", 1) - 0.06, at("yet") - 0.06, year, "zoom"),
    (at("yet") - 0.06, at("selling", 2) - 0.06, four, "zoom"),
    (at("selling", 2) - 0.06, at("and", 3) - 0.06, hidden, "whip"),
    (at("and", 3) - 0.06, at("so") - 0.06, bestworst, "zoom"),
    (at("so") - 0.06, at("the", 10) - 0.06, hero, "fade"),
    (at("the", 10) - 0.06, at("red", 2) - 0.08, patient, "wipe"),
    (at("red", 2) - 0.08, 65.2, finale, "zoom"),
    (65.2, DUR, loopback, "zoom"),
]
TR = 0.32
SHAKES = [(at("down") + 0.85, 0.45, 9), (at("crashed") + 0.1, 0.5, 10), (at("red", 1) + 0.05, 0.35, 6),
          (at("green") + 0.05, 0.4, 7)]
FLASH_C = (235, 245, 238)


def tint_at(t):
    k = 0.26 * prog(t, at("down") + 0.6, 0.3) * (1 - prog(t, 3.0, 0.6))
    k = max(k, 0.2 * prog(t, at("crashed"), 0.4) * (1 - prog(t, 13.2, 0.4)))
    if 13.5 <= t < 17.2:
        k = max(k, (0.1 + 0.06 * math.sin(t * 7)) * prog(t, 13.6, 0.3) * (1 - prog(t, 16.6, 0.5)))
    k = max(k, 0.24 * prog(t, at("red", 1), 0.4) * (1 - prog(t, at("stay"), 0.5)))
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
    f = F(0.0)
    f.text(540, 300, "YOUR PORTFOLIO", 30, MUTED, 1, "sb", track=0.3)
    f.text(540, 440, MINUS + "30%", 220, RED, 1, "black")
    f.text(540, 625, "EVERYONE IS SELLING.", 62, WHITE, 1, "black")
    f.text(540, 715, "WHAT DO YOU DO?", 80, GOLD_HI, 1, "black")
    f.dash(20, G + 2, 1060, G + 2, MUTED, 0.35)
    for x in (150, 280, 800, 930):
        f.pawn(x, G, 118, qmix(WHITE, RED, 1), 0.5)
        f.pill(x, G - 156, "SELL", 15, 0.55, fill=RED, tc=WHITE, padx=13, pady=7)
    you(f, 540, G, 175, spot=1.15)
    f.dash(505, 1085, 360, 1015, MUTED, 0.5)
    f.dash(575, 1085, 720, 1015, MUTED, 0.5)
    f.pill(300, 985, "SELL", 36, 1, fill=None, outline=RED, tc=RED, track=0.22)
    f.pill(780, 985, "HOLD", 36, 1, fill=GOLD, tc=NAVY, track=0.22)
    f.text(540, 990, "?", 110, GOLD_HI, 1, "black")
    im = post(f.img, 0.0, tint=(RED, 0.16))
    d = ImageDraw.Draw(im, "RGBA")
    d.text((W - 60, 1700), "Moneycheck", font=font("sb", 32), fill=(255, 255, 255, 153), anchor="rm")
    im.save("cover_hold_or_sell_1080x1920.png")


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

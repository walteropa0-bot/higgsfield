"""YT01 scenes: 'Most stocks lose money - so why does the market go up?' (16:9, ~9.5 min).

Every scene starts on a phrase of script.txt and every animation inside a scene is keyed to phrases (T / TE),
so the same code works with the estimated timing (preview) and with the real Voice Studio word times.
"""
import functools
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import lib16 as L  # noqa: E402
from lib16 import (W, H, prog, eo, eio, eback, lerp, mixc, qmix, clamp, WHITE, MUTED, GOLD, GOLD_HI, GREEN,  # noqa: E402
                   GREEN_HI, RED, RED_HI, NAVY, DARKCARD, DARKCARD2, kline, kwords, label, figure, rays, card, bar,
                   hbar, arrow, money)
from tl import Timeline  # noqa: E402

TL = Timeline()
T = functools.lru_cache(maxsize=None)(TL.T)
TE = functools.lru_cache(maxsize=None)(TL.TE)
DUR = TL.dur
AMBER = (232, 160, 70)
DIM = (70, 84, 112)
SC = []

DATA = json.load(open(os.path.join(HERE, "data", "sp500_tbill_1928_2025.json")))["years"]
YEARS = sorted(int(y) for y in DATA)


def scene(phrase, n=1, chapter=None, src=None, lead=0.25, fx=()):
    def deco(fn):
        SC.append(dict(phrase=phrase, n=n, fn=fn, chapter=chapter, src=src, lead=lead, fx=list(fx)))
        return fn
    return deco


def ap(t, phrase, d=0.45, n=1, off=0.0):
    """appear-progress keyed to a phrase"""
    return prog(t, T(phrase, n) + off, d)


def gone(t, phrase, d=0.35, n=1, off=0.0):
    return 1 - eio(prog(t, T(phrase, n) + off, d))


def push(f, lt, z0=1.0, z1=1.04, d=8.0, cx=W / 2, cy=H / 2):
    f.cam(cx, cy, z0 + (z1 - z0) * eio(lt / d))


def headline(f, t, phrase, lines, y0=200, size=74, gap=None, a=1.0, n=1, off=0.0):
    gap = gap or size * 1.12
    for i, (s, c) in enumerate(lines):
        kline(f, W / 2, y0 + i * gap, s, size if i == 0 else size * 0.92, c, t, T(phrase, n) + off + 0.12 * i, a)


def perm(n, seed):
    return np.random.default_rng(seed).permutation(n)


def grid_pos(i, cols, cx, cy, sx, sy, n):
    rows = (n + cols - 1) // cols
    r, c = divmod(i, cols)
    return cx + (c - (cols - 1) / 2) * sx, cy + (r - (rows - 1) / 2) * sy


def pawn_grid(f, t, a, n, cols, cx, cy, sx, sy, h, col_fn, alpha_fn=None, appear=None, bob=0.0):
    for i in range(n):
        x, y = grid_pos(i, cols, cx, cy, sx, sy, n)
        aa = a
        if appear is not None:
            aa *= eo(clamp((appear * (n + 12) - i) / 12))
        if alpha_fn:
            aa *= alpha_fn(i)
        if aa > 0.01:
            f.pawn(x, y + h * 0.5, h, col_fn(i), aa, bob * abs(math.sin(t * 5 + i)))


def chapter_card(f, t, a, lt, num, title):
    push(f, lt, 1.0, 1.05, 4.0)
    p = eo(prog(lt, 0.0, 0.6))
    f.halo(W / 2, 520, 520, GOLD, 0.18 * a * p, sy=0.55)
    f.text(W / 2, 470, f"{num:02d}", 300 * (0.9 + 0.1 * eback(prog(lt, 0, 0.6))), GOLD, a * p * 0.9, "black")
    kline(f, W / 2, 670, title, 96, WHITE, lt, 0.25, a, track=0.06)
    q = eio(prog(lt, 0.45, 0.8))
    f.line([(W / 2 - 330 * q, 755), (W / 2 + 330 * q, 755)], GOLD_HI, a * q, 4)
    label(f, W / 2, 330, f"CHAPTER {num}", 24, a * eo(prog(lt, 0.1, 0.4)))


def stat(f, t, x, y, big, small, c, t0, a=1.0, size=150, ssize=30):
    p = prog(t, t0, 0.5)
    if p <= 0:
        return
    f.text(x, y, big, size * (0.85 + 0.15 * eback(p)), c, a * eo(p), "black")
    kline(f, x, y + size * 0.62, small, ssize, WHITE, t, t0 + 0.2, a, w="xb", track=0.14)


def coin_flip(f, x, y, r, t, a, spin=True):
    f.halo(x, y, r * 1.6, GOLD, 0.35 * a)
    f.coin(x, y, r, a, spin=t * 7 if spin else 0.0)


def paper(f, x, y, w, h, a, title_lines, tag, tc=GOLD_HI):
    if a <= 0.01:
        return
    card(f, x - w / 2, y - h / 2, x + w / 2, y + h / 2, a, c=(236, 238, 244), r=10)
    f.rect(x - w / 2, y - h / 2, x + w / 2, y - h / 2 + 46, GOLD, a, r=10)
    f.rect(x - w / 2, y - h / 2 + 30, x + w / 2, y - h / 2 + 46, GOLD, a)
    f.text(x, y - h / 2 + 24, tag, 20, NAVY, a, "black", track=0.16)
    for i, s in enumerate(title_lines):
        f.text(x, y - h / 2 + 92 + i * 38, s, 28, NAVY, a, "black")
    for i in range(5):
        yy = y - h / 2 + 100 + len(title_lines) * 38 + i * 26
        if yy < y + h / 2 - 20:
            f.line([(x - w / 2 + 34, yy), (x + w / 2 - 34 - (i % 3) * 40, yy)], (150, 160, 180), a * 0.8, 5)


def check(f, x, y, s, c, a, p=1.0):
    pts = [(x - 0.5 * s, y), (x - 0.15 * s, y + 0.35 * s), (x + 0.55 * s, y - 0.4 * s)]
    f.line(L.partial(pts, max(0.002, p)), c, a, 0.16 * s)


def cross(f, x, y, s, c, a):
    f.line([(x - s, y - s), (x + s, y + s)], c, a, 0.25 * s)
    f.line([(x - s, y + s), (x + s, y - s)], c, a, 0.25 * s)


def donut(f, x, y, r, w, share, c, a, base=(44, 58, 88), start=-90):
    box = (f.X(x - r), f.Y(y - r), f.X(x + r), f.Y(y + r))
    f.d.arc(box, 0, 360, fill=L.ca(base, 0.9 * a), width=f.wpx(w))
    if share > 0.002:
        f.d.arc(box, start, start + 360 * share, fill=L.ca(c, a), width=f.wpx(w))


def market_curve(x0, x1, ybot, ytop, years=YEARS, key="sp500", vmax=None):
    v = 1.0
    vals = []
    for y in years:
        v *= 1 + DATA[str(y)][key]
        vals.append(v)
    lv = np.log(vals)
    hi = math.log(vmax) if vmax else lv.max()
    pts = [(lerp(x0, x1, i / (len(years) - 1)), lerp(ybot, ytop, (l - 0) / hi)) for i, l in enumerate(lv)]
    return pts, vals


# ================================================================== PART 1 · HOOK
@scene("Here's a fact that sounds impossible.", lead=0.0, fx=[(None, 0.0, "bass", 0.5), (None, 0.3, "riser", 0.25)])
def s01(f, t, a, lt):
    push(f, lt, 1.0, 1.06, 6.0)
    for i in range(11):
        x = 360 + i * 120
        on = i == 5
        figure(f, x, 900, 120 if on else 92, a * (1.0 if on else 0.35), c=WHITE if on else (150, 165, 200),
               spot=0.9 if on else 0.0, bob=0)
    kline(f, W / 2, 330, "A FACT THAT SOUNDS", 78, WHITE, lt, 0.1, a)
    p = prog(lt, 0.55, 0.5)
    f.text(W / 2, 455, "IMPOSSIBLE.", 150 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")


@scene("Over the last one hundred years", src="BESSEMBINDER (2026), CRSP 1926–2025: +1,504,057% · CURVE: S&P 500 INCL. DIVIDENDS 1928–2025 (DAMODARAN)",
       fx=[(None, 0.0, "whoosh", 0.4), ("Over the last", 0.3, "swoosh_up", 0.35), ("fifteen thousand dollars", 0.0, "cash", 0.5)])
def s02(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 8.0)
    x0, x1, yb, yt = 300, 1640, 880, 330
    pts, vals = market_curve(x0, x1, yb, yt)
    t0, t1 = T("one hundred years"), TE("fifteen thousand dollars")
    p = eio(prog(t, t0, max(0.5, t1 - t0)))
    f.dash(x0, yb, x1, yb, MUTED, 0.5 * a)
    f.text(x0, yb + 40, "1926", 26, MUTED, a, "xb")
    f.text(x1, yb + 40, "2025", 26, MUTED, a, "xb")
    sub = L.partial(pts, max(0.002, p))
    cols = [GREEN if y1 <= y0 else RED for (x0_, y0), (x1_, y1) in zip(sub, sub[1:])] or [GREEN]
    f.cline(sub, cols, a, 6)
    hx, hy = sub[-1]
    f.halo(hx, hy, 70, GREEN, 0.8 * a)
    f.circ(hx, hy, 9, GREEN_HI, a)
    val = math.exp(math.log(15041.57) * p)
    label(f, W / 2, 150, "THE U.S. STOCK MARKET · 100 YEARS", 24, a * eo(ap(t, "the US stock market")))
    f.text(W / 2, 250, "$1  →  " + money(val), 104, GREEN_HI if p > 0.98 else WHITE, a * eo(ap(t, "one dollar")), "black")
    f.burst(hx, hy, prog(t, TE("fifteen thousand dollars") - 0.1, 1.4), seed=3, n=18, spread=380, a=a)


@scene("And yet, the typical US stock lost money.", src="BESSEMBINDER (2026): MEDIAN LIFETIME BUY-AND-HOLD RETURN −6.9%",
       fx=[(None, 0.0, "whoosh", 0.4), ("lost money", 0.0, "sweep_down", 0.45)])
def s03(f, t, a, lt):
    push(f, lt, 1.0, 1.05, 5.0)
    for i in range(15):
        if i == 7:
            continue
        x = 300 + i * 94
        f.pawn(x, 930, 70, (120, 135, 170), a * 0.28)
    red = eo(ap(t, "lost money", 0.6))
    figure(f, W / 2, 900, 230, a, c=mixc(WHITE, RED, red), spot=1.0)
    label(f, W / 2, 360, "THE TYPICAL STOCK", 30, a * eo(ap(t, "typical")), c=WHITE)
    p = ap(t, "lost money", 0.5)
    f.text(W / 2, 250, "−6.9%", 160 * (0.85 + 0.15 * eback(p)), RED_HI, a * eo(p), "black")


@scene("Not a few unlucky ones.", src="BESSEMBINDER (2026): ONLY 48% OF STOCKS HAD A POSITIVE LIFETIME RETURN · ONLY 41% BEAT 1-MONTH T-BILLS",
       fx=[(None, 0.0, "whoosh", 0.35), ("more than half", 0.0, "sweep_down", 0.35), ("didn't even beat", 0.2, "alert", 0.3)])
def s04(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    order = perm(100, 4)
    rank = np.empty(100, int)
    rank[order] = np.arange(100)
    p1 = eio(ap(t, "more than half", 1.4))
    p2 = eio(ap(t, "didn't even beat", 1.0))

    def col(i):
        r = rank[i]
        if r < 52 and r < p1 * 52:
            return RED
        if 52 <= r < 59 and (r - 52) < p2 * 7:
            return AMBER
        return (205, 214, 232)

    pawn_grid(f, t, a, 100, 20, W / 2, 610, 74, 92, 54, col, appear=prog(lt, 0.0, 1.0))
    kline(f, W / 2, 175, "MORE THAN HALF LOST MONEY", 64, RED_HI, t, T("more than half"), a)
    kline(f, W / 2, 255, "MOST DIDN'T BEAT A TREASURY BILL", 46, AMBER, t, T("didn't even beat"), a)
    if p2 > 0:
        f.pill(560, 920, "LOST MONEY · 52%", 22, a * eo(p2), fill=RED, tc=WHITE, track=0.12)
        f.pill(960, 920, "LESS THAN T-BILLS · 7%", 22, a * eo(p2), fill=AMBER, tc=NAVY, track=0.12)
        f.pill(1360, 920, "BEAT T-BILLS · 41%", 22, a * eo(p2), fill=None, outline=WHITE, tc=WHITE, track=0.12)


@scene("Both facts are true at the same time.", fx=[(None, 0.0, "whoosh", 0.4), ("Both facts", 0.3, "ding", 0.35),
                                                    ("real data", 0.0, "pop", 0.4), ("coin-flip game", 0.0, "pop", 0.4),
                                                    ("what it means", 0.0, "pop", 0.4)])
def s05(f, t, a, lt):
    push(f, lt, 1.0, 1.02, 10.0)
    up = eio(ap(t, "I'll show you how", 0.8))
    y = lerp(500, 380, up)
    s = lerp(1.15, 0.9, up)
    pl, pr = eo(prog(lt, 0.0, 0.5)), eo(prog(lt, 0.25, 0.5))
    card(f, 600 - 290 * s, y - 150 * s, 600 + 290 * s, y + 150 * s, a * pl, edge=GREEN, glow=GREEN)
    f.text(600, y - 80 * s, "THE MARKET", 30 * s, GREEN_HI, a * pl, "xb", track=0.2)
    f.text(600, y + 20 * s, "$1 → $15,041", 82 * s, WHITE, a * pl, "black")
    card(f, 1320 - 290 * s, y - 150 * s, 1320 + 290 * s, y + 150 * s, a * pr, edge=RED, glow=RED)
    f.text(1320, y - 80 * s, "THE TYPICAL STOCK", 30 * s, RED_HI, a * pr, "xb", track=0.2)
    f.text(1320, y + 20 * s, "−6.9%", 96 * s, WHITE, a * pr, "black")
    pb = ap(t, "true at the same time", 0.5)
    f.pill(W / 2, y + 195 * s, "BOTH ARE TRUE", 30 * (0.8 + 0.2 * eback(pb)), a * eo(pb), fill=GOLD, tc=NAVY, track=0.2)
    for i, (ph, s_) in enumerate((("real data", "REAL DATA"), ("coin-flip game", "A COIN-FLIP GAME"),
                                  ("what it means", "WHAT IT MEANS"))):
        p = ap(t, ph, 0.45)
        x = 480 + i * 480
        f.circ(x, 760, 46 * eo(p), GOLD_HI, a * eo(p), w=4)
        f.text(x, 760, str(i + 1), 44, GOLD_HI, a * eo(p), "black")
        f.text(x, 850, s_, 30 * (0.85 + 0.15 * eback(p)), WHITE, a * eo(p), "black", track=0.06)


@scene("This is Moneycheck.", fx=[(None, 0.0, "whoosh", 0.4), ("This is Moneycheck.", 0.1, "impact", 0.4),
                                  ("This is Moneycheck.", 0.15, "sparkle", 0.4)])
def s06(f, t, a, lt):
    push(f, lt, 1.0, 1.06, 4.0)
    p = prog(lt, 0.05, 0.6)
    f.ring(W / 2, 470, prog(lt, 0.1, 1.2), GOLD_HI, 0.8 * a, rmax=620)
    rays(f, W / 2, 470, t, a * eo(p))
    f.text(W / 2, 470, "MONEYCHECK", 150 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black", track=0.06)
    q = ap(t, "Let's get into it", 0.6)
    kline(f, W / 2, 640, "MOST STOCKS LOSE MONEY.", 52, WHITE, t, T("Let's get into it"), a)
    kline(f, W / 2, 712, "SO WHY DOES THE MARKET GO UP?", 52, GOLD_HI, t, T("Let's get into it") + 0.2, a)


@scene("Chapter one.", chapter=(1, "THE STUDY"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s07(f, t, a, lt):
    chapter_card(f, t, a, lt, 1, "THE STUDY")


@scene("This data comes from Hendrik Bessembinder", src="BESSEMBINDER (2018), JOURNAL OF FINANCIAL ECONOMICS 129(3) · BESSEMBINDER (MARCH 2026), WORKING PAPER",
       fx=[(None, 0.0, "whoosh", 0.4), ("In 2018,", 0.0, "pop", 0.4), ("in March 2026,", 0.0, "pop", 0.4),
           ("a full century.", 0.0, "ding", 0.35)])
def s08(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 12.0)
    figure(f, 330, 760, 190, a, spot=0.8, ring=0.6)
    gy = 760 - 0.8 * 190
    f.circ(313, gy, 14, NAVY, a, w=4)
    f.circ(347, gy, 14, NAVY, a, w=4)
    f.line([(327, gy), (333, gy)], NAVY, a, 4)
    kline(f, 330, 840, "HENDRIK BESSEMBINDER", 34, WHITE, t, T("Hendrik Bessembinder"), a)
    kline(f, 330, 885, "FINANCE PROFESSOR", 22, MUTED, t, T("a finance professor"), a, w="xb", track=0.18)
    kline(f, 330, 918, "ARIZONA STATE UNIVERSITY", 22, MUTED, t, T("Arizona State University"), a, w="xb", track=0.18)
    p1 = ap(t, "In 2018,", 0.6)
    paper(f, 900, 520 + 30 * (1 - eo(p1)), 470, 520, a * eo(p1), ["DO STOCKS", "OUTPERFORM", "TREASURY BILLS?"], "2018 · JFE")
    p2 = ap(t, "in March 2026,", 0.6)
    paper(f, 1450, 520 + 30 * (1 - eo(p2)), 470, 520, a * eo(p2), ["ONE HUNDRED", "YEARS IN THE U.S.", "STOCK MARKETS"], "MARCH 2026")
    p3 = ap(t, "a full century.", 0.5)
    f.pill(1450, 830, "1926 → 2025 · 100 YEARS", 26 * (0.8 + 0.2 * eback(p3)), a * eo(p3), fill=GOLD, tc=NAVY, track=0.14)


@scene("He looked at every US common stock", src="BESSEMBINDER (2026): 29,754 COMMON STOCKS OF 29,081 FIRMS · CRSP, JAN 1926 – DEC 2025",
       fx=[(None, 0.0, "whoosh", 0.4), ("twenty-nine thousand,", 0.0, "riser", 0.35), ("stocks. From", 0.0, "ding", 0.4),
           ("giants like Apple,", 0.1, "sparkle", 0.35), ("no longer exist.", 0.0, "puff", 0.4)])
def s09(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 14.0)
    n, cols = 2975, 85
    x0, y0, sp = 960 - (cols - 1) * 8.5, 330, 17.0
    tc0, tc1 = T("twenty-nine thousand,"), TE("stocks. From") - 0.25
    fill = clamp((t - tc0) / max(0.5, tc1 - tc0))
    k = int(n * eio(fill))
    fade = eio(ap(t, "never heard of", 1.2))
    gi = set(int(v) for v in perm(n, 9)[:7])
    rr = 5.2
    for i in range(k):
        r, c = divmod(i, cols)
        x, y = x0 + c * sp, y0 + r * sp
        g = i in gi
        cc = GOLD_HI if g and ap(t, "giants like Apple,") > 0 else (180, 192, 220)
        aa = a * (1.0 if g else (1 - 0.75 * fade))
        f.circ(x, y, rr * (1.6 if g and ap(t, "giants like Apple,") > 0 else 1.0), cc, aa)
    label(f, W / 2, 160, "EVERY U.S. COMMON STOCK · 1926–2025", 24, a * eo(prog(lt, 0.0, 0.5)))
    v = 29754 * eio(fill)
    f.text(W / 2, 250, f"{v:,.0f}", 110, WHITE, a * eo(ap(t, "twenty-nine thousand,")), "black")
    pa = ap(t, "giants like Apple,", 0.5)
    if pa > 0:
        gx, gy = x0 + (min(gi) % cols) * sp, y0 + (min(gi) // cols) * sp
        f.pill(gx, gy - 40, "APPLE", 22, a * eo(pa), fill=GOLD, tc=NAVY, track=0.16)
    kline(f, W / 2, 960, "MOST NO LONGER EXIST", 40, MUTED, t, T("no longer exist."), a, w="black", track=0.08)


@scene("For each one, he asked a simple question.", fx=[(None, 0.0, "whoosh", 0.4), ("bought this stock", 0.0, "pop", 0.4),
                                                        ("reinvested every dividend,", 0.0, "coin", 0.4),
                                                        ("held on", 0.0, "tick", 0.4), ("delisted,", 0.0, "pop", 0.4),
                                                        ("how did you do?", 0.0, "ding", 0.4)])
def s10(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 14.0)
    kline(f, W / 2, 190, "ONE SIMPLE QUESTION FOR EVERY STOCK", 56, WHITE, t, T("he asked a simple question."), a)
    nodes = [("bought this stock", "BUY AT LISTING"), ("reinvested every dividend,", "REINVEST DIVIDENDS"),
             ("held on", "HOLD"), ("delisted,", "DELISTED OR END OF 2025"), ("how did you do?", "HOW DID YOU DO?")]
    xs = [300, 630, 960, 1290, 1620]
    y = 560
    ps = [ap(t, ph, 0.45) for ph, _ in nodes]
    for i in range(4):
        q = eio(prog(t, T(nodes[i][0]), max(0.3, T(nodes[i + 1][0]) - T(nodes[i][0]))))
        f.dash(xs[i] + 70, y, xs[i + 1] - 70, y, MUTED, 0.4 * a)
        f.line([(xs[i] + 70, y), (lerp(xs[i] + 70, xs[i + 1] - 70, q), y)], GOLD_HI, a * (q > 0), 4)
    for i, ((ph, s), x, p) in enumerate(zip(nodes, xs, ps)):
        f.circ(x, y, 62, DARKCARD, a * eo(p))
        f.circ(x, y, 62, GOLD_HI if i == 4 else WHITE, a * eo(p), w=4)
        if i == 0:
            f.text(x, y + 2, "$", 60, GREEN_HI, a * eo(p), "black")
        elif i == 1:
            f.coin(x, y, 30, a * eo(p), spin=t * 3)
        elif i == 2:
            f.stopwatch(x, y + 6, 32, a * eo(p), ang=t * 2)
        elif i == 3:
            f.flag(x - 20, y + 34, a * eo(p), t, h=70, fw=46)
        else:
            f.text(x, y + 4, "?", 72, GOLD_HI, a * eo(p), "black")
        f.text(x, y + 112, s, 22, WHITE if i < 4 else GOLD_HI, a * eo(p), "black", track=0.06)
    seg = sum(1 for p in ps if p > 0) - 1
    if seg >= 0:
        i = min(seg, 4)
        nx = xs[min(i + 1, 4)]
        q = eio(prog(t, T(nodes[i][0]), 0.6))
        px = lerp(xs[max(0, i - 1)], xs[i], q) if i > 0 else xs[0]
        f.pawn(px, y - 80, 70, WHITE, a, abs(math.sin(t * 9)) * 6 * (q < 1))


@scene("The benchmark is the most boring investment", src="BENCHMARK: 1-MONTH U.S. TREASURY BILLS (BESSEMBINDER 2018/2026)",
       fx=[(None, 0.0, "whoosh", 0.4), ("Treasury bill.", 0.0, "pop", 0.4), ("lending money", 0.2, "coin", 0.4)])
def s11(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    label(f, W / 2, 160, "THE BENCHMARK", 26, a * eo(prog(lt, 0, 0.4)))
    kline(f, W / 2, 255, "1-MONTH U.S. TREASURY BILL", 70, WHITE, t, T("one-month US Treasury bill."), a)
    bx, by = 1260, 640
    pb = eo(ap(t, "lending money", 0.6))
    f.poly([(bx - 230, by - 120), (bx, by - 220), (bx + 230, by - 120)], WHITE, a * pb)
    f.rect(bx - 220, by - 120, bx + 220, by - 100, WHITE, a * pb)
    for i in range(6):
        cx_ = bx - 180 + i * 72
        f.rect(cx_ - 14, by - 95, cx_ + 14, by + 100, WHITE, a * pb * 0.9, r=4)
    f.rect(bx - 240, by + 100, bx + 240, by + 124, WHITE, a * pb)
    f.text(bx, by - 148, "U.S. TREASURY", 22, NAVY, a * pb, "black", track=0.12)
    figure(f, 560, 760, 150, a * eo(prog(lt, 0.3, 0.5)), spot=0.6)
    q = prog(t, T("lending money") + 0.3, 1.4)
    if 0 < q < 1:
        f.coin(lerp(620, 1010, eio(q)), 640 - 120 * math.sin(math.pi * q), 26, a, spin=t * 8)
    q2 = prog(t, T("for a few weeks.") + 0.2, 1.4)
    if 0 < q2 < 1:
        f.coin(lerp(1010, 620, eio(q2)), 700 + 90 * math.sin(math.pi * q2), 30, a, spin=t * 8)
    kline(f, 830, 880, "+ A LITTLE INTEREST, ALMOST NO RISK", 30, GREEN_HI, t, T("for a few weeks.") + 0.6, a, w="black", track=0.06)


@scene("Here's what he found.", fx=[(None, 0.0, "whoosh", 0.4), (None, 0.2, "riser", 0.35)])
def s12(f, t, a, lt):
    push(f, lt, 1.0, 1.08, 2.5)
    for i in range(300):
        r, c = divmod(i, 30)
        f.circ(525 + c * 30, 360 + r * 36, 5, (150, 165, 200), a * 0.4)
    gx = 700 + 520 * eio(prog(lt, 0.0, 1.6))
    f.circ(gx, 520, 120, GOLD_HI, a, w=12)
    f.line([(gx + 85, 605), (gx + 180, 700)], GOLD_HI, a, 22)
    kline(f, W / 2, 860, "THE RESULTS", 96, WHITE, lt, 0.1, a, track=0.08)


@scene("The median stock,", src="BESSEMBINDER (2026): MEDIAN LIFETIME BUY-AND-HOLD RETURN −6.9% (MEAN +30,621%)",
       fx=[(None, 0.0, "whoosh", 0.4), ("right in the middle,", 0.0, "pop", 0.45), ("six point nine percent", 0.0, "sweep_down", 0.45)])
def s13(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 8.0)
    vals = [-100, -98, -94, -88, -80, -70, -58, -45, -33, -20, -6.9, 6, 20, 38, 65, 110, 190, 350, 700, 2000, 30000]
    zero = 700
    hl = ap(t, "right in the middle,", 0.5)
    grow = eio(prog(lt, 0.1, 1.4))
    for i, v in enumerate(vals):
        x = 400 + i * 56
        h = math.copysign(80 * math.log10(1 + abs(v) / 8), v) * grow
        c = RED if v < 0 else GREEN
        mid = i == 10
        aa = a * (0.6 if (not mid and hl > 0) else 1.0)
        if h < 0:
            f.rect(x - 20, zero, x + 20, zero - h, c, 0.85 * aa, r=6)
        else:
            f.rect(x - 20, zero - h, x + 20, zero, c, 0.85 * aa, r=6)
        if mid and hl > 0:
            f.rect(x - 28, zero - 8, x + 28, zero - h + 8, GOLD_HI, a * eo(hl), r=8, w=4)
            figure(f, x, zero - 14, 90, a * eo(hl), c=GOLD_HI, spot=0.7)
            f.pill(x, zero - 150, "MEDIAN", 22, a * eo(hl), fill=GOLD, tc=NAVY, track=0.18)
    f.line([(360, zero), (1560, zero)], MUTED, 0.7 * a, 3)
    f.text(400, zero + 130, "WORST", 22, MUTED, a, "xb", track=0.18)
    f.text(1520, zero + 130, "BEST", 22, MUTED, a, "xb", track=0.18)
    f.text(1590, zero, "0%", 24, MUTED, a, "xb", anchor="lm")
    kline(f, W / 2, 170, "21 STOCKS, SORTED BY LIFETIME RETURN", 40, MUTED, t, T("The median stock,"), a, w="black", track=0.06)
    p = ap(t, "six point nine percent", 0.5)
    f.text(W / 2, 320, "−6.9%", 170 * (0.85 + 0.15 * eback(p)), RED_HI, a * eo(p), "black")
    kline(f, W / 2, 430, "THE MEDIAN STOCK OVER ITS LIFETIME", 34, WHITE, t, T("six point nine percent") + 0.3, a, w="black", track=0.06)


@scene("Only forty-eight percent", src="BESSEMBINDER (2026): 48% POSITIVE · 41% BEAT 1-MONTH T-BILLS · FEWER THAN 28% BEAT THE MARKET INDEX",
       fx=[(None, 0.0, "whoosh", 0.4), ("Only forty-eight percent", 0.1, "pop", 0.45), ("Only forty-one percent", 0.1, "pop", 0.45),
           ("fifty-nine percent", 0.0, "alert", 0.3), ("fewer than twenty-eight percent", 0.1, "ding", 0.45)])
def s14(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 14.0)
    order = perm(100, 7)
    rank = np.empty(100, int)
    rank[order] = np.arange(100)
    p48 = eio(ap(t, "Only forty-eight percent", 1.0))
    p41 = eio(ap(t, "Only forty-one percent", 1.0))
    p28 = eio(ap(t, "fewer than twenty-eight percent", 1.0))

    def col(i):
        r = rank[i]
        if r < 48 * p48:
            if r < 28 and r < 28 * p28:
                return GOLD_HI
            if 41 <= r < 48 and (r - 41) < 7 * p41:
                return AMBER
            return GREEN
        return (185, 70, 70) if p48 > 0.5 else (205, 214, 232)

    pawn_grid(f, t, a, 100, 20, 620, 620, 52, 86, 44, col)
    x = 1500
    stage = 0 if p41 <= 0 else (1 if p28 <= 0 else 2)
    big = ["48%", "41%", "<28%"][stage]
    sm = ["MADE ANY MONEY AT ALL", "BEAT TREASURY BILLS", "BEAT THE MARKET"][stage]
    cc = [GREEN_HI, GREEN_HI, GOLD_HI][stage]
    t0 = [T("Only forty-eight percent"), T("Only forty-one percent"), T("fewer than twenty-eight percent")][stage]
    stat(f, t, x, 520, big, sm, cc, t0, a, size=170, ssize=26)
    pn = ap(t, "fifty-nine percent", 0.5) * (1 - prog(t, T("fewer than twenty-eight percent"), 0.3))
    f.pill(x, 760, "59% DID WORSE THAN T-BILLS", 24, a * eo(pn), fill=RED, tc=WHITE, track=0.1)
    kline(f, 620, 185, "100 STOCKS = THE WHOLE MARKET", 40, MUTED, t, T("Only forty-eight percent"), a, w="black", track=0.08)


@scene("So if most stocks lose,", fx=[(None, 0.0, "whoosh", 0.4), ("how did the market", 0.0, "riser", 0.3),
                                       ("fifteen thousand?", 0.0, "impact", 0.4)])
def s15(f, t, a, lt):
    push(f, lt, 1.0, 1.05, 6.0)
    pawn_grid(f, t, a * 0.85, 100, 10, 470, 560, 40, 52, 30,
              lambda i: RED if (i * 37) % 100 < 52 else (205, 214, 232))
    pts, _ = market_curve(1180, 1680, 760, 400)
    f.cline(pts, [GREEN] * len(pts), a, 5)
    f.text(1430, 830, "$1 → $15,041", 48, GREEN_HI, a, "black")
    f.text(470, 860, "MOST STOCKS LOSE", 34, RED_HI, a, "black", track=0.06)
    p = ap(t, "how did the market", 0.5)
    f.text(960, 560, "?", 220 * (0.8 + 0.2 * eback(p)) * (1 + 0.04 * math.sin(t * 5)), GOLD_HI, a * eo(p), "black")
    kline(f, W / 2, 190, "SO HOW DID THE MARKET WIN?", 70, WHITE, t, T("how did the market"), a)


# ================================================================== PART 2 · THE FEW
@scene("Chapter two.", chapter=(2, "THE FEW"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s16(f, t, a, lt):
    chapter_card(f, t, a, lt, 2, "THE FEW")


@scene("Bessembinder also measured how much wealth", src="SHAREHOLDER WEALTH CREATION = DOLLARS ABOVE WHAT 1-MONTH T-BILLS WOULD HAVE PAID (BESSEMBINDER)",
       fx=[(None, 0.0, "whoosh", 0.4), ("in dollars,", 0.0, "coin", 0.4), ("above what Treasury bills", 0.1, "pop", 0.4)])
def s17(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    kline(f, W / 2, 180, "WEALTH CREATED = DOLLARS ABOVE T-BILLS", 58, WHITE, t, T("Bessembinder also measured"), a)
    base = 880
    p1 = eio(ap(t, "how much wealth", 1.2))
    p2 = eio(ap(t, "above what Treasury bills", 1.0))
    for j in range(int(16 * p1)):
        f.coin(1180 + (j % 2) * 8, base - 22 - j * 30, 52, a, spin=0.0)
    for j in range(int(6 * p2)):
        f.coin(740 + (j % 2) * 8, base - 22 - j * 30, 52, a * 0.8, spin=0.0)
    f.text(1185, base + 60, "WHAT SHAREHOLDERS GOT", 24, WHITE, a * eo(prog(lt, 0.3, 0.5)), "black", track=0.1)
    f.text(745, base + 60, "WHAT T-BILLS WOULD PAY", 24, MUTED, a * eo(p2), "black", track=0.1)
    if p2 > 0.8:
        q = eo(prog(t, T("above what Treasury bills") + 0.9, 0.5))
        ytop, ymid = base - 22 - 15 * 30 - 30, base - 22 - 6 * 30
        f.line([(1290, ytop), (1320, ytop), (1320, ymid), (1290, ymid)], GOLD_HI, a * q, 5)
        f.pill(1490, (ytop + ymid) / 2, "WEALTH CREATED", 24, a * q, fill=GOLD, tc=NAVY, track=0.14)


@scene("Over the century, the US stock market created", src="BESSEMBINDER (2026): ≈ $91 TRILLION NET SHAREHOLDER WEALTH CREATION, 1926–2025",
       fx=[(None, 0.0, "whoosh", 0.4), ("ninety-one trillion dollars", 0.0, "cash", 0.55), ("ninety-one trillion dollars", 0.05, "impact", 0.35)])
def s18(f, t, a, lt):
    push(f, lt, 1.0, 1.05, 6.0)
    p = eio(ap(t, "ninety-one trillion dollars", 1.4, off=-0.6))
    f.halo(W / 2, 760, 520, GOLD, 0.3 * a * p, sy=0.4)
    for row in range(7):
        for c in range(9 - row):
            k = row * 9 + c
            if k / 50 < p:
                x = W / 2 + (c - (8 - row) / 2) * 120
                y = 900 - row * 46
                f.rect(x - 54, y - 20, x + 54, y + 20, GOLD, a, r=6)
                f.rect(x - 46, y - 14, x + 46, y - 6, GOLD_HI, a * 0.9, r=3)
    label(f, W / 2, 170, "NET WEALTH CREATED · 1926–2025", 24, a * eo(prog(lt, 0, 0.5)))
    v = 91 * p
    f.text(W / 2, 330, f"${v:,.0f} TRILLION", 140, GOLD_HI, a * eo(ap(t, "created about")), "black")
    f.burst(W / 2, 640, prog(t, TE("ninety-one trillion dollars"), 1.6), seed=8, n=24, spread=520, a=a)


@scene("And all of it came from just", src="BESSEMBINDER (2026): TOP 3.72% OF FIRMS (≈1,082) ACCOUNT FOR ALL $91 TRILLION",
       fx=[(None, 0.0, "whoosh", 0.4), ("three point seven percent", 0.0, "sparkle", 0.5), ("About one thousand", 0.0, "ding", 0.4)])
def s19(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 9.0)
    n, cols = 1000, 50
    gold = set(int(v) for v in perm(n, 19)[:37])
    pg = eo(ap(t, "three point seven percent", 0.8))
    for i in range(n):
        r, c = divmod(i, cols)
        x, y = 960 - 24.5 * 26 + c * 26, 360 + r * 26
        g = i in gold
        if g and pg > 0:
            f.halo(x, y, 26, GOLD, 0.5 * a * pg)
            f.circ(x, y, 8, GOLD_HI, a)
        else:
            f.circ(x, y, 6.5, (150, 165, 200), a * (0.75 - 0.4 * pg))
    kline(f, W / 2, 175, "ALL OF IT CAME FROM JUST", 52, WHITE, t, T("And all of it came from"), a)
    p = ap(t, "three point seven percent", 0.5)
    f.text(W / 2, 270, "3.7% OF COMPANIES", 96 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    f.pill(W / 2, 950, "≈ 1,082 FIRMS = 100% OF THE NET WEALTH", 26, a * eo(ap(t, "About one thousand")), fill=GOLD, tc=NAVY, track=0.12)


@scene("The other ninety-six percent,", src="BESSEMBINDER (2026): THE REMAINING ~96% OF FIRMS NETTED OUT TO ZERO VS T-BILLS",
       fx=[(None, 0.0, "whoosh", 0.4), ("netted out", 0.0, "tick", 0.4), ("cancelled each other out.", 0.0, "ding", 0.35)])
def s20(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 8.0)
    kline(f, W / 2, 180, "THE OTHER 96%: GAINS − LOSSES ≈ 0", 64, WHITE, t, T("The other ninety-six percent,"), a)
    cx, cy = W / 2, 520
    tilt = 0.22 * math.sin(lt * 2.2) * (1 - eio(ap(t, "cancelled each other out.", 1.2)))
    f.poly([(cx - 40, 900), (cx + 40, 900), (cx + 8, cy), (cx - 8, cy)], WHITE, a * 0.9)
    lx, ly = cx - 420 * math.cos(tilt), cy - 420 * math.sin(tilt)
    rx, ry = cx + 420 * math.cos(tilt), cy + 420 * math.sin(tilt)
    f.line([(lx, ly), (rx, ry)], WHITE, a, 10)
    f.circ(cx, cy, 18, GOLD_HI, a)
    for (px, py, c, s) in ((lx, ly, GREEN, "GAINS"), (rx, ry, RED, "LOSSES")):
        f.line([(px, py), (px - 120, py + 160)], MUTED, a, 3)
        f.line([(px, py), (px + 120, py + 160)], MUTED, a, 3)
        f.ell(px, py + 165, 150, 26, c, a * 0.9)
        for j in range(6):
            f.pawn(px - 100 + j * 40, py + 150, 46, qmix(WHITE, c, 0.6), a)
        f.text(px, py + 240, s, 34, c, a, "black", track=0.12)
    pz = ap(t, "netted out", 0.5)
    f.pill(cx, 960, "NET RESULT ≈ $0 ABOVE T-BILLS", 26, a * eo(pz), fill=None, outline=GOLD, tc=GOLD_HI, track=0.12)


@scene("At the very top,", src="BESSEMBINDER (2026): THE TOP 46 FIRMS ACCOUNT FOR HALF OF THE $91 TRILLION (89 FIRMS IN THE 2018 STUDY)",
       fx=[(None, 0.0, "whoosh", 0.4), ("Just forty-six companies", 0.0, "impact", 0.4), ("half of all that wealth.", 0.0, "cash", 0.45)])
def s21(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 7.0)
    kline(f, W / 2, 180, "JUST 46 COMPANIES CREATED HALF", 70, WHITE, t, T("Just forty-six companies"), a)
    x0, x1, y = 260, 1660, 600
    p = eio(ap(t, "half of all that wealth.", 1.0))
    f.rect(x0, y - 60, x1, y + 60, DARKCARD2, a, r=18)
    f.rect(x0, y - 60, lerp(x0, (x0 + x1) / 2, max(p, 0.002)), y + 60, GOLD, a, r=18)
    f.text((x0 + x1) / 2, y - 100, "$91 TRILLION", 40, GOLD_HI, a, "black")
    if p > 0.5:
        q = eo(prog(t, T("half of all that wealth.") + 0.5, 0.5))
        f.text(lerp(x0, (x0 + x1) / 2, 0.5), y, "46 COMPANIES", 44, NAVY, a * q, "black", track=0.06)
        f.text(lerp((x0 + x1) / 2, x1, 0.5), y, "EVERYONE ELSE", 40, WHITE, a * q, "black", track=0.06)
    pp = ap(t, "Just forty-six companies", 1.0)
    for i in range(46):
        q = clamp(pp * 46 - i)
        if q > 0:
            x = x0 + 30 + (i % 23) * 30
            yy = 790 + (i // 23) * 64
            f.pawn(x, yy, 46, GOLD_HI, a * eo(q))
    f.text(lerp(x0, (x0 + x1) / 2, 0.5), 950, "46 OF ≈ 29,000 FIRMS", 24, GOLD_HI, a * eo(pp), "black", track=0.12)


@scene("Apple alone:", src="BESSEMBINDER (2026), WEALTH CREATED VS T-BILLS 1926–2025: APPLE $5.02T · NVIDIA $4.58T · MICROSOFT $4.03T · TOP 5 = 21%",
       fx=[(None, 0.0, "whoosh", 0.4), ("Apple alone:", 0.0, "coin", 0.45), ("Nvidia:", 0.0, "coin", 0.45),
           ("Microsoft:", 0.0, "coin", 0.45), ("The top five companies", 0.1, "ding", 0.45)])
def s22(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 12.0)
    kline(f, W / 2, 160, "THE BIGGEST WEALTH CREATORS OF THE CENTURY", 50, WHITE, t, T("Apple alone:"), a)
    rows = [("Apple alone:", "APPLE", 5.02), ("Nvidia:", "NVIDIA", 4.58), ("Microsoft:", "MICROSOFT", 4.03)]
    for i, (ph, nm, v) in enumerate(rows):
        p = eio(ap(t, ph, 0.9))
        y = 330 + i * 120
        f.text(560, y, nm, 40, WHITE, a * eo(ap(t, ph, 0.3)), "black", anchor="rm", track=0.04)
        hbar(f, 600, y, 900 * v / 5.02 * p, 70, GOLD, a)
        if p > 0.2:
            f.text(600 + 900 * v / 5.02 * p + 24, y, f"${v * p:.2f}T", 40, GOLD_HI, a, "black", anchor="lm")
    pt = ap(t, "The top five companies", 0.6)
    if pt > 0:
        share = 0.21 * eio(prog(t, T("The top five companies") + 0.2, 1.2))
        donut(f, 960, 820, 120, 34, share, GOLD_HI, a * eo(pt))
        f.text(960, 820, f"{share * 100:.0f}%", 64, GOLD_HI, a * eo(pt), "black")
        f.text(1290, 790, "TOP 5 TOGETHER", 30, WHITE, a * eo(pt), "black", anchor="lm", track=0.06)
        f.text(1290, 840, "+ ALPHABET + AMAZON", 24, MUTED, a * eo(pt), "xb", anchor="lm", track=0.12)
        f.text(630, 820, "OF 100 YEARS OF", 26, WHITE, a * eo(pt), "black", anchor="rm", track=0.06)
        f.text(630, 860, "WEALTH CREATION", 26, WHITE, a * eo(pt), "black", anchor="rm", track=0.06)


@scene("Out of almost thirty thousand stocks,", fx=[(None, 0.0, "whoosh", 0.4), ("heavy lifting.", 0.0, "bass", 0.4)])
def s23(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 6.0)
    for i in range(60):
        x = 120 + (i % 30) * 58 + (i // 30) * 29
        y = 940 - (i // 30) * 50
        f.pawn(x, y, 50, (110, 125, 160), a * 0.45)
    lift = eio(ap(t, "did most of the heavy lifting.", 1.4))
    by = 640 - 90 * lift
    f.halo(W / 2, by, 500, GOLD, 0.3 * a, sy=0.3)
    f.rect(W / 2 - 460, by - 50, W / 2 + 460, by + 50, GOLD, a, r=14)
    f.rect(W / 2 - 440, by - 40, W / 2 + 440, by - 24, GOLD_HI, a * 0.9, r=6)
    f.text(W / 2, by + 6, "THE MARKET'S GAINS", 40, NAVY, a, "black", track=0.1)
    for i in range(8):
        x = W / 2 - 385 + i * 110
        f.pawn(x, by + 52 + 120, 120, GOLD_HI, a)
        f.line([(x, by + 52), (x, by + 52 + 18)], GOLD_HI, a, 6)
    kline(f, W / 2, 180, "A FEW DOZEN DID THE HEAVY LIFTING", 66, WHITE, t, T("a few dozen"), a)


# ================================================================== CHAPTER 3 · THE MATH
@scene("Chapter three.", chapter=(3, "THE MATH"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s24(f, t, a, lt):
    chapter_card(f, t, a, lt, 3, "THE MATH")


@scene("So why does this happen?", fx=[(None, 0.0, "whoosh", 0.4), ("It's not a conspiracy.", 0.0, "pop", 0.4),
                                        ("It's math.", 0.0, "impact", 0.4), ("a simple game.", 0.0, "coin", 0.45)])
def s25(f, t, a, lt):
    push(f, lt, 1.0, 1.05, 6.0)
    for i in range(16):
        sym = "%×÷+−="[i % 6]
        side = -1 if i % 2 else 1
        x = W / 2 + side * (620 + (i * 53) % 260)
        y = 170 + ((i * 211) % 760) - 40 * math.sin(t * 0.6 + i)
        f.text(x, y, sym, 56 + (i % 4) * 14, GOLD, a * 0.12, "black")
    kline(f, W / 2, 330, "IT'S NOT A CONSPIRACY.", 70, MUTED, t, T("It's not a conspiracy."), a)
    q = eio(ap(t, "It's math.", 0.4))
    if q > 0:
        w2 = f.twidth("IT'S NOT A CONSPIRACY.", 70, "black") / 2
        f.line([(W / 2 - w2 - 10, 335), (W / 2 - w2 - 10 + (2 * w2 + 20) * q, 335)], RED_HI, a, 7)
    p = ap(t, "It's math.", 0.5)
    f.text(W / 2, 520, "IT'S MATH.", 180 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    pc = ap(t, "a simple game.", 0.5)
    if pc > 0:
        coin_flip(f, W / 2, 800, 80 * eo(pc), t, a * eo(pc))


@scene("Imagine a stock that flips a coin every year.", src="MONEYCHECK THOUGHT EXPERIMENT · NOT A REAL STOCK",
       fx=[(None, 0.0, "whoosh", 0.4), ("flips a coin", 0.0, "coin", 0.5), ("Heads,", 0.0, "swoosh_up", 0.4),
           ("fifty percent.", 0.0, "ding", 0.4), ("Tails,", 0.0, "sweep_down", 0.4), ("forty percent.", 0.0, "pop", 0.4)])
def s26(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 9.0)
    kline(f, W / 2, 175, "ONE COIN FLIP PER YEAR", 60, WHITE, t, T("flips a coin"), a)
    spin = t < T("Heads,") + 0.2
    coin_flip(f, W / 2, 560, 130, t, a, spin=spin)
    figure(f, W / 2, 900, 110, a, spot=0.6)
    ph = ap(t, "Heads,", 0.5)
    f.text(470, 470, "HEADS", 44, WHITE, a * eo(ph), "black", track=0.14)
    f.text(470, 590, "+50%", 150 * (0.85 + 0.15 * eback(ap(t, "fifty percent.", 0.5))), GREEN_HI,
           a * eo(ap(t, "fifty percent.", 0.4)), "black")
    arrow(f, 470, 800, 470, 690, GREEN, a * eo(ap(t, "fifty percent.", 0.4)), 10, 34)
    pt = ap(t, "Tails,", 0.5)
    f.text(1450, 470, "TAILS", 44, WHITE, a * eo(pt), "black", track=0.14)
    f.text(1450, 590, "−40%", 150 * (0.85 + 0.15 * eback(ap(t, "forty percent.", 0.5))), RED_HI,
           a * eo(ap(t, "forty percent.", 0.4)), "black")
    arrow(f, 1450, 690, 1450, 800, RED, a * eo(ap(t, "forty percent.", 0.4)), 10, 34)


@scene("On average, that's a gain of five percent per year.", src="MONEYCHECK THOUGHT EXPERIMENT: (+50% − 40%) / 2 = +5% AVERAGE PER YEAR",
       fx=[(None, 0.0, "whoosh", 0.4), ("five percent per year.", 0.0, "ding", 0.45), ("Sounds like a decent stock.", 0.2, "pop", 0.35)])
def s27(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 6.0)
    kwords(f, W / 2, 420, [("(+50%", GREEN_HI), ("−40%)", RED_HI), ("÷ 2", WHITE)], 110, t, T("On average,"), a, step=0.16)
    p = ap(t, "five percent per year.", 0.5)
    f.text(W / 2, 600, "= +5% PER YEAR", 130 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    q = ap(t, "Sounds like a decent stock.", 0.6)
    f.circ(800, 820, 46, GREEN, a * eo(q), w=5)
    check(f, 800, 820, 50, GREEN_HI, a * eo(q), eio(q))
    f.text(860, 820, "SOUNDS LIKE A DECENT STOCK", 38, WHITE, a * eo(q), "black", anchor="lm", track=0.05)


# ---------------------------------------------------------------- the coin-flip market (one long scene)
_POP = np.array([bin(i).count("1") for i in range(1024)])
_J = np.zeros(1024, int)
_cnt = [0] * 11
for _i in range(1024):
    _J[_i] = _cnt[_POP[_i]]
    _cnt[_POP[_i]] += 1
_RET = {k: 1.5 ** k * 0.6 ** (10 - k) - 1 for k in range(11)}
_GOLDEN = math.pi * (3 - math.sqrt(5))


def _grid_xy(i):
    r, c = divmod(i, 64)
    return 960 - 31.5 * 22 + c * 22, 430 + r * 22


def _hist_xy(i):
    k, j = _POP[i], _J[i]
    return 960 + (k - 5) * 140 + ((j % 6) - 2.5) * 15, 880 - (j // 6) * 11.2


def _ball_xy(i):
    r = 165 * math.sqrt((i + 0.5) / 1024)
    g = i * _GOLDEN
    return 960 + r * math.cos(g), 560 + r * math.sin(g)


def _pct(v):
    s = f"{abs(v) * 100:,.0f}%"
    return ("+" if v >= 0 else "−") + s


@scene("Now let's build a whole market", src="MONEYCHECK CALCULATION: +50% OR −40% PER YEAR · 10 YEARS · ALL 1,024 HEADS/TAILS SEQUENCES ONCE",
       fx=[(None, 0.0, "whoosh", 0.4), ("One thousand and twenty-four", 0.0, "riser", 0.3), ("Over ten years,", 0.0, "flutter", 0.4),
           ("Just counting.", 0.0, "swoosh_up", 0.45), ("Two hundred and fifty-two", 0.0, "pop", 0.45),
           ("minus forty-one percent.", 0.0, "sweep_down", 0.45), ("Up fifty, down forty,", 0.0, "whoosh", 0.35),
           ("In total, six hundred", 0.0, "alert", 0.35), ("ten heads in a row", 0.0, "swoosh_up", 0.4),
           ("fifty-seven dollars", 0.0, "cash", 0.5), ("Add everything up,", 0.0, "whoosh", 0.4),
           ("sixty-three percent.", 0.0, "ding", 0.45), ("And here's the kicker.", 0.0, "impact", 0.4),
           ("produced all of its net gains.", 0.0, "sparkle", 0.45), ("Sound familiar?", 0.0, "pop", 0.4)])
def s28(f, t, a, lt):
    push(f, lt, 1.0, 1.015, 40.0)
    tA, tB, tC = T("Now let's build"), T("Over ten years,"), T("Just counting.")
    tD, tN, tM = T("The most common result"), T("Two hundred and fifty-two"), T("minus forty-one percent.")
    tE, tE2, tF = T("Up fifty, down forty,"), T("Because a forty percent loss"), T("In total, six hundred")
    tG, tG2, tG3 = T("But a few lucky ones"), T("ten heads in a row"), T("fifty-seven dollars")
    tH, tH2, tI = T("Add everything up,"), T("sixty-three percent."), T("And here's the kicker.")
    tI2, tI3 = T("produced all of its net gains."), T("Sound familiar?")
    appear = prog(t, tA, 1.4)
    card_on = eio(prog(t, tE, 0.5)) * (1 - eio(prog(t, tF - 0.2, 0.5)))
    dimk = 1 - 0.75 * card_on
    for i in range(1024):
        if appear * 1100 < i:
            continue
        k = _POP[i]
        st = (i % 37) / 37 * 0.6
        gx, gy = _grid_xy(i)
        hx, hy = _hist_xy(i)
        bx, by = _ball_xy(i)
        pc = eio(prog(t, tC + st, 1.2))
        pb = eio(prog(t, tH + st * 0.6, 1.0)) * (1 - eio(prog(t, tI + st * 0.6, 1.0)))
        x, y = lerp(lerp(gx, hx, pc), bx, pb), lerp(lerp(gy, hy, pc), by, pb)
        c = (205, 214, 232)
        if k <= 5 and t > tF + 0.12 * k:
            c = RED
        if k >= 6 and t > tG + 0.25 * (k - 6):
            c = GREEN_HI if k >= 7 else GREEN
        aa = a * dimk
        if t > tI:
            q = eio(prog(t, tI + 0.6, 0.6))
            if k >= 8:
                c = mixc(c, GOLD_HI, q)
            else:
                aa *= 1 - 0.7 * q
        r = 4.6
        if k == 10 and tG2 <= t:
            r = 4.6 + 9 * eo(prog(t, tG2, 0.5)) * (1 - pb)
            f.halo(x, y, 40, GREEN, 0.7 * aa)
        f.circ(x, y, r, c, aa)
    label(f, W / 2, 140, "A COIN-FLIP MARKET", 24, a * eo(prog(lt, 0, 0.5)) * (1 - eio(prog(t, tC, 0.5))))
    # phase A/B: counter + coin row
    pa = ap(t, "One thousand and twenty-four", 0.5) * (1 - eio(prog(t, tC, 0.5)))
    f.text(W / 2, 270, "1,024 STOCKS", 92 * (0.85 + 0.15 * eback(ap(t, "One thousand and twenty-four", 0.5))), WHITE,
           a * eo(pa), "black")
    pbq = ap(t, "Over ten years,", 0.4) * (1 - eio(prog(t, tC, 0.5)))
    if pbq > 0:
        for j in range(10):
            x = 960 + (j - 4.5) * 76
            f.coin(x, 840, 26, a * eo(pbq), spin=t * 6 + j)
        f.text(W / 2, 915, "10 YEARS · EVERY POSSIBLE HEADS/TAILS SEQUENCE EXACTLY ONCE", 26, GOLD_HI,
               a * eo(ap(t, "every possible sequence", 0.4)) * (1 - eio(prog(t, tC, 0.5))), "black", track=0.06)
    # axis (after the histogram forms)
    hx_on = eo(prog(t, tC + 0.8, 0.6)) * (1 - eio(prog(t, tH, 0.4)) + eio(prog(t, tI + 0.4, 0.5)))
    hx_on = clamp(hx_on) * dimk
    if hx_on > 0.01:
        f.text(960, 168, "RESULT AFTER 10 YEARS, BY NUMBER OF HEADS", 34, WHITE, a * hx_on, "black", track=0.06)
        for k in range(11):
            x = 960 + (k - 5) * 140
            f.text(x, 918, f"{k}", 28, WHITE, a * hx_on, "black")
            pr = prog(t, tF + 0.1 * k, 0.4) if k <= 5 else prog(t, tG + 0.25 * (k - 6), 0.4)
            if k == 5:
                pr = max(pr, prog(t, tM, 0.4))
            cc = RED_HI if _RET[k] < 0 else GREEN_HI
            f.text(x, 956, _pct(_RET[k]), 24, cc, a * hx_on * eo(pr), "black")
        f.text(960 - 5 * 140 - 95, 918, "HEADS", 20, MUTED, a * hx_on, "xb", anchor="rm", track=0.12)
        f.text(960 - 5 * 140 - 95, 956, "RESULT", 20, MUTED, a * hx_on, "xb", anchor="rm", track=0.12)
    # phase D: the most common result
    pd = eo(prog(t, tD, 0.5)) * (1 - eio(prog(t, tF, 0.5))) * dimk
    if pd > 0.01:
        f.rect(960 - 62, 880 - 43 * 11.2 - 16, 960 + 62, 896, GOLD_HI, a * pd, r=10, w=4)
        f.pill(960, 880 - 43 * 11.2 - 50, "5 HEADS · 5 TAILS", 22, a * pd, fill=GOLD, tc=NAVY, track=0.12)
        pn = ap(t, "Two hundred and fifty-two", 0.4)
        f.text(300, 470, "252 STOCKS", 50, WHITE, a * pd * eo(pn), "black", anchor="lm")
        pm = ap(t, "minus forty-one percent.", 0.4)
        f.text(300, 535, "END AT −41%", 50, RED_HI, a * pd * eo(pm), "black", anchor="lm")
        if pn > 0:
            arrow(f, 640, 500, 880, 500, GOLD_HI, a * pd * eo(pn), 5, 22)
    # phase E: why (modal card)
    if card_on > 0.01:
        card(f, 460, 300, 1460, 800, a * card_on, c=DARKCARD, edge=GOLD)
        steps = [("$1.00", WHITE), ("× 1.5", GREEN_HI), ("$1.50", WHITE), ("× 0.6", RED_HI), ("$0.90", RED_HI)]
        for j, (s, c) in enumerate(steps):
            pj = prog(t, tE + 0.35 * j, 0.4)
            f.text(600 + j * 180, 420, s, 54, c, a * card_on * eo(pj), "black")
        f.text(960, 500, "ONE UP + ONE DOWN = −10%", 34, WHITE, a * card_on * eo(prog(t, tE + 1.8, 0.4)), "black", track=0.06)
        f.text(960, 600, "0.9 × 0.9 × 0.9 × 0.9 × 0.9 = 0.59", 50, GOLD_HI, a * card_on * eo(prog(t, tE + 2.6, 0.5)), "black")
        kline(f, 960, 710, "A 40% LOSS HURTS MORE THAN A 50% GAIN HELPS", 34, WHITE, t, tE2, a * card_on, w="black")
    # phase F: losers
    pf = eo(prog(t, tF + 0.6, 0.5)) * (1 - eio(prog(t, tG, 0.5)))
    f.pill(960, 240, "638 OF 1,024 STOCKS (62%) END WITH A LOSS", 28, a * pf, fill=RED, tc=WHITE, track=0.08)
    # phase G: lucky ones + ten heads
    pg = eo(prog(t, tG2, 0.5)) * (1 - eio(prog(t, tH, 0.4)))
    if pg > 0.01:
        x10, y10 = _hist_xy(1023)
        arrow(f, x10, y10 - 30, x10, 330, GREEN_HI, a * pg, 6, 26)
        pv = prog(t, tG3, 0.5)
        f.text(x10 - 10, 280, "$1 → $57.67", 52 * (0.85 + 0.15 * eback(pv)), GREEN_HI, a * eo(pv), "black", anchor="rm")
        f.text(x10 - 10, 230, "10 HEADS IN A ROW", 24, WHITE, a * pg, "xb", anchor="rm", track=0.12)
    # phase H: the whole market
    ph = eo(prog(t, tH + 0.8, 0.5)) * (1 - eio(prog(t, tI, 0.4)))
    if ph > 0.01:
        f.halo(960, 560, 260, GREEN, 0.25 * a * ph)
        pv = prog(t, tH2, 0.5)
        f.text(960, 300, "THE WHOLE MARKET", 40, WHITE, a * ph, "black", track=0.12)
        f.text(960, 830, "+63%", 120 * (0.85 + 0.15 * eback(pv)), GREEN_HI, a * eo(pv), "black")
        f.text(960, 915, "= EXACTLY 5% A YEAR, COMPOUNDED", 30, WHITE, a * eo(prog(t, tH2 + 0.6, 0.4)) * ph, "black", track=0.06)
    # phase I: the kicker
    pi = eo(prog(t, tI + 0.6, 0.5))
    if pi > 0.01:
        f.halo(1520, 850, 260, GOLD, 0.3 * a * pi, sy=0.4)
        f.rect(1325, 880 - 8 * 11.2 - 24, 1715, 898, GOLD_HI, a * pi, r=12, w=4)
        f.text(1520, 880 - 8 * 11.2 - 50, "56 STOCKS", 30, GOLD_HI, a * pi, "black", track=0.08)
        f.pill(960, 240, "TOP 56 STOCKS = 5.5% OF THE MARKET", 28, a * pi, fill=GOLD, tc=NAVY, track=0.08)
        pk = ap(t, "produced all of its net gains.", 0.5)
        f.text(1330, 480, "→ 100% OF", 44, GOLD_HI, a * eo(pk), "black", anchor="lm")
        f.text(1330, 535, "THE NET GAINS", 44, GOLD_HI, a * eo(pk), "black", anchor="lm")
        ps = ap(t, "Sound familiar?", 0.5)
        f.pill(560, 360, "REAL MARKET: 3.7% OF FIRMS → ALL OF IT", 24, a * eo(ps), fill=None, outline=WHITE, tc=WHITE, track=0.08)


@scene("That's the core of Bessembinder's finding.", fx=[(None, 0.0, "whoosh", 0.4), ("lose one hundred percent.", 0.0, "bass", 0.4),
                                                         ("thousands of percent.", 0.0, "swoosh_up", 0.45), ("Losses are capped.", 0.0, "impact", 0.35),
                                                         ("Gains are not.", 0.0, "sparkle", 0.45)])
def s29(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    ax = 700
    f.line([(ax, 920), (ax, 120)], MUTED, a * 0.8, 4)
    arrow(f, ax, 200, ax, 110, MUTED, a * 0.8, 4, 22)
    ticks = [(-1.0, 900, "−100%"), (0.0, 760, "0%"), (1.0, 650, "+100%"), (9.0, 470, "+1,000%"), (99.0, 290, "+10,000%")]
    for v, y, s in ticks:
        f.line([(ax - 14, y), (ax + 14, y)], MUTED, a, 3)
        f.text(ax - 30, y, s, 26, RED_HI if v < 0 else (GREEN_HI if v > 0 else WHITE), a, "black", anchor="rm")
    pf = eo(ap(t, "lose one hundred percent.", 0.5))
    f.rect(ax - 330, 900, ax + 330, 930, RED, a * pf, r=6)
    f.text(ax - 160, 970, "THE FLOOR", 26, RED_HI, a * pf, "black", track=0.14)
    figure(f, ax + 140, 900, 90, a * pf, c=qmix(WHITE, RED, 0.8))
    pr = eio(ap(t, "thousands of percent.", 2.2))
    if pr > 0:
        y = lerp(760, 210, pr)
        for j in range(8):
            f.circ(ax + 70, y + 30 + j * 26, 7 - j * 0.7, GOLD_HI, a * (0.7 - j * 0.08))
        f.halo(ax + 70, y - 40, 100, GOLD, 0.6 * a)
        f.pawn(ax + 70, y, 90, GOLD_HI, a)
    kline(f, 1400, 430, "LOSSES ARE CAPPED.", 68, RED_HI, t, T("Losses are capped."), a)
    kline(f, 1400, 560, "GAINS ARE NOT.", 84, GREEN_HI, t, T("Gains are not."), a)
    kline(f, 1400, 250, "A STOCK CAN LOSE AT MOST 100%", 34, WHITE, t, T("A stock can only lose"), a, w="black", track=0.05)


def _lognorm(x, mu, s):
    return np.exp(-(np.log(x) - mu) ** 2 / (2 * s * s)) / (x * s * math.sqrt(2 * math.pi))


@scene("So a few giant winners pull the average up,", src="ILLUSTRATION: LOGNORMAL DISTRIBUTION OF STOCK OUTCOMES (NOT REAL DATA)",
       fx=[(None, 0.0, "whoosh", 0.4), ("pull the average up,", 0.0, "swoosh_up", 0.4), ("sits below it.", 0.0, "pop", 0.4),
           ("positive skewness.", 0.0, "ding", 0.45), ("the stronger it gets.", 0.0, "riser", 0.35)])
def s30(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    x0, x1, base, hmax = 260, 1660, 860, 430
    grow = eio(ap(t, "the longer you compound,", 2.4))
    s = 0.55 + 0.75 * grow
    mu = 0.15
    xs = np.linspace(0.02, 8.0, 260)
    ys = _lognorm(xs, mu, s)
    ys = ys / _lognorm(np.array([math.exp(mu - 0.55 ** 2)]), mu, 0.55)[0]
    X = lambda v: x0 + (v / 8.0) * (x1 - x0)
    pts = [(X(v), base - min(1.25, yv) * hmax) for v, yv in zip(xs, ys)]
    pd = eio(prog(lt, 0.0, 1.2))
    sub = L.partial(pts, max(0.002, pd))
    f.poly(sub + [(sub[-1][0], base), (sub[0][0], base)], (60, 90, 150), 0.35 * a)
    f.line(sub, WHITE, a, 5)
    f.line([(x0, base), (x1, base)], MUTED, a * 0.7, 3)
    med, mean = math.exp(mu), math.exp(mu + s * s / 2)
    pm = eo(ap(t, "sits below it.", 0.5))
    f.line([(X(med), base), (X(med), base - hmax - 40)], RED_HI, a * pm, 5)
    f.text(X(med), base - hmax - 70, "TYPICAL (MEDIAN)", 26, RED_HI, a * pm, "black", track=0.08)
    pa = eo(ap(t, "pull the average up,", 0.5))
    f.line([(X(mean), base), (X(mean), base - hmax + 40)], GOLD_HI, a * pa, 5)
    f.text(X(mean) + 16, base - hmax + 60, "AVERAGE (MEAN)", 26, GOLD_HI, a * pa, "black", anchor="lm", track=0.08)
    for j in range(5):
        v = 5.0 + j * 0.6
        f.halo(X(v), base - 30 - 10 * math.sin(t * 3 + j), 30, GOLD, 0.6 * a * pa)
        f.circ(X(v), base - 30 - 10 * math.sin(t * 3 + j), 9, GOLD_HI, a * pa)
    f.text(X(6.2), base - 90, "A FEW GIANT WINNERS", 24, GOLD_HI, a * pa, "black", track=0.1)
    ps = ap(t, "positive skewness.", 0.5)
    f.pill(W / 2, 150, "POSITIVE SKEWNESS", 34 * (0.8 + 0.2 * eback(ps)), a * eo(ps), fill=GOLD, tc=NAVY, track=0.2)
    pg = ap(t, "the longer you compound,", 0.4)
    yrs = "1 YEAR" if grow < 0.33 else ("10 YEARS" if grow < 0.8 else "30 YEARS")
    f.pill(1500, 260, f"COMPOUNDING: {yrs}", 24, a * eo(pg), fill=None, outline=WHITE, tc=WHITE, track=0.12)
    f.text(x0, base + 40, "LOST EVERYTHING", 20, MUTED, a, "xb", anchor="lm", track=0.12)
    f.text(x1, base + 40, "HUGE WINNERS", 20, MUTED, a, "xb", anchor="rm", track=0.12)


# ================================================================== CHAPTER 4 · THE GRAVEYARD
@scene("Chapter four.", chapter=(4, "THE GRAVEYARD"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s31(f, t, a, lt):
    chapter_card(f, t, a, lt, 4, "THE GRAVEYARD")


@scene("There's another reason this feels so surprising.", fx=[(None, 0.0, "whoosh", 0.4), ("We only remember the winners.", 0.0, "ding", 0.4)])
def s32(f, t, a, lt):
    push(f, lt, 1.0, 1.05, 6.0)
    dark = eio(ap(t, "We only remember the winners.", 1.4))
    for i in range(36):
        x = 140 + (i % 18) * 96 + (i // 18) * 48
        y = 960 - (i // 18) * 70
        f.pawn(x, y, 60, (120, 135, 170), a * (0.5 - 0.42 * dark))
    f.rect(760, 760, 1160, 800, WHITE, a * 0.9, r=6)
    f.rect(830, 700, 1090, 760, WHITE, a * 0.9, r=6)
    for i, (x, h) in enumerate(((860, 140), (960, 170), (1060, 140))):
        figure(f, x, 700 if i == 1 else 760, h, a, c=GOLD_HI, spot=0.8 * dark)
    kline(f, W / 2, 230, "WE ONLY REMEMBER THE WINNERS", 66, WHITE, t, T("We only remember the winners."), a)
    label(f, W / 2, 330, "SURVIVORSHIP BIAS", 24, a * eo(ap(t, "We only remember the winners.", 0.5, off=0.6)))


@scene("Everyone knows Apple, Microsoft and Amazon.", src="BESSEMBINDER (2026): THE AVERAGE STOCK WAS IN THE CRSP DATABASE FOR 11.7 YEARS",
       fx=[(None, 0.0, "whoosh", 0.4), ("Apple,", 0.0, "pop", 0.4), ("Microsoft", 0.0, "pop", 0.4), ("Amazon.", 0.0, "pop", 0.4),
           ("eleven point seven years.", 0.0, "tick", 0.4), ("get bought,", 0.0, "whoosh", 0.3), ("shrink,", 0.0, "whoosh", 0.3),
           ("simply disappear.", 0.0, "puff", 0.4)])
def s33(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 12.0)
    names = [("Apple,", "APPLE"), ("Microsoft", "MICROSOFT"), ("Amazon.", "AMAZON")]
    pk = eio(ap(t, "But the average stock", 0.8))
    for i, (ph, nm) in enumerate(names):
        p = ap(t, ph, 0.45)
        x = lerp(560 + i * 400, 300 + i * 150, pk)
        hh = lerp(150, 90, pk)
        figure(f, x, 560, hh, a * eo(p), c=GOLD_HI)
        f.pill(x, 560 - hh * 1.45, nm, lerp(28, 18, pk), a * eo(p), fill=GOLD, tc=NAVY, track=0.12)
    if pk > 0:
        p = prog(t, T("eleven point seven years.") - 0.3, 0.9)
        f.stopwatch(1250, 470, 120 * eo(pk), a * eo(pk), ang=t * 1.4)
        f.text(1250, 680, f"{11.7 * eio(p):.1f} YEARS", 84, WHITE, a * eo(min(1.0, p * 3)), "black")
        f.text(1250, 750, "AVERAGE TIME A STOCK WAS LISTED", 24, MUTED, a * eo(min(1.0, p * 3)), "xb", track=0.14)
    exits = [("get bought,", "BOUGHT", GREEN_HI), ("shrink,", "SHRANK", AMBER), ("simply disappear.", "DISAPPEARED", RED_HI)]
    for i, (ph, s, c) in enumerate(exits):
        p = ap(t, ph, 1.2)
        if p <= 0:
            continue
        x = 760 + i * 300 + 260 * eio(p)
        f.pawn(x, 960, 70, WHITE, a * (1 - eio(prog(t, T(ph) + 0.8, 0.5))))
        f.pill(760 + i * 300, 880, s, 22, a * eo(prog(t, T(ph), 0.3)), fill=None, outline=c, tc=c, track=0.14)


def tomb(f, x, base, w, h, a, name, year):
    if a <= 0.01:
        return
    f.rect(x - w / 2, base - h, x + w / 2, base - h * 0.4, (150, 160, 182), a, r=w / 2)
    f.rect(x - w / 2, base - h * 0.55, x + w / 2, base, (150, 160, 182), a, r=6)
    f.rect(x - w / 2 + 8, base - h + 10, x + w / 2 - 8, base - 8, (120, 130, 152), a * 0.25, r=w / 2 - 8)
    size = min(30.0, 30.0 * (w - 44) / f.twidth(name, 30, "black", 0.04))
    f.text(x, base - h * 0.52, name, size, NAVY, a, "black", track=0.04)
    f.text(x, base - h * 0.32, year, 26, (60, 70, 92), a, "black")
    f.line([(x - 24, base - h * 0.78), (x + 24, base - h * 0.78)], (60, 70, 92), a, 6)
    f.line([(x, base - h * 0.88), (x, base - h * 0.66)], (60, 70, 92), a, 6)


@scene("Some were household names.", src="BANKRUPTCY FILINGS: ENRON 2001 · WORLDCOM 2002 · LEHMAN BROTHERS 2008 · EASTMAN KODAK 2012 · SEARS HOLDINGS 2018",
       fx=[(None, 0.0, "whoosh", 0.4), ("Enron.", 0.0, "bass", 0.4), ("WorldCom.", 0.0, "bass", 0.4), ("Lehman Brothers.", 0.0, "bass", 0.4),
           ("Kodak.", 0.0, "bass", 0.4), ("Sears.", 0.0, "bass", 0.4), ("All of them went bankrupt.", 0.0, "impact", 0.4)])
def s34(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 10.0)
    f.halo(1500, 230, 160, (200, 210, 240), 0.35 * a)
    f.circ(1500, 230, 60, (220, 228, 245), a * 0.8)
    f.rect(100, 870, 1820, 1000, (16, 26, 46), a, r=0)
    f.line([(100, 870), (1820, 870)], (60, 76, 110), a, 3)
    stones = [("Enron.", "ENRON", "2001"), ("WorldCom.", "WORLDCOM", "2002"), ("Lehman Brothers.", "LEHMAN BROS.", "2008"),
              ("Kodak.", "KODAK", "2012"), ("Sears.", "SEARS", "2018")]
    for i, (ph, nm, yr) in enumerate(stones):
        p = eo(ap(t, ph, 0.6))
        x = 400 + i * 280
        tomb(f, x, 880 + 40 * (1 - p), 200, 300, a * p, nm, yr)
    kline(f, W / 2, 170, "ONCE HOUSEHOLD NAMES", 60, WHITE, t, T("Some were household names."), a)
    pb = ap(t, "All of them went bankrupt.", 0.5)
    f.pill(W / 2, 960, "ALL WENT BANKRUPT", 34 * (0.8 + 0.2 * eback(pb)), a * eo(pb), fill=RED, tc=WHITE, track=0.18)


@scene("And it's rarely obvious in advance.", src="J.P. MORGAN, 'THE AGONY & THE ECSTASY, PART IV' (OCT 2024): CATASTROPHIC DECLINE = −70% FROM PEAK, NO RECOVERY",
       fx=[(None, 0.0, "whoosh", 0.4), ("fell at least seventy percent", 0.0, "sweep_down", 0.5), ("didn't recover.", 0.0, "bass", 0.35),
           ("Fifty-four percent", 0.0, "pop", 0.45), ("strong buy.", 0.0, "impact", 0.45)])
def s35(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 12.0)
    rng = np.random.default_rng(35)
    up = [(260 + i * 28, 820 - 480 * (i / 22) ** 1.6 + float(rng.uniform(-14, 14))) for i in range(23)]
    peak = up[-1]
    down = [(peak[0] + i * 26, lerp(peak[1], 676, eio(i / 12)) + float(rng.uniform(-10, 10))) for i in range(1, 13)]
    flat = [(down[-1][0] + i * 30, 676 + 12 * math.sin(i * 1.3) + float(rng.uniform(-6, 6))) for i in range(1, 11)]
    p_up = eio(prog(lt, 0.0, 1.6))
    p_dn = eio(ap(t, "fell at least seventy percent", 1.0))
    p_fl = eio(ap(t, "didn't recover.", 1.0))
    pts = L.partial(up, max(0.002, p_up))
    if p_up >= 1:
        pts = up + L.partial(down, max(0.002, p_dn))[1:] if p_dn > 0 else up
        if p_dn >= 1 and p_fl > 0:
            pts += L.partial(flat, max(0.002, p_fl))[1:]
    cols = [GREEN if y1 <= y0 else RED for (x0, y0), (x1, y1) in zip(pts, pts[1:])] or [GREEN]
    f.cline(pts, cols, a, 6)
    f.line([(240, 880), (1200, 880)], MUTED, a * 0.6, 3)
    if p_dn > 0.9:
        q = eo(prog(t, T("fell at least seventy percent") + 1.0, 0.4))
        f.dash(peak[0] + 20, peak[1], 1180, peak[1], MUTED, a * q * 0.8)
        arrow(f, 1150, peak[1] + 10, 1150, 666, RED_HI, a * q, 5, 22)
        f.text(1175, (peak[1] + 676) / 2, "−70%", 54, RED_HI, a * q, "black", anchor="lm")
    if p_fl > 0.5:
        f.pill(1060, 760, "NO RECOVERY", 22, a * eo(p_fl), fill=None, outline=RED, tc=RED_HI, track=0.14)
    ps = ap(t, "strong buy.", 0.4)
    if ps > 0:
        sc = 1.6 - 0.6 * eo(ps)
        x, y = peak[0] - 10, peak[1] - 70
        f.rect(x - 150 * sc, y - 34 * sc, x + 150 * sc, y + 34 * sc, GREEN, a * eo(ps), r=10 * sc, w=5 * sc)
        f.text(x, y, "STRONG BUY", 40 * sc, GREEN_HI, a * eo(ps), "black", track=0.12)
    p54 = ap(t, "Fifty-four percent", 0.6)
    if p54 > 0:
        sh = 0.54 * eio(prog(t, T("Fifty-four percent"), 1.0))
        donut(f, 1560, 420, 130, 36, sh, GREEN_HI, a * eo(p54))
        f.text(1560, 420, f"{sh * 100:.0f}%", 70, WHITE, a * eo(p54), "black")
        f.text(1560, 600, "WERE PROFITABLE", 28, WHITE, a * eo(p54), "black", track=0.08)
        f.text(1560, 640, "AT THEIR PEAK", 28, WHITE, a * eo(p54), "black", track=0.08)
    kline(f, 720, 170, "STOCKS THAT FELL 70%+ AND NEVER CAME BACK", 44, WHITE, t, T("J.P. Morgan studied"), a)


@scene("Even the winners keep changing.", src="BESSEMBINDER (2026): 19 OF THE TOP 30 WEALTH CREATORS OF 2017–2025 WERE NOT IN THE TOP 30 THROUGH 2016",
       fx=[(None, 0.0, "whoosh", 0.4), ("nineteen weren't", 0.0, "flutter", 0.45), ("Names like Nvidia,", 0.0, "pop", 0.4),
           ("Tesla,", 0.0, "pop", 0.35), ("Meta,", 0.0, "pop", 0.35), ("Eli Lilly", 0.0, "pop", 0.35), ("AMD.", 0.0, "pop", 0.35)])
def s36(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    kline(f, W / 2, 165, "TOP 30 WEALTH CREATORS, 2017–2025", 52, WHITE, t, T("Of the thirty biggest"), a)
    new = set(int(v) for v in perm(30, 36)[:19])
    order = sorted(new)
    tf = T("nineteen weren't")
    for i in range(30):
        r, c = divmod(i, 6)
        x, y = 460 + c * 200, 320 + r * 108
        pa = eo(prog(lt, 0.2 + i * 0.02, 0.3))
        flip = 0.0
        if i in new:
            flip = prog(t, tf + order.index(i) * 0.07, 0.35)
        sx = abs(math.cos(math.pi * flip))
        isnew = flip > 0.5
        col = GOLD if isnew else DARKCARD2
        f.rect(x - 85 * sx, y - 42, x + 85 * sx, y + 42, col, a * pa, r=10)
        if sx > 0.3:
            f.text(x, y, "NEW" if isnew else "", 26, NAVY, a * pa, "black", track=0.18)
            if not isnew:
                f.rect(x - 50 * sx, y - 6, x + 50 * sx, y + 6, (60, 78, 112), a * pa, r=4)
    p19 = ap(t, "nineteen weren't", 0.5, off=1.4)
    f.text(1680, 480, "19", 140, GOLD_HI, a * eo(p19), "black")
    f.text(1680, 570, "OF 30 WERE NEW", 24, WHITE, a * eo(p19), "black", track=0.1)
    for i, (ph, s) in enumerate((("Names like Nvidia,", "NVIDIA"), ("Tesla,", "TESLA"), ("Meta,", "META"),
                                 ("Eli Lilly", "ELI LILLY"), ("AMD.", "AMD"))):
        p = ap(t, ph, 0.4)
        f.pill(560 + i * 200, 900, s, 24 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=GOLD, tc=NAVY, track=0.12)


# ================================================================== CHAPTER 5 · AROUND THE WORLD
@scene("Chapter five.", chapter=(5, "AROUND THE WORLD"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s37(f, t, a, lt):
    chapter_card(f, t, a, lt, 5, "AROUND THE WORLD")


_SPH = []
for _k in range(900):
    _y = 1 - 2 * (_k + 0.5) / 900
    _r = math.sqrt(1 - _y * _y)
    _g = _k * _GOLDEN
    _SPH.append((_r * math.cos(_g), _y, _r * math.sin(_g)))
_GOLD_SPH = set(int(v) for v in perm(900, 40)[:22])


def globe(f, cx, cy, R, t, a, gold=0.0):
    rot = t * 0.22
    cr, sr = math.cos(rot), math.sin(rot)
    f.halo(cx, cy, R * 1.25, (90, 120, 200), 0.25 * a)
    f.circ(cx, cy, R, (24, 40, 74), a * 0.9)
    f.circ(cx, cy, R, (90, 115, 170), a * 0.6, w=3)
    for k, (x, y, z) in enumerate(_SPH):
        xr, zr = x * cr + z * sr, -x * sr + z * cr
        if zr < 0:
            continue
        g = k in _GOLD_SPH and gold > 0
        c = GOLD_HI if g else (165, 182, 220)
        rr = (7 if g else 4.2) * (0.6 + 0.4 * zr)
        f.circ(cx + xr * R, cy - y * R, rr, c, a * (0.35 + 0.65 * zr) * (1 if g else 0.85))


@scene("Maybe this is just an American thing?", src="BESSEMBINDER, CHEN, CHOI & WEI (2023), FINANCIAL ANALYSTS JOURNAL 79(3): 64,000+ STOCKS, JAN 1990 – DEC 2020",
       fx=[(None, 0.0, "whoosh", 0.4), ("It's not.", 0.0, "pop", 0.4), ("sixty-four thousand stocks", 0.0, "riser", 0.3),
           ("found the same pattern.", 0.0, "ding", 0.4)])
def s38(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 12.0)
    globe(f, 620, 560, 330, t, a * eo(prog(lt, 0.0, 0.8)))
    kline(f, 1350, 330, "JUST AN AMERICAN THING?", 52, WHITE, t, T("Maybe this is just"), a)
    kline(f, 1350, 420, "NO.", 110, GOLD_HI, t, T("It's not."), a)
    p = ap(t, "sixty-four thousand stocks", 0.5)
    f.text(1350, 600, "64,000+ STOCKS", 72 * (0.85 + 0.15 * eback(p)), WHITE, a * eo(p), "black")
    kline(f, 1350, 680, "WORLDWIDE · 1990–2020", 30, MUTED, t, T("from 1990 to 2020,"), a, w="black", track=0.12)
    pp = ap(t, "found the same pattern.", 0.5)
    f.pill(1350, 790, "SAME PATTERN", 28, a * eo(pp), fill=GOLD, tc=NAVY, track=0.2)


@scene("Fifty-five percent of US stocks,", src="BESSEMBINDER ET AL. (2023): 55.2% OF U.S. AND 57.4% OF NON-U.S. STOCKS TRAILED 1-MONTH U.S. T-BILLS, 1990–2020",
       fx=[(None, 0.0, "whoosh", 0.4), ("Fifty-five percent", 0.0, "pop", 0.45), ("fifty-seven percent", 0.0, "pop", 0.45)])
def s39(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 8.0)
    kline(f, W / 2, 170, "DID WORSE THAN 1-MONTH U.S. T-BILLS", 54, WHITE, t, T("did worse than one-month"), a)
    for x, ph, v, s in ((640, "Fifty-five percent", 0.552, "U.S. STOCKS"), (1280, "fifty-seven percent", 0.574, "NON-U.S. STOCKS")):
        p = ap(t, ph, 0.6)
        sh = v * eio(prog(t, T(ph), 1.2))
        donut(f, x, 560, 210, 50, sh, RED, a * eo(p))
        f.text(x, 560, f"{sh * 100:.1f}%", 84, WHITE, a * eo(p), "black")
        f.text(x, 830, s, 34, WHITE, a * eo(p), "black", track=0.12)


@scene("And just two point four percent", src="BESSEMBINDER ET AL. (2023): TOP 2.4% OF FIRMS = ALL $75.7T NET GLOBAL WEALTH · OUTSIDE THE U.S.: 1.41% = $30.7T",
       fx=[(None, 0.0, "whoosh", 0.4), ("two point four percent", 0.0, "sparkle", 0.5), ("seventy-six trillion", 0.0, "cash", 0.5),
           ("one point four percent.", 0.0, "ding", 0.45)])
def s40(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 10.0)
    globe(f, 620, 560, 330, t, a, gold=1.0 if ap(t, "two point four percent") > 0 else 0.0)
    p = ap(t, "two point four percent", 0.5)
    f.text(1350, 330, "2.4% OF FIRMS", 84 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    q = ap(t, "seventy-six trillion", 0.5)
    v = 75.7 * eio(prog(t, T("seventy-six trillion") - 0.4, 1.0))
    f.text(1350, 470, f"= ALL ${v:.1f} TRILLION", 56, WHITE, a * eo(q), "black")
    kline(f, 1350, 545, "OF NET GLOBAL WEALTH", 30, MUTED, t, T("of net global wealth."), a, w="black", track=0.12)
    r = ap(t, "one point four percent.", 0.5)
    f.pill(1350, 700, "OUTSIDE THE U.S.: JUST 1.41%", 30 * (0.8 + 0.2 * eback(r)), a * eo(r), fill=GOLD, tc=NAVY, track=0.12)


# ================================================================== CHAPTER 6 · THE PROS
@scene("Chapter six.", chapter=(6, "THE PROS"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s41(f, t, a, lt):
    chapter_card(f, t, a, lt, 6, "THE PROS")


def tie_pawn(f, x, y, h, c, a, tie=GOLD, bob=0.0):
    f.pawn(x, y, h, c, a, bob)
    ty = y - bob - 0.5 * h
    f.poly([(x - 0.06 * h, ty), (x + 0.06 * h, ty), (x + 0.04 * h, ty + 0.26 * h), (x, ty + 0.32 * h),
            (x - 0.04 * h, ty + 0.26 * h)], tie, a)


@scene("So if a few winners drive everything,", fx=[(None, 0.0, "whoosh", 0.4), ("Just find the winners.", 0.0, "pop", 0.45),
                                                     ("research teams,", 0.0, "pop", 0.4), ("data,", 0.0, "blip", 0.45),
                                                     ("decades of experience.", 0.0, "ding", 0.4)])
def s42(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 12.0)
    kline(f, W / 2, 170, "JUST FIND THE WINNERS?", 76, WHITE, t, T("Just find the winners."), a)
    for i in range(240):
        r, c = divmod(i, 24)
        x, y = 920 + c * 34, 400 + r * 46
        g = i in (37, 151, 212)
        f.circ(x, y, 7 if g else 6, GOLD_HI if g else (160, 175, 210), a * (0.9 if g else 0.5))
    mx = 1100 + 380 * math.sin(lt * 0.7)
    my = 560 + 120 * math.sin(lt * 1.1)
    f.circ(mx, my, 80, WHITE, a, w=8)
    f.line([(mx - 58, my + 58), (mx - 130, my + 130)], WHITE, a, 14)
    tie_pawn(f, 450, 760, 170, WHITE, a)
    pt = ap(t, "research teams,", 0.6)
    for j in range(4):
        tie_pawn(f, 260 + j * 90 + (j > 1) * 280, 860, 90, (210, 220, 240), a * eo(clamp(pt * 4 - j)))
    pd = ap(t, "data,", 0.5)
    for j in range(2):
        x = 300 + j * 300
        card(f, x - 110, 330, x + 110, 470, a * eo(pd), edge=GOLD)
        f.line([(x - 80, 440), (x - 30, 400), (x + 10, 420), (x + 80, 360)], GREEN_HI, a * eo(pd), 5)
    pe = ap(t, "decades of experience.", 0.5)
    f.pill(450, 960, "DECADES OF EXPERIENCE", 24, a * eo(pe), fill=None, outline=GOLD, tc=GOLD_HI, track=0.14)


@scene("But according to S&P Dow Jones Indices,", src="S&P DOW JONES INDICES, SPIVA U.S. YEAR-END 2025: 92.9% OF ACTIVE LARGE-CAP FUNDS TRAILED THE S&P 500 OVER 20 YEARS; 78.8% IN 2025",
       fx=[(None, 0.0, "whoosh", 0.4), ("ninety-three percent", 0.0, "sweep_down", 0.5), ("seventy-nine percent.", 0.0, "pop", 0.45)])
def s43(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    order = perm(100, 43)
    rank = np.empty(100, int)
    rank[order] = np.arange(100)
    p = eio(ap(t, "ninety-three percent", 1.4))
    for i in range(100):
        x, y = grid_pos(i, 10, 560, 560, 70, 70, 100)
        lose = rank[i] < 93 * p
        tie_pawn(f, x, y + 26, 52, (150, 70, 70) if lose else WHITE, a * (0.75 if lose else 1.0), tie=RED if lose else GOLD)
    kline(f, 1400, 230, "OVER 20 YEARS", 40, MUTED, t, T("over the twenty years"), a, w="black", track=0.12)
    q = ap(t, "ninety-three percent", 0.6)
    f.text(1400, 400, f"{93 * eio(prog(t, T('ninety-three percent'), 1.2)):.0f}%", 190 * (0.85 + 0.15 * eback(q)), RED_HI, a * eo(q), "black")
    kline(f, 1400, 545, "OF ACTIVE U.S. LARGE-CAP FUNDS", 30, WHITE, t, T("actively managed"), a, w="black", track=0.06)
    kline(f, 1400, 590, "DID WORSE THAN THE S&P 500", 30, WHITE, t, T("did worse than the S&P 500."), a, w="black", track=0.06)
    r = ap(t, "In 2025 alone,", 0.5)
    f.pill(1400, 720, "2025 ALONE: 79%", 34 * (0.8 + 0.2 * eback(r)), a * eo(r), fill=RED, tc=WHITE, track=0.14)


def haystack(f, cx, base, w, h, a, t):
    pts = [(cx + w / 2 * math.cos(math.pi * k / 30), base - h * math.sin(math.pi * k / 30)) for k in range(31)]
    f.poly(pts, (176, 136, 44), a)
    rng = np.random.default_rng(44)
    for k in range(140):
        u, v = rng.uniform(-1, 1), rng.uniform(0, 1)
        if u * u + v * v > 0.95:
            continue
        x, y = cx + u * w / 2, base - v * h
        g = rng.uniform(-0.6, 0.6)
        f.line([(x, y), (x + 40 * math.cos(g), y - 40 * math.sin(g))], (232, 196, 96), a * 0.8, 3)


@scene("That doesn't mean nobody can do it.", fx=[(None, 0.0, "whoosh", 0.4), ("nobody can do it.", 0.0, "ding", 0.4),
                                                  ("finding the needles", 0.0, "sparkle", 0.45)])
def s44(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 8.0)
    ph = eio(ap(t, "finding the needles", 0.8))
    order = perm(100, 43)
    rank = np.empty(100, int)
    rank[order] = np.arange(100)
    for i in range(100):
        x, y = grid_pos(i, 10, 560, 560, 70, 70, 100)
        win = rank[i] >= 93
        if win:
            f.halo(x, y, 50, GOLD, 0.6 * a * eo(ap(t, "nobody can do it.", 0.5)))
        tie_pawn(f, x, y + 26, 52, GOLD_HI if win else (150, 70, 70), a * (1 - 0.8 * ph) * (1.0 if win else 0.6),
                 tie=GOLD if win else RED)
    f.pill(560, 960, "SOME DO", 26, a * eo(ap(t, "nobody can do it.", 0.5)) * (1 - ph), fill=GOLD, tc=NAVY, track=0.2)
    if ph > 0:
        haystack(f, 760, 900, 760 * eo(ph), 460 * eo(ph), a * ph, t)
        sx, sy = 880, 640
        f.line([(sx - 50, sy + 30), (sx + 50, sy - 30)], WHITE, a * ph, 4)
        f.sparkle(sx + 50, sy - 30, 40 * (0.7 + 0.3 * math.sin(t * 6)), WHITE, a * ph)
    kline(f, 1450, 430, "FINDING THE NEEDLES", 56, WHITE, t, T("finding the needles"), a)
    kline(f, 1450, 510, "IN ADVANCE IS HARD.", 56, GOLD_HI, t, T("in advance is extremely hard."), a)
    kline(f, 1450, 600, "EVEN FOR PROFESSIONALS.", 34, MUTED, t, T("Even for professionals."), a, w="black", track=0.08)


# ================================================================== CHAPTER 7 · WHAT IT MEANS
@scene("Chapter seven.", chapter=(7, "WHAT IT MEANS"), fx=[(None, 0.0, "whoosh", 0.45), (None, 0.15, "bass", 0.35)])
def s45(f, t, a, lt):
    chapter_card(f, t, a, lt, 7, "WHAT IT MEANS")


def badge(f, x, y, n, a, p=1.0):
    f.circ(x, y, 56 * eo(p), GOLD, a * eo(p))
    f.text(x, y + 2, str(n), 64, NAVY, a * eo(p), "black")


@scene("So what does all of this mean for you?", fx=[(None, 0.0, "whoosh", 0.4), ("doesn't give financial advice.", 0.0, "pop", 0.45),
                                                     ("three things.", 0.0, "ding", 0.45)])
def s46(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 8.0)
    kline(f, W / 2, 230, "WHAT DOES THIS MEAN FOR YOU?", 76, WHITE, t, T("So what does all"), a)
    p = ap(t, "doesn't give financial advice.", 0.5)
    f.pill(W / 2, 380, "NOT FINANCIAL ADVICE", 36 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=None, outline=GOLD, tc=GOLD_HI, track=0.22)
    q = ap(t, "three things.", 0.5)
    kline(f, W / 2, 560, "3 THINGS THE MATH SAYS", 56, WHITE, t, T("But the math does tell us"), a)
    for i in range(3):
        badge(f, 760 + i * 200, 720, i + 1, a, prog(t, T("three things.") + 0.15 * i, 0.4))


def mini_skew(f, cx, base, w, hmax, a, t, p=1.0):
    xs = np.linspace(0.02, 8.0, 160)
    ys = _lognorm(xs, 0.15, 1.0)
    ys = ys / ys.max()
    X = lambda v: cx - w / 2 + v / 8.0 * w
    pts = [(X(v), base - yv * hmax) for v, yv in zip(xs, ys)]
    sub = L.partial(pts, max(0.002, p))
    f.poly(sub + [(sub[-1][0], base), (sub[0][0], base)], (60, 90, 150), 0.35 * a)
    f.line(sub, WHITE, a, 5)
    f.line([(cx - w / 2, base), (cx + w / 2, base)], MUTED, a * 0.7, 3)
    med, mean = math.exp(0.15), math.exp(0.15 + 0.5)
    f.line([(X(med), base), (X(med), base - hmax - 30)], RED_HI, a * p, 5)
    f.text(X(med), base - hmax - 60, "LIKELY", 26, RED_HI, a * p, "black", track=0.1)
    f.line([(X(mean), base), (X(mean), base - hmax * 0.8)], GOLD_HI, a * p, 5)
    f.text(X(mean) + 14, base - hmax * 0.8 + 10, "AVERAGE", 26, GOLD_HI, a * p, "black", anchor="lm", track=0.1)


@scene("One. The average return is not your likely return.", fx=[(None, 0.0, "whoosh", 0.4), ("One.", 0.0, "pop", 0.45),
                                                                 ("below the average.", 0.0, "sweep_down", 0.35)])
def s47(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 8.0)
    badge(f, 300, 250, 1, a, ap(t, "One.", 0.4))
    kline(f, 420, 230, "THE AVERAGE RETURN", 60, WHITE, t, T("The average return"), a, anchor="lm")
    kline(f, 420, 300, "IS NOT YOUR LIKELY RETURN.", 60, GOLD_HI, t, T("is not your likely return."), a, anchor="lm")
    mini_skew(f, W / 2, 880, 1300, 400, a, t, eio(ap(t, "In a skewed world,", 1.4)))


@scene("Back to our coin-flip market.", src="MONEYCHECK SIMULATION: MEDIAN OF 200,000 RANDOM PORTFOLIOS FROM THE 1,024-STOCK COIN-FLIP MARKET · TOY MODEL: NO CRASHES, NO FEES",
       fx=[(None, 0.0, "whoosh", 0.4), ("just one random stock,", 0.0, "pop", 0.45), ("minus forty-one percent.", 0.0, "sweep_down", 0.4),
           ("With five random stocks,", 0.0, "pop", 0.45), ("With ten,", 0.0, "pop", 0.45), ("With a hundred,", 0.0, "pop", 0.45),
           ("And with all of them,", 0.0, "ding", 0.45)])
def s48(f, t, a, lt):
    push(f, lt, 1.0, 1.02, 14.0)
    kline(f, W / 2, 150, "TYPICAL RESULT AFTER 10 YEARS (MEDIAN)", 44, WHITE, t, T("Back to our coin-flip market."), a)
    zero, k = 640, 4.0
    f.line([(380, zero), (1560, zero)], MUTED, a * 0.8, 3)
    f.text(360, zero, "0%", 24, MUTED, a, "xb", anchor="rm")
    pm = ap(t, "And with all of them,", 0.6)
    f.dash(380, zero - 63 * k, 1560, zero - 63 * k, GOLD_HI, a * 0.7 * eo(prog(lt, 0.3, 0.5)))
    f.text(1580, zero - 63 * k, "MARKET +63%", 24, GOLD_HI, a * eo(prog(lt, 0.3, 0.5)), "black", anchor="lm")
    bars = [("just one random stock,", "1 STOCK", -41), ("With five random stocks,", "5 STOCKS", 19), ("With ten,", "10 STOCKS", 36),
            ("With a hundred,", "100 STOCKS", 59), ("And with all of them,", "ALL 1,024", 63)]
    for i, (ph, s, v) in enumerate(bars):
        p = eio(ap(t, ph, 0.8))
        x = 520 + i * 230
        c = RED if v < 0 else (GOLD if i == 4 else GREEN)
        hgt = abs(v) * k * p
        if v < 0:
            f.rect(x - 70, zero, x + 70, zero + hgt, c, 0.3 * a, r=10)
            f.rect(x - 70, zero, x + 70, zero + hgt, c, 0.95 * a, r=10, w=3)
            f.text(x, zero + hgt + 40, f"−{abs(v) * p:.0f}%", 44, RED_HI, a * (p > 0.05), "black")
            f.text(x, zero - 36, s, 24, WHITE, a * eo(ap(t, ph, 0.3)), "black", track=0.06)
        else:
            bar(f, x, zero, 140, max(1, hgt), c, a, top=f"+{v * p:.0f}%" if p > 0.05 else None,
                tc=GOLD_HI if i == 4 else GREEN_HI, tsize=44)
            f.text(x, zero + 36, s, 24, WHITE, a * eo(ap(t, ph, 0.3)), "black", track=0.06)
    f.text(W / 2, 960, "THE MORE STOCKS YOU OWN, THE CLOSER YOUR RESULT MOVES TO THE MARKET'S", 26, WHITE,
           a * eo(ap(t, "And with all of them,", 0.5, off=1.2)), "black", track=0.04)


@scene("The more you own,", src="JOHN C. BOGLE, 'THE LITTLE BOOK OF COMMON SENSE INVESTING' (WILEY, 2007)",
       fx=[(None, 0.0, "whoosh", 0.4), ("Don't look for the needle", 0.0, "pop", 0.4), ("Just buy the haystack.", 0.0, "ding", 0.45)])
def s49(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 10.0)
    pq = eo(ap(t, "That's what the late", 0.6))
    kline(f, W / 2, 300, "THE MORE YOU OWN,", 64, WHITE, t, T("The more you own,"), a * (1 - pq))
    kline(f, W / 2, 390, "THE CLOSER YOU GET TO THE MARKET.", 64, GOLD_HI, t, T("the closer your result"), a * (1 - pq))
    if pq > 0:
        haystack(f, 1610, 900, 400, 290, a * pq * 0.9, t)
        f.text(330, 330, "“", 260, GOLD, a * pq, "black")
        kline(f, 420, 420, "DON'T LOOK FOR THE NEEDLE", 60, WHITE, t, T("Don't look for the needle"), a, anchor="lm")
        kline(f, 420, 495, "IN THE HAYSTACK.", 60, WHITE, t, T("in the haystack."), a, anchor="lm")
        kline(f, 420, 600, "JUST BUY THE HAYSTACK.", 72, GOLD_HI, t, T("Just buy the haystack."), a, anchor="lm")
        kline(f, 420, 700, "— JOHN C. BOGLE, VANGUARD FOUNDER", 28, MUTED, t, T("John Bogle"), a, w="black", anchor="lm", track=0.08)


@scene("Two. Owning many stocks doesn't remove risk.", src="S&P 500 TOTAL RETURN 2008: −36.55% (DAMODARAN, NYU STERN, JAN 2026)",
       fx=[(None, 0.0, "whoosh", 0.4), ("Two.", 0.0, "pop", 0.45), ("In 2008,", 0.0, "sweep_down", 0.5),
           ("thirty-seven percent.", 0.0, "impact", 0.4), ("What diversification reduces", 0.0, "swoosh_up", 0.4)])
def s50(f, t, a, lt):
    push(f, lt, 1.0, 1.03, 12.0)
    badge(f, 300, 200, 2, a, ap(t, "Two.", 0.4))
    kline(f, 420, 180, "OWNING MANY STOCKS", 56, WHITE, t, T("Owning many stocks"), a, anchor="lm")
    kline(f, 420, 245, "DOESN'T REMOVE RISK.", 56, RED_HI, t, T("doesn't remove risk."), a, anchor="lm")
    pc = eio(ap(t, "In 2008,", 1.6))
    xs = [260 + i * 33 for i in range(30)]
    rng = np.random.default_rng(50)
    ys = []
    for i, x in enumerate(xs):
        if i < 10:
            v = 470 - 5 * i
        elif i < 22:
            v = 420 + (i - 10) * 30
        else:
            v = 780 - (i - 22) * 14
        ys.append(v + float(rng.uniform(-9, 9)))
    pts = list(zip(xs, ys))
    sub = L.partial(pts, max(0.002, pc))
    cols = [GREEN if y1 <= y0 else RED for (x0, y0), (x1, y1) in zip(sub, sub[1:])] or [GREEN]
    f.cline(sub, cols, a * (1 - 0.6 * eio(ap(t, "What diversification reduces", 0.6))), 6)
    p37 = ap(t, "thirty-seven percent.", 0.5)
    f.text(660, 860, "2008: S&P 500 −37%", 50 * (0.85 + 0.15 * eback(p37)), RED_HI, a * eo(p37), "black")
    pr = ap(t, "What diversification reduces", 0.6)
    if pr > 0:
        cx, cy = 1420, 650
        f.ell(cx, cy + 150, 300, 50, GOLD, a * eo(pr) * 0.9, w=6)
        f.line([(cx - 300, cy + 150), (cx - 240, cy - 120)], GOLD, a * eo(pr), 6)
        f.line([(cx + 300, cy + 150), (cx + 240, cy - 120)], GOLD, a * eo(pr), 6)
        for j in range(18):
            x = cx - 200 + (j % 6) * 80
            y = cy + 120 - (j // 6) * 80
            g = j in (4, 9, 15)
            f.pawn(x, y, 60, GOLD_HI if g else (205, 214, 232), a * eo(clamp(pr * 18 - j)))
        f.text(cx, cy - 190, "LESS RISK OF MISSING", 30, WHITE, a * eo(pr), "black", track=0.06)
        f.text(cx, cy - 150, "THE FEW BIG WINNERS", 30, GOLD_HI, a * eo(pr), "black", track=0.06)


@scene("Three. Patience and breadth.", src="DAMODARAN (NYU STERN), UPDATED JAN 5, 2026: $100 AT START OF 1928 → $1,157,599 (S&P 500 INCL. DIVIDENDS) VS $2,578 (3-MONTH T-BILLS), END OF 2025 · NOMINAL",
       fx=[(None, 0.0, "whoosh", 0.4), ("Three.", 0.0, "pop", 0.45), ("ten percent a year,", 0.0, "ding", 0.4),
           ("one point one six million dollars", 0.0, "cash", 0.55), ("two thousand six hundred.", 0.0, "pop", 0.4)])
def s51(f, t, a, lt):
    push(f, lt, 1.0, 1.02, 16.0)
    badge(f, 300, 170, 3, a, ap(t, "Three.", 0.4))
    kline(f, 420, 170, "PATIENCE AND BREADTH", 56, WHITE, t, T("Patience and breadth."), a, anchor="lm")
    x0, x1, yb, yt = 330, 1450, 900, 330
    vmax = 11576.0
    sp, spv = market_curve(x0, x1, yb, yt, key="sp500", vmax=vmax)
    tb, tbv = market_curve(x0, x1, yb, yt, key="tbill", vmax=vmax)
    for v, s in ((1, "$100"), (10, "$1K"), (100, "$10K"), (1000, "$100K"), (10000, "$1M")):
        y = lerp(yb, yt, math.log(v) / math.log(vmax))
        f.dash(x0, y, x1, y, MUTED, a * 0.25)
        f.text(x0 - 16, y, s, 22, MUTED, a, "xb", anchor="rm")
    f.text(x0, yb + 36, "1928", 24, MUTED, a, "xb")
    f.text(x1, yb + 36, "2025", 24, MUTED, a, "xb")
    t0 = T("One hundred dollars in the S&P 500")
    t1 = TE("by the end of 2025.")
    p = eio(prog(t, t0, max(0.5, t1 - t0)))
    s1 = L.partial(sp, max(0.002, p))
    s2 = L.partial(tb, max(0.002, p))
    f.line(s2, MUTED, a, 5)
    f.cline(s1, [GREEN] * len(s1), a, 6)
    hx, hy = s1[-1]
    f.halo(hx, hy, 60, GREEN, 0.7 * a)
    pr = ap(t, "ten percent a year,", 0.5)
    f.pill(980, 300, "STOCKS ≈ 10% / YEAR", 26, a * eo(pr), fill=GREEN, tc=NAVY, track=0.1)
    pt = ap(t, "about three percent", 0.5)
    f.pill(1150, 830, "T-BILLS ≈ 3% / YEAR", 26, a * eo(pt), fill=None, outline=MUTED, tc=WHITE, track=0.1)
    pm = ap(t, "one point one six million dollars", 0.5)
    f.text(1490, 330, "$1.16 MILLION", 54 * (0.85 + 0.15 * eback(pm)), GREEN_HI, a * eo(pm), "black", anchor="lm")
    pw = ap(t, "two thousand six hundred.", 0.5)
    f.text(1490, tb[-1][1], "$2,578", 46, WHITE, a * eo(pw), "black", anchor="lm")
    pd = ap(t, "With dividends reinvested,", 0.4)
    f.text(1490, 400, "DIVIDENDS REINVESTED", 20, MUTED, a * eo(pd), "xb", anchor="lm", track=0.12)
    f.text(1490, 430, "BEFORE TAXES & FEES", 20, MUTED, a * eo(pd), "xb", anchor="lm", track=0.12)


@scene("But that return didn't come from most stocks.", fx=[(None, 0.0, "whoosh", 0.4), ("It came from a few.", 0.0, "sparkle", 0.45),
                                                            ("nobody knows in advance", 0.0, "pop", 0.4)])
def s52(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 8.0)
    gold = {12, 47, 73, 88}
    pf = ap(t, "It came from a few.", 0.6)
    pq = ap(t, "nobody knows in advance", 0.6)
    for i in range(100):
        x, y = grid_pos(i, 20, W / 2, 640, 80, 96, 100)
        g = i in gold
        c = GOLD_HI if (g and pf > 0 and pq <= 0) else (205, 214, 232)
        aa = a * (1.0 if g or pf <= 0 else 0.45) if pq <= 0 else a * 0.8
        if g and pf > 0 and pq <= 0:
            f.halo(x, y + 6, 60, GOLD, 0.6 * a * eo(pf))
        f.pawn(x, y + 30, 56, c, aa)
        if pq > 0:
            f.text(x, y - 46 - 4 * math.sin(t * 4 + i), "?", 30, GOLD_HI, a * eo(clamp(pq * 3 - (i % 20) / 20)), "black")
    kline(f, W / 2, 200, "NOT FROM MOST STOCKS. FROM A FEW.", 62, WHITE, t, T("But that return"), a * (1 - eo(pq)))
    kline(f, W / 2, 200, "AND NOBODY KNOWS WHICH ONES IN ADVANCE.", 56, GOLD_HI, t, T("nobody knows in advance"), a)


@scene("So here's the paradox, solved.", fx=[(None, 0.0, "whoosh", 0.4), ("Most stocks lose.", 0.0, "sweep_down", 0.4),
                                             ("A few win so big", 0.0, "swoosh_up", 0.4), ("The average is real.", 0.0, "pop", 0.4),
                                             ("tiny minority.", 0.0, "ding", 0.5)])
def s53(f, t, a, lt):
    push(f, lt, 1.0, 1.04, 10.0)
    label(f, W / 2, 180, "THE PARADOX, SOLVED", 28, a * eo(prog(lt, 0, 0.5)))
    kline(f, W / 2, 330, "MOST STOCKS LOSE.", 90, RED_HI, t, T("Most stocks lose."), a)
    kline(f, W / 2, 470, "A FEW WIN SO BIG THEY CARRY THE MARKET.", 62, GREEN_HI, t, T("A few win so big"), a)
    kline(f, W / 2, 610, "THE AVERAGE IS REAL.", 70, WHITE, t, T("The average is real."), a)
    kline(f, W / 2, 720, "BUT IT'S EARNED BY A TINY MINORITY.", 62, GOLD_HI, t, T("But it's earned"), a)


@scene("That won't tell you which stock to buy.", fx=[(None, 0.0, "whoosh", 0.4), ("subscribe", 0.0, "pop", 0.5),
                                                      ("This was Moneycheck.", 0.0, "impact", 0.35),
                                                      ("This was Moneycheck.", 0.1, "sparkle", 0.4)])
def s54(f, t, a, lt):
    tm = T("This was Moneycheck.")
    end = eio(prog(t, tm - 0.2, 0.8))
    push(f, lt, 1.0, 1.05, 12.0)
    a1 = a * (1 - end)
    if a1 > 0.01:
        for i in range(160):
            x = 120 + (i * 97) % 1680
            y = 120 + (i * 53) % 560
            f.circ(x, y, 2.5 + (i % 3), (200, 210, 240), a1 * (0.25 + 0.25 * math.sin(t * 2 + i)))
        for i in (17, 61, 103, 140):
            x = 120 + (i * 97) % 1680
            y = 120 + (i * 53) % 560
            f.sparkle(x, y, 22, GOLD_HI, a1 * 0.9)
        figure(f, W / 2, 940, 130, a1, spot=0.5)
        kline(f, W / 2, 760, "IT MIGHT CHANGE HOW YOU SEE EVERY STOCK YOU OWN.", 46, WHITE, t, T("But it might change"), a1)
        ps = ap(t, "subscribe", 0.5)
        f.pill(W / 2, 850, "SUBSCRIBE FOR MORE", 30 * (0.8 + 0.2 * eback(ps)), a1 * eo(ps), fill=GOLD, tc=NAVY, track=0.2)
    if end > 0:
        f.cam()
        rays(f, W / 2, 330, t, a * end)
        f.ring(W / 2, 330, prog(t, tm, 1.4), GOLD_HI, 0.7 * a, rmax=560)
        f.text(W / 2, 330, "MONEYCHECK", 120 * (0.9 + 0.1 * eback(prog(t, tm, 0.7))), GOLD_HI, a * end, "black", track=0.06)
        kline(f, W / 2, 450, "THANKS FOR WATCHING", 34, WHITE, t, tm + 0.5, a, w="black", track=0.2)
        kline(f, W / 2, 1000, "NOT FINANCIAL ADVICE · FOR EDUCATIONAL PURPOSES ONLY · SOURCES IN THE DESCRIPTION", 20, MUTED,
              t, tm + 0.8, a, w="xb", track=0.1)


# ================================================================== assembly
def build():
    out = []
    for i, s in enumerate(SC):
        t0 = 0.0 if i == 0 else max(0.0, T(s["phrase"], s["n"]) - s["lead"])
        out.append([t0, None, s])
    for i in range(len(out)):
        out[i][1] = out[i + 1][0] + L.FADE if i + 1 < len(out) else DUR
    return [(t0, t1, s) for t0, t1, s in out]


TIMELINE = build()
SCENES = [(t0, t1, s["fn"]) for t0, t1, s in TIMELINE]
CHAPTERS = []
for _t0, _t1, _s in TIMELINE:
    if _s["chapter"]:
        CHAPTERS.append((_t0, _s["chapter"]))


def overlay(f, t):
    cur = None
    for t0, t1, s in TIMELINE:
        if t0 <= t:
            cur = (t0, t1, s)
    chap = None
    for t0, c in CHAPTERS:
        if t0 <= t:
            chap = (t0, c)
    end_t = T("This was Moneycheck.")
    if chap and t < end_t:
        t0c, (num, title) = chap
        on_card = cur and cur[2]["chapter"]
        a = eo(prog(t, cur[0] + 0.6, 0.5)) if on_card else 1.0
        if on_card and t > cur[1] - L.FADE:
            a = eo(prog(t, cur[1] - L.FADE, L.FADE))
        f.pill(70 + f.twidth(f"{num:02d} · {title}", 18, "xb", 0.22) / 2 + 22, 54, f"{num:02d} · {title}", 18, a * 0.9,
               fill=None, outline=GOLD, tc=GOLD_HI, track=0.22)
    # source line (per scene, fades with the scene) or disclaimer
    srcs = []
    for t0, t1, s in TIMELINE:
        if s["src"] and t0 - 0.01 <= t <= t1:
            aa = eio(prog(t, t0, L.FADE)) * (1 - eio(prog(t, t1 - L.FADE, L.FADE)))
            srcs.append((s["src"], aa))
    for s, aa in srcs:
        f.text(60, 1046, "SOURCE: " + s, 14, MUTED, 0.85 * aa, "sb", anchor="ls", track=0.06)
    if not srcs and t < end_t:
        f.text(60, 1046, "NOT FINANCIAL ADVICE · EDUCATIONAL ONLY", 14, MUTED, 0.7, "sb", anchor="ls", track=0.08)


def events():
    ev = []
    for t0, t1, s in TIMELINE:
        for ph, off, name, g in s["fx"]:
            tt = (t0 + s["lead"] if ph is None else T(ph)) + off
            ev.append((max(0.0, tt), name, g))
    return sorted(ev)


def chapters_for_description():
    rows = [(0.0, "Intro: most stocks lose, the market still wins")]
    names = {1: "The study: 100 years, 29,754 stocks", 2: "The few: 3.7% created all the wealth",
             3: "The math: the coin-flip market", 4: "The graveyard: survivorship bias",
             5: "Around the world: 64,000 stocks", 6: "The pros: 93% trail the S&P 500", 7: "What it means for you"}
    for t0, (num, _) in CHAPTERS:
        rows.append((t0 + 0.25, names[num]))
    return rows

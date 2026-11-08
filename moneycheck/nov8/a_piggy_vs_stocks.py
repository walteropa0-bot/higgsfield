"""Nov 8 · Video A (no voice, 25 s): $5 a day for 20 years – piggy bank vs. stock market.

Saver drops $5 a day into a piggy bank (0%). Investor puts the same $5 a day into the S&P 500 at his PC
(total return, dividends reinvested). Numbers from a_calc.py (Damodaran annual returns 2006-2025, smoothed monthly):
piggy $36,500 vs. stocks $161,198 (4.4x). In 2008-2009 the piggy bank is ahead for 24 months.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import eng14 as E  # noqa: E402
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, partial, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI,  # noqa: E402
                   NAVY, RED, RED_HI, DARKCARD, kline, kwords, footnote, follow, figure, rays, rain, money)
from PIL import Image  # noqa: E402

DUR = 25.0
NF = int(DUR * FPS)
NAME = "piggy_vs_stocks"
PINK = (240, 152, 180)
PINK_D = (196, 108, 140)
PINK_HI = (255, 206, 222)

SER = json.load(open(os.path.join(HERE, "a_series.json")))
TS = [0.0] + [p["t"] - 2006 for p in SER]
PIG = [0.0] + [p["piggy"] for p in SER]
STK = [0.0] + [p["stocks"] for p in SER]
FINAL_P, FINAL_S = PIG[-1], STK[-1]
COVER = False


def val(series, yrs):
    """value after yrs years (0..20), linear between month ends"""
    yrs = max(0.0, min(20.0, yrs))
    i = min(len(TS) - 2, int(yrs * 12))
    u = (yrs - TS[i]) / (TS[i + 1] - TS[i])
    return series[i] + (series[i + 1] - series[i]) * max(0.0, min(1.0, u))


# ------------------------------------------------------------------ props
def piggy(f, x, y, s, a, c=PINK, wob=0.0):
    if a <= 0.01:
        return
    y = y + wob
    for dx in (-62, -26, 30, 64):
        f.rect(x + (dx - 13) * s, y + 50 * s, x + (dx + 13) * s, y + 98 * s, PINK_D, a, r=8 * s)
    f.arc(x - 128 * s, y - 6 * s, 22 * s, 120, 400, PINK_D, a, w=6 * s)
    f.ell(x, y, 122 * s, 86 * s, c, a)
    f.ell(x - 20 * s, y - 34 * s, 70 * s, 30 * s, PINK_HI, a * 0.35)
    f.poly([(x + 52 * s, y - 70 * s), (x + 92 * s, y - 112 * s), (x + 98 * s, y - 56 * s)], PINK_D, a)
    f.ell(x + 120 * s, y + 6 * s, 26 * s, 32 * s, PINK_D, a)
    f.circ(x + 114 * s, y, 5 * s, (120, 60, 80), a)
    f.circ(x + 126 * s, y + 12 * s, 5 * s, (120, 60, 80), a)
    f.circ(x + 72 * s, y - 24 * s, 8 * s, NAVY, a)
    f.rect(x - 34 * s, y - 92 * s, x + 26 * s, y - 80 * s, (110, 50, 72), a, r=5 * s)


def pc_desk(f, x, y, s, a, t, chart=None, red=0.0):
    """desk with monitor; chart = list of (u, v) points in 0..1 drawn on the screen"""
    if a <= 0.01:
        return
    mx, my = x + 40 * s, y - 165 * s
    f.rect(mx - 140 * s, my - 92 * s, mx + 140 * s, my + 92 * s, DARKCARD, a, r=12 * s)
    f.rect(mx - 140 * s, my - 92 * s, mx + 140 * s, my + 92 * s, WHITE, a, r=12 * s, w=4 * s)
    sx0, sy0, sx1, sy1 = mx - 124 * s, my - 76 * s, mx + 124 * s, my + 76 * s
    f.rect(sx0, sy0, sx1, sy1, mixc((14, 28, 54), (60, 14, 20), red), a, r=6 * s)
    if chart:
        pts = [(lerp(sx0 + 10 * s, sx1 - 10 * s, u), lerp(sy1 - 10 * s, sy0 + 12 * s, v)) for u, v in chart]
        cols = [GREEN if y1 <= y0 else RED for (x0, y0), (x1, y1) in zip(pts, pts[1:])] or [GREEN]
        f.cline(pts, cols, a, 4 * s)
        f.circ(pts[-1][0], pts[-1][1], 6 * s, GREEN_HI if red < 0.5 else RED_HI, a)
    f.rect(mx - 12 * s, my + 92 * s, mx + 12 * s, my + 130 * s, (150, 162, 188), a)
    f.rect(mx - 62 * s, my + 128 * s, mx + 62 * s, my + 138 * s, (150, 162, 188), a, r=4 * s)
    f.rect(x - 250 * s, y - 28 * s, x + 250 * s, y - 8 * s, (176, 188, 212), a, r=6 * s)
    f.rect(x - 228 * s, y - 8 * s, x - 206 * s, y + 110 * s, (120, 132, 160), a)
    f.rect(x + 206 * s, y - 8 * s, x + 228 * s, y + 110 * s, (120, 132, 160), a)
    f.rect(x - 70 * s, y - 42 * s, x + 110 * s, y - 30 * s, (70, 84, 112), a, r=4 * s)


def mini_monitor(f, x, y, s, a, red=0.0):
    f.rect(x - 34 * s, y - 24 * s, x + 34 * s, y + 20 * s, mixc((14, 28, 54), (60, 14, 20), red), a, r=5 * s)
    f.rect(x - 34 * s, y - 24 * s, x + 34 * s, y + 20 * s, WHITE, a, r=5 * s, w=3 * s)
    f.line([(x - 24 * s, y + 10 * s), (x - 6 * s, y - 2 * s), (x + 6 * s, y + 4 * s), (x + 24 * s, y - 14 * s)],
           RED if red > 0.5 else GREEN_HI, a, 3 * s)
    f.rect(x - 4 * s, y + 20 * s, x + 4 * s, y + 30 * s, WHITE, a)


def counter_box(f, x, y, label, v, c, a, icon, winning=None):
    f.rect(x - 200, y - 70, x + 200, y + 70, DARKCARD, 0.92 * a, r=20)
    f.rect(x - 200, y - 70, x + 200, y + 70, c, a, r=20, w=4)
    icon(x - 140, y - 28)
    f.text(x - 98, y - 30, label, 26, c, a, "black", anchor="lm", track=0.12)
    f.text(x, y + 28, money(v), 58, WHITE, a, "black")
    if winning:
        f.pill(x, y + 98, winning[0], 20, a * winning[1], fill=c, tc=NAVY, track=0.14)


def coin_drop(f, x, y_slot, lt, a, period=0.55, n=None):
    k = int(lt / period)
    u = (lt % period) / period
    if n is not None and k >= n:
        return
    yy = lerp(y_slot - 170, y_slot - 10, eio(min(1.0, u * 1.25)))
    if u < 0.82:
        f.coin(x, yy, 26, a, spin=u * 9)


# ------------------------------------------------------------------ beats
def b0(f, t, a, lt):
    """hook: premise in the first frame"""
    f.cam(540, 900, 1.0 + 0.025 * eio(lt / 3.2))
    p = prog(lt, -1, 0.01)
    f.text(540, 360, "$5 A DAY", 150, GOLD_HI, a, "black")
    f.text(540, 470, "FOR 20 YEARS", 56, WHITE, a, "black", track=0.06)
    f.pill(540, 560, "PIGGY BANK  VS.  STOCK MARKET", 30, a, fill=GOLD, tc=NAVY, track=0.12)
    piggy(f, 290, 900, 1.0, a, wob=4 * math.sin(lt * 9) * (lt % 0.55 > 0.42))
    coin_drop(f, 288, 900 - 86, lt, a)
    figure(f, 140, 1010, 110, a)
    f.text(270, 1110, "THE SAVER", 30, PINK, a, "black", track=0.12)
    chart = [(i / 16, 0.2 + 0.55 * (i / 16) + 0.08 * math.sin(i * 1.7)) for i in range(17)]
    k = max(2, int(2 + 15 * ((lt * 0.5) % 1.0)))
    figure(f, 640, 1085, 110, a, bob=abs(math.sin(lt * 14)) * 3)
    pc_desk(f, 760, 1030, 0.62, a, t, chart=chart[:k])
    f.text(780, 1110, "THE INVESTOR", 30, GREEN_HI, a, "black", track=0.12)
    f.text(540, 900, "VS", 60, WHITE, a * 0.9, "black")


YKEYS = [(0.0, 0.0), (1.4, 2.0), (3.4, 3.0), (5.0, 4.4), (7.6, 16.0), (8.8, 17.0), (10.6, 20.0)]


def yrs_at(lt):
    if lt <= YKEYS[0][0]:
        return 0.0
    for (l0, y0), (l1, y1) in zip(YKEYS, YKEYS[1:]):
        if lt <= l1:
            return y0 + (y1 - y0) * (lt - l0) / (l1 - l0)
    return 20.0


CX0, CX1, CY0, CY1 = 150, 900, 1300, 700


def b1(f, t, a, lt):
    """the race: one chart, dynamic y-scale, piggy line vs stock line"""
    f.cam(540, 900, 1.0)
    yv = yrs_at(lt)
    pv, sv = val(PIG, yv), val(STK, yv)
    top = max(7000.0, max(sv, pv) * 1.22)
    n = max(2, int(yv * 12) + 1)
    span = max(3.6, yv * 1.06 + 0.3)  # the chart zooms out with time: early years use the full width
    X = lambda yy: lerp(CX0, CX1, yy / span)
    Y = lambda v: lerp(CY0, CY1, v / top)
    steps = [1000, 2000, 5000, 10000, 20000, 50000, 100000]
    step = next(s for s in steps if top / s <= 4.5)
    g = step
    while g < top:
        f.dash(CX0, Y(g), CX1, Y(g), MUTED, 0.22 * a)
        if Y(g) > 760:
            f.text(CX0 + 4, Y(g) - 18, f"${g // 1000}K", 20, MUTED, a * 0.9, "xb", anchor="lm")
        g += step
    f.line([(CX0, CY0), (CX1, CY0)], MUTED, 0.6 * a, 3)
    ystep = 1 if span <= 5 else (2 if span <= 10 else 5)
    for k in range(0, 21, ystep):
        if k <= span:
            f.text(X(k), CY0 + 34, str(2006 + k), 22, MUTED, a, "xb")
    ppts = [(X(k / 12), Y(PIG[k])) for k in range(n)] + [(X(yv), Y(pv))]
    spts = [(X(k / 12), Y(STK[k])) for k in range(n)] + [(X(yv), Y(sv))]
    f.line(ppts, PINK, a, 6)
    cols = [GREEN if y1 <= y0 + 0.01 else RED for (x0, y0), (x1, y1) in zip(spts, spts[1:])]
    f.cline(spts, cols, a, 7)
    hx, hy = spts[-1]
    px, py = ppts[-1]
    crash = 1.0 if 2.0 < yv < 3.05 else 0.0
    up = sv >= pv  # the leader's icon sits above its line, the other one below
    f.halo(hx, hy, 70, RED if crash else GREEN, 0.75 * a)
    f.halo(px, py, 60, PINK, 0.6 * a)
    mini_monitor(f, hx, hy - 52 if up else hy + 56, 0.9, a, red=crash)
    piggy(f, px, py + 44 if up else py - 40, 0.28, a)
    # year + counters
    f.text(540, 330, f"{2006 + min(19, int(yv))}", 92, WHITE, a, "black")
    behind = sv < pv and yv > 1.9
    counter_box(f, 300, 525, "PIGGY BANK", pv, PINK, a, lambda x, y: piggy(f, x, y + 4, 0.2, a),
                winning=("PIGGY BANK IS WINNING", 1.0) if behind else None)
    counter_box(f, 780, 525, "STOCKS", sv, GREEN_HI, a, lambda x, y: mini_monitor(f, x, y + 4, 0.7, a, red=crash))
    # events
    pc = prog(lt, 1.55, 0.35) * (1 - prog(lt, 3.6, 0.4))
    f.pill(540, 412, "2008: MARKET CRASH  −37%", 26 * (0.8 + 0.2 * eback(pc)), a * eo(pc), fill=RED, tc=WHITE, track=0.1)
    kline(f, 540, 690, "HE DIDN'T SELL. HE KEPT BUYING.", 40, WHITE, lt, 3.5, a * (1 - prog(lt, 5.1, 0.4)))
    pl = prog(lt, 4.85, 0.3) * (1 - prog(lt, 6.4, 0.4))
    f.pill(540, 412, "STOCKS TAKE THE LEAD", 28 * (0.8 + 0.2 * eback(pl)), a * eo(pl), fill=GREEN, tc=NAVY, track=0.12)
    p22 = prog(lt, 7.65, 0.3) * (1 - prog(lt, 9.0, 0.4))
    f.pill(540, 412, "2022: −18%  ·  HE HELD ON", 26 * (0.8 + 0.2 * eback(p22)), a * eo(p22), fill=RED, tc=WHITE, track=0.1)
    pe = prog(lt, 10.5, 0.4)
    f.burst(hx, hy - 30, prog(lt, 10.6, 1.4), seed=4, n=18, spread=380, a=a)
    if pe > 0:
        f.ring(hx, hy, prog(lt, 10.6, 1.0), GREEN_HI, 0.8 * a, rmax=260)


def b2(f, t, a, lt):
    """result"""
    f.cam(540, 900, 1.0 + 0.02 * eio(lt / 4.5))
    if COVER:
        f.text(540, 330, "$5 A DAY", 110, GOLD_HI, a, "black")
        f.text(540, 412, "PIGGY BANK VS. STOCKS · 20 YEARS", 30, WHITE, a, "black", track=0.08)
    else:
        kline(f, 540, 330, "AFTER 20 YEARS", 52, WHITE, lt, 0.0, a, track=0.06)
        kline(f, 540, 400, "SAME $36,500 PUT IN", 30, MUTED, lt, 0.2, a, w="black", track=0.1)
    f.rect(100, 470, 510, 1060, DARKCARD, 0.92 * a, r=26)
    f.rect(100, 470, 510, 1060, PINK, a, r=26, w=4)
    piggy(f, 305, 640, 0.9, a)
    f.text(305, 800, "PIGGY BANK", 34, PINK, a, "black", track=0.1)
    vp = FINAL_P * eio(prog(lt, 0.3, 1.0))
    f.text(305, 880, money(vp), 64, WHITE, a, "black")
    f.text(305, 950, "+$0 GROWTH", 24, MUTED, a * eo(prog(lt, 1.2, 0.4)), "xb", track=0.12)
    f.rect(570, 470, 980, 1060, DARKCARD, 0.92 * a, r=26)
    f.rect(570, 470, 980, 1060, GREEN_HI, a, r=26, w=4)
    f.halo(775, 650, 220, GREEN, 0.3 * a * eo(prog(lt, 1.0, 0.6)))
    pc_desk(f, 775, 700, 0.6, a, t, chart=[(i / 20, val(STK, i) / FINAL_S) for i in range(21)])
    f.text(775, 800, "STOCK MARKET", 34, GREEN_HI, a, "black", track=0.1)
    vs = FINAL_S * eio(prog(lt, 0.5, 1.4))
    f.text(775, 880, money(vs), 64, WHITE, a, "black")
    f.text(775, 950, f"+{money(FINAL_S - FINAL_P)}", 26, GREEN_HI, a * eo(prog(lt, 1.9, 0.4)), "black")
    p = prog(lt, 2.0, 0.5)
    f.text(540, 1200, "4.4× MORE", 120 * (0.85 + 0.15 * eback(p)), GOLD_HI, a * eo(p), "black")
    if not COVER:
        rain(f, lt, 2.0, a * 0.8, n=14)


def b3(f, t, a, lt):
    """the punchline"""
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.4))
    kline(f, 540, 420, "THE PIGGY BANK", 70, WHITE, lt, 0.05, a)
    kline(f, 540, 505, "NEVER CRASHED.", 82, WHITE, lt, 0.25, a)
    kline(f, 540, 640, "IT JUST NEVER GREW.", 72, PINK, lt, 1.0, a)
    piggy(f, 330, 1010, 0.95, a)
    f.line([(160, 1150), (500, 1150)], PINK, a, 6)
    q = eio(prog(lt, 0.4, 2.2))
    pts = [(600 + 300 * i / 30, 1150 - 260 * (i / 30) ** 1.6 + 26 * math.sin(i * 0.9) * (i / 30)) for i in range(31)]
    sub = partial(pts, max(0.002, q))
    cols = [GREEN if y1 <= y0 else RED for (x0, y0), (x1, y1) in zip(sub, sub[1:])] or [GREEN]
    f.cline(sub, cols, a, 6)
    f.halo(sub[-1][0], sub[-1][1], 60, GREEN, 0.7 * a)


def b4(f, t, a, lt):
    """question + follow -> loops into the hook"""
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 2.6))
    kline(f, 540, 470, "WHICH ONE", 96, WHITE, lt, 0.05, a)
    kline(f, 540, 575, "ARE YOU?", 110, GOLD_HI, lt, 0.3, a)
    piggy(f, 300, 900, 0.8, a, wob=3 * math.sin(lt * 6))
    f.text(300, 1030, "SAVER", 30, PINK, a, "black", track=0.14)
    mini_monitor(f, 780, 880, 2.6, a)
    f.text(780, 1030, "INVESTOR", 30, GREEN_HI, a, "black", track=0.14)
    f.text(540, 900, "OR", 48, MUTED, a, "black")
    follow(f, lt, 0.9, a)


BEATS = [(0.0, 3.2, b0), (3.2, 14.6, b1), (14.6, 19.2, b2), (19.2, 22.4, b3), (22.4, DUR, b4)]
L1 = 3.2  # race start
SHAKES = [(L1 + 2.3, 0.45, 9)]
FLASHES = [(L1 + 4.85, 0.16, 0.16), (14.6 + 2.0, 0.2, 0.28)]


def tint(t):
    lt = t - L1
    k = 0.2 * prog(lt, 1.6, 0.4) * (1 - prog(lt, 3.4, 0.5))
    return (RED, k) if k > 0.01 else None


def persistent(f, t):
    footnote(f, "S&P 500 INCL. DIVIDENDS, ANNUAL DATA (DAMODARAN, NYU STERN) · NO TAXES/FEES · PAST ≠ FUTURE")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES, tint).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES, tint).resize((360, 640), Image.LANCZOS)


def cover():
    global COVER
    COVER = True
    f = E.compose(17.4, BEATS, DUR, persistent)
    im = E.post(f.img, 0.0)
    from PIL import ImageDraw
    ImageDraw.Draw(im, "RGBA").text((E.OW - 60 * E.K, 1700 * E.K), "Moneycheck", font=E.font("sb", 32 * E.K),
                                    fill=(255, 255, 255, 153), anchor="rm")
    im.save(f"cover_{NAME}.png")


# ------------------------------------------------------------------ sound
EVENTS = [(0.0, "bass", 0.55), (0.0, "pop", 0.45), (0.15, "pop", 0.4), (0.3, "swoosh_up", 0.35)]
EVENTS += [(0.42 + 0.55 * k, "coin", 0.32) for k in range(5)]
EVENTS += [(0.2 + 0.18 * k, "tick", 0.12) for k in range(14)]
EVENTS += [(L1, "whoosh", 0.5), (L1 + 0.1, "riser", 0.3)]
EVENTS += [(L1 + 0.7 * k, "coin_p", 0.22, 1600 + 60 * k) for k in range(3)]
EVENTS += [(L1 + 1.55, "alert", 0.4), (L1 + 1.7, "sweep_down", 0.55), (L1 + 2.3, "impact", 0.6), (L1 + 2.3, "bass", 0.5)]
EVENTS += [(L1 + 3.5, "pop", 0.4), (L1 + 4.85, "ding", 0.55), (L1 + 4.9, "swoosh_up", 0.45)]
EVENTS += [(L1 + 5.0 + 0.26 * k, "coin_p", 0.26, 1900 + 70 * k) for k in range(10)]
EVENTS += [(L1 + 7.65, "sweep_down", 0.4), (L1 + 7.8, "pop", 0.35), (L1 + 8.9, "riser", 0.4)]
EVENTS += [(L1 + 9.0 + 0.2 * k, "coin_p", 0.3, 2093 + 120 * k) for k in range(8)]
EVENTS += [(L1 + 10.6, "cash", 0.6), (L1 + 10.6, "impact", 0.4), (L1 + 10.65, "sparkle", 0.45)]
EVENTS += [(14.6, "whoosh", 0.5), (14.7, "pop", 0.4), (14.9, "coin", 0.4), (15.1, "riser", 0.3), (16.6, "cash", 0.6),
           (16.6, "impact", 0.45), (16.65, "sparkle", 0.45)]
EVENTS += [(19.2, "whoosh", 0.5), (19.3, "pop", 0.4), (19.5, "pop", 0.4), (20.2, "ding", 0.45)]
EVENTS += [(22.4, "whoosh", 0.5), (22.5, "pop", 0.45), (22.75, "pop", 0.45), (23.3, "ding", 0.4), (DUR - 0.55, "whoosh", 0.55)]

if __name__ == "__main__":
    E.main(sys.argv, fb, thumb, NF, NAME, cover, EVENTS, DUR)

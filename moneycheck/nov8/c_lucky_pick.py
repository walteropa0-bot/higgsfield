"""Video C - "One lucky pick": can a single stock make you rich, and how likely is that?
cryothum-style animation in Moneycheck colours (lib20), voice af_heart (voice_local.py), 1080x1920, 30 fps.

Data: Hendrik Bessembinder (2026), "One Hundred Years in the U.S. Stock Markets", summary by Larry Swedroe,
WealthManagement.com, 26 May 2026: 29,754 stocks of 29,081 firms, 1926-2025 (CRSP). The top 46 firms created half
of the $91 trillion of net wealth (odds 29,081 / 46 = 1 in 632, said "about one in six hundred thirty"); 3.7% of
firms created all of it (1 in 27); only 48% of stocks had any positive return; whole market +1,504,057%
($1 -> $15,041). Every dot in the grid is one firm (29,081 dots); the colours use those shares.

python3 c_lucky_pick.py sheet out.png [t ...] | frame out.png t | video | cover
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import lib20 as L  # noqa: E402
import mix20  # noqa: E402
from lib20 import (W, H, FPS, SS, clamp, prog, eo, eio, eback, lerp, mixc, qmix, hit, headline, num, money,  # noqa: E402
                   NAVY, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, RED, RED_HI, LINE, DIM, PANEL)

NAME = "lucky_pick"
WD = L.Words(os.path.join(HERE, "c_words.json"))
T = WD.T
VOICE = os.path.join(HERE, "c_voice.mp3")
DUR = round(WD.end + 0.95, 2)
GROUND = 1250

# word anchors (phrases are unique; numbered where a word repeats)
TPUT, TTHOU, TINTO, TSINGLE, TSTOCK = T("put"), T("thousand"), T("into one"), T("single"), T("stock")
TBEST, TSUP, TRICH = T("Best"), T("superstar"), T("rich")
TBUT, TLIKELY = T("But how"), T("likely")
TSTUDY, TTRACK, TEVERY, T29, TCOMP = T("A study"), T("tracked"), T("every"), T("Twenty-nine"), T("companies")
TJUST, T46, THALF = T("Just"), T("forty-six"), T("half")
TYOUR, TODDS, TPICK, T630 = T("Your odds"), T("odds"), T("picking"), T("one in six")
TANY, TWIN, T27 = T("Any of"), T("winners"), T("one in twenty-seven")
TMOST, TMORE, TLOST = T("The most"), T("More than half"), T("lost money")
TMEAN, TMARKET, TWHOLE, TDOLLAR, TINTO2, T15 = (T("Meanwhile"), T("market as"), T("whole"), T("one dollar"),
                                                T("into more"), T("fifteen"))
TLUCK, TRICH2, TODDS2, TSIDE = T("Luck"), T("rich", 2), T("odds", 2), T("side")

# ------------------------------------------------------------------ the grid: one dot per firm
GX, GY, GW, GH = 1820.0, 880.0, 860.0, 850.0  # 5-px grid: integer spacing at 2x -> no moire
COLS, ROWS, NF = 172, 170, 29081
N_GOLD, N_GREEN, N_RED = 46, 1076, 15122  # 46 firms; 3.7% of 29,081; 52% (only 48% positive)


def _grid():
    rng = np.random.default_rng(46)
    perm = rng.permutation(NF)
    cat = np.zeros(NF, np.uint8)
    cat[perm[N_GOLD:N_GREEN]] = 30
    cat[perm[:N_GOLD]] = 40
    cat[perm[N_GREEN:N_GREEN + N_RED]] = 20
    cat[cat == 0] = 10
    wpx, hpx = int(GW * SS), int(GH * SS)
    ims = {k: Image.new("L", (wpx, hpx), 0) for k in ("m", "db", "dr", "cat")}
    dr = {k: ImageDraw.Draw(v) for k, v in ims.items()}
    sx, sy, r = GW / COLS * SS, GH / ROWS * SS, 1.55 * SS
    noise = rng.random(NF)
    rnd = rng.random(NF)
    pos = []
    for i in range(NF):
        c, rw = i % COLS, i // COLS
        x, y = (c + 0.5) * sx, (rw + 0.5) * sy
        box = (x - r, y - r, x + r, y + r)
        dr["m"].ellipse(box, fill=255)
        dr["db"].ellipse(box, fill=1 + int(254 * (0.86 * rw / ROWS + 0.14 * noise[i])))
        dr["dr"].ellipse(box, fill=1 + int(254 * rnd[i]))
        dr["cat"].ellipse(box, fill=int(cat[i]))
        pos.append((GX - GW / 2 + x / SS, GY - GH / 2 + y / SS))
    arr = {k: np.asarray(v) for k, v in ims.items()}
    return arr, cat, np.array(pos)


GRID, CAT, POS = _grid()
GOLD_POS = POS[CAT == 40]


def _pick_dot():
    c0, r0 = 74, 40  # upper middle of the grid, away from the headline
    for d in range(40):
        for rw in range(r0 - d, r0 + d + 1):
            for c in range(c0 - d, c0 + d + 1):
                i = rw * COLS + c
                if 0 <= i < NF and CAT[i] == 10:
                    return tuple(POS[i])
    return tuple(POS[0])


PICK = _pick_dot()


def grid_state(t):
    pb = eo(prog(t, TSTUDY - 0.05, T29 - TSTUDY + 0.05))
    base_a = lerp(0.42, 0.26, eo(prog(t, T46 - 0.3, 0.3)))
    pg = eo(prog(t, T46 - 0.25, 0.25))
    pgr = prog(t, TWIN - 0.45, 0.45)
    pr = prog(t, TMORE - 0.5, 0.5)
    return tuple(int(round(v * 64)) for v in (pb, base_a, pg, pgr, pr))


_cache = {}


def grid_image(state):
    if state in _cache:
        return _cache[state]
    pb, base_a, pg, pgr, pr = (v / 64 for v in state)
    m, db, drr, cat = GRID["m"], GRID["db"], GRID["dr"], GRID["cat"]
    vis = (db > 0) & (db <= max(1, int(pb * 255)))
    a = np.where(vis, m.astype(np.float32) / 255 * base_a, 0.0)
    rgb = np.empty(m.shape + (3,), np.uint8)
    rgb[:] = LINE
    for code, prg, col in ((20, pr, RED), (30, pgr, GREEN_HI), (40, pgr, GREEN_HI), (40, pg, GOLD_HI)):
        if prg <= 0:
            continue
        sel = vis & (cat == code) & (drr <= max(1, int(prg * 255)))
        rgb[sel] = col
        a[sel] = m[sel] / 255
    im = Image.fromarray(np.dstack([rgb, (np.clip(a, 0, 1) * 255).astype(np.uint8)]), "RGBA")
    if len(_cache) > 6:
        _cache.clear()
    _cache[state] = im
    return im


def s_grid(f, t):
    if t < TSTUDY - 0.9 or t > TMEAN + 0.3:
        return
    fa = eo(prog(t, TSTUDY - 0.35, 0.3))
    L.box(f, GX - GW / 2 - 18, GY - GH / 2 - 18, GX + GW / 2 + 18, GY + GH / 2 + 18, fa, c=DIM, w=2, r=16, fill=None, glow_a=0.08)
    L.paste_world(f, grid_image(grid_state(t)), GX, GY)
    pg = eo(prog(t, T46 - 0.25, 0.25))
    if pg > 0.01:
        pulse = 0.75 + 0.25 * math.sin(t * 6)
        for x, y in GOLD_POS:
            f.halo(x, y, 19, GOLD, 0.75 * pg * pulse)
            f.circ(x, y, 3.4, GOLD_HI, pg)
    # the pick: a cursor wanders and lands on one firm
    if TYOUR - 0.25 <= t <= TANY:
        a = eo(prog(t, TYOUR - 0.25, 0.2)) * (1 - eio(prog(t, TANY - 0.3, 0.25)))
        way = [(GX + 330, GY - 400), (GX + 120, GY - 140), (GX - 230, GY - 320), (PICK[0] + 40, PICK[1] - 60), PICK]
        u = eio(prog(t, TYOUR - 0.2, TPICK - TYOUR + 0.2))
        k = min(int(u * (len(way) - 1)), len(way) - 2)
        q = eio(u * (len(way) - 1) - k)
        cx, cy = lerp(way[k][0], way[k + 1][0], q), lerp(way[k][1], way[k + 1][1], q)
        press = prog(t, TPICK - 0.02, 0.2)
        f.ring(PICK[0], PICK[1], prog(t, TPICK, 0.5), WHITE, a, rmax=46, w=3)
        if t >= TPICK:
            f.circ(PICK[0], PICK[1], 7, WHITE, a * 0.9, w=2)
        L.cursor(f, cx, cy, a, s=1.0 / f.z, press=press)


# ------------------------------------------------------------------ station 1: the bet (also the loop start/end)
WX, WY, WW, WH = 700, 690, 600, 440
CH = [1.0, 1.04, 0.99, 1.08, 1.03, 1.12, 1.07, 1.18, 1.3, 1.55, 2.1, 3.0, 4.4, 6.5]


def chart_p(t):
    if t < TLUCK - 0.7:
        return 0.62 * eo(prog(t, TSTOCK - 0.3, 0.7)) + 0.38 * eio(prog(t, TSUP - 0.45, 0.45))
    return 0.62 * eo(prog(t, TLUCK - 0.2, 0.5)) + 0.38 * eio(prog(t, TRICH2 - 0.45, 0.45))


def s1(f, t):
    L.ground(f, -300, 1400, GROUND)
    end = t >= TLUCK - 0.7
    arms, ring = None, 0.0
    if not end and TRICH - 0.15 <= t < TBUT - 0.1:
        arms, ring = "up", eo(prog(t, TRICH - 0.15, 0.2))
    if end and TRICH2 - 0.15 <= t < TODDS2 - 0.05:
        arms, ring = "up", eo(prog(t, TRICH2 - 0.15, 0.2))
    if end and TODDS2 - 0.05 <= t < TSIDE + 0.45:
        arms = "side"
    L.guy(f, 270, GROUND, 170, arms=arms, t=t, spot=0.9, label="YOU", ring=ring)
    x0, y0, x1, y1 = L.window(f, WX, WY, WW, WH, url="MY PORTFOLIO")
    ca_ = 1 - eio(prog(t, DUR - 0.75, 0.4))
    L.chart(f, x0 + 34, y0 + 82, x1 - 34, y1 - 100, CH, chart_p(t), ca_, GREEN, vmin=0.8, vmax=6.7)
    f.pill(x0 + 92, y0 + 40, "1 STOCK", 17, hit(t, TSINGLE, 0.2) * ca_ if t < TLUCK - 0.7 else ca_ * eo(prog(t, TLUCK - 0.2, 0.3)),
           fill=None, outline=GOLD_HI, tc=GOLD_HI, track=0.3, padx=18, pady=8)
    L.button(f, WX, y1 - 48, "BUY", 26, press=prog(t, TPUT - 0.02, 0.18))
    # cursor: hovers BUY at the start, clicks on "put", leaves; comes back for the loop
    a_cur = (1 - eio(prog(t, TBEST - 0.2, 0.2))) if t < TLUCK else eo(prog(t, DUR - 0.65, 0.3))
    L.cursor(f, WX + 26, y1 - 40, a_cur, press=prog(t, TPUT - 0.02, 0.18))
    f.ring(WX, y1 - 48, prog(t, TPUT, 0.45), WHITE, 1.0, rmax=80, w=4)
    # $1,000 flies from the figure into the stock
    if TTHOU - 0.25 <= t < TSINGLE + 0.25:
        pin = hit(t, TTHOU, 0.22)
        mv = eio(prog(t, TINTO - 0.05, TSINGLE - TINTO + 0.05))
        bx, by = lerp(300, x0 + 92, mv), lerp(880, y0 + 40, mv)
        s = lerp(1.0, 0.45, mv)
        a = pin * (1 - prog(t, TSINGLE - 0.12, 0.14))
        L.statbox(f, bx, by, 250 * s, 120 * s, "INVESTED", "$1,000", a, vc=GREEN_HI, size=52 * s)
    if not end:
        f.burst(270, 1060, prog(t, TRICH, 1.2), seed=3, n=18, spread=380, a=1.0)
        f.burst(WX + 230, y0 + 120, prog(t, TSUP, 1.0), seed=5, n=10, spread=260, scale=0.8)
        if TLIKELY - 0.2 <= t:
            L.bubble(f, 375, 985, "?", 1.15 * (0.6 + 0.4 * eback(hit(t, TLIKELY, 0.2))), hit(t, TLIKELY, 0.2))
    else:
        f.burst(270, 1060, prog(t, TRICH2, 1.1), seed=8, n=12, spread=320)


# ------------------------------------------------------------------ station 3: the whole market
TX = 3140


def tower_grow(t):
    return eio(prog(t, TINTO2 - 0.1, T15 - TINTO2 + 0.1))


def s_tower(f, t):
    if t < TMEAN - 0.9 or t > TLUCK + 0.3:
        return
    L.ground(f, TX - 760, TX + 760, GROUND)
    g = eo(prog(t, TWHOLE - 0.2, 0.25))
    for i, x in enumerate((TX - 440, TX - 345, TX - 250, TX + 250, TX + 345, TX + 440)):
        L.guy(f, x, GROUND, 84 + 8 * (i % 2), c=qmix(WHITE, GREEN_HI, g), a=0.85, t=t,
              arms="up" if t >= T15 - 0.1 else None)
    gr = tower_grow(t)
    hgt = 630 * gr
    pc = hit(t, TDOLLAR, 0.2)
    if hgt > 2:
        f.halo(TX, GROUND - hgt / 2, max(140, hgt * 0.6), GOLD, 0.35, sx=0.5, sy=1.0)
        f.rect(TX - 92, GROUND - hgt, TX + 92, GROUND, (120, 92, 22), 1.0, r=10)
        f.rect(TX - 92, GROUND - hgt, TX + 92, GROUND, GOLD_HI, 1.0, r=10, w=4)
        for k in range(int(hgt // 34)):
            yy = GROUND - 17 - k * 34
            f.line([(TX - 80, yy), (TX + 80, yy)], GOLD, 0.6, 2)
    if pc > 0:
        f.coin(TX, GROUND - hgt - 40, 40 * (0.6 + 0.4 * eback(pc)), pc, spin=t * 3)
    f.burst(TX, GROUND - 650, prog(t, T15, 1.3), seed=9, n=26, spread=470)


# ------------------------------------------------------------------ screen-space headlines (no overlaps)
def big(text, color, size=110, y=330, label=None, label_c=MUTED, ly=None):
    def draw(f, a, dy):
        num(f, W / 2, y + dy, text, size, color, a)
        if label:
            f.text(W / 2, (ly or y + size * 0.72) + dy, label, 24, label_c, a, "xb", track=0.3)
    return draw


def lbl(text, color=MUTED, y=398, size=23):
    def draw(f, a, dy):
        f.text(W / 2, y + dy, text, size, color, a, "xb", track=0.3)
    return draw


def pill(text, fill=GOLD, tc=NAVY, y=330, size=34, outline=None):
    def draw(f, a, dy):
        f.pill(W / 2, y + dy, text, size, a, fill=fill, tc=tc, outline=outline, track=0.26)
    return draw


def hook(f, a, dy):
    f.text(W / 2, 300 + dy, "ONE STOCK.", 74, WHITE, a, "black")
    f.text(W / 2, 400 + dy, "RICH?", 112, GOLD_HI, a, "black")


def overlay(f, t):
    headline(f, t, 0.0, TBEST - 0.06, hook)
    headline(f, t, DUR - 0.02, DUR + 9, hook, d_in=0.42)
    headline(f, t, TBEST, TBUT - 0.12, pill("BEST CASE"))
    cnt = lambda t_: money(29081 * eio(prog(t_, TEVERY, T29 - TEVERY)))[1:]  # noqa: E731
    headline(f, t, TEVERY, TJUST - 0.1, lambda f_, a, dy: num(f_, W / 2, 330 + dy, cnt(t), 104, WHITE, a))
    headline(f, t, TTRACK, TCOMP - 0.03, lbl("EVERY U.S. STOCK · 1926–2025"))
    headline(f, t, TCOMP, TJUST - 0.1, lbl("COMPANIES", WHITE))
    headline(f, t, T46, TYOUR - 0.12, big("46", GOLD_HI, 120))
    headline(f, t, THALF, TYOUR - 0.12, lbl("CREATED HALF OF ALL THE WEALTH", GOLD_HI))
    headline(f, t, TODDS, T630 - 0.03, lbl("YOUR ODDS", WHITE))
    headline(f, t, T630, TANY - 0.12, big("1 IN 630", GOLD_HI, 110))
    headline(f, t, T630, TANY - 0.12, lbl("TO PICK ONE OF THE 46", MUTED))
    headline(f, t, TWIN, T27 - 0.12, big("3.7%", GREEN_HI, 110))
    headline(f, t, TWIN, T27 - 0.12, lbl("CREATED ALL $91 TRILLION", GREEN_HI))
    headline(f, t, T27, TMOST - 0.1, big("1 IN 27", GREEN_HI, 110))
    headline(f, t, T27, TMOST - 0.1, lbl("ANY BIG WINNER AT ALL", MUTED))
    headline(f, t, TMORE, TMEAN - 0.62, big("MORE THAN HALF", RED_HI, 76))
    headline(f, t, TLOST, TMEAN - 0.62, lbl("LOST MONEY", RED_HI, y=400))
    headline(f, t, TMARKET, TLUCK - 0.66, lbl("THE WHOLE MARKET · 1926–2025", WHITE, y=420))
    val = lambda t_: 15041 ** tower_grow(t_)  # noqa: E731
    headline(f, t, TDOLLAR, TLUCK - 0.66,
             lambda f_, a, dy: num(f_, W / 2, 330 + dy, money(val(t)), 104, GREEN_HI if t >= T15 else WHITE, a))
    headline(f, t, TLUCK, TODDS2 - 0.1, pill("LUCK"))
    headline(f, t, TODDS2, DUR - 0.5, big("1 IN 27", WHITE, 96))
    headline(f, t, TODDS2, DUR - 0.5, lbl("THE ODDS", MUTED, y=400))
    headline(f, t, TSIDE + 0.25, DUR - 0.36, pill("FOLLOW FOR MORE", fill=None, tc=GOLD_HI, outline=GOLD_HI, y=1420, size=26))


def footnote(t):
    if TSTUDY - 0.3 <= t < TMEAN - 0.6:
        return "SOURCE: BESSEMBINDER (2026), CRSP 1926–2025 · EACH DOT = 1 OF 29,081 FIRMS"
    if TMEAN - 0.6 <= t < TLUCK - 0.6:
        return "SOURCE: BESSEMBINDER (2026) · TOTAL U.S. MARKET +1,504,057%, 1926–2025"
    return ""


CAM = L.Cam((540, 960, 1.0), [
    (TBUT, (540, 1010, 0.9), 0.45),
    (TSTUDY, (1840, 960, 1.0), 0.55),
    (TYOUR, (PICK[0] + 60, PICK[1] + 180, 1.32), 0.45),
    (TANY, (1840, 960, 1.0), 0.45),
    (TMEAN, (TX, 960, 1.0), 0.55),
    (TLUCK, (540, 960, 1.0), 0.62),
])

VIDEO = L.Video(DUR, CAM, [(-400, 1500, s1), (1300, 2400, s_grid), (TX - 800, TX + 800, s_tower)],
                shakes=[(T29 + 0.02, 0.3, 6), (T630 + 0.02, 0.3, 6), (T15 + 0.02, 0.4, 9)],
                flashes=[(T15, 0.18, 0.18)], footnote=footnote, overlay=overlay)


def events():
    ev = [(0.0, "bass", 0.45), (0.02, "pop", 0.3), (TPUT, "click", 0.6), (TTHOU - 0.02, "coin", 0.4), (TTHOU, "pop", 0.3),
          (TINTO, "whoosh", 0.22), (TSINGLE, "blip", 0.4), (TBEST, "ding", 0.32), (TSUP - 0.45, "swoosh_up", 0.45),
          (TRICH, "kaching", 0.5), (TRICH, "sparkle", 0.35), (TBUT - 0.45, "swish", 0.3), (TLIKELY, "pop", 0.4),
          (TSTUDY - 0.55, "swish", 0.45), (T29, "impact", 0.35)]
    n = 12
    for i in range(n):  # counting up: rising mallet
        ev.append((lerp(TEVERY, T29 - 0.1, i / (n - 1)), "mallet", 0.18, {"freq": round(523.25 * 2 ** (i / 12), 1)}))
    ev += [(T46 - 0.05, "sparkle", 0.45), (T46, "ding", 0.35), (THALF, "swoosh_up", 0.3),
           (TYOUR - 0.45, "swish", 0.3)] + [(lerp(TYOUR, TPICK - 0.1, i / 5), "tick", 0.15) for i in range(6)]
    ev += [(TPICK, "click", 0.6), (T630, "bass", 0.45), (T630, "pop", 0.35), (TANY - 0.45, "swish", 0.25),
           (TWIN - 0.3, "sparkle", 0.4), (TWIN, "mallet", 0.25, {"freq": 1046.5}), (TWIN + 0.08, "mallet", 0.22, {"freq": 1318.5}),
           (T27, "pop", 0.4), (T27, "bass", 0.35), (TMORE - 0.45, "sweep_down", 0.35), (TMORE, "thud", 0.55),
           (TLOST, "thud", 0.4), (TMEAN - 0.55, "swish", 0.45), (TDOLLAR, "coin", 0.45), (T15 - 1.15, "riser", 0.35),
           (T15, "kaching", 0.55), (T15, "impact", 0.4), (T15, "sparkle", 0.4), (TLUCK - 0.62, "swish", 0.45),
           (TLUCK, "ding", 0.3), (TRICH2, "coin", 0.35), (TODDS2, "thud", 0.35), (TSIDE + 0.25, "pop", 0.3),
           (DUR - 0.45, "whoosh", 0.22)]
    return ev


def cover():
    f = L.F2(0.0, 1840, 860, 1.0)
    L.box(f, GX - GW / 2 - 18, GY - GH / 2 - 18, GX + GW / 2 + 18, GY + GH / 2 + 18, 1, c=DIM, w=2, r=16, fill=None, glow_a=0.08)
    L.paste_world(f, grid_image(tuple(int(round(v * 64)) for v in (1, 0.26, 1, 0, 0))), GX, GY)
    for x, y in GOLD_POS:
        f.halo(x, y, 19, GOLD, 0.8)
        f.circ(x, y, 3.4, GOLD_HI, 1)
    f.cam(W / 2, H / 2, 1.0)
    num(f, W / 2, 285, "1 IN 630", 132, GOLD_HI)
    f.text(W / 2, 410, "ONE STOCK. RICH?", 58, WHITE, 1, "black")
    im = L.post(f.img, 0.0)
    L.chrome(im, 0.0, DUR, "EACH DOT = 1 OF 29,081 U.S. FIRMS · BESSEMBINDER (2026)")
    im.save(f"cover_{NAME}.png")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "sheet":
        L.sheet(VIDEO, sys.argv[2], [float(x) for x in sys.argv[3:]])
    elif mode == "frame":
        VIDEO.frame(int(round(float(sys.argv[3]) * FPS))).save(sys.argv[2])
    elif mode == "cover":
        cover()
    elif mode == "video":
        L.render(VIDEO, f"{NAME}_video.mp4")
        mix20.mix(VOICE, events(), DUR, f"{NAME}_audio.wav")
        mix20.mux(f"{NAME}_video.mp4", f"{NAME}_audio.wav", f"moneycheck_{NAME}.mp4")
        mix20.handy(f"moneycheck_{NAME}.mp4", f"moneycheck_{NAME}_handy.mp4")
        print("done", NAME, DUR, "s")
    elif mode == "info":
        print("DUR", DUR, "PICK", PICK)

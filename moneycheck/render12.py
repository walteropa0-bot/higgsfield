"""Moneycheck Short #10 - "99% of Warren Buffett's money came after his 50th birthday" (20 s, viral loop).
Female voice (Samara X), no subtitles. 1080x1920, 30 fps. Anchors = exact word times (words.json).
Facts: Morgan Housel, The Psychology of Money (99% of net worth after age 50, 97% after 65); first stock at 11 (1942).

Usage:  python3 render12.py stills 1.0 ... | python3 render12.py sheet out.png 1 2 ... | python3 render12.py cover | video
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


DUR = 20.0
NF = int(round(DUR * FPS))
DARKCARD = (20, 34, 62)


def rays(f, cx, cy, t, a, c=GOLD, n=14, r0=40, r1=900, w=0.07):
    if a <= 0.01:
        return
    for i in range(n):
        g = t * 0.35 + i * 2 * math.pi / n
        f.poly([(cx + math.cos(g) * r0, cy + math.sin(g) * r0), (cx + math.cos(g - w) * r1, cy + math.sin(g - w) * r1),
                (cx + math.cos(g + w) * r1, cy + math.sin(g + w) * r1)], c, 0.09 * a)


def arc(f, cx, cy, r, w, a0, a1, c, a=1.0):
    if a <= 0.01 or a1 <= a0:
        return
    f.d.arc((f.X(cx - r), f.Y(cy - r), f.X(cx + r), f.Y(cy + r)), a0, a1, fill=ca(c, a), width=f.wpx(w))


def confetti(f, cx, cy, p, seed=1, n=34, a=1.0):
    if not 0 < p < 1:
        return
    rng = np.random.default_rng(seed)
    cols = [GOLD_HI, GREEN, WHITE, GOLD, GREEN_HI]
    for i in range(n):
        g = rng.uniform(-math.pi * 0.95, -math.pi * 0.05)
        sp = rng.uniform(300, 760)
        x = cx + math.cos(g) * sp * p
        y = cy + math.sin(g) * sp * p + 700 * p * p
        s = rng.uniform(6, 12)
        r0 = rng.uniform(0, 6) + p * 9
        pts = [(x + math.cos(r0 + k * math.pi / 2) * s, y + math.sin(r0 + k * math.pi / 2) * s * 0.5) for k in range(4)]
        f.poly(pts, cols[i % len(cols)], a * (1 - p))


# ------------------------------------------------------------------ 1 hook: 99% ring
RC, RR, RW = (540, 820), 250, 46


def cake(f, x, y, a, t):
    if a <= 0.01:
        return
    f.rect(x - 120, y - 40, x + 120, y + 60, DARKCARD, a, r=14)
    f.rect(x - 120, y - 40, x + 120, y + 60, WHITE, a, r=14, w=4)
    f.line([(x - 120 + 20 * i, y - 40 + (10 if i % 2 else 0)) for i in range(13)], GOLD_HI, a, 6)
    for dx, ch in ((-38, "5"), (38, "0")):
        f.text(x + dx, y - 82, ch, 66, WHITE, a, "black")
        fl = 0.85 + 0.15 * math.sin(t * 19 + dx)
        f.halo(x + dx, y - 140, 40, GOLD_HI, 0.7 * a)
        f.ell(x + dx, y - 136 - 4 * fl, 9, 16 * fl, GOLD_HI, a)


def hook(f, t):
    f.cam(540, 900, 1.0 + 0.05 * eio(t / 5.0))
    cx, cy = RC
    arc(f, cx, cy, RR, RW, 0, 360, (26, 42, 76), 1)
    arc(f, cx, cy, RR, RW, -88, 264.5, GOLD, 1)
    arc(f, cx, cy, RR, RW, 266.5, 268.8, WHITE, 1)
    sw = eo(prog(t, 0.05, 1.4))
    if 0 < sw < 1:
        th = -90 + 360 * sw
        arc(f, cx, cy, RR, RW + 6, th - 50, th, GOLD_HI, 0.85)
        hx, hy = cx + RR * math.cos(math.radians(th)), cy + RR * math.sin(math.radians(th))
        f.halo(hx, hy, 110, GOLD_HI, 0.9)
        f.circ(hx, hy, 14, WHITE, 1)
    f.halo(cx, cy, 330, GOLD, 0.12 + 0.06 * math.sin(t * 3))
    p9 = prog(t, at("ninetynine"), 0.35)
    f.text(cx, cy, "99%", 138 * (1 + 0.06 * math.sin(math.pi * p9)), GOLD_HI, 1, "black")
    pw = prog(t, at("warren"), 0.35)
    f.text(540, 440, "OF WARREN BUFFETT'S MONEY", 30 * (0.85 + 0.15 * eback(pw)), WHITE, eo(pw), "xb", track=0.14)
    f.text(300, 560, "1% BEFORE 50", 22, WHITE, 0.8 * eo(pw), "xb", track=0.15, anchor="mm")
    f.line([(405, 566), (520, 574)], MUTED, 0.6 * eo(pw), 2)
    pa = prog(t, at("after"), 0.35)
    f.pill(540, 1140, "CAME AFTER AGE 50", 34 * (0.75 + 0.25 * eback(pa)), eo(pa), fill=GOLD, tc=NAVY, track=0.16)
    pc = prog(t, at("fiftieth"), 0.4)
    cake(f, 540, 1350, eo(pc) * (1 if pc > 0 else 0), t)
    confetti(f, 540, 1300, prog(t, at("birthday"), 1.4), seed=7)
    for i in range(6):
        sa = math.sin(math.pi * prog(t, at("birthday") + 0.08 * i, 0.6))
        f.sparkle(540 + 330 * math.cos(i * 1.05 + 0.4), 820 + 300 * math.sin(i * 1.05 + 0.4), 26 * sa, GOLD_HI, sa)


# ------------------------------------------------------------------ 2 skill vs secret
def hourglass(f, x, y, s, a, p, rot=0.0):
    if a <= 0.01:
        return
    c, sn = math.cos(rot), math.sin(rot)

    def P(u, v):
        return (x + (u * c - v * sn) * s, y + (u * sn + v * c) * s)

    f.halo(x, y, 120 * s, GOLD, 0.35 * a)
    f.line([P(-36, -54), P(36, -54)], WHITE, a, 6 * s)
    f.line([P(-36, 54), P(36, 54)], WHITE, a, 6 * s)
    f.line([P(-28, -50), P(-4, -4), P(-4, 4), P(-28, 50)], WHITE, a, 4 * s)
    f.line([P(28, -50), P(4, -4), P(4, 4), P(28, 50)], WHITE, a, 4 * s)
    q = 1 - clamp(p)
    if q > 0.02:
        f.poly([P(-22 * q, -6 - 36 * q), P(22 * q, -6 - 36 * q), P(0, -4)], GOLD_HI, a)
    if 0.02 < p < 0.98:
        f.line([P(0, 0), P(0, 44)], GOLD_HI, a, 2.5 * s)
    k = clamp(p * 1.4)
    if k > 0.02:
        f.poly([P(-22 * k, 46), P(22 * k, 46), P(0, 46 - 32 * clamp(p))], GOLD_HI, a)


def secret(f, t):
    ts, ti, tb, tse, tti = at("skill"), at("investing"), at("but"), at("secret"), at("time")
    f.cam(540, 900, 1.0 + 0.04 * eio(prog(t, 5.1, 4.4)))
    dim = 1 - 0.6 * prog(t, tb, 0.4)
    p1 = prog(t, ts - 0.15, 0.35)
    f.text(540, 400, "HIS SKILL", 26, MUTED, eo(p1) * dim, "xb", track=0.3)
    p2 = prog(t, ti, 0.35)
    f.text(540, 495, "INVESTING", 96 * (0.85 + 0.15 * eback(p2)), WHITE, eo(p2) * dim, "black")
    chart = [(380, 650), (430, 625), (470, 635), (520, 590), (565, 600), (615, 555), (660, 565), (700, 520)]
    f.line(partial(chart, max(0.002, eio(prog(t, ti + 0.1, 0.8)))), GREEN, eo(p2) * dim, 6)
    pr = eo(prog(t, tti - 0.1, 0.5))
    rays(f, 540, 1180, t, pr, GOLD)
    p3 = prog(t, tse - 0.1, 0.35)
    f.text(540, 770, "HIS SECRET", 26, GOLD, eo(p3), "xb", track=0.3)
    p4 = prog(t, tti, 0.35)
    f.text(540, 905, "TIME", 220 * (0.8 + 0.2 * eback(p4)), GOLD_HI, eo(p4), "black")
    flip = eio(prog(t, tti, 0.6))
    hourglass(f, 540, 1215, 1.9, eo(p3), prog(t, tti + 0.5, 3.0), rot=math.pi * flip)
    f.halo(770, 1412, 100, (130, 150, 200), 0.5 * eo(p3), sy=0.15)
    f.pawn(770, 1410, 115, WHITE, eo(p3))


# ------------------------------------------------------------------ 3 first stock at eleven, never stopped
AGES = [11, 20, 30, 40, 50]
TLX = lambda age: 150 + (age - 11) * 750 / 39


def certificate(f, x, y, a, t):
    if a <= 0.01:
        return
    f.halo(x, y, 260, GOLD, 0.3 * a)
    f.rect(x - 190, y - 120, x + 190, y + 120, (238, 233, 218), a, r=10)
    f.rect(x - 175, y - 105, x + 175, y + 105, GOLD, a, r=6, w=4)
    f.text(x, y - 62, "STOCK CERTIFICATE", 22, NAVY, a, "xb", track=0.14)
    f.text(x, y + 2, "3 SHARES", 52, NAVY, a, "black")
    f.text(x, y + 62, "1942", 24, (120, 100, 50), a, "xb", track=0.3)


def eleven(f, t):
    tbo, tel, tan, tst = at("bought"), at("eleven"), at("and", 1), at("stopped", end=True)
    f.cam(540, 940, 1.0)
    pc = prog(t, tbo - 0.05, 0.4)
    certificate(f, 540, 760, eo(pc), t)
    walk = eio(prog(t, tan, tst - tan - 0.05))
    age = 11 + 39 * walk
    pe = prog(t, tel, 0.35)
    f.pill(540, 430, f"AGE {int(round(age))}", 44 * (0.75 + 0.25 * eback(pe)), eo(pe), fill=GOLD, tc=NAVY, track=0.18)
    f.text(540, 520, "FIRST STOCK", 24, MUTED, eo(pe) * (1 - prog(t, tan, 0.3)), "xb", track=0.3)
    f.text(540, 520, "NEVER STOPPED", 24, GREEN_HI, eo(prog(t, at("never"), 0.3)), "xb", track=0.3)
    y0 = 1180
    f.dash(100, y0 + 2, 980, y0 + 2, MUTED, 0.45)
    for ag in AGES:
        x = TLX(ag)
        lit = age >= ag - 0.3
        f.line([(x, y0 - 8), (x, y0 + 10)], WHITE if lit else MUTED, 0.8, 3)
        f.text(x, y0 + 46, str(ag), 26, WHITE if lit else MUTED, 1.0 if lit else 0.5, "black")
    x = TLX(age)
    n = int((x - 150) / 46)
    for i in range(n + 1):
        cx = 150 + i * 46
        pb = prog(t, tan + (tst - tan) * (i * 46 / 750), 0.25)
        f.coin(cx + 20, y0 - 18 - 14 * math.sin(math.pi * clamp(pb * 1.4)) * (pb < 0.7), 15, eo(pb), spin=t * 8 + i)
    h = 78 + 72 * walk
    bob = abs(math.sin(t * 12)) * 6 if 0 < walk < 1 else 0
    f.halo(x, y0 + 2, h * 0.8, (130, 150, 200), 0.5, sy=0.15)
    f.pawn(x, y0, h, WHITE, eo(prog(t, tbo - 0.2, 0.3)), bob)


# ------------------------------------------------------------------ 4 compounding needs decades... then it explodes
BASE, CH = 1250, 690
AX = lambda age: 110 + (age - 11) * 830 / 84
AY = lambda age: BASE - CH * ((age - 11) / 84) ** 7.5
CURVE = [(AX(11 + i * 0.5), AY(11 + i * 0.5)) for i in range(169)]


def rain(f, t, t0, a=1.0, n=26, seed=9):
    if t < t0 or a <= 0.01:
        return
    rng = np.random.default_rng(seed)
    for i in range(n):
        x0 = rng.uniform(80, 1000)
        sp = rng.uniform(380, 620)
        d0 = rng.uniform(0, 1.2)
        u = t - t0 - d0
        if u < 0:
            continue
        y = -120 + sp * u
        if y > 2000:
            continue
        f.bill(x0 + 40 * math.sin(u * 3 + i), y, 0.8, a * 0.9, ang=u * 2.4 * (1 if i % 2 else -1) + i)


def explode(f, t):
    t0, tdec, tand, tex = at("because"), at("decades"), at("and", 2), at("explodes")
    p1 = eio(prog(t, t0 + 0.1, tand - t0 - 0.1))
    age1 = 11 + 44 * p1
    p2 = eio(prog(t, tand, tex - tand))
    age = age1 + 7 * p2
    p3 = eo(prog(t, tex, 0.65))
    age = age + (95 - 62) * p3
    k = eio(prog(t, tand - 0.1, 0.9))
    f.cam(lerp(240 + 260 * p1, 540, k), lerp(1150, 920, k), lerp(1.5, 1.0, k))
    f.dash(96, BASE + 2, 984, BASE + 2, MUTED, 0.45)
    for ag, lab in ((11, "11"), (30, "30"), (50, "50"), (65, "65"), (95, "95")):
        f.text(AX(ag), BASE + 44, lab, 26, WHITE if age >= ag else MUTED, 1 if age >= ag else 0.5, "black")
    f.text(540, BASE + 92, "AGE", 20, MUTED, 0.8, "xb", track=0.3)
    x50, x65 = AX(50), AX(65)
    a50 = eo(prog(t, tand - 0.1, 0.5))
    f.dash(x50, BASE, x50, lerp(BASE - 120, 560, a50), GOLD, 0.65)
    f.pill(x50, 540, "AGE 50", 22, a50, fill=None, outline=GOLD, tc=GOLD_HI, track=0.2)
    f.dash(x65, BASE, x65, 760, MUTED, 0.35)
    for ag in (21, 31, 41, 51):
        if age >= ag:
            f.circ(AX(ag), AY(ag), 6, WHITE, 0.9)
    n = int((age - 11) / 0.5)
    pts = CURVE[:n + 1] + [(AX(age), AY(age))]
    if p3 > 0:
        fill = [(x, y) for x, y in pts if x >= x50]
        if len(fill) > 2:
            f.poly(fill + [(fill[-1][0], BASE), (x50, BASE)], GREEN, 0.16 * p3)
    cols = [WHITE if x < x50 else mixc(WHITE, GREEN, p3 if p3 > 0 else 0.25) for (x, y) in pts[:-1]]
    f.cline(pts, cols, 1, 7)
    hx, hy = pts[-1]
    rays(f, hx, hy, t, eo(prog(t, tex, 0.3)) * (1 - 0.5 * prog(t, tex + 1.5, 1.0)), GREEN)
    f.halo(hx, hy, 90 + 60 * p3, GREEN if p3 > 0 else (200, 210, 240), 0.8)
    f.pawn(hx, hy - 4, 110, WHITE, 1, abs(math.sin(t * 10)) * 6 * (p3 < 1))
    yrs = int(age - 11)
    ya = eo(prog(t, t0 + 0.3, 0.3)) * (1 - prog(t, tex - 0.2, 0.3))
    if yrs >= 1:
        f.pill(hx, hy - 175, f"+{yrs} YEARS", 22, ya, fill=DARKCARD, tc=WHITE, outline=MUTED, track=0.15)
    f.burst(hx, hy - 20, prog(t, tex + 0.05, 1.6), seed=12, n=30, spread=520)
    f.ring(hx, hy, prog(t, tex, 1.0), GREEN_HI, 0.9, rmax=520, w=8)
    rain(f, t, tex + 0.3, eo(prog(t, tex + 0.3, 0.4)))
    for i in range(7):
        sa = math.sin(math.pi * prog(t, tex + 0.2 + 0.13 * i, 0.6))
        f.sparkle(hx - 260 + 80 * i, hy - 140 + 50 * math.sin(i * 1.9), 26 * sa, GOLD_HI, sa)
    pb = prog(t, tex + 0.15, 0.4)
    f.text(285, 700, "99%", 128 * (0.8 + 0.2 * eback(pb)), GREEN, eo(pb), "black")
    f.text(285, 785, "CAME AFTER AGE 50", 21, GREEN_HI, eo(pb), "xb", track=0.12)
    pq = prog(t, tex + 0.45, 0.4)
    f.text(x65 - 14, 1150, "97% AFTER 65", 18, WHITE, eo(pq) * 0.85, "xb", anchor="rm", track=0.12)
    pf = prog(t, tex + 1.3, 0.4)
    f.cam(540, 960, 1.0)
    f.pill(540, 1430, "FOLLOW FOR MORE", 26 * (0.8 + 0.2 * eback(pf)), eo(pf), fill=None, outline=GOLD, tc=GOLD_HI, track=0.2)


def loopback(f, t):
    hook(f, 0.0)


# ------------------------------------------------------------------ timeline
SHOTS = [
    (0.0, at("his", 2) - 0.1, hook, None),
    (at("his", 2) - 0.1, at("he") - 0.08, secret, "zoom"),
    (at("he") - 0.08, at("because") - 0.1, eleven, "whip"),
    (at("because") - 0.1, DUR - 0.7, explode, "zoom"),
    (DUR - 0.7, DUR, loopback, "zoom"),
]
TR = 0.3
SHAKES = [(at("explodes") + 0.02, 0.55, 14), (at("time") + 0.02, 0.3, 5)]
FLASHES = [(at("explodes"), 0.28, 0.45)]
FLASH_C = (235, 245, 238)


def transition(kind, old, new, e):
    if kind == "zoom":
        z = 1.08 - 0.08 * eio(e)
        big = new.resize((int(W * z), int(H * z)), Image.BILINEAR)
        x0, y0 = (big.width - W) // 2, (big.height - H) // 2
        return Image.blend(old, big.crop((x0, y0, x0 + W, y0 + H)), eio(e))
    if kind == "whip":
        off = int(W * eio(e))
        out = Image.new("RGB", (W, H))
        out.paste(old, (-off, 0))
        out.paste(new, (W - off, 0))
        return out.filter(ImageFilter.BoxBlur(int(2 + 22 * math.sin(math.pi * e))))
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
    return post(f.img, t)


def frame(i):
    t = i / FPS
    k = shot_at(t)
    im = draw(k, t)
    a, kind = SHOTS[k][0], SHOTS[k][3]
    if k > 0 and kind and t - a < TR:
        im = transition(kind, draw(k - 1, t), im, (t - a) / TR)
    for t0, dur, kk in FLASHES:
        if t0 <= t < t0 + dur:
            im = Image.blend(im, Image.new("RGB", (W, H), FLASH_C), kk * (1 - (t - t0) / dur) ** 1.5)
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
    f.cam(540, 960, 1.0)
    cx, cy = 540, 760
    f.halo(cx, cy, 360, GOLD, 0.3)
    arc(f, cx, cy, 270, 50, 0, 360, (26, 42, 76), 1)
    arc(f, cx, cy, 270, 50, -88, 264.5, GOLD, 1)
    arc(f, cx, cy, 270, 50, 266.5, 268.8, WHITE, 1)
    f.text(cx, cy, "99%", 150, GOLD_HI, 1, "black")
    f.text(540, 330, "WARREN BUFFETT", 34, MUTED, 1, "xb", track=0.3)
    f.text(540, 1140, "OF HIS MONEY CAME", 60, WHITE, 1, "black")
    f.text(540, 1225, "AFTER AGE 50", 84, GOLD_HI, 1, "black")
    f.pill(540, 1355, "HERE'S WHY", 34, 1, fill=GOLD, tc=NAVY, track=0.2)
    im = post(f.img, 0.0)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((W - 60, 1700), "Moneycheck", font=font("sb", 32), fill=(255, 255, 255, 153), anchor="rm")
    im.save("cover_buffett_99_1080x1920.png")


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

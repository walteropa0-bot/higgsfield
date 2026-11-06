"""Moneycheck Short #11 - "$100 a month at 20 = $500 a month at 40" (about 20 s, viral loop, for young investors).
Female voice (Samara X), no subtitles. 1080x1920, 30 fps. Anchors = exact word times (words.json).
Math: 7% a year, compounded monthly, deposit at the end of each month, until age 60 (illustration, not guaranteed).

Usage:  python3 render13.py stills 1.0 ... | sheet out.png 1 2 ... | cover | video
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


DUR = round(max(20.0, WORDS[-1]["end"] + 1.6), 2)
NF = int(round(DUR * FPS))
DARKCARD = (20, 34, 62)
R = 0.07 / 12


def fv(p, months):
    return 0.0 if months <= 0 else p * ((1 + R) ** months - 1) / R


FV_A = lambda age: fv(100, (age - 20) * 12)
FV_B = lambda age: fv(500, (age - 40) * 12)
FV_C = lambda age: fv(500, (age - 20) * 12)
NOTE = "ASSUMES 7% A YEAR · MONTHLY DEPOSITS · NOT GUARANTEED · BEFORE TAXES & FEES"


def money(v):
    return "$" + format(int(round(v)), ",")


def kfmt(v):
    return f"${v / 1000:.0f}K"


def footnote(f, a=0.8):
    f.text(540, 1460, NOTE, 16, MUTED, a, "sb", track=0.08)


def rays(f, cx, cy, t, a, c=GOLD, n=14, r0=40, r1=900, w=0.07):
    if a <= 0.01:
        return
    for i in range(n):
        g = t * 0.35 + i * 2 * math.pi / n
        f.poly([(cx + math.cos(g) * r0, cy + math.sin(g) * r0), (cx + math.cos(g - w) * r1, cy + math.sin(g - w) * r1),
                (cx + math.cos(g + w) * r1, cy + math.sin(g + w) * r1)], c, 0.09 * a)


# ------------------------------------------------------------------ 1 hook: $100 at 20 = $500 at 40
def side(f, x, age, amount, c, h, a, t, pop=1.0):
    if a <= 0.01:
        return
    f.rect(x - 210, 560, x + 210, 1300, DARKCARD, 0.75 * a, r=34)
    f.rect(x - 210, 560, x + 210, 1300, mixc(MUTED, c, 0.5), 0.55 * a, r=34, w=3)
    f.pill(x, 630, f"AGE {age}", 26, a, fill=None, outline=c, tc=c, track=0.25)
    f.spot(x, 700, 1010, 330, 0.7 * a)
    f.halo(x, 1012, h * 0.8, (130, 150, 200), 0.5 * a, sy=0.15)
    f.pawn(x, 1010, h, WHITE, a, abs(math.sin(t * 3 + x)) * 3)
    f.text(x, 1115, amount, 104 * (0.85 + 0.15 * eback(pop)), c, a, "black")
    f.text(x, 1205, "PER MONTH", 22, WHITE, 0.85 * a, "xb", track=0.25)


def hook(f, t):
    f.cam(540, 930, 1.0 + 0.04 * eio(t / 4.5))
    f.text(540, 380, "INVESTING EVERY MONTH", 26, MUTED, 1, "xb", track=0.28)
    side(f, 280, 20, "$100", GREEN, 140, 1, t, prog(t, at("hundred", 1), 0.35))
    pe = prog(t, at("equals"), 0.35)
    f.text(540, 930, "=", 150 * (0.7 + 0.3 * eback(pe)), GOLD_HI, eo(pe), "black")
    pb = prog(t, at("five", 1) - 0.1, 0.35)
    if pb < 1:
        side(f, 800, 40, "?", MUTED, 165, 0.35 * (1 - eo(pb)), t, 0.0)
    side(f, 800, 40, "$500", GOLD_HI, 165, eo(pb), t, pb)
    ps = prog(t, at("forty", 1) + 0.2, 0.35)
    f.pill(540, 1380, "SAME MONEY AT 60", 30 * (0.75 + 0.25 * eback(ps)), eo(ps), fill=GOLD, tc=NAVY, track=0.18)
    footnote(f, 0.7)


# ------------------------------------------------------------------ 2 the race to 60
CX0, CX1, CB = 140, 940, 1250
AXX = lambda age: CX0 + (age - 20) * (CX1 - CX0) / 40


def chart_axes(f, a=1.0, ages=(20, 30, 40, 50, 60), lit_to=60):
    f.dash(96, CB + 2, 984, CB + 2, MUTED, 0.45 * a)
    for ag in ages:
        lit = ag <= lit_to + 0.01
        f.text(AXX(ag), CB + 44, str(ag), 26, WHITE if lit else MUTED, a * (1 if lit else 0.5), "black")
    f.text(540, CB + 92, "AGE", 20, MUTED, 0.8 * a, "xb", track=0.3)


def curve(fn, a0, a1, scale, top=620):
    pts = []
    n = max(2, int((a1 - a0) * 4) + 1)
    for i in range(n):
        ag = a0 + (a1 - a0) * i / (n - 1)
        pts.append((AXX(ag), CB - fn(ag) / scale * top))
    return pts


def race(f, t):
    t0, t60 = at("both") - 0.1, at("sixty", 2, end=True)
    f.cam(540, 930, 1.0)
    age = 20 + 40 * eio(prog(t, t0 + 0.15, t60 - t0 - 0.25))
    pa = prog(t, t0, 0.3)
    f.pill(540, 360, f"AGE {int(age)}", 40, eo(pa), fill=WHITE, tc=NAVY, track=0.2)
    chart_axes(f, eo(pa), lit_to=age)
    sc = 280000
    if age > 20.05:
        pts = curve(FV_A, 20, age, sc)
        f.line(pts, GREEN, 1, 7)
        hx, hy = pts[-1]
        f.halo(hx, hy, 70, GREEN, 0.8)
        f.pawn(hx, hy - 4, 80, WHITE, 1)
        f.pill(hx - 92, hy - 40, "$100", 20, 1, fill=GREEN, tc=NAVY, track=0.1)
    x40 = AXX(40)
    f.dash(x40, CB, x40, 760, GOLD, 0.5 * eo(prog(t, t0 + 0.3, 0.4)))
    if age > 40.05:
        pts = curve(FV_B, 40, age, sc)
        f.line(pts, GOLD_HI, 1, 7)
        hx, hy = pts[-1]
        f.halo(hx, hy, 70, GOLD, 0.8)
        f.pawn(hx + 16, hy - 4, 92, WHITE, 1)
        f.pill(hx - 96, hy + 48, "$500", 20, 1, fill=GOLD_HI, tc=NAVY, track=0.1)
    else:
        f.pawn(x40, CB, 92, WHITE, 0.55)
        f.pill(x40 + 96, CB - 60, "$500 · WAITS", 18, 0.7 * eo(pa), fill=None, outline=GOLD, tc=GOLD_HI, track=0.1)
    pv = prog(t, t60 - 0.15, 0.4)
    if pv > 0:
        f.ring(AXX(60), CB - FV_A(60) / sc * 620, prog(t, t60 - 0.1, 0.9), GOLD_HI, 0.8, rmax=240)
        f.text(330, 520, "≈ $260K", 96 * (0.8 + 0.2 * eback(pv)), GOLD_HI, eo(pv), "black")
        f.text(330, 600, "BOTH AT 60", 22, WHITE, eo(pv), "xb", track=0.25)
    footnote(f, 0.7)


# ------------------------------------------------------------------ 3 paid in vs compounding
BS = 640 / 280000


def stacked(f, x, paid, grow, c, a, pg, label, tlab):
    if a <= 0.01:
        return
    hp = paid * BS * eo(pg)
    f.rect(x - 110, CB - hp, x + 110, CB, (190, 200, 222), 0.85 * a, r=10)
    if pg > 0.3:
        f.text(x, CB - hp / 2, label, 24, NAVY, a * eo((pg - 0.3) / 0.7), "black")
    hg = grow * BS * eo(tlab)
    if hg > 1:
        f.rect(x - 110, CB - hp - hg, x + 110, CB - hp - 4, c, 0.9 * a, r=10)
        f.halo(x, CB - hp - hg, 120, c, 0.5 * a * eo(tlab), sy=0.4)
        f.text(x, CB - hp - hg / 2, "+" + kfmt(grow), 34, NAVY, a * eo(tlab), "black")


def paid(f, t):
    to, tth, tco = at("one"), at("other"), at("start") - 0.1
    f.cam(540, 930, 1.0)
    f.text(540, 360, "SAME RESULT", 26, MUTED, 1, "xb", track=0.3)
    f.text(540, 445, "DIFFERENT PRICE", 64, WHITE, 1, "black")
    f.dash(96, CB + 2, 984, CB + 2, MUTED, 0.45)
    pa = prog(t, to, 0.6)
    pb = prog(t, tth, 0.6)
    grow = prog(t, tth + 0.7, 0.8)
    stacked(f, 330, 48000, FV_A(60) - 48000, GREEN, 1, pa, "$48K", grow)
    stacked(f, 750, 120000, FV_B(60) - 120000, GOLD_HI, eo(prog(t, tth - 0.2, 0.3)), pb, "$120K", grow)
    f.text(330, CB + 50, "START AT 20", 22, GREEN, 1, "xb", track=0.18)
    f.text(330, CB + 84, "$100/MONTH", 20, WHITE, 0.8, "xb", track=0.15)
    f.text(750, CB + 50, "START AT 40", 22, GOLD_HI, eo(prog(t, tth - 0.2, 0.3)), "xb", track=0.18)
    f.text(750, CB + 84, "$500/MONTH", 20, WHITE, 0.8 * eo(prog(t, tth - 0.2, 0.3)), "xb", track=0.15)
    ly = eo(prog(t, to + 0.2, 0.4))
    f.pill(150, 1060, "YOU PAID", 18, ly, fill=None, outline=MUTED, tc=WHITE, track=0.18)
    lg = eo(grow)
    f.pill(540, 600, "COMPOUND GROWTH", 22, lg, fill=None, outline=GREEN, tc=GREEN_HI, track=0.18)
    footnote(f, 0.7)


# ------------------------------------------------------------------ 4 start at 20 with $500 -> over a million
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


def million(f, t):
    ts, tm = at("start"), at("million")
    f.cam(540, 930, 1.0)
    pp = prog(t, ts - 0.05, 0.35)
    f.pill(540, 360, "$500/MONTH FROM AGE 20", 30 * (0.8 + 0.2 * eback(pp)), eo(pp), fill=GOLD, tc=NAVY, track=0.14)
    age = 20 + 40 * eio(prog(t, ts + 0.2, tm - ts - 0.15))
    sc = lerp(280000, 1450000, eio(prog(t, ts + 0.6, tm - ts - 0.5)))
    chart_axes(f, 1, lit_to=age)
    f.line(curve(FV_A, 20, 60, sc), GREEN, 0.35, 5)
    f.line(curve(FV_B, 40, 60, sc), GOLD_HI, 0.35, 5)
    v = FV_C(age)
    if age > 20.05:
        pts = curve(FV_C, 20, age, sc)
        f.line(pts, GREEN_HI, 1, 8)
        hx, hy = pts[-1]
        rays(f, hx, hy, t, eo(prog(t, tm, 0.3)), GREEN)
        f.halo(hx, hy, 90, GREEN, 0.85)
        f.pawn(hx, hy - 4, 96, WHITE, 1)
        f.burst(hx, hy - 20, prog(t, tm + 0.05, 1.6), seed=12, n=30, spread=520)
        f.ring(hx, hy, prog(t, tm, 1.0), GREEN_HI, 0.9, rmax=520, w=8)
    pc = prog(t, ts + 0.2, 0.3)
    big = prog(t, tm, 0.4)
    f.text(540, 520, money(v), (104 if v < 1e6 else 104 * (0.85 + 0.15 * eback(big))), GREEN if v >= 1e6 else WHITE, eo(pc), "black")
    f.text(540, 600, "AT AGE 60", 22, WHITE, eo(pc) * 0.85, "xb", track=0.25)
    pm = prog(t, tm + 0.2, 0.4)
    f.pill(540, 690, "MILLIONAIRE", 34 * (0.75 + 0.25 * eback(pm)), eo(pm), fill=GREEN, tc=NAVY, track=0.25)
    f.text(800, 1150, "YOU PAID $240K", 20, WHITE, eo(pm) * 0.85, "xb", anchor="mm", track=0.12)
    rain(f, t, tm + 0.3, 0.6 * eo(prog(t, tm + 0.3, 0.4)), n=18)
    f.cam(540, 960, 1.0)
    pe = prog(t, tm + 1.0, 0.4)
    f.pill(320, 930, "START EARLY", 34 * (0.8 + 0.2 * eback(pe)), eo(pe), fill=None, outline=GOLD, tc=GOLD_HI, track=0.25)
    footnote(f, 0.7)


def loopback(f, t):
    hook(f, 0.0)


# ------------------------------------------------------------------ timeline
SHOTS = [
    (0.0, at("both") - 0.1, hook, None),
    (at("both") - 0.1, at("one") - 0.1, race, "zoom"),
    (at("one") - 0.1, at("start") - 0.1, paid, "whip"),
    (at("start") - 0.1, DUR - 0.6, million, "zoom"),
    (DUR - 0.6, DUR, loopback, "zoom"),
]
TR = 0.3
SHAKES = [(at("million") + 0.02, 0.5, 13)]
FLASHES = [(at("million"), 0.25, 0.4)]
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
    f.text(540, 300, "INVESTING EVERY MONTH", 30, MUTED, 1, "xb", track=0.28)
    side(f, 280, 20, "$100", GREEN, 150, 1, 0.0)
    f.text(540, 930, "=", 170, GOLD_HI, 1, "black")
    side(f, 800, 40, "$500", GOLD_HI, 175, 1, 0.0)
    f.text(540, 1400, "SAME MONEY AT 60.", 66, WHITE, 1, "black")
    f.pill(540, 1500, "HERE'S WHY", 32, 1, fill=GOLD, tc=NAVY, track=0.2)
    im = post(f.img, 0.0)
    d = ImageDraw.Draw(im, "RGBA")
    d.text((W - 60, 1700), "Moneycheck", font=font("sb", 32), fill=(255, 255, 255, 153), anchor="rm")
    im.save("cover_100_vs_500_1080x1920.png")


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

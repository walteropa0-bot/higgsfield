"""Moneycheck - animation engine in the cryothum style, in Moneycheck colours (since 8 Nov 2026).

Rules (owner feedback on Video B: animations lagged behind the voice, scene ends looked messy):
- One world, one camera. Stations sit side by side; the camera travels between them. No cross-fades of two
  pictures. A station is fully built when its first word is spoken.
- Hit timing: an element's entrance is finished when its word starts (hit(t, T("word"))), never after it.
- Dot grid in world space (moves with the camera), glowing line-art props, figures ("Maennchen") with arms.
Palette from lib10: navy background, white lines/figures, gold accents, GREEN gains, RED losses.
"""
import json
import math
import re
import subprocess
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from lib10 import (W, H, FPS, SS, F, post, font, clamp, prog, eo, eio, eback, lerp, mixc, qmix, partial, ca,
                   NAVY, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, RED, RED_HI, MINUS)

PANEL = (13, 23, 44)   # fill of cards, windows, icons
LINE = (210, 220, 240)  # line-art strokes
DIM = (64, 80, 114)     # dimmed elements
DOT_C = (50, 66, 104)   # dot grid
SP = 30                 # dot grid spacing (world px)


# ------------------------------------------------------------------ background: gradient + world-space dots
def _grad():
    ys = (np.arange(H * SS, dtype=np.float32) + 0.5) / SS
    xs = (np.arange(W * SS, dtype=np.float32) + 0.5) / SS
    X, Y = np.meshgrid(xs, ys)
    k = np.clip(np.sqrt(((X - W / 2) / W) ** 2 + ((Y - H * 0.46) / H) ** 2) / 0.8, 0, 1) ** 1.35
    img = np.empty((H * SS, W * SS, 3), np.float32)
    for i, (c0, c1) in enumerate(zip((20, 36, 66), (6, 11, 22))):
        img[..., i] = c0 * (1 - k) + c1 * k
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def _dots(zmin=0.8):
    w = int(W * SS / zmin) + 2 * SP * SS
    h = int(H * SS / zmin) + 2 * SP * SS
    xs = np.arange(w, dtype=np.float32) / SS
    ys = np.arange(h, dtype=np.float32) / SS
    dx = SP / 2 - np.abs((xs % SP) - SP / 2)
    dy = SP / 2 - np.abs((ys % SP) - SP / 2)
    d = np.sqrt(dx[None, :] ** 2 + dy[:, None] ** 2)
    return Image.fromarray((np.clip(1.9 - d, 0, 1) * 255).astype(np.uint8), "L")


def _band():
    ys = (np.arange(H * SS, dtype=np.float32) + 0.5) / SS
    b = np.clip(np.minimum((ys - 250) / 240, (1640 - ys) / 240), 0, 1)
    return Image.fromarray((np.repeat(b[:, None], W * SS, 1) * 255).astype(np.uint8), "L")


GRAD, DOTS, BAND = _grad(), _dots(), _band()


class F2(F):
    """lib10 frame with a world camera; the dot grid moves with the camera."""

    def __init__(self, t, cx=W / 2, cy=H / 2, z=1.0):
        self.t = t
        self.cx, self.cy, self.z = cx, cy, z
        self.img = GRAD.copy()
        x0, y0 = cx - W / 2 / z, cy - H / 2 / z
        ox, oy = int(round((x0 % SP) * SS)), int(round((y0 % SP) * SS))
        cw, ch = int(round(W * SS / z)), int(round(H * SS / z))
        m = DOTS.crop((ox, oy, ox + cw, oy + ch))
        if (cw, ch) != (W * SS, H * SS):
            m = m.resize((W * SS, H * SS), Image.BILINEAR)
        self.img.paste(DOT_C, (0, 0, W * SS, H * SS), ImageChops.multiply(m, BAND))
        self.d = ImageDraw.Draw(self.img, "RGBA")


# ------------------------------------------------------------------ timing
def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


class Words:
    """Exact word times from voice_local.py (words.json). T("phrase") = start of the phrase."""

    def __init__(self, path):
        self.w = json.load(open(path, encoding="utf-8"))
        self.n = [norm(x["text"]) for x in self.w]

    def _find(self, phrase, k):
        q = [norm(x) for x in phrase.split() if norm(x)]
        hits = 0
        for i in range(len(self.n) - len(q) + 1):
            if self.n[i:i + len(q)] == q:
                hits += 1
                if hits == k:
                    return i, i + len(q) - 1
        raise KeyError((phrase, k))

    def T(self, phrase, k=1):
        return float(self.w[self._find(phrase, k)[0]]["start"])

    def TE(self, phrase, k=1):
        return float(self.w[self._find(phrase, k)[1]]["end"])

    @property
    def end(self):
        return float(self.w[-1]["end"])


def hit(t, tw, d=0.22):
    """entrance progress 0..1 that is complete exactly when the word at tw starts"""
    return prog(t, tw - d, d)


def ease_cam(p):
    p = clamp(p)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


class Cam:
    """Camera path: start pose, then moves [(t_arrive, (cx, cy, z), duration)]; holds drift slowly."""

    def __init__(self, start, moves, drift=0.012):
        self.keys = [(0.0,) + tuple(start)]
        cur = tuple(start)
        for ta, pose, dur in moves:
            self.keys.append((ta - dur,) + cur)
            self.keys.append((ta,) + tuple(pose))
            cur = tuple(pose)
        self.drift = drift

    def at(self, t):
        ks = self.keys
        for (t0, *a), (t1, *b) in zip(ks, ks[1:]):
            if t <= t1:
                if a == b:  # hold: slow push-in keeps the picture alive
                    z = a[2] * (1 + self.drift * eio((t - t0) / max(t1 - t0, 1e-6)))
                    return a[0], a[1], z
                e = ease_cam((t - t0) / max(t1 - t0, 1e-6))
                return lerp(a[0], b[0], e), lerp(a[1], b[1], e), lerp(a[2], b[2], e)
        return ks[-1][1], ks[-1][2], ks[-1][3]


# ------------------------------------------------------------------ line-art props
def stroke(f, p0, p1, c, a=1.0, w=4):
    if a <= 0.01:
        return
    f.line([p0, p1], c, a, w)
    f.circ(p0[0], p0[1], w / 2, c, a)
    f.circ(p1[0], p1[1], w / 2, c, a)


def box(f, x0, y0, x1, y1, a=1.0, c=LINE, w=3, r=22, fill=PANEL, glow_a=0.16):
    if a <= 0.01:
        return
    bw, bh = x1 - x0, y1 - y0
    m = max(bw, bh)
    if glow_a:
        f.halo((x0 + x1) / 2, (y0 + y1) / 2, m * 0.62, c, glow_a * a, sx=max(0.2, bw / m), sy=max(0.2, bh / m))
    if fill is not None:
        f.rect(x0, y0, x1, y1, fill, a, r=r)
    f.rect(x0, y0, x1, y1, c, a, r=r, w=w)


def card(f, x, y, w, h, title, a=1.0, hh=58, tsize=21):
    """cryothum card: white header strip with spaced caps, dark body"""
    x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
    box(f, x0, y0, x1, y1, a)
    f.rect(x0, y0, x1, y0 + hh, WHITE, a, r=22)
    f.rect(x0, y0 + hh / 2, x1, y0 + hh, WHITE, a)
    f.text(x, y0 + hh / 2 + 1, title, tsize, NAVY, a, "xb", track=0.26)
    return x0, y0 + hh, x1, y1


def check(f, x, y, r, p, a=1.0, ok=True):
    c = WHITE if ok else RED
    e = eo(p)
    f.circ(x, y, r, PANEL, a)
    f.circ(x, y, r, c, a * (0.4 + 0.6 * e), w=3)
    if p <= 0:
        return
    if ok:
        f.line(partial([(x - r * 0.45, y + r * 0.02), (x - r * 0.1, y + r * 0.36), (x + r * 0.48, y - r * 0.34)], e),
               c, a, max(3.0, r * 0.17))
    else:
        k = r * 0.38
        f.line(partial([(x - k, y - k), (x + k, y + k)], clamp(e * 2)), c, a, max(3.0, r * 0.17))
        if e > 0.5:
            f.line(partial([(x + k, y - k), (x - k, y + k)], clamp(e * 2 - 1)), c, a, max(3.0, r * 0.17))


def button(f, x, y, label, size=28, a=1.0, press=0.0, fill=WHITE, tc=NAVY):
    s = 1 - 0.1 * math.sin(math.pi * clamp(press))
    if press > 0:
        f.halo(x, y, size * 3.2, fill, 0.35 * a * math.sin(math.pi * clamp(press)), sy=0.45)
    f.pill(x, y, label, size * s, a, fill=fill, tc=tc, track=0.26, padx=size * 1.25 * s, pady=size * 0.6 * s)


def cursor(f, x, y, a=1.0, s=1.0, press=0.0):
    k = s * (1 - 0.14 * math.sin(math.pi * clamp(press)))
    pts = [(0, 0), (0, 46), (12, 35), (21, 55), (30, 51), (21, 32), (37, 32)]
    P = [(x + px * k, y + py * k) for px, py in pts]
    f.poly(P, WHITE, a)
    f.line(P + [P[0]], NAVY, a, 3)


def toggle(f, x, y, p, a=1.0, s=1.0, label=None):
    w, h = 136 * s, 72 * s
    on = eio(p)
    f.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, mixc(PANEL, (18, 74, 52), on), a, r=h / 2)
    f.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, mixc(LINE, GREEN_HI, on), a, r=h / 2, w=3)
    kx = lerp(x - w / 2 + h / 2, x + w / 2 - h / 2, on)
    if on > 0.05:
        f.halo(kx, y, h * 1.1, GREEN, 0.45 * a * on)
    f.circ(kx, y, h * 0.37, WHITE, a)
    if label:
        f.text(x, y + h * 0.98, label, 19 * s, mixc(MUTED, GREEN_HI, on), a, "xb", track=0.3)


def num(f, x, y, s, size, c, a=1.0, w="black", anchor="m"):
    """text with fixed-width digits: counters do not jitter"""
    if a <= 0.01:
        return
    fnt = font(w, f.L(size))
    dw = max(fnt.getlength(d) for d in "0123456789")
    widths = [dw if ch.isdigit() else fnt.getlength(ch) for ch in s]
    X = f.X(x) - {"l": 0.0, "m": sum(widths) / 2, "r": sum(widths)}[anchor]
    Y = f.Y(y)
    for ch, wd in zip(s, widths):
        f.d.text((X + wd / 2, Y), ch, font=fnt, fill=ca(c, a), anchor="mm")
        X += wd


def money(v):
    return "$" + f"{v:,.0f}"


def statbox(f, x, y, w, h, label, value, a=1.0, vc=WHITE, size=None, c=LINE):
    box(f, x - w / 2, y - h / 2, x + w / 2, y + h / 2, a, c=c)
    f.text(x, y - h / 2 + 30, label, 17, MUTED, a, "xb", track=0.3)
    num(f, x, y + 16, value, size or h * 0.4, vc, a)


def window(f, x, y, w, h, a=1.0, url="", c=LINE):
    x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
    box(f, x0, y0, x1, y1, a, c=c, r=18)
    f.line([(x0, y0 + 50), (x1, y0 + 50)], c, a * 0.7, 2)
    for i in range(3):
        f.circ(x0 + 28 + i * 22, y0 + 25, 6, c, a * 0.8)
    if url:
        f.pill(x + 30, y0 + 25, url, 13, a * 0.85, fill=None, outline=c, tc=c, track=0.3, padx=40, pady=7)
    return x0, y0 + 50, x1, y1


def monitor(f, x, y, w, h, a=1.0):
    box(f, x - w / 2, y - h / 2, x + w / 2, y + h / 2, a, r=14, glow_a=0.24)
    f.rect(x - 13, y + h / 2, x + 13, y + h / 2 + 44, LINE, a, r=4)
    f.rect(x - 86, y + h / 2 + 40, x + 86, y + h / 2 + 52, LINE, a, r=6)
    return x - w / 2 + 16, y - h / 2 + 16, x + w / 2 - 16, y + h / 2 - 16


def desk(f, x, y, w, a=1.0):
    f.rect(x - w / 2, y, x + w / 2, y + 14, LINE, a, r=7)
    for sx in (-1, 1):
        stroke(f, (x + sx * (w / 2 - 34), y + 14), (x + sx * (w / 2 - 34), y + 160), LINE, a, 7)


def building(f, x, yb, w, h, a=1.0, lit=1.0, seed=3, c=LINE):
    box(f, x - w / 2, yb - h, x + w / 2, yb, a, c=c, r=10, glow_a=0.1)
    rng = np.random.default_rng(seed)
    cols, rows = max(2, int(w // 52)), max(2, int((h - 90) // 56))
    for i in range(cols):
        for j in range(rows):
            wx = x - w / 2 + (i + 0.5) * w / cols
            wy = yb - h + 44 + j * 56
            on = rng.random() < 0.6 * lit
            f.rect(wx - 12, wy - 15, wx + 12, wy + 15, GOLD_HI if on else DIM, a * (0.85 if on else 0.55), r=3)
    f.rect(x - 24, yb - 70, x + 24, yb, LINE, a, r=4, w=3)


def phone(f, x, y, s=1.0, a=1.0, c=LINE, lit=0.0):
    w, h = 76 * s, 140 * s
    box(f, x - w / 2, y - h / 2, x + w / 2, y + h / 2, a, c=c, r=15 * s, glow_a=0.14)
    if lit > 0:
        f.rect(x - w / 2 + 8 * s, y - h / 2 + 24 * s, x + w / 2 - 8 * s, y + h / 2 - 22 * s, mixc(PANEL, (40, 70, 130), lit), a, r=6 * s)
    f.rect(x - 14 * s, y - h / 2 + 9 * s, x + 14 * s, y - h / 2 + 15 * s, c, a, r=3 * s)
    f.rect(x - 18 * s, y + h / 2 - 13 * s, x + 18 * s, y + h / 2 - 9 * s, c, a * 0.8, r=2 * s)


def bag(f, x, y, s=1.0, a=1.0, c=LINE):
    w, h = 98 * s, 96 * s
    top = y - h / 2 + 22 * s
    pts = [(x - w / 2, top), (x + w / 2, top), (x + w * 0.46, y + h / 2), (x - w * 0.46, y + h / 2)]
    f.poly(pts, PANEL, a)
    f.line(pts + [pts[0]], c, a, 3)
    f.arc(x, top, 25 * s, 180, 360, c, a, 3)


def shoe(f, x, y, s=1.0, a=1.0, c=LINE):
    pts = [(-62, 12), (-62, -18), (-40, -22), (-22, -48), (6, -48), (12, -30), (42, -22), (64, -6), (64, 12)]
    P = [(x + px * s, y + py * s) for px, py in pts]
    f.poly(P, PANEL, a)
    f.line(P + [P[0]], c, a, 3)
    f.line([(x - 62 * s, y + 2 * s), (x + 64 * s, y + 2 * s)], c, a * 0.7, 2)
    for i in range(3):
        f.line([(x - 12 * s + i * 12 * s, y - 40 * s + i * 7 * s), (x + 2 * s + i * 12 * s, y - 34 * s + i * 7 * s)], c, a * 0.8, 2)


def bubble(f, x, y, ch, s=1.0, a=1.0, c=WHITE):
    r = 32 * s
    f.poly([(x - r * 0.55, y + r * 0.6), (x - r * 0.95, y + r * 1.35), (x - r * 0.05, y + r * 0.85)], PANEL, a)
    f.line([(x - r * 0.55, y + r * 0.74), (x - r * 0.95, y + r * 1.35), (x - r * 0.12, y + r * 0.92)], c, a, 3)
    f.circ(x, y, r, PANEL, a)
    f.circ(x, y, r, c, a, w=3)
    f.text(x, y + 2 * s, ch, 36 * s, c, a, "black")


def chart(f, x0, y0, x1, y1, vals, p, a=1.0, c=GREEN, fill=True, w=5, vmin=None, vmax=None, head=True):
    if a <= 0.01 or p <= 0:
        return None
    vmin = min(vals) if vmin is None else vmin
    vmax = max(vals) if vmax is None else vmax
    n = len(vals)
    pts = [(lerp(x0, x1, i / (n - 1)), y1 - (v - vmin) / max(vmax - vmin, 1e-9) * (y1 - y0)) for i, v in enumerate(vals)]
    seg = partial(pts, p)
    if fill and len(seg) > 1:
        f.poly(seg + [(seg[-1][0], y1), (seg[0][0], y1)], c, 0.13 * a)
    f.line(seg, c, a, w)
    hx, hy = seg[-1]
    if head:
        f.halo(hx, hy, 46, c, 0.65 * a)
        f.circ(hx, hy, w * 1.5, WHITE, a)
    return hx, hy


def notif(f, x, y, title, value, p, a=1.0, c=GREEN_HI, w=430, h=88):
    e = eo(p)
    if e <= 0.01:
        return
    xx, aa = x + (1 - e) * 130, a * e
    box(f, xx - w / 2, y - h / 2, xx + w / 2, y + h / 2, aa, r=20, glow_a=0.22)
    f.circ(xx - w / 2 + 46, y, 24, c, aa)
    f.text(xx - w / 2 + 46, y + 1, "$", 26, NAVY, aa, "black")
    f.text(xx - w / 2 + 86, y - 15, title, 15, MUTED, aa, "xb", "lm", track=0.28)
    f.text(xx - w / 2 + 86, y + 16, value, 29, c, aa, "black", "lm")


def ground(f, x0, x1, y, a=1.0):
    f.dash(x0, y, x1, y, MUTED, 0.4 * a, w=2)


def guy(f, x, y, h, c=WHITE, a=1.0, bob=0.0, arms=None, t=0.0, spot=0.0, label=None, ring=0.0):
    """pawn figure with optional arms: 'up' (cheer), 'side', 'point', 'hip'; spotlight, label, gold ring"""
    if a <= 0.01:
        return
    if spot > 0:
        f.spot(x, y - h * 3.3, y + 16, h * 3.1, spot * a)
    f.halo(x, y + 2, h * 0.8, (130, 150, 200), 0.45 * a, sy=0.15)
    if ring > 0:
        f.halo(x, y + 2, h * 0.9, GOLD, 0.35 * ring * a, sy=0.18)
        f.ell(x, y + 2, h * 0.62 * (0.8 + 0.2 * ring), h * 0.13, GOLD_HI, ring * a, w=4)
    yb = y - bob
    if arms:
        sh = yb - 0.47 * h
        wv = 0.06 * h * math.sin(t * 9)
        hands = {"up": [(x - 0.55 * h, yb - 1.0 * h + wv), (x + 0.55 * h, yb - 1.0 * h - wv)],
                 "side": [(x - 0.48 * h, yb - 0.2 * h), (x + 0.48 * h, yb - 0.2 * h)],
                 "point": [(x - 0.4 * h, yb - 0.16 * h), (x + 0.78 * h, yb - 0.66 * h)],
                 "hip": [(x - 0.5 * h, yb - 0.36 * h), (x + 0.5 * h, yb - 0.36 * h)]}[arms]
        for sx, hp in zip((-1, 1), hands):
            stroke(f, (x + sx * 0.25 * h, sh), hp, c, a, 0.13 * h)
    f.pawn(x, y, h, c, a, bob)
    if label:
        f.text(x, y + 44, label, 21, WHITE, 0.9 * a, "xb", track=0.32)


def headline(f, t, t_in, t_out, draw, d_in=0.2, d_out=0.14, rise=36):
    """screen-space element: slides up and fades in, finished exactly at t_in; leaves (finished) at t_out.
    Use t_out before the next camera move and t_in at the first word of the next station -> no overlaps."""
    if t < t_in - d_in or t > t_out:
        return
    pin = eo(prog(t, t_in - d_in, d_in))
    pout = eio(prog(t, t_out - d_out, d_out))
    a = pin * (1 - pout)
    if a > 0.01:
        draw(f, a, (1 - pin) * rise - pout * rise * 0.8)


def paste_world(f, im, x, y):
    """paste an RGBA image prepared at SS scale for zoom 1, centred at world (x, y)"""
    z = f.z
    w, h = im.size
    if abs(z - 1.0) > 0.002:
        im = im.resize((max(1, int(round(w * z))), max(1, int(round(h * z)))), Image.BILINEAR)
    X0, Y0 = int(round(f.X(x) - im.width / 2)), int(round(f.Y(y) - im.height / 2))
    f.img.paste(im, (X0, Y0), im)


# ------------------------------------------------------------------ chrome, frame, render
def chrome(im, t, dur, footnote=""):
    d = ImageDraw.Draw(im, "RGBA")
    x0, x1, y = 90, 990, 205
    d.rounded_rectangle((x0, y, x1, y + 8), radius=4, fill=(28, 40, 68, 255))
    xe = x0 + (x1 - x0) * clamp(t / dur)
    if xe > x0 + 8:
        d.rounded_rectangle((x0, y, xe, y + 8), radius=4, fill=GOLD + (255,))
    if footnote:
        fnt = font("xb", 15)
        tot = sum(fnt.getlength(ch) for ch in footnote) + 0.28 * fnt.size * (len(footnote) - 1)
        x = W / 2 - tot / 2
        for ch in footnote:
            d.text((x, 1640), ch, font=fnt, fill=(140, 155, 185, 150), anchor="lm")
            x += fnt.getlength(ch) + 0.28 * fnt.size
    d.text((60, 1700), "Not financial advice · educational only", font=font("sb", 26), fill=(140, 155, 185, 190), anchor="lm")
    d.text((W - 60, 1700), "Moneycheck", font=font("sb", 32), fill=(255, 255, 255, 153), anchor="rm")


class Video:
    """stations: list of (x_min, x_max, draw(f, t)) in world coordinates; shakes: (t0, dur, amp)"""

    def __init__(self, dur, cam, stations, shakes=(), flashes=(), footnote=lambda t: "", tint=lambda t: None,
                 overlay=None):
        self.dur, self.cam, self.stations = dur, cam, stations
        self.shakes, self.flashes, self.footnote, self.tint = shakes, flashes, footnote, tint
        self.overlay = overlay
        self.nf = int(round(dur * FPS))

    def frame(self, i, chrome_on=True):
        t = i / FPS
        cx, cy, z = self.cam.at(t)
        for t0, d, amp in self.shakes:
            if t0 <= t < t0 + d:
                q = 1 - (t - t0) / d
                cx += amp * q * math.sin(t * 71) / z
                cy += amp * 0.6 * q * math.cos(t * 53) / z
        f = F2(t, cx, cy, z)
        half = W / 2 / z + 60
        for x_min, x_max, draw in self.stations:
            if x_max >= cx - half and x_min <= cx + half:
                draw(f, t)
        if self.overlay:
            f.cam(W / 2, H / 2, 1.0)  # screen space: headlines, big numbers
            self.overlay(f, t)
        im = post(f.img, t, tint=self.tint(t))
        for t0, d, k in self.flashes:
            if t0 <= t < t0 + d:
                im = Image.blend(im, Image.new("RGB", (W, H), (235, 242, 255)), k * (1 - (t - t0) / d))
        if chrome_on:
            chrome(im, t, self.dur, self.footnote(t))
        return im


_V = None


def _fb(i):
    return _V.frame(i).tobytes()


def _thumb(ts):
    return _V.frame(int(round(ts * FPS))).resize((360, 640), Image.LANCZOS)


def render(video, out):
    global _V
    _V = video
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for b in pool.imap(_fb, range(video.nf), chunksize=4):
            ff.stdin.write(b)
    ff.stdin.close()
    ff.wait()


def sheet(video, out, times):
    global _V
    _V = video
    with Pool(4) as pool:
        th = pool.map(_thumb, times)
    cols = 6
    rows = (len(th) + cols - 1) // cols
    sh = Image.new("RGB", (cols * 360, rows * 640))
    d = ImageDraw.Draw(sh)
    for i, (im, ts) in enumerate(zip(th, times)):
        sh.paste(im, ((i % cols) * 360, (i // cols) * 640))
        d.text(((i % cols) * 360 + 8, (i // cols) * 640 + 8), f"{ts:.2f}", font=font("xb", 26), fill=(255, 255, 0))
    sh.save(out)

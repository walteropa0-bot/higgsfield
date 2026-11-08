"""Moneycheck landscape engine (16:9) for long-form YouTube videos (first used in YT01).

- design space 1920x1080, drawn at 2x (3840x2160) with the lib10 primitives (true alpha, round joins, pawn sprites)
- output 2560x1440 (LANCZOS from the 2x canvas): YouTube serves 1440p uploads with a better codec than 1080p
- post(): bloom on bright elements + fine film grain (also prevents colour banding), optional vignette tint
- scenes: [(t0, t1, fn)] with cross-fades; fn(f, t, a, lt) draws with alpha a (lt = time since scene start)
"""
import math
import subprocess
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

import lib10
from lib10 import (FPS, SS, font, clamp, prog, eo, eio, eback, lerp, mixc, qmix, ca, partial, _lut,  # noqa: F401
                   NAVY, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, RED, RED_HI, MINUS)

W, H = 1920, 1080
OW, OH = 2560, 1440
K = OW / W
DARKCARD = (20, 34, 62)
DARKCARD2 = (28, 45, 80)
FADE = 0.38


# ------------------------------------------------------------------ static textures (landscape)
def _bg():
    ys = (np.arange(H * SS, dtype=np.float32) + 0.5) / SS
    xs = (np.arange(W * SS, dtype=np.float32) + 0.5) / SS
    X, Y = np.meshgrid(xs, ys)
    k = np.clip(np.sqrt(((X - W / 2) / W) ** 2 + ((Y - H * 0.45) / H) ** 2) / 0.78, 0, 1) ** 1.35
    img = np.empty((H * SS, W * SS, 3), np.float32)
    for i, (c0, c1) in enumerate(zip((20, 36, 66), (6, 11, 22))):
        img[..., i] = c0 * (1 - k) + c1 * k
    del k
    band = np.clip(np.minimum(np.minimum((Y - 40) / 170, (H - 40 - Y) / 170),
                              np.minimum((X - 40) / 260, (W - 40 - X) / 260)), 0, 1)
    dx = 15 - np.abs((X % 30) - 15)
    dy = 15 - np.abs((Y % 30) - 15)
    dot = np.clip(1.9 - np.sqrt(dx * dx + dy * dy), 0, 1) * band
    for i, v in enumerate((26, 36, 58)):
        img[..., i] += dot * v
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


BG = _bg()


def _vig():
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    d = np.sqrt(((xx - OW / 2) / (OW * 0.6)) ** 2 + ((yy - OH / 2) / (OH * 0.62)) ** 2)
    return Image.fromarray((np.clip((d - 0.5) / 0.65, 0, 1) ** 1.2 * 255).astype(np.uint8), "L")


VIG = _vig()
_rng = np.random.default_rng(16)
# one static grain layer: still breaks up colour banding, but costs the encoder nothing (changing grain every frame
# made x264 the bottleneck at 1440p and pushed the bitrate past 19 Mbit/s)
GRAIN = [_rng.normal(0, 1.6, (OH, OW, 1)).astype(np.float32)]


# ------------------------------------------------------------------ frame
class F(lib10.F):
    """lib10 frame with a landscape canvas and camera"""

    def __init__(self, t):
        self.t = t
        self.img = BG.copy()
        self.d = ImageDraw.Draw(self.img, "RGBA")
        self.cx, self.cy, self.z = W / 2, H / 2, 1.0

    def cam(self, cx=W / 2, cy=H / 2, z=1.0):
        self.cx, self.cy, self.z = cx, cy, z

    def X(self, x):
        return ((x - self.cx) * self.z + W / 2) * SS

    def Y(self, y):
        return ((y - self.cy) * self.z + H / 2) * SS


def post(img2x, t, bloom=0.55, tint=None):
    im = img2x.resize((OW, OH), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    sm = np.asarray(im.resize((OW // 4, OH // 4), Image.BILINEAR), np.float32)
    k = np.clip((sm.max(axis=2, keepdims=True) - 105) / 120, 0, 1)
    bs = Image.fromarray((sm * k).astype(np.uint8))
    b1 = np.asarray(bs.filter(ImageFilter.GaussianBlur(4)).resize((OW, OH), Image.BILINEAR), np.float32)
    b2 = np.asarray(bs.filter(ImageFilter.GaussianBlur(16)).resize((OW, OH), Image.BILINEAR), np.float32)
    out = a + (b1 * 0.55 + b2 * 0.6) * bloom + GRAIN[int(round(t * FPS)) % len(GRAIN)]
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if tint is not None and tint[1] > 0.01:
        res.paste(tint[0], (0, 0, OW, OH), VIG.point(_lut(tint[1])))
    return res


def watermark(im):
    d = ImageDraw.Draw(im, "RGBA")
    d.text((OW - 44 * K, OH - 38 * K), "Moneycheck", font=font("sb", 26 * K), fill=(255, 255, 255, 153), anchor="rs")


# ------------------------------------------------------------------ composer
def scene_alpha(t, t0, t1, first, last):
    a = 1.0 if first else eio(prog(t, t0, FADE))
    if not last:
        a *= 1 - eio(prog(t, t1 - FADE, FADE))
    return a


def compose(t, scenes, overlay=None):
    f = F(t)
    n = len(scenes)
    for i, (t0, t1, fn) in enumerate(scenes):
        if t < t0 - 0.001 or t > t1 + 0.001:
            continue
        a = scene_alpha(t, t0, t1, i == 0, i == n - 1)
        if a > 0.004:
            f.cam()
            fn(f, t, a, t - t0)
    if overlay:
        f.cam()
        overlay(f, t)
    return f


def render_frame(t, scenes, overlay=None, shakes=(), flashes=(), tint=None):
    f = compose(t, scenes, overlay)
    im = post(f.img, t, tint=tint(t) if tint else None)
    for t0, d, kk in flashes:
        if t0 <= t < t0 + d:
            im = Image.blend(im, Image.new("RGB", (OW, OH), (235, 245, 238)), kk * (1 - (t - t0) / d) ** 1.5)
    for t0, d, amp in shakes:
        if t0 <= t < t0 + d:
            q = 1 - (t - t0) / d
            im = ImageChops.offset(im, int(amp * K * q * math.sin(t * 71)), int(amp * K * 0.6 * q * math.cos(t * 53)))
    watermark(im)
    return im


# ------------------------------------------------------------------ typography (landscape)
def kline(f, x, y, s, size, c, t, t0, a=1.0, w="black", dur=0.45, rise=24, track=0.0, anchor="mm"):
    p = prog(t, t0, dur)
    if p <= 0 or a <= 0.01:
        return
    f.text(x, y + rise * (1 - eo(p)), s, size * (0.92 + 0.08 * eback(p)), c, a * eo(p), w, anchor=anchor, track=track)


def kwords(f, x, y, parts, size, t, t0, a=1.0, step=0.08, w="black", anchor="m"):
    """word-by-word pop; parts = [(text, colour), ...]; anchor 'm' centres on x, 'l' starts at x"""
    words = [(wd, c) for s, c in parts for wd in s.split()]
    sp = f.twidth(" ", size, w)
    ws = [f.twidth(wd, size, w) for wd, _ in words]
    tot = sum(ws) + sp * (len(ws) - 1)
    x0 = x - tot / 2 if anchor == "m" else x
    for i, ((wd, c), ww) in enumerate(zip(words, ws)):
        p = prog(t, t0 + i * step, 0.32)
        if p > 0 and a > 0.01:
            f.text(x0 + ww / 2, y + 20 * (1 - eo(p)), wd, size * (0.9 + 0.1 * eback(p)), c, a * eo(p), w)
        x0 += ww + sp


def label(f, x, y, s, size, a=1.0, c=GOLD, fill=None, tc=None, track=0.22):
    f.pill(x, y, s, size, a, fill=fill, outline=c if fill is None else None, tc=tc or (GOLD_HI if c == GOLD else c),
           track=track)


def money(v, dec=0):
    return "$" + f"{v:,.{dec}f}"


# ------------------------------------------------------------------ props
def figure(f, x, y, h, a=1.0, c=WHITE, ring=0.0, bob=0.0, spot=0.0, tie=None):
    if a <= 0.01:
        return
    if spot > 0:
        f.spot(x, y - h * 3.2, y + 14, h * 3.0, spot * a)
    f.halo(x, y + 2, h * 0.8, (130, 150, 200), 0.45 * a, sy=0.15)
    if ring > 0:
        f.halo(x, y + 2, h * 0.9, GOLD, 0.35 * ring * a, sy=0.18)
        f.ell(x, y + 2, h * 0.6, h * 0.13, GOLD_HI, ring * a, w=4)
    f.pawn(x, y, h, c, a, bob)
    if tie:
        ty = y - bob - 0.5 * h
        f.poly([(x - 0.06 * h, ty), (x + 0.06 * h, ty), (x + 0.04 * h, ty + 0.26 * h), (x, ty + 0.32 * h),
                (x - 0.04 * h, ty + 0.26 * h)], tie, a)


def rays(f, cx, cy, t, a, c=GOLD, n=16, r0=40, r1=1300, w=0.06):
    if a <= 0.01:
        return
    for i in range(n):
        g = t * 0.3 + i * 2 * math.pi / n
        f.poly([(cx + math.cos(g) * r0, cy + math.sin(g) * r0), (cx + math.cos(g - w) * r1, cy + math.sin(g - w) * r1),
                (cx + math.cos(g + w) * r1, cy + math.sin(g + w) * r1)], c, 0.08 * a)


def card(f, x0, y0, x1, y1, a=1.0, c=DARKCARD, edge=None, r=22, glow=None):
    if a <= 0.01:
        return
    if glow:
        f.halo((x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) * 0.55, glow, 0.25 * a, sy=(y1 - y0) / max(1, x1 - x0))
    f.rect(x0, y0, x1, y1, c, 0.92 * a, r=r)
    if edge:
        f.rect(x0, y0, x1, y1, edge, a, r=r, w=3)


def bar(f, x, base, w, h, c, a=1.0, top=None, tc=WHITE, tsize=40, r=10):
    if a <= 0.01 or h <= 0.5:
        return
    f.rect(x - w / 2, base - h, x + w / 2, base, c, 0.28 * a, r=r)
    f.rect(x - w / 2, base - h, x + w / 2, base, c, 0.95 * a, r=r, w=3)
    f.rect(x - w / 2, base - h, x + w / 2, base - h + 9, c, a, r=4)
    f.halo(x, base - h, w * 0.7, c, 0.3 * a, sy=0.35)
    if top:
        f.text(x, base - h - 36, top, tsize, tc, a, "black")


def hbar(f, x, y, w, h, c, a=1.0, r=10):
    if a <= 0.01 or w <= 0.5:
        return
    f.rect(x, y - h / 2, x + w, y + h / 2, c, 0.28 * a, r=r)
    f.rect(x, y - h / 2, x + w, y + h / 2, c, 0.95 * a, r=r, w=3)
    f.rect(x + w - 9, y - h / 2, x + w, y + h / 2, c, a, r=4)


def arrow(f, x0, y0, x1, y1, c, a=1.0, w=6, head=22):
    if a <= 0.01:
        return
    ang = math.atan2(y1 - y0, x1 - x0)
    bx, by = x1 - math.cos(ang) * head * 0.8, y1 - math.sin(ang) * head * 0.8
    f.line([(x0, y0), (bx, by)], c, a, w)
    f.poly([(x1, y1), (x1 - math.cos(ang - 0.45) * head, y1 - math.sin(ang - 0.45) * head),
            (x1 - math.cos(ang + 0.45) * head, y1 - math.sin(ang + 0.45) * head)], c, a)


# ------------------------------------------------------------------ main helpers
def contact_sheet(thumbs, times, out, cols=5, tw=480, th=270):
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th))
    d = ImageDraw.Draw(sheet)
    for i, (im, ts) in enumerate(zip(thumbs, times)):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), ((i % cols) * tw, (i // cols) * th))
        d.text(((i % cols) * tw + 6, (i // cols) * th + 4), f"{ts:.1f}", font=font("xb", 22), fill=(255, 255, 0))
    sheet.save(out)


def encode(frame_bytes_fn, nf, out, procs=4, crf=16, preset="fast"):
    # 'slow' needed ~1.6 of the 4 cores at 1440p and starved the frame workers; 'fast' at crf 16 looks the same here
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(procs) as pool:
        for i, b in enumerate(pool.imap(frame_bytes_fn, range(nf), chunksize=6)):
            ff.stdin.write(b)
            if i % 900 == 0:
                print(f"frame {i}/{nf}", flush=True)
    ff.stdin.close()
    ff.wait()

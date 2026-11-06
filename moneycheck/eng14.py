"""Moneycheck engine for short text-driven videos (no voice), output 1440x2560.

- drawing: lib10 (2x supersampled canvas in 1080x1920 design units, true alpha, bloom)
- output: LANCZOS down to 1440x2560 (sharper than 1080p), bloom + grain at output size
- beats: [(t0, t1, fn)], fn(f, t, a, lt) draws with alpha a (cross-fades between beats on one canvas)
- loop: the last LOOP seconds fade back into beat 0 at lt=0 (first frame == last frame)
- sound: event list -> mix -> two-pass loudnorm -14 LUFS -> mux with the video
"""
import math
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from lib10 import (W, H, FPS, SS, F, font, clamp, prog, eo, eio, eback, lerp, mixc, qmix, partial, ca, _lut,
                   NAVY, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI, RED, RED_HI, MINUS)

OW, OH = 1440, 2560
K = OW / W
DARKCARD = (20, 34, 62)
FLASH_C = (235, 245, 238)
FADE = 0.32
LOOP = 0.55

_rng = np.random.default_rng(21)
GRAIN = [_rng.normal(0, 2.0, (OH, OW, 1)).astype(np.float32) for _ in range(5)]


def _vig():
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    d = np.sqrt(((xx - OW / 2) / (OW * 0.62)) ** 2 + ((yy - OH / 2) / (OH * 0.6)) ** 2)
    return Image.fromarray((np.clip((d - 0.5) / 0.65, 0, 1) ** 1.2 * 255).astype(np.uint8), "L")


VIG = _vig()


def post(img2x, t, bloom=0.6, tint=None):
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


def chrome(im, t, dur):
    d = ImageDraw.Draw(im, "RGBA")
    x0, x1, y = 90 * K, 990 * K, 205 * K
    d.rounded_rectangle((x0, y, x1, y + 8 * K), radius=4 * K, fill=(28, 40, 68, 255))
    xe = x0 + (x1 - x0) * clamp(t / dur)
    if xe > x0 + 8 * K:
        d.rounded_rectangle((x0, y, xe, y + 8 * K), radius=4 * K, fill=GOLD + (255,))
    d.text((60 * K, 1700 * K), "Not financial advice · educational only", font=font("sb", 26 * K),
           fill=(140, 155, 185, 190), anchor="lm")
    d.text((OW - 60 * K, 1700 * K), "Moneycheck", font=font("sb", 32 * K), fill=(255, 255, 255, 153), anchor="rm")


# ------------------------------------------------------------------ beat helpers
def beat_alpha(t, t0, t1, first=False, last=False):
    a = 1.0 if first else eio(prog(t, t0, FADE))
    if not last:
        a *= 1 - eio(prog(t, t1 - FADE, FADE))
    return a


def compose(t, beats, dur, persistent=None):
    """draw all visible beats on one canvas; returns the lib10 frame"""
    f = F(t)
    n = len(beats)
    for i, (t0, t1, fn) in enumerate(beats):
        if t < t0 - 0.001 or t > t1 + 0.001:
            continue
        a = beat_alpha(t, t0, t1, first=(i == 0), last=(i == n - 1))
        if i == n - 1:
            a *= 1 - eio(prog(t, dur - LOOP, LOOP * 0.5))
        if a > 0.005:
            fn(f, t, a, t - t0)
    lp = eo(prog(t, dur - LOOP * 0.5, LOOP * 0.5 - 1.0 / FPS))
    if lp > 0:
        beats[0][2](f, 0.0, lp, 0.0)
    if persistent:
        f.cam()
        persistent(f, t)
    return f


def frame(i, beats, dur, persistent=None, shakes=(), flashes=(), tint=None):
    t = i / FPS
    f = compose(t, beats, dur, persistent)
    im = post(f.img, t, tint=tint(t) if tint else None)
    for t0, d, kk in flashes:
        if t0 <= t < t0 + d:
            im = Image.blend(im, Image.new("RGB", (OW, OH), FLASH_C), kk * (1 - (t - t0) / d) ** 1.5)
    for t0, d, amp in shakes:
        if t0 <= t < t0 + d:
            q = 1 - (t - t0) / d
            im = ImageChops.offset(im, int(amp * K * q * math.sin(t * 71)), int(amp * K * 0.6 * q * math.cos(t * 53)))
    chrome(im, t, dur)
    return im


# ------------------------------------------------------------------ typography
def kline(f, x, y, s, size, c, t, t0, a=1.0, w="black", dur=0.4, rise=28, track=0.0, anchor="mm"):
    p = prog(t, t0, dur)
    if p <= 0 or a <= 0.01:
        return
    f.text(x, y + rise * (1 - eo(p)), s, size * (0.9 + 0.1 * eback(p)), c, a * eo(p), w, anchor=anchor, track=track)


def kwords(f, x, y, parts, size, t, t0, a=1.0, step=0.09, w="black"):
    """word-by-word pop, centred on x. parts = [(text, colour), ...] (each text may hold several words)"""
    words = [(wd, c) for s, c in parts for wd in s.split()]
    sp = f.twidth(" ", size, w)
    ws = [f.twidth(wd, size, w) for wd, _ in words]
    x0 = x - (sum(ws) + sp * (len(ws) - 1)) / 2
    for i, ((wd, c), ww) in enumerate(zip(words, ws)):
        p = prog(t, t0 + i * step, 0.3)
        if p > 0 and a > 0.01:
            f.text(x0 + ww / 2, y + 22 * (1 - eo(p)), wd, size * (0.88 + 0.12 * eback(p)), c, a * eo(p), w)
        x0 += ww + sp


def topic(f, s, a=1.0, c=GOLD):
    f.pill(540, 300, s, 24, a, fill=None, outline=c, tc=GOLD_HI if c == GOLD else c, track=0.25)


def footnote(f, s, a=0.75):
    f.text(540, 1462, s, 15, MUTED, a, "sb", track=0.08)


def follow(f, t, t0, a=1.0, y=1385):
    f.cam()
    p = prog(t, t0, 0.4)
    f.pill(540, y, "FOLLOW FOR MORE", 24 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=None, outline=GOLD, tc=GOLD_HI, track=0.22)


def money(v):
    return "$" + format(int(round(v)), ",")


# ------------------------------------------------------------------ props
def rays(f, cx, cy, t, a, c=GOLD, n=14, r0=40, r1=900, w=0.07):
    if a <= 0.01:
        return
    for i in range(n):
        g = t * 0.35 + i * 2 * math.pi / n
        f.poly([(cx + math.cos(g) * r0, cy + math.sin(g) * r0), (cx + math.cos(g - w) * r1, cy + math.sin(g - w) * r1),
                (cx + math.cos(g + w) * r1, cy + math.sin(g + w) * r1)], c, 0.09 * a)


def rain(f, t, t0, a=1.0, n=20, seed=9):
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
        if y < 2000:
            f.bill(x0 + 40 * math.sin(u * 3 + i), y, 0.8, a * 0.75, ang=u * 2.4 * (1 if i % 2 else -1) + i)


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


def bar(f, x, base, w, h, c, a=1.0, label=None, lc=NAVY, top=None, tc=WHITE, tsize=40):
    if a <= 0.01 or h <= 0.5:
        return
    f.rect(x - w / 2, base - h, x + w / 2, base, c, 0.3 * a, r=12)
    f.rect(x - w / 2, base - h, x + w / 2, base, c, 0.95 * a, r=12, w=3)
    f.rect(x - w / 2, base - h, x + w / 2, base - h + 10, c, a, r=5)
    f.halo(x, base - h, w * 0.7, c, 0.35 * a, sy=0.35)
    if top:
        f.text(x, base - h - 46, top, tsize, tc, a, "black")


def phone(f, x, y, s, a, c=WHITE, screen=None):
    if a <= 0.01:
        return
    w, h = 150 * s, 290 * s
    f.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, DARKCARD, a, r=26 * s)
    f.rect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, c, a, r=26 * s, w=5 * s)
    f.rect(x - w / 2 + 12 * s, y - h / 2 + 40 * s, x + w / 2 - 12 * s, y + h / 2 - 50 * s, screen or (30, 48, 86), a, r=6 * s)
    f.circ(x, y + h / 2 - 25 * s, 12 * s, c, a, w=3 * s)
    f.line([(x - 18 * s, y - h / 2 + 20 * s), (x + 18 * s, y - h / 2 + 20 * s)], c, a, 4 * s)


# ------------------------------------------------------------------ sound
def mix(events, dur, out="sfx.wav"):
    from sfx import _env
    from sfx3 import SFX, SR

    def coin_p(freq=2093, d=0.45):
        n = int(SR * d)
        tt = np.arange(n) / SR
        x = (np.sin(2 * np.pi * freq * tt) + 0.55 * np.sin(2 * np.pi * freq * 1.26 * tt) * (tt > 0.05)) * np.exp(-tt * 10)
        return (x / np.abs(x).max() * 0.4 * _env(n, 0.001)).astype(np.float32)

    buf = np.zeros(int(SR * dur), np.float32)
    cache = {}
    for t, name, g, *kw in events:
        key = (name, tuple(kw))
        if key not in cache:
            cache[key] = coin_p(float(kw[0])) if name == "coin_p" else SFX[name]()
        s = cache[key]
        i0 = int(t * SR)
        n = min(len(s), len(buf) - i0)
        if n > 0 and i0 >= 0:
            buf[i0:i0 + n] += s[:n] * g
    raw = np.clip(buf / max(1e-6, np.abs(buf).max()) * 0.9, -1, 1).tobytes()
    meas = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af",
                           "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          input=raw, capture_output=True).stderr.decode()
    import json
    m = json.loads(meas[meas.rindex("{"):])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", af,
                    "-ar", "48000", "-ac", "2", out], input=raw, check=True)


# ------------------------------------------------------------------ main
def main(argv, fb, thumb, nf, name, cover_fn, events, dur):
    mode = argv[1]
    if mode == "sheet":
        times = [float(x) for x in argv[3:]]
        with Pool(4) as pool:
            th = pool.map(thumb, times)
        cols = 6
        rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 360, rows * 640))
        d = ImageDraw.Draw(sheet)
        for i, (im, ts) in enumerate(zip(th, times)):
            sheet.paste(im, ((i % cols) * 360, (i // cols) * 640))
            d.text(((i % cols) * 360 + 8, (i // cols) * 640 + 8), f"{ts:.1f}", font=font("xb", 28), fill=(255, 255, 0))
        sheet.save(argv[2])
    elif mode == "cover":
        cover_fn()
    else:
        vid = f"{name}_video.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt",
                               "yuv420p", "-movflags", "+faststart", vid], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for b in pool.imap(fb, range(nf), chunksize=4):
                ff.stdin.write(b)
        ff.stdin.close()
        ff.wait()
        mix(events, dur, f"{name}_sfx.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", f"{name}_sfx.wav", "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                        "-movflags", "+faststart", f"moneycheck_{name}.mp4"], check=True)
        print("done", name)

"""Moneycheck - premium drawing library (first used in Short #8).

- everything is drawn at 2x (SS) with true alpha blending and box-downsampled -> smooth, anti-aliased lines
- a per-frame camera maps world coordinates (1080x1920 design space) to the screen, with zoom
- post(): bloom (soft glow on bright elements) + fine film grain (also prevents colour banding)
Palette: navy background, white figures/lines, gold accents, GREEN money/gains, RED losses.
"""
import functools
import math
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SS = 1080, 1920, 30, 2


def _fc(q):
    return subprocess.check_output(["fc-match", "-f", "%{file}", q]).decode()


FONTS = {"black": _fc("Inter:style=Black"), "xb": _fc("Inter:style=ExtraBold"), "sb": _fc("Inter:style=SemiBold")}


@functools.lru_cache(maxsize=4096)
def font(w, px):
    return ImageFont.truetype(FONTS[w], max(6, int(round(px))))


NAVY = (11, 20, 38)
WHITE = (245, 247, 250)
MUTED = (140, 155, 185)
GOLD = (212, 175, 55)
GOLD_HI = (245, 215, 110)
GREEN = (46, 204, 113)
GREEN_HI = (120, 250, 170)
RED = (239, 83, 80)
RED_HI = (255, 140, 130)
MINUS = "−"


# ------------------------------------------------------------------ easing / helpers
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def prog(t, t0, d):
    if d <= 0:
        return 1.0 if t >= t0 else 0.0
    return clamp((t - t0) / d)


def eo(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def eio(p):
    p = clamp(p)
    return p * p * (3 - 2 * p)


def eback(p):
    p = clamp(p)
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


def lerp(a, b, p):
    return a + (b - a) * p


def mixc(c1, c2, p):
    p = clamp(p)
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * p)) for i in range(3))


def qmix(c1, c2, p, steps=8):
    """colour mix, quantised (keeps the figure-sprite cache small)"""
    return mixc(c1, c2, round(clamp(p) * steps) / steps)


def ca(c, a):
    return (int(c[0]), int(c[1]), int(c[2]), int(round(255 * clamp(a))))


def partial(pts, p):
    """polyline cut at fraction p of its length; segment i of the result = segment i of pts."""
    if p >= 1:
        return list(pts)
    seg = [math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:])]
    target = sum(seg) * clamp(p)
    out = [pts[0]]
    acc = 0.0
    for i, L in enumerate(seg):
        if acc + L >= target:
            u = (target - acc) / L if L > 0 else 0.0
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            out.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
            return out
        acc += L
        out.append(pts[i + 1])
    return out


# ------------------------------------------------------------------ static textures
def _bg():
    ys = (np.arange(H * SS, dtype=np.float32) + 0.5) / SS
    xs = (np.arange(W * SS, dtype=np.float32) + 0.5) / SS
    X, Y = np.meshgrid(xs, ys)
    k = np.clip(np.sqrt(((X - W / 2) / W) ** 2 + ((Y - H * 0.46) / H) ** 2) / 0.8, 0, 1) ** 1.35
    img = np.empty((H * SS, W * SS, 3), np.float32)
    for i, (c0, c1) in enumerate(zip((20, 36, 66), (6, 11, 22))):
        img[..., i] = c0 * (1 - k) + c1 * k
    del k
    band = np.clip(np.minimum((Y - 250) / 240, (1640 - Y) / 240), 0, 1)
    dx = 15 - np.abs((X % 30) - 15)
    dy = 15 - np.abs((Y % 30) - 15)
    dot = np.clip(1.9 - np.sqrt(dx * dx + dy * dy), 0, 1) * band
    for i, v in enumerate((30, 40, 64)):
        img[..., i] += dot * v
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


BG2 = _bg()


def _vig():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.6)) ** 2)
    return Image.fromarray((np.clip((d - 0.5) / 0.65, 0, 1) ** 1.2 * 255).astype(np.uint8), "L")


VIG = _vig()
_rng = np.random.default_rng(11)
GRAIN = [_rng.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(6)]


@functools.lru_cache(maxsize=1)
def _gauss():
    g = np.linspace(-1, 1, 256, dtype=np.float32)
    m = np.exp(-(g[None, :] ** 2 + g[:, None] ** 2) / 0.13)
    return Image.fromarray((m * 255).astype(np.uint8), "L")


@functools.lru_cache(maxsize=1)
def _cone():
    w, h = 240, 480
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = yy / h
    half = (0.12 + 0.38 * v) * w
    edge = np.clip((half - np.abs(xx - w / 2)) / (0.16 * w), 0, 1)
    inten = (0.5 + 0.5 * v) * np.clip(v / 0.18, 0, 1) * np.clip((1 - v) / 0.1, 0, 1)
    return Image.fromarray((edge * inten * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(5))


@functools.lru_cache(maxsize=320)
def _pawn(hp, c):
    """glowing pawn figure (round head, rounded body), hp px tall. returns sprite + anchor (bottom centre)."""
    s = 3
    hh = hp * s
    wpad = int(hp * 0.75) * s
    im = Image.new("L", (wpad * 2, int(hp * 1.38) * s), 0)
    d = ImageDraw.Draw(im)
    cx, by = wpad, int(hp * 1.2) * s
    bw, bh = 0.62 * hh, 0.56 * hh
    d.rounded_rectangle((cx - bw / 2, by - bh, cx + bw / 2, by), radius=bw / 2, fill=255)
    d.rectangle((cx - bw / 2, by - bh * 0.45, cx + bw / 2, by), fill=255)
    r = 0.19 * hh
    hy = by - bh - r * 1.25
    d.ellipse((cx - r, hy - r, cx + r, hy + r), fill=255)
    m = im.resize((im.width // s, im.height // s), Image.LANCZOS)
    g = np.asarray(m.filter(ImageFilter.GaussianBlur(max(1.0, hp * 0.14))), np.float32) / 255 * 0.42
    mm = np.asarray(m, np.float32) / 255
    al = np.clip(np.maximum(mm, g), 0, 1)
    shade = np.linspace(1.0, 0.88, mm.shape[0], dtype=np.float32)[:, None, None]
    rgb = np.ones(mm.shape + (3,), np.float32) * np.array(c, np.float32) * shade
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8), "RGBA"), (wpad // s, by // s)


def _lut(a):
    a = clamp(a)
    return [int(v * a) for v in range(256)]


# ------------------------------------------------------------------ frame + drawing
class F:
    def __init__(self, t):
        self.t = t
        self.img = BG2.copy()
        self.d = ImageDraw.Draw(self.img, "RGBA")
        self.cx, self.cy, self.z = W / 2, H / 2, 1.0

    def cam(self, cx=W / 2, cy=H / 2, z=1.0):
        self.cx, self.cy, self.z = cx, cy, z

    def X(self, x):
        return ((x - self.cx) * self.z + W / 2) * SS

    def Y(self, y):
        return ((y - self.cy) * self.z + H / 2) * SS

    def P(self, x, y):
        return (self.X(x), self.Y(y))

    def L(self, v):
        return v * self.z * SS

    def wpx(self, w):
        return max(1, int(round(self.L(w))))

    # --- primitives
    def line(self, pts, c, a=1.0, w=4):
        if a <= 0.01 or len(pts) < 2:
            return
        self.d.line([self.P(x, y) for x, y in pts], fill=ca(c, a), width=self.wpx(w), joint="curve")

    def cline(self, pts, cols, a=1.0, w=5):
        """polyline with one colour per segment and round joins"""
        if a <= 0.01 or len(pts) < 2:
            return
        r = self.L(w) / 2
        q = [self.P(x, y) for x, y in pts]
        c0 = cols[0]
        self.d.ellipse((q[0][0] - r, q[0][1] - r, q[0][0] + r, q[0][1] + r), fill=ca(c0, a))
        for i in range(len(q) - 1):
            c = cols[min(i, len(cols) - 1)]
            self.d.line([q[i], q[i + 1]], fill=ca(c, a), width=self.wpx(w))
            self.d.ellipse((q[i + 1][0] - r, q[i + 1][1] - r, q[i + 1][0] + r, q[i + 1][1] + r), fill=ca(c, a))

    def dash(self, x0, y0, x1, y1, c, a=1.0, w=2, on=14, off=10, phase=0.0):
        if a <= 0.01:
            return
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 1:
            return
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        s = -(phase % (on + off))
        while s < L:
            a0, b0 = max(0.0, s), min(L, s + on)
            if b0 > a0:
                self.d.line([self.P(x0 + ux * a0, y0 + uy * a0), self.P(x0 + ux * b0, y0 + uy * b0)],
                            fill=ca(c, a), width=self.wpx(w))
            s += on + off

    def circ(self, x, y, r, c, a=1.0, w=0):
        if a <= 0.01 or r <= 0:
            return
        X, Y, R = self.X(x), self.Y(y), self.L(r)
        if w:
            self.d.ellipse((X - R, Y - R, X + R, Y + R), outline=ca(c, a), width=self.wpx(w))
        else:
            self.d.ellipse((X - R, Y - R, X + R, Y + R), fill=ca(c, a))

    def ell(self, x, y, rx, ry, c, a=1.0, w=0):
        if a <= 0.01:
            return
        X, Y, RX, RY = self.X(x), self.Y(y), self.L(rx), self.L(ry)
        if w:
            self.d.ellipse((X - RX, Y - RY, X + RX, Y + RY), outline=ca(c, a), width=self.wpx(w))
        else:
            self.d.ellipse((X - RX, Y - RY, X + RX, Y + RY), fill=ca(c, a))

    def arc(self, x, y, r, a0, a1, c, a=1.0, w=4):
        if a <= 0.01:
            return
        X, Y, R = self.X(x), self.Y(y), self.L(r)
        self.d.arc((X - R, Y - R, X + R, Y + R), a0, a1, fill=ca(c, a), width=self.wpx(w))

    def rect(self, x0, y0, x1, y1, c, a=1.0, r=0, w=0):
        if a <= 0.01:
            return
        box = (self.X(x0), self.Y(y0), self.X(x1), self.Y(y1))
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            return
        rr = min(self.L(r), (box[2] - box[0]) / 2, (box[3] - box[1]) / 2)
        if w:
            self.d.rounded_rectangle(box, radius=rr, outline=ca(c, a), width=self.wpx(w))
        else:
            self.d.rounded_rectangle(box, radius=rr, fill=ca(c, a))

    def poly(self, pts, c, a=1.0):
        if a <= 0.01 or len(pts) < 3:
            return
        self.d.polygon([self.P(x, y) for x, y in pts], fill=ca(c, a))

    # --- text
    def text(self, x, y, s, size, c, a=1.0, w="xb", anchor="mm", track=0.0):
        if a <= 0.01 or not s or size <= 1:
            return
        f = font(w, self.L(size))
        if not track:
            self.d.text(self.P(x, y), s, font=f, fill=ca(c, a), anchor=anchor)
            return
        ws = [f.getlength(ch) for ch in s]
        sp = track * f.size
        tot = sum(ws) + sp * (len(s) - 1)
        X = self.X(x) - {"l": 0.0, "m": tot / 2, "r": tot}[anchor[0]]
        Y = self.Y(y)
        for ch, wd in zip(s, ws):
            self.d.text((X, Y), ch, font=f, fill=ca(c, a), anchor="l" + anchor[1])
            X += wd + sp

    def twidth(self, s, size, w="xb", track=0.0):
        f = font(w, self.L(size))
        ws = [f.getlength(ch) for ch in s] if track else [f.getlength(s)]
        tot = sum(ws) + (track * f.size * (len(s) - 1) if track else 0)
        return tot / (self.z * SS)

    def pill(self, x, y, s, size=24, a=1.0, fill=WHITE, tc=NAVY, outline=None, track=0.16, w="xb", padx=None, pady=None):
        """cryothum-style label: rounded pill with letter-spaced caps"""
        if a <= 0.01 or size <= 2:
            return
        padx = size * 0.95 if padx is None else padx
        pady = size * 0.5 if pady is None else pady
        bw = self.twidth(s, size, w, track) + 2 * padx
        bh = size + 2 * pady
        box = (x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2)
        if fill is not None:
            self.rect(*box, fill, a, r=bh / 2)
        if outline is not None:
            self.rect(*box, outline, a, r=bh / 2, w=max(2.0, size * 0.1))
        self.text(x, y, s, size, tc, a, w, "mm", track)

    # --- light
    def halo(self, x, y, r, c, a=1.0, sx=1.0, sy=1.0):
        if a <= 0.01 or r <= 0:
            return
        R = self.L(r)
        wp, hp = max(2, int(2 * R * sx)), max(2, int(2 * R * sy))
        if wp > 3 * W * SS or hp > 3 * H * SS:
            return
        m = _gauss().resize((wp, hp), Image.BILINEAR)
        if a < 0.999:
            m = m.point(_lut(a))
        X0, Y0 = int(self.X(x) - wp / 2), int(self.Y(y) - hp / 2)
        self.img.paste(tuple(int(v) for v in c), (X0, Y0, X0 + wp, Y0 + hp), m)

    def spot(self, x, ytop, ybot, wbot, a=1.0, c=(185, 200, 240)):
        if a <= 0.01:
            return
        wp, hp = max(2, int(self.L(wbot))), max(2, int(self.L(ybot - ytop)))
        m = _cone().resize((wp, hp), Image.BILINEAR).point(_lut(0.3 * a))
        X0, Y0 = int(self.X(x) - wp / 2), int(self.Y(ytop))
        self.img.paste(c, (X0, Y0, X0 + wp, Y0 + hp), m)

    # --- figures & props
    def pawn(self, x, y, h, c=WHITE, a=1.0, bob=0.0):
        if a <= 0.01:
            return
        hp = int(round(self.L(h)))
        if hp < 8:
            return
        sp, (ax, ay) = _pawn(hp, tuple(int(v) for v in c))
        if a < 0.99:
            sp = sp.copy()
            sp.putalpha(sp.getchannel("A").point(_lut(a)))
        self.img.paste(sp, (int(round(self.X(x) - ax)), int(round(self.Y(y - bob) - ay))), sp)

    def coin(self, x, y, r, a=1.0, spin=0.0):
        if a <= 0.01:
            return
        sx = max(0.12, abs(math.cos(spin)))
        X, Y, R = self.X(x), self.Y(y), self.L(r)
        self.d.ellipse((X - R * sx, Y - R, X + R * sx, Y + R), fill=ca((170, 132, 28), a))
        self.d.ellipse((X - R * sx * 0.88, Y - R * 0.88, X + R * sx * 0.88, Y + R * 0.88), fill=ca(GOLD, a))
        self.d.ellipse((X - R * sx * 0.66, Y - R * 0.66, X + R * sx * 0.66, Y + R * 0.66),
                       outline=ca(GOLD_HI, a), width=max(1, int(R * 0.09)))
        if sx > 0.5:
            self.d.text((X, Y), "$", font=font("black", R * 1.05), fill=ca((118, 86, 12), a), anchor="mm")

    def bill(self, x, y, s=1.0, a=1.0, ang=0.0):
        if a <= 0.01:
            return
        w, h = 110 * s, 54 * s
        c, sn = math.cos(ang), math.sin(ang)

        def rp(px, py):
            return self.P(x + px * c - py * sn, y + px * sn + py * c)

        self.d.polygon([rp(-w / 2, -h / 2), rp(w / 2, -h / 2), rp(w / 2, h / 2), rp(-w / 2, h / 2)], fill=ca((30, 146, 82), a))
        m = 6 * s
        self.d.polygon([rp(-w / 2 + m, -h / 2 + m), rp(w / 2 - m, -h / 2 + m), rp(w / 2 - m, h / 2 - m), rp(-w / 2 + m, h / 2 - m)],
                       outline=ca(GREEN_HI, a * 0.8), width=max(1, int(self.L(2))))
        X, Y = rp(0, 0)
        R = self.L(14 * s)
        self.d.ellipse((X - R, Y - R, X + R, Y + R), fill=ca(GREEN, a))
        self.d.text((X, Y), "$", font=font("black", R * 1.3), fill=ca((12, 70, 40), a), anchor="mm")

    def burst(self, cx, cy, p, seed=1, n=20, spread=420, grav=900, a=1.0, scale=1.0, kinds="cbb"):
        if p <= 0 or p >= 1 or a <= 0.01:
            return
        rng = np.random.default_rng(seed)
        for i in range(n):
            ang = rng.uniform(-math.pi * 0.92, -math.pi * 0.08)
            sp = rng.uniform(0.45, 1.0) * spread * 1.6
            r0 = rng.uniform(-1, 1)
            tt = p * 1.1
            x = cx + math.cos(ang) * sp * tt
            y = cy + math.sin(ang) * sp * tt + 0.5 * grav * tt * tt
            aa = a * clamp((1 - p) * 2.2)
            if kinds[i % len(kinds)] == "c":
                self.coin(x, y, 15 * scale, aa, spin=r0 * 6 + p * 14)
            else:
                self.bill(x, y, 0.62 * scale, aa, ang=r0 + p * 5 * (1 if i % 2 else -1))

    def sparkle(self, x, y, r, c=GOLD_HI, a=1.0):
        if a <= 0.01 or r <= 0:
            return
        k = 0.2
        self.poly([(x, y - r), (x + r * k, y - r * k), (x + r, y), (x + r * k, y + r * k), (x, y + r),
                   (x - r * k, y + r * k), (x - r, y), (x - r * k, y - r * k)], c, a)

    def ring(self, x, y, p, c, a=1.0, rmax=300, w=6):
        if 0 < p < 1:
            self.circ(x, y, rmax * eo(p), c, a * (1 - p), w=max(1.0, w * (1 - 0.6 * p)))

    def flag(self, x, y, a=1.0, t=0.0, c=GOLD, h=150, fw=96):
        if a <= 0.01:
            return
        self.line([(x, y), (x, y - h)], WHITE, a, 5)
        top = [(x + fw * i / 8, y - h + 7 * math.sin(t * 6 + i / 2) * i / 8) for i in range(9)]
        bot = [(px, py + fw * 0.6) for px, py in reversed(top)]
        self.poly(top + bot, c, a)

    def stopwatch(self, x, y, r, a=1.0, ang=0.0, c=WHITE):
        if a <= 0.01:
            return
        self.circ(x, y, r, c, a, w=5)
        self.rect(x - 13, y - r - 24, x + 13, y - r - 11, c, a, r=4)
        self.line([(x, y - r - 12), (x, y - r)], c, a, 5)
        for i in range(12):
            q = i / 12 * 2 * math.pi
            self.line([(x + math.sin(q) * r * 0.76, y - math.cos(q) * r * 0.76),
                       (x + math.sin(q) * r * 0.88, y - math.cos(q) * r * 0.88)], c, a * 0.6, 3)
        self.line([(x, y), (x + math.sin(ang) * r * 0.68, y - math.cos(ang) * r * 0.68)], GOLD_HI, a, 5)
        self.circ(x, y, 6, GOLD_HI, a)


# ------------------------------------------------------------------ post
def post(img2x, t, bloom=0.6, tint=None):
    im = img2x.reduce(SS)
    a = np.asarray(im, np.float32)
    sm = np.asarray(im.resize((W // 4, H // 4), Image.BILINEAR), np.float32)
    k = np.clip((sm.max(axis=2, keepdims=True) - 105) / 120, 0, 1)
    bs = Image.fromarray((sm * k).astype(np.uint8))
    b1 = np.asarray(bs.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR), np.float32)
    b2 = np.asarray(bs.filter(ImageFilter.GaussianBlur(12)).resize((W, H), Image.BILINEAR), np.float32)
    out = a + (b1 * 0.55 + b2 * 0.6) * bloom + GRAIN[int(round(t * FPS)) % len(GRAIN)]
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if tint is not None and tint[1] > 0.01:
        res.paste(tint[0], (0, 0, W, H), VIG.point(_lut(tint[1])))
    return res

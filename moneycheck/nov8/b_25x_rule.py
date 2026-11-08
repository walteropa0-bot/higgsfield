"""Nov 8 · Video B (female voice, ~25 s): "How much money do you need to stop working?" -> spending x 25 (the 4% rule).

Voice: Kokoro (local), text in b_script.txt. Every beat and sound hangs on words of the script (T("phrase")):
with b_words.json (speech-recognition word times) the real word times are used, without it an estimate (preview).
Facts: 25 = 1 / 4%. Bengen (1994, Journal of Financial Planning): 4% inflation-adjusted withdrawals survived every
rolling 30-year period in US data 1926-1992 (stocks/bonds mix). Trinity study (Cooley, Hubbard & Walz, AAII Journal 1998):
high success rates for 30-year periods at 4% with stock-heavy portfolios. Rule of thumb, not a guarantee.

python3 b_25x_rule.py sheet out.png t1 t2 ... | cover | video   (run inside an output folder)
"""
import difflib
import json
import math
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import eng14 as E  # noqa: E402
from eng14 import (FPS, prog, eo, eio, eback, lerp, mixc, partial, WHITE, MUTED, GOLD, GOLD_HI, GREEN, GREEN_HI,  # noqa: E402
                   NAVY, RED, RED_HI, DARKCARD, kline, kwords, footnote, follow, figure, rays, rain, money)
from PIL import Image, ImageDraw  # noqa: E402

NAME = "25x_rule"
SCRIPT = open(os.path.join(HERE, "b_script.txt"), encoding="utf-8").read().split()
VOICE = os.path.join(HERE, "b_voice.mp3")
WORDS = os.path.join(HERE, "b_words.json")


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


TOK = [norm(w) for w in SCRIPT]


def _estimate():
    st, en, t = [], [], 0.35
    for w in SCRIPT:
        d = 0.058 * len(norm(w)) + 0.085
        st.append(t)
        en.append(t + d)
        t += d + (0.42 if w.endswith((".", "?", "!")) else 0.17 if w.endswith(",") else 0.0)
    k = (len(" ".join(SCRIPT)) / 15.6) / t
    return [s * k for s in st], [e * k for e in en]


def _from_words():
    words = [w for w in json.load(open(WORDS)) if norm(w["text"])]
    b = [norm(w["text"]) for w in words]
    st, en = [None] * len(TOK), [None] * len(TOK)
    for blk in difflib.SequenceMatcher(None, TOK, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            st[blk.a + k], en[blk.a + k] = words[blk.b + k]["start"], words[blk.b + k]["end"]
    for i in range(len(TOK)):  # fill gaps (numbers spoken vs transcribed differently) by neighbours
        if st[i] is None:
            j = max([k for k in range(i) if st[k] is not None], default=None)
            m = min([k for k in range(i + 1, len(TOK)) if st[k] is not None], default=None)
            t0 = en[j] if j is not None else 0.0
            t1 = st[m] if m is not None else t0 + 0.4
            n_gap = (m if m is not None else len(TOK)) - (j if j is not None else -1) - 1
            pos = i - (j if j is not None else -1)
            st[i] = t0 + (t1 - t0) * (pos - 1) / max(1, n_gap)
            en[i] = t0 + (t1 - t0) * pos / max(1, n_gap)
    return st, en


HAVE_VOICE = os.path.exists(WORDS) and os.path.exists(VOICE)
ST, EN = _from_words() if HAVE_VOICE else _estimate()
DUR = round(EN[-1] + 1.3, 2)
NF = int(DUR * FPS)


def T(phrase, n=1):
    q = [norm(w) for w in phrase.split() if norm(w)]
    hits = 0
    for i in range(len(TOK) - len(q) + 1):
        if TOK[i:i + len(q)] == q:
            hits += 1
            if hits == n:
                return ST[i]
    raise KeyError(phrase)


# ------------------------------------------------------------------ props
def receipt(f, x, y, a, p, lt):
    rows = [("RENT", 18000), ("FOOD", 7200), ("CAR", 6000), ("BILLS", 4800), ("FUN", 4000)]
    h = 120 + 64 * len(rows) * eo(p)
    f.rect(x - 210, y - 40, x + 210, y - 40 + h, (236, 238, 244), a, r=10)
    for k in range(9):
        f.poly([(x - 210 + k * 46.6, y - 40 + h), (x - 186.7 + k * 46.6, y - 22 + h), (x - 163.4 + k * 46.6, y - 40 + h)],
               (236, 238, 244), a)
    f.text(x, y, "MY YEAR", 30, NAVY, a, "black", track=0.2)
    for i, (s, v) in enumerate(rows):
        q = prog(lt, 0.15 + 0.16 * i, 0.25) * (p > 0)
        yy = y + 64 + i * 58
        f.text(x - 180, yy, s, 28, NAVY, a * eo(q), "black", anchor="lm", track=0.06)
        f.text(x + 180, yy, money(v), 28, (60, 70, 92), a * eo(q), "black", anchor="rm")
    tq = prog(lt, 1.1, 0.3)
    f.line([(x - 180, y + 64 + len(rows) * 58 - 22), (x + 180, y + 64 + len(rows) * 58 - 22)], (150, 160, 180), a * eo(tq), 3)
    f.text(x - 180, y + 64 + len(rows) * 58 + 16, "TOTAL", 30, NAVY, a * eo(tq), "black", anchor="lm", track=0.08)
    f.text(x + 180, y + 64 + len(rows) * 58 + 16, "$40,000", 34, (20, 120, 70), a * eo(tq), "black", anchor="rm")


def money_pile(f, x, base, w, h, a, c=GOLD):
    rows = int(h / 34)
    for r in range(rows):
        k = max(1, int((w / 112) * (1 - r / (rows + 2))))
        for c_ in range(k):
            xx = x + (c_ - (k - 1) / 2) * 112
            yy = base - 18 - r * 34
            f.rect(xx - 52, yy - 15, xx + 52, yy + 15, c, a, r=5)
            f.rect(xx - 44, yy - 10, xx + 44, yy - 4, GOLD_HI, a * 0.9, r=3)


# ------------------------------------------------------------------ beats (start times come from the words)
def b0(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 3.0))
    kline(f, 540, 360, "HOW MUCH MONEY", 80, WHITE, lt, -1, a)
    kline(f, 540, 460, "DO YOU NEED TO", 80, WHITE, lt, -1, a)
    kline(f, 540, 575, "STOP WORKING?", 104, GOLD_HI, lt, -1, a)
    money_pile(f, 600, 1180, 560, 300, a)
    f.halo(600, 1040, 300, GOLD, 0.25 * a)
    q = 1 + 0.05 * math.sin(lt * 5)
    f.text(600, 920, "?", 200 * q, NAVY, a, "black")
    f.text(600, 900, "?", 200 * q, WHITE, a, "black")
    figure(f, 230, 1180, 150, a, tie=GOLD, bob=abs(math.sin(lt * 3)) * 4)


def b1(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 340, "YOUR YEARLY SPENDING", 60, WHITE, lt, 0.0, a)
    t25 = T("multiply it by twenty-five.") - (T("Take what you spend") - 0.25)
    p = prog(lt, 0.2, 0.6)
    receipt(f, 540 - 180 * eio(prog(lt, t25, 0.5)), 470, a, p, lt)
    q = prog(lt, t25, 0.45)
    if q > 0:
        f.halo(770, 690, 240, GOLD, 0.5 * a * eo(q))
        f.text(770, 690, "× 25", 160 * (0.7 + 0.3 * eback(q)), GOLD_HI, a * eo(q), "black")


def b2(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 4.0))
    kline(f, 540, 360, "SPEND $40,000 A YEAR?", 66, WHITE, lt, 0.0, a)
    kline(f, 540, 470, "$40,000 × 25 =", 74, MUTED, lt, 0.4, a)
    tn = T("Your number is") - (T("Spend forty thousand") - 0.25)
    p = prog(lt, tn, 1.2)
    v = 1_000_000 * eio(p)
    f.text(540, 640, money(v), 150 * (0.9 + 0.1 * eback(prog(lt, tn, 0.5))), GREEN_HI if p >= 1 else WHITE,
           a * eo(prog(lt, tn, 0.3)), "black")
    f.pill(540, 780, "YOUR NUMBER", 34, a * eo(prog(lt, tn + 1.0, 0.4)), fill=GOLD, tc=NAVY, track=0.2)
    g = 0.25 + 0.75 * eio(prog(lt, tn, 1.2))
    money_pile(f, 540, 1290, 700 * g * eo(prog(lt, 0.2, 0.5)), 330 * g, a)
    f.burst(540, 1000, prog(lt, tn + 1.15, 1.4), seed=7, n=22, spread=480, a=a)


def b3(f, t, a, lt):
    f.cam(540, 900, 1.0)
    kline(f, 540, 400, "WHY 25?", 110, WHITE, lt, 0.0, a)
    t4 = T("It's the four percent rule.") - (T("Why twenty-five?") - 0.25)
    kwords(f, 540, 600, [("1", WHITE), ("÷", MUTED), ("25", GOLD_HI), ("=", MUTED), ("4%", GREEN_HI)], 120, lt, 0.5, a, step=0.12)
    p = prog(lt, t4, 0.45)
    f.pill(540, 800, "THE 4% RULE", 56 * (0.8 + 0.2 * eback(p)), a * eo(p), fill=GOLD, tc=NAVY, track=0.16)
    rays(f, 540, 800, t, a * eo(p) * 0.8)


def b4(f, t, a, lt):
    f.cam(540, 900, 1.0)
    t0 = T("In a famous study,") - 0.25
    tw = T("withdrawing four percent") - t0
    ti = T("then adjusting for inflation,") - t0
    tl_ = T("lasted at least thirty years") - t0
    pc = eo(prog(lt, 0.0, 0.4)) * (1 - eio(prog(lt, tw + 0.3, 0.5)))
    if pc > 0.01:
        f.rect(240, 330, 840, 520, (236, 238, 244), a * pc, r=14)
        f.rect(240, 330, 840, 376, GOLD, a * pc, r=14)
        f.rect(240, 360, 840, 376, GOLD, a * pc)
        f.text(540, 354, "TRINITY STUDY · 1998", 24, NAVY, a * pc, "black", track=0.16)
        f.text(540, 430, "RETIREMENT WITHDRAWALS,", 30, NAVY, a * pc, "black")
        f.text(540, 474, "U.S. DATA SINCE 1926", 30, NAVY, a * pc, "black")
    pw = eio(prog(lt, tw, 0.5))
    if pw > 0:
        yrs = 30 * clamp01((lt - tw - 0.4) / max(0.5, tl_ - tw + 0.6))
        f.text(540, 360, f"YEAR {max(1, int(yrs) + 1) if yrs < 30 else 30}", 70, WHITE, a * pw, "black")
        kline(f, 540, 450, "TAKE 4%, THEN + INFLATION", 36, GOLD_HI, lt, tw + 0.2, a, w="black", track=0.06)
        h = 300 * (1 + 0.12 * math.sin(yrs * 0.9) + 0.006 * yrs)
        money_pile(f, 470, 1250, 560, h, a * pw)
        for k in range(4):
            u = ((lt * 1.6) + k / 4) % 1.0
            if lt > tw + 0.4:
                f.coin(lerp(620, 860, u), lerp(1080 - h * 0.4, 1150, u) - 120 * math.sin(math.pi * u), 22, a * pw, spin=u * 9)
        figure(f, 900, 1250, 130, a * pw, ring=0.6)
        f.text(900, 1300, "$40K/YR + INFLATION", 22, GREEN_HI, a * pw, "black", track=0.06)
    pl = prog(lt, tl_, 0.45)
    if pl > 0:
        f.halo(540, 640, 260, GREEN, 0.45 * a * eo(pl))
        f.text(540, 620, "30+ YEARS", 130 * (0.8 + 0.2 * eback(pl)), GREEN_HI, a * eo(pl), "black")
        kline(f, 540, 730, "IN MOST HISTORICAL CASES", 34, WHITE, lt, tl_ + 0.5, a, w="black", track=0.08)


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def b5(f, t, a, lt):
    f.cam(540, 900, 1.0 + 0.03 * eio(lt / 2.5))
    kline(f, 540, 430, "WHAT'S YOUR", 92, WHITE, lt, 0.0, a)
    kline(f, 540, 540, "NUMBER?", 120, GOLD_HI, lt, 0.2, a)
    f.pill(540, 690, "YEARLY SPENDING × 25", 40, a * eo(prog(lt, 0.4, 0.4)), fill=None, outline=GOLD, tc=GOLD_HI, track=0.14)
    money_pile(f, 540, 1200, 620, 260, a)
    follow(f, lt, 0.8, a)


def beats():
    s = [0.0, T("Take what you spend") - 0.25, T("Spend forty thousand") - 0.25, T("Why twenty-five?") - 0.25,
         T("In a famous study,") - 0.25, T("So, what's your number?") - 0.25, DUR]
    fns = [b0, b1, b2, b3, b4, b5]
    return [(s[i], s[i + 1] + (E.FADE if i < 5 else 0.0), fns[i]) for i in range(6)]


BEATS = beats()
SHAKES = [(T("multiply it by twenty-five.") + 0.05, 0.35, 8), (T("Your number is") + 1.2, 0.35, 6)]
FLASHES = [(T("multiply it by twenty-five.") + 0.05, 0.18, 0.22)]


def persistent(f, t):
    footnote(f, "RULE OF THUMB · BENGEN (1994), TRINITY STUDY (1998): U.S. DATA, 30-YEAR PERIODS · NOT GUARANTEED")


def fb(i):
    return E.frame(i, BEATS, DUR, persistent, SHAKES, FLASHES).tobytes()


def thumb(ts):
    return E.frame(int(round(ts * FPS)), BEATS, DUR, persistent, SHAKES, FLASHES).resize((360, 640), Image.LANCZOS)


def cover():
    # Zähler steht nach „Your number is“ + 1.2 s bei 1.000.000; bei +1.3 s hat der Geldregen das Label noch nicht erreicht
    f = E.compose(T("Your number is") + 1.3, BEATS, DUR, persistent)
    im = E.post(f.img, 0.0)
    ImageDraw.Draw(im, "RGBA").text((E.OW - 60 * E.K, 1700 * E.K), "Moneycheck", font=E.font("sb", 32 * E.K),
                                    fill=(255, 255, 255, 153), anchor="rm")
    im.save(f"cover_{NAME}.png")


def events():
    ev = [(0.0, "bass", 0.5), (0.05, "pop", 0.4), (0.4, "pop", 0.35)]
    tb = BEATS[1][0]
    ev += [(tb, "whoosh", 0.45)] + [(tb + 0.4 + 0.16 * i, "tick", 0.2) for i in range(5)] + [(tb + 1.3, "ding", 0.35)]
    t25 = T("multiply it by twenty-five.")
    ev += [(t25, "impact", 0.55), (t25, "bass", 0.45)]
    tn = T("Your number is")
    ev += [(BEATS[2][0], "whoosh", 0.45), (tn, "riser", 0.35)] + [(tn + 0.1 * i, "coin_p", 0.22, 1800 + 90 * i) for i in range(10)]
    ev += [(tn + 1.05, "cash", 0.6), (tn + 1.05, "sparkle", 0.4)]
    ev += [(BEATS[3][0], "whoosh", 0.45), (BEATS[3][0] + 0.5, "pop", 0.35), (T("It's the four percent rule."), "ding", 0.5)]
    ev += [(BEATS[4][0], "whoosh", 0.45), (BEATS[4][0] + 0.3, "pop", 0.35)]
    tw = T("withdrawing four percent")
    ev += [(tw + 0.5 + 0.38 * k, "coin", 0.18) for k in range(8)]
    tl_ = T("lasted at least thirty years")
    ev += [(tl_, "ding", 0.5), (tl_ + 0.05, "sparkle", 0.4)]
    ev += [(BEATS[5][0], "whoosh", 0.45), (BEATS[5][0] + 0.3, "pop", 0.4), (DUR - 0.5, "whoosh", 0.5)]
    return sorted(ev)


# ------------------------------------------------------------------ audio
SR = 48000


def _sfx(dur):
    from sfx import _env
    from sfx3 import SFX, SR as SR3
    assert SR3 == SR

    def coin_p(freq=2093, d=0.45):
        n = int(SR * d)
        tt = np.arange(n) / SR
        x = (np.sin(2 * np.pi * freq * tt) + 0.55 * np.sin(2 * np.pi * freq * 1.26 * tt) * (tt > 0.05)) * np.exp(-tt * 10)
        return (x / np.abs(x).max() * 0.4 * _env(n, 0.001)).astype(np.float32)

    buf = np.zeros(int(SR * dur), np.float32)
    cache = {}
    for t, name, g, *kw in events():
        key = (name, tuple(kw))
        if key not in cache:
            cache[key] = coin_p(float(kw[0])) if name == "coin_p" else SFX[name]()
        s = cache[key]
        i0 = int(t * SR)
        n = min(len(s), len(buf) - i0)
        if n > 0 and i0 >= 0:
            buf[i0:i0 + n] += s[:n] * g
    buf /= max(1e-6, np.abs(buf).max())
    return np.stack([buf, buf], 1)


def _measure(x):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       input=np.ascontiguousarray(x, np.float32).tobytes(), capture_output=True).stderr.decode()
    return json.loads(r[r.rindex("{"):])


def _gain(x, target):
    return x * 10 ** ((target - float(_measure(x)["input_i"])) / 20)


def mix(out):
    n = int(SR * DUR)
    fx = _sfx(DUR)[:n]
    if HAVE_VOICE:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VOICE, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        v = np.frombuffer(raw, np.float32).reshape(-1, 2)
        vv = np.zeros((n, 2), np.float32)
        vv[:min(n, len(v))] = v[:n]
        x = _gain(vv, -16.0) + _gain(fx, -25.0)
    else:
        x = fx
    m = _measure(x)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", af,
                    "-ar", str(SR), out], input=np.ascontiguousarray(x, np.float32).tobytes(), check=True)


def video():
    vid = f"{NAME}_video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                           f"{E.OW}x{E.OH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", vid], stdin=subprocess.PIPE)
    from multiprocessing import Pool
    with Pool(4) as pool:
        for b in pool.imap(fb, range(NF), chunksize=4):
            ff.stdin.write(b)
    ff.stdin.close()
    ff.wait()
    mix(f"{NAME}_audio.wav")
    suffix = "" if HAVE_VOICE else "_PREVIEW_no_voice"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", f"{NAME}_audio.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "12M", "-bufsize", "24M",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", f"moneycheck_{NAME}{suffix}.mp4"], check=True)
    print("done", NAME, "voice" if HAVE_VOICE else "PREVIEW", DUR, "s")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "info":
        print("voice" if HAVE_VOICE else "estimate", "DUR", DUR)
        for t0, t1, fn in BEATS:
            print(f"{t0:6.2f}-{t1:6.2f} {fn.__name__}")
    elif mode == "video":
        video()
    else:
        E.main(sys.argv, fb, thumb, NF, NAME, cover, events(), DUR)

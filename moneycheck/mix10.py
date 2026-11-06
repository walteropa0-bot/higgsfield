"""Sound design for Short #8: female voice + money/whoosh/impact effects, all anchored to exact word times.
-> voice_sfx.wav (48 kHz stereo, -14 LUFS)."""
import json
import re
import subprocess

import numpy as np

from sfx import _lowpass, _env
from sfx3 import SFX, SR

WORDS = json.load(open("words.json"))
DUR = 65.9
rng = np.random.default_rng(10)


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


def coin_p(freq=2093, dur=0.45):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.55 * np.sin(2 * np.pi * freq * 1.26 * t) * (t > 0.05)) * np.exp(-t * 10)
    return (x / np.abs(x).max() * 0.4 * _env(n, 0.001)).astype(np.float32)


def step(dur=0.06):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = _lowpass(rng.standard_normal(n), 300) * np.exp(-t * 60)
    return (x / np.abs(x).max() * 0.5).astype(np.float32)


raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", "voice.mp3", "-af",
                               "highpass=f=70,equalizer=f=3200:t=q:w=1.2:g=1.5,"
                               "acompressor=threshold=-20dB:ratio=2.2:attack=5:release=90:makeup=2",
                               "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
voice = np.frombuffer(raw, np.float32)
out = np.zeros(int(SR * DUR), np.float32)
out[:min(len(voice), len(out))] += voice[:len(out)] / max(1e-6, np.abs(voice).max()) * 0.8

ev = []


def add(t, name, g, **kw):
    ev.append((t, name, g, tuple(sorted(kw.items()))))


# 1 hook
add(at("down") - 1.0, "riser", 0.25)
add(at("down") - 0.05, "sweep_down", 0.5)
add(at("down") + 0.85, "impact", 0.55)
add(at("down") + 0.85, "bass", 0.4)
# 2 everyone is selling / what do you do
te = at("everyone")
add(te - 0.12, "whoosh", 0.35)
for k in range(8):
    add(te + 0.1 + 0.11 * k, "pop", 0.22)
add(te + 0.7, "whoosh", 0.2)
add(te + 1.1, "whoosh", 0.18)
add(at("what"), "pop", 0.4)
add(at("what") + 0.18, "pop", 0.4)
add(at("do", 2), "ping", 0.3)
# 3 crash 2020
tc = at("crashed")
add(at("in") - 0.1, "whoosh", 0.3)
add(at("in"), "pop", 0.3)
add(at("in") + 0.35, "ping", 0.18)
add(tc - 0.05, "sweep_down", 0.55)
add(tc + 0.1, "impact", 0.6)
add(tc + 0.1, "bass", 0.45)
t33 = at("thirtythree", end=True)
for d in range(0, 34, 3):
    add(tc + (t33 - tc) * d / 33, "tick", 0.22)
add(at("days"), "alert", 0.22)
# 4 fear
tf = at("fear")
add(tf - 0.06, "whoosh", 0.35)
add(tf, "bass", 0.5)
add(tf, "alert", 0.3)
for i in range(11):
    add(at("many") + 0.06 * i, "pop", 0.14)
add(at("many") + 0.2, "whoosh", 0.22)
add(at("sold", 1, end=True) - 0.3, "swoosh_up", 0.25)
# 5 recovery
tb, th = at("but"), at("high")
add(tb - 0.06, "whoosh", 0.3)
add(tb, "swoosh_up", 0.35)
for i in range(6):
    add(tb + i * (th - tb) / 5, "tick", 0.28)
add(at("five"), "pop", 0.25)
add(th, "ding", 0.45)
add(th, "cash", 0.45)
add(th + 0.05, "sparkle", 0.35)
for i, fq in enumerate((2093, 2349, 2637, 3136)):
    add(th + 0.08 + 0.09 * i, "coin_p", 0.35, freq=fq)
# 6 sold vs stayed
add(at("the", 2) - 0.06, "whoosh", 0.3)
add(at("sold", 2), "pop", 0.3)
add(at("locked"), "tick", 0.6)
add(at("locked"), "impact", 0.22)
add(at("losses"), "sweep_down", 0.3)
add(at("ones", 2) - 0.3, "swoosh_up", 0.3)
tg = at("got")
for i in range(9):
    add(tg + 0.1 * i + 0.5, "coin_p", 0.3, freq=float(1900 + 160 * (i % 5)))
add(at("back", 2, end=True) - 0.1, "cash", 0.5)
add(at("back", 2, end=True), "sparkle", 0.35)
# 7 an average year
t0 = at("and", 1)
add(t0 - 0.06, "whoosh", 0.3)
x = t0 + 0.2
while x < at("yet") - 0.35:
    add(x, "step", 0.22)
    x += 0.34
add(at("drops"), "sweep_down", 0.4)
add(at("fourteen"), "pop", 0.4)
add(at("fourteen"), "bass", 0.28)
# 8 three out of four
ty = at("yet")
add(ty - 0.06, "whoosh", 0.3)
for i in range(4):
    add(ty + 0.02 + 0.2 * i, "pop", 0.28)
add(at("three"), "blip", 0.35)
add(at("four"), "blip", 0.35)
for i in range(4):
    if i == 2:
        add(at("still") + 0.12 * i, "puff", 0.3)
    else:
        add(at("still") + 0.12 * i, "coin_p", 0.35, freq=float(2093 + 260 * i))
add(at("end", 1), "ding", 0.3)
# 9 hidden cost / 10 best days
ts = at("selling", 2)
add(ts - 0.06, "whoosh", 0.35)
add(ts + 0.05, "flutter", 0.25)
add(at("hidden"), "alert", 0.22)
for i in range(10):
    add(at("ten") + 0.07 * i, "coin_p", 0.18, freq=float(1800 + 120 * i))
    add(at("years", 2) + 0.06 * i, "pop", 0.13)
add(at("and", 2), "swoosh_up", 0.35)
add(at("less"), "sweep_down", 0.45)
add(at("half"), "pop", 0.4)
add(at("half"), "bass", 0.25)
# 10 best days follow worst days
t3 = at("and", 3)
add(t3 - 0.06, "whoosh", 0.3)
for i in range(0, 34, 3):
    add(t3 + 0.022 * i, "tick", 0.15)
add(at("best", 2), "ping", 0.35)
add(at("best", 2), "coin", 0.3)
add(at("worst"), "bass", 0.4)
add(at("worst"), "sweep_down", 0.3)
add(at("worst") + 0.35, "pop", 0.25)
# 11 don't run / focus / discipline
add(at("so") - 0.06, "whoosh", 0.3)
add(at("screen") - 0.35, "swoosh_up", 0.25)
add(at("red", 1), "alert", 0.45)
add(at("red", 1), "impact", 0.35)
add(at("dont") - 0.05, "vroom", 0.3)
add(at("dont") + 0.25, "whoosh", 0.22)
add(at("dont") + 0.15, "bass", 0.35)
add(at("stay"), "swoosh_up", 0.35)
add(at("stay") + 0.15, "puff", 0.25)
add(at("stay"), "pop", 0.35)
add(at("keep"), "pop", 0.35)
for i in range(4):
    add(at("keep") + 0.1 + 0.32 * i + 0.42, "coin_p", 0.45, freq=float(2093 + 200 * i))
# 12 smartest vs most patient
t10 = at("the", 10)
add(t10 - 0.06, "whoosh", 0.3)
zt0, zt1 = t10 + 0.1, at("rewards") - 0.35
for i in range(9):
    add(zt0 + (zt1 - zt0) * i / 9, "blip", 0.2)
add(at("smartest"), "pop", 0.3)
add(at("rewards"), "swoosh_up", 0.3)
add(at("patient"), "pop", 0.35)
add(at("patient") + 0.05, "sparkle", 0.25)
tend = at("ones", 4, end=True) - 0.2
add(tend, "cash", 0.45)
add(tend, "ding", 0.4)
for i in range(3):
    add(tend + 0.1 + 0.1 * i, "coin_p", 0.3, freq=float(2349 + 200 * i))
# 13 red days -> green years
tr2, tgr = at("red", 2), at("green")
add(tr2 - 0.08, "whoosh", 0.3)
add(tr2, "impact", 0.35)
add(tr2, "bass", 0.3)
add(tgr - 1.2, "riser", 0.35)
add(tgr, "cash", 0.6)
add(tgr, "ding", 0.45)
add(tgr, "bass", 0.45)
add(tgr + 0.05, "sparkle", 0.4)
for i in range(6):
    add(tgr + 0.12 + 0.11 * i, "coin_p", 0.38, freq=float(2093 + 180 * i))
add(at("years", 3, end=True) + 0.27, "pop", 0.3)
add(65.2, "whoosh", 0.4)

cache = {}
for t, name, g, kw in ev:
    key = (name, kw)
    if key not in cache:
        cache[key] = coin_p(**dict(kw)) if name == "coin_p" else step() if name == "step" else SFX[name]()
    s = cache[key]
    i0 = int(t * SR)
    n = min(len(s), len(out) - i0)
    if n > 0 and i0 >= 0:
        out[i0:i0 + n] += s[:n] * g * 0.42
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2", "voice_sfx.wav"],
               input=np.clip(out, -1, 1).tobytes(), check=True)
print("ok", DUR, "s | sound effects:", len(ev))

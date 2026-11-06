"""Sound design for Short #9: female voice + crash/money/mining effects at the exact word times -> voice_sfx.wav."""
import subprocess

import numpy as np

from sfx import _lowpass, _env
from sfx3 import SFX, SR
import render11 as V

at, TL, DUR = V.at, V.TL, V.DUR
rng = np.random.default_rng(11)


def coin_p(freq=2093, dur=0.45):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.55 * np.sin(2 * np.pi * freq * 1.26 * t) * (t > 0.05)) * np.exp(-t * 10)
    return (x / np.abs(x).max() * 0.4 * _env(n, 0.001)).astype(np.float32)


def thud(dur=0.12):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = _lowpass(rng.standard_normal(n), 260) * np.exp(-t * 40)
    return (x / np.abs(x).max() * 0.6).astype(np.float32)


def pick(dur=0.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    clink = np.sin(2 * np.pi * 2350 * t) * np.exp(-t * 48) + 0.5 * np.sin(2 * np.pi * 3650 * t) * np.exp(-t * 65)
    th = _lowpass(rng.standard_normal(n), 480) * np.exp(-t * 32)
    x = 0.45 * clink / np.abs(clink).max() + 0.9 * th / np.abs(th).max()
    return (x / np.abs(x).max() * 0.5).astype(np.float32)


LOCAL = {"coin_p": coin_p, "thud": thud, "pick": pick}

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
tv = at("vanished")
add(0.03, "bass", 0.32)
add(tv, "sweep_down", 0.5)
add(tv + 0.1, "impact", 0.45)
for i in range(4):
    add(tv + 0.08 + 0.2 * i, "flutter", 0.3)
add(at("single"), "pop", 0.35)
# 2 under pressure / buy the dip
t0 = at("so")
add(t0 - 0.1, "whoosh", 0.3)
for i in range(8):
    add(t0 + 0.08 * i, "tick", 0.18)
add(at("under"), "alert", 0.3)
add(at("buy", 1), "pop", 0.4)
add(at("dip", 1), "ping", 0.3)
# 3 Nasdaq
add(at("on", 1) - 0.1, "whoosh", 0.35)
add(at("on", 1) + 0.2, "pop", 0.25)
for i in range(6):
    add(at("on", 1) + 0.15 + 0.22 * i, "tick", 0.14)
add(at("fell") - 0.05, "sweep_down", 0.55)
add(at("fell") + 0.3, "impact", 0.5)
add(at("fell") + 0.3, "bass", 0.4)
add(at("slipped"), "tick", 0.3)
add(at("correction"), "alert", 0.4)
add(at("correction"), "pop", 0.35)
# 4 chips
add(at("chip") - 0.1, "whoosh", 0.3)
add(at("worst"), "impact", 0.6)
add(at("worst"), "bass", 0.5)
add(at("worst") + 0.05, "puff", 0.3)
for i in range(5):
    add(at("worst") + 0.15 + 0.1 * i, "tick", 0.12)
add(at("since"), "pop", 0.3)
# 5 names
add(at("nvidia") - 0.08, "whoosh", 0.3)
for w in ("nvidia", "amd", "arm", "qualcomm"):
    add(at(w), "pop", 0.35)
    add(at(w) + 0.1, "sweep_down", 0.15)
add(at("crushed"), "impact", 0.5)
add(at("crushed"), "bass", 0.35)
# 6 the fear
add(at("the", 4) - 0.06, "whoosh", 0.3)
add(at("fear", 1), "bass", 0.35)
add(at("midterms") - 0.2, "pop", 0.3)
add(at("midterms") + 0.5, "tick", 0.35)
add(at("investors"), "swoosh_up", 0.25)
add(at("worry"), "blip", 0.25)
add(at("limits"), "impact", 0.35)
add(at("limits"), "alert", 0.3)
add(at("plus") - 0.15, "whoosh", 0.3)
for w, k in (("qualcomm", 2), ("intel", 1)):
    add(at(w, k) - 0.15, "pop", 0.35)
    add(at(w, k), "sweep_down", 0.25)
# 7 falling price != bargain
add(at("but") - 0.06, "whoosh", 0.3)
add(at("price"), "pop", 0.3)
add(at("isnt"), "bass", 0.3)
add(at("bargain") - 0.35, "sparkle", 0.35)
add(at("bargain") - 0.3, "ping", 0.25)
# 8 the mine
add(at("before", 1) - 0.08, "whoosh", 0.35)
add(at("dig"), "pop", 0.35)
spans = [(at("dig"), TL(0))] + [(TL(k) + 0.2, V.layer_end(k)) for k in range(5)] + [(at("keep") - 0.45, at("keep") + 0.35)]
for a, b in spans:
    n = 0
    while True:
        th = a + (n + 0.28) / 2.2
        if th >= b:
            break
        add(th, "pick", 0.2)
        n += 1
for k in range(5):
    add(TL(k), "swoosh_up", 0.28)
    add(TL(k) + 0.05, "pop", 0.3)
add(at("fear", 2), "pop", 0.3)
add(at("real"), "pop", 0.35)
for i, tt in enumerate((at("sales"), at("sales") + 0.25, at("profits"))):
    add(tt, "coin_p", 0.25, freq=float(1800 + 300 * i))
add(at("growing"), "ding", 0.3)
add(at("debt"), "bass", 0.3)
add(at("storm"), "impact", 0.3)
add(at("storm"), "bass", 0.3)
add(at("cheap"), "pop", 0.3)
add(at("cheap") + 0.05, "coin", 0.25)
add(at("expensive"), "pop", 0.3)
add(at("expensive") + 0.05, "sweep_down", 0.2)
add(at("never"), "swoosh_up", 0.25)
for i in range(5):
    add(at("never") + 0.24 * i, "tick", 0.15)
add(at("one", 2), "ding", 0.3)
add(at("most") - 0.15, "whoosh", 0.35)
add(at("stop"), "sweep_down", 0.25)
add(at("headline"), "pop", 0.35)
add(at("headline"), "alert", 0.2)
add(at("the", 8) - 0.1, "whoosh", 0.3)
tk = at("keep")
add(tk + 0.2, "impact", 0.45)
add(tk + 0.2, "bass", 0.35)
add(tk + 0.25, "puff", 0.3)
add(tk + 0.85, "thud", 0.45)
add(at("find"), "pop", 0.35)
tdm = at("diamonds")
for i in range(7):
    add(tdm - 0.3 + 0.12 * i, "coin_p", 0.3, freq=float(2093 + 150 * i))
add(tdm - 0.2, "sparkle", 0.4)
add(tdm + 0.1, "cash", 0.55)
add(tdm + 0.1, "ding", 0.45)
add(tdm + 0.1, "bass", 0.3)
add(DUR - 0.7, "whoosh", 0.4)

cache = {}
for t, name, g, kw in ev:
    key = (name, kw)
    if key not in cache:
        cache[key] = LOCAL[name](**dict(kw)) if name in LOCAL else SFX[name]()
    s = cache[key]
    i0 = int(t * SR)
    n = min(len(s), len(out) - i0)
    if n > 0 and i0 >= 0:
        out[i0:i0 + n] += s[:n] * g * 0.42
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2", "voice_sfx.wav"],
               input=np.clip(out, -1, 1).tobytes(), check=True)
print("ok", DUR, "s | sound effects:", len(ev))

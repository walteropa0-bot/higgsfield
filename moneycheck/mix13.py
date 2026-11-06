"""Sound design for Short #11 (about 20 s): voice + pops/coins/race ticks/riser/million explosion at the exact word times."""
import subprocess

import numpy as np

from sfx import _env
from sfx3 import SFX, SR
import render13 as V

at, DUR = V.at, V.DUR


def coin_p(freq=2093, dur=0.45):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.55 * np.sin(2 * np.pi * freq * 1.26 * t) * (t > 0.05)) * np.exp(-t * 10)
    return (x / np.abs(x).max() * 0.4 * _env(n, 0.001)).astype(np.float32)


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


add(0.0, "bass", 0.3)
add(0.02, "swoosh_up", 0.3)
add(at("hundred", 1), "pop", 0.35)
add(at("hundred", 1) + 0.05, "coin", 0.28)
add(at("equals"), "ding", 0.35)
add(at("equals"), "pop", 0.28)
add(at("five", 1) - 0.1, "pop", 0.35)
add(at("five", 1), "coin", 0.3)
add(at("forty", 1) + 0.2, "pop", 0.3)
t0, t60 = at("both") - 0.1, at("sixty", 2, end=True)
add(t0, "whoosh", 0.3)
c0, c1 = t0 + 0.15, t60 - 0.1
for ag in range(25, 61, 5):
    u = (ag - 20) / 40
    tt = c0 + (c1 - c0) * (np.arccos(1 - 2 * u) / np.pi if 0 < u < 1 else u)
    add(float(tt), "blip" if ag == 40 else "tick", 0.3 if ag == 40 else 0.18)
add(t60 - 0.15, "ding", 0.45)
add(t60 - 0.1, "sparkle", 0.35)
add(at("one") - 0.1, "whoosh", 0.35)
for i in range(3):
    add(at("one") + 0.12 * i, "coin_p", 0.25, freq=float(1900 + 150 * i))
for i in range(5):
    add(at("other") + 0.1 * i, "coin_p", 0.25, freq=float(1700 + 120 * i))
add(at("other") + 0.7, "swoosh_up", 0.35)
add(at("other") + 1.4, "sparkle", 0.3)
ts, tm = at("start"), at("million")
add(ts - 0.1, "whoosh", 0.35)
x = ts + 0.25
k = 0
while x < tm - 0.1:
    add(x, "coin_p", 0.18, freq=float(1800 + 60 * k))
    x += 0.24
    k += 1
add(tm - 1.2, "riser", 0.45)
add(tm, "impact", 0.55)
add(tm, "bass", 0.5)
add(tm + 0.02, "cash", 0.6)
add(tm + 0.05, "sparkle", 0.45)
add(tm + 0.08, "ding", 0.4)
for i in range(8):
    add(tm + 0.1 + 0.12 * i, "coin_p", 0.3, freq=float(2093 + 140 * i))
add(tm + 0.2, "pop", 0.3)
add(tm + 1.0, "pop", 0.28)
add(DUR - 0.6, "whoosh", 0.4)

cache = {}
for t, name, g, kw in ev:
    key = (name, kw)
    if key not in cache:
        cache[key] = coin_p(**dict(kw)) if name == "coin_p" else SFX[name]()
    s = cache[key]
    i0 = int(t * SR)
    n = min(len(s), len(out) - i0)
    if n > 0 and i0 >= 0:
        out[i0:i0 + n] += s[:n] * g * 0.42
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2", "voice_sfx.wav"],
               input=np.clip(out, -1, 1).tobytes(), check=True)
print("ok", DUR, "s | sound effects:", len(ev))

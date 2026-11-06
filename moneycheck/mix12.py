"""Sound design for Short #10 (20 s): voice + sweep/ding/coins/riser/explosion at the exact word times -> voice_sfx.wav."""
import subprocess

import numpy as np

from sfx import _env
from sfx3 import SFX, SR
import render12 as V

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


add(0.0, "bass", 0.35)
add(0.05, "swoosh_up", 0.35)
add(0.9, "sparkle", 0.3)
add(at("warren"), "pop", 0.3)
add(at("after"), "pop", 0.38)
add(at("fiftieth"), "pop", 0.3)
add(at("birthday"), "sparkle", 0.4)
add(at("birthday") + 0.02, "ping", 0.28)
add(at("his", 2) - 0.1, "whoosh", 0.3)
add(at("skill") - 0.15, "pop", 0.25)
add(at("investing") + 0.1, "blip", 0.25)
add(at("secret") - 0.1, "swoosh_up", 0.3)
add(at("time"), "bass", 0.38)
add(at("time"), "ding", 0.42)
for i in range(3):
    add(at("time") + 0.45 + 0.33 * i, "tick", 0.18)
add(at("he") - 0.08, "whoosh", 0.3)
add(at("bought") - 0.05, "pop", 0.35)
add(at("bought"), "coin", 0.3)
add(at("eleven"), "ding", 0.3)
t_a, t_s = at("and", 1), at("stopped", end=True)
for i in range(17):
    add(t_a + (t_s - t_a) * (i * 46 / 750), "coin_p", 0.22, freq=float(1800 + 45 * i))
add(at("because") - 0.1, "whoosh", 0.3)
for i in range(6):
    add(at("decades") - 0.4 + 0.3 * i, "tick", 0.16)
tex = at("explodes")
add(tex - 1.2, "riser", 0.5)
add(tex, "impact", 0.6)
add(tex, "bass", 0.5)
add(tex + 0.02, "cash", 0.6)
add(tex + 0.05, "sparkle", 0.45)
add(tex + 0.08, "ding", 0.4)
for i in range(9):
    add(tex + 0.1 + 0.12 * i, "coin_p", 0.32, freq=float(2093 + 140 * i))
for i in range(6):
    add(tex + 1.4 + 0.25 * i, "coin_p", 0.18, freq=float(2349 + 90 * (i % 3)))
add(tex + 1.3, "pop", 0.28)
add(DUR - 0.7, "whoosh", 0.4)

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

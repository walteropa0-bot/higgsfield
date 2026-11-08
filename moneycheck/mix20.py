"""Moneycheck sound design for the lib20 videos.

Effects = the existing sfx3 set (whoosh, pop, tick, ding, coin, cash, impact, riser, sparkle, ...) plus new
UI and money sounds: click, toggle, typing, notif, kaching, swish (camera moves), thud (losses), mallet (counts).
Mix like Video B (which the owner liked): voice -16 LUFS + effects bus -25 LUFS, then two-pass loudnorm
to -14 LUFS / -1.5 dBTP, 48 kHz stereo.
"""
import json
import subprocess

import numpy as np

from sfx import _env
from sfx3 import SFX as BASE, SR

_rng = np.random.default_rng(20)


def _bp(x, f0, bw):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    X *= np.exp(-0.5 * ((fr - f0) / bw) ** 2)
    return np.fft.irfft(X, len(x)).astype(np.float32)


def _norm(x, peak):
    return (np.asarray(x, np.float32) / max(1e-9, float(np.abs(x).max())) * peak).astype(np.float32)


def _noise(n):
    return _rng.standard_normal(n).astype(np.float32)


def click(dur=0.07):
    n = int(SR * dur)
    x = np.zeros(n, np.float32)
    for t0, g in ((0.0, 1.0), (0.03, 0.55)):
        i0, m = int(t0 * SR), int(0.014 * SR)
        k = np.arange(m)
        x[i0:i0 + m] += _bp(_noise(m) * np.exp(-k / (0.0025 * SR)), 4200, 1800) * g
        x[i0:i0 + m] += 0.45 * g * np.sin(2 * np.pi * 2600 * k / SR) * np.exp(-k / (0.002 * SR))
    return _norm(x, 0.5)


def toggle(dur=0.25):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 700 + 520 * np.clip(t / 0.06, 0, 1)
    blip = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.05) * (t < 0.13)
    thump = np.sin(2 * np.pi * 120 * t) * np.exp(-t / 0.035)
    x = 0.65 * blip + 0.5 * thump
    c = click()
    x[:len(c)] += 0.7 * c[:n]
    return _norm(x, 0.5)


def typing(dur=0.9):
    n = int(SR * dur)
    x = np.zeros(n, np.float32)
    t0 = 0.0
    while t0 < dur - 0.05:
        i0, m = int(t0 * SR), int(0.03 * SR)
        k = np.arange(m)
        x[i0:i0 + m] += _bp(_noise(m) * np.exp(-k / (0.004 * SR)), _rng.uniform(2500, 4600), 1400) * _rng.uniform(0.5, 1.0)
        t0 += _rng.uniform(0.055, 0.11)
    return _norm(x, 0.35)


def notif(dur=0.7):
    n = int(SR * dur)
    t = np.arange(n) / SR

    def tone(f, t0, d):
        tt = np.maximum(t - t0, 0)
        return (t >= t0) * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * np.exp(-tt / d)

    return _norm((tone(1318.5, 0.0, 0.08) + tone(1975.5, 0.085, 0.22)) * _env(n, 0.002), 0.4)


def kaching(dur=1.1):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ka = _bp(_noise(n) * np.exp(-t / 0.012), 2500, 1500)
    tb = np.maximum(t - 0.07, 0)
    bell = sum(g * np.sin(2 * np.pi * f * tb) * np.exp(-tb / d) * (t >= 0.07)
               for f, g, d in ((2093, 1.0, 0.35), (2637, 0.7, 0.3), (3136, 0.5, 0.25), (4186, 0.4, 0.2), (5274, 0.25, 0.15)))
    return _norm(0.55 * ka + bell, 0.5)


def swish(dur=0.34):
    n = int(SR * dur)
    t = np.arange(n) / SR
    nz = _noise(n)
    out = np.zeros(n, np.float32)
    seg = max(256, n // 6)
    win = np.hanning(seg).astype(np.float32)
    for i0 in range(0, n - seg, seg // 2):
        out[i0:i0 + seg] += _bp(nz[i0:i0 + seg] * win, 500 + 2300 * i0 / n, 700)
    return _norm(out * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5, 0.35)


def thud(dur=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 78 - 32 * np.clip(t / 0.25, 0, 1)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.12) + 0.3 * _bp(_noise(n) * np.exp(-t / 0.01), 300, 200)
    return _norm(x, 0.6)


def mallet(freq=880.0, dur=0.35):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 4 * freq * t) * np.exp(-t / 0.02)) * np.exp(-t / 0.09)
    return _norm(x * _env(n, 0.001), 0.35)


SFX = dict(BASE)
SFX.update(click=click, toggle=toggle, typing=typing, notif=notif, kaching=kaching, swish=swish, thud=thud, mallet=mallet)


def _decode(path, n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.float32).reshape(-1, 2)
    out = np.zeros((n, 2), np.float32)
    out[:min(n, len(v))] = v[:n]
    return out


def _measure(x):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       input=np.ascontiguousarray(x, np.float32).tobytes(), capture_output=True).stderr.decode()
    return json.loads(r[r.rindex("{"):])


def _gain(x, target):
    return x * 10 ** ((target - float(_measure(x)["input_i"])) / 20)


def mix(voice, events, dur, out):
    """events: (t, name, gain) or (t, name, gain, {kwargs}); writes a -14 LUFS 48 kHz stereo WAV"""
    n = int(SR * dur)
    fx = np.zeros(n, np.float32)
    cache = {}
    for ev in events:
        t, name, g = ev[0], ev[1], ev[2]
        kw = ev[3] if len(ev) > 3 else {}
        key = (name, tuple(sorted(kw.items())))
        if key not in cache:
            cache[key] = SFX[name](**kw)
        s = cache[key]
        i0 = int(round(t * SR))
        m = min(len(s), n - i0)
        if i0 >= 0 and m > 0:
            fx[i0:i0 + m] += s[:m] * g
    x = _gain(_decode(voice, n), -16.0) + _gain(np.stack([fx, fx], 1), -25.0)
    m = _measure(x)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", af,
                    "-ar", str(SR), out], input=np.ascontiguousarray(x, np.float32).tobytes(), check=True)


def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out],
                   check=True)

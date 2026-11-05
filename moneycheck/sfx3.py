"""Extra sound effects for the 'two choices' Short: engine 'vroom', sparkle, paper flutter, smoke puff."""
import numpy as np

from sfx import SR, _lowpass, _env
from sfx2 import SFX as BASE

rng = np.random.default_rng(23)


def vroom(dur=1.1):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    f = 58 + 110 * np.sin(np.pi * np.clip(t * 1.15, 0, 1)) ** 1.3
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1.0) - 1
    x = _lowpass(saw, 500 + 1600 * np.sin(np.pi * t)) * 0.9 + _lowpass(rng.standard_normal(n), 350) * 0.35
    x *= np.minimum(1, t / 0.04) * (1 - t) ** 0.7
    return (x / np.abs(x).max() * 0.55).astype(np.float32)


def sparkle(dur=0.6):
    n = int(SR * dur)
    x = np.zeros(n)
    for k in range(7):
        t0 = rng.uniform(0, 0.4)
        f = rng.uniform(2800, 5200)
        i0 = int(t0 * SR)
        m = n - i0
        tt = np.arange(m) / SR
        x[i0:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 28) * rng.uniform(0.5, 1.0)
    return (x / np.abs(x).max() * 0.3).astype(np.float32)


def flutter(dur=0.35):
    n = int(SR * dur)
    x = np.zeros(n)
    for k in range(5):
        i0 = int((0.02 + 0.06 * k) * SR)
        m = int(0.04 * SR)
        b = rng.standard_normal(m)
        b = b - _lowpass(b, 1800)
        x[i0:i0 + m] += b * np.hanning(m) * (1 - 0.12 * k)
    return (x / np.abs(x).max() * 0.35).astype(np.float32)


def puff(dur=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = _lowpass(rng.standard_normal(n), 700) * np.minimum(1, t / 0.03) * np.exp(-t * 7)
    return (x / np.abs(x).max() * 0.45).astype(np.float32)


SFX = dict(BASE)
SFX.update(vroom=vroom, sparkle=sparkle, flutter=flutter, puff=puff)

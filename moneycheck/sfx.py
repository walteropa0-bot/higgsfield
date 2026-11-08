"""Synthesize simple, clean sound effects as numpy arrays (mono, 48 kHz, float32)."""
import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def _env(n, attack=0.005, release=None):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    if release is None:
        return a
    return a * np.exp(-t / release)


def _lowpass(x, cutoff):
    # one-pole lowpass; cutoff may be an array (time-varying)
    cutoff = np.broadcast_to(cutoff, x.shape)
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha[i] * (x[i] - acc)
        y[i] = acc
    return y


def whoosh(dur=0.45):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    cutoff = 300 + 5000 * np.sin(np.pi * t) ** 2
    x = _lowpass(noise, cutoff) - _lowpass(noise, cutoff * 0.25)
    x *= np.sin(np.pi * t) ** 1.5
    return (x / np.abs(x).max() * 0.55).astype(np.float32)


def swoosh_up(dur=0.6):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    cutoff = 200 + 7000 * t ** 2
    x = _lowpass(noise, cutoff) - _lowpass(noise, 120)
    x *= t ** 1.2 * (1 - t) ** 0.25
    return (x / np.abs(x).max() * 0.5).astype(np.float32)


def pop(dur=0.12):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 30) + 220
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * _env(n, 0.001, 0.03)
    return (x * 0.6).astype(np.float32)


def tick(dur=0.05):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 3200 * t) * 0.6 + rng.standard_normal(n) * 0.3) * _env(n, 0.0005, 0.006)
    return (x * 0.5).astype(np.float32)


def ding(dur=1.4):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = 1318.5  # E6
    x = (np.sin(2 * np.pi * f0 * t)
         + 0.45 * np.sin(2 * np.pi * f0 * 2.01 * t) * np.exp(-t * 3)
         + 0.25 * np.sin(2 * np.pi * f0 * 3.02 * t) * np.exp(-t * 6))
    x *= _env(n, 0.002, 0.45)
    return (x / np.abs(x).max() * 0.45).astype(np.float32)


def bass_hit(dur=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 38 + 90 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * _env(n, 0.002, 0.35)
    click = rng.standard_normal(n) * _env(n, 0.0005, 0.004) * 0.3
    x = np.tanh((x + click) * 1.6)
    return (x / np.abs(x).max() * 0.8).astype(np.float32)


SFX = {
    "whoosh": whoosh,
    "swoosh_up": swoosh_up,
    "pop": pop,
    "tick": tick,
    "ding": ding,
    "bass": bass_hit,
}

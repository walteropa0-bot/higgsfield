"""Extra synthesized sound effects (48 kHz mono float32), on top of sfx.py."""
import numpy as np

from sfx import SFX as BASE, SR, _env, _lowpass

rng = np.random.default_rng(11)


def riser(dur=1.2):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    f = 180 + 900 * t ** 2
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * 0.35 + np.sin(ph * 2.01) * 0.12
    noise = rng.standard_normal(n)
    nz = _lowpass(noise, 300 + 6000 * t ** 2) * 0.6
    x = (tone + nz) * t ** 1.6 * (1 - np.clip((t - 0.96) / 0.04, 0, 1))
    return (x / np.abs(x).max() * 0.5).astype(np.float32)


def impact(dur=1.1):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 32 + 70 * np.exp(-t * 14)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    nz = _lowpass(rng.standard_normal(n), 1800) * np.exp(-t * 22) * 0.9
    x = np.tanh((sub + nz) * 1.8)
    return (x / np.abs(x).max() * 0.85).astype(np.float32)


def alert(dur=0.62):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, (t0, f) in enumerate([(0.0, 880), (0.16, 660), (0.32, 880), (0.48, 660)]):
        i0, i1 = int(t0 * SR), int((t0 + 0.13) * SR)
        tt = t[i0:i1] - t0
        x[i0:i1] += np.sin(2 * np.pi * f * tt) * np.minimum(1, tt / 0.005) * np.exp(-tt * 9)
    return (x / np.abs(x).max() * 0.35).astype(np.float32)


def coin(dur=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 2093 * t) + 0.6 * np.sin(2 * np.pi * 2637 * t) * (t > 0.06)) * np.exp(-t * 9)
    x *= _env(n, 0.001)
    return (x / np.abs(x).max() * 0.4).astype(np.float32)


def cash(dur=0.9):
    n = int(SR * dur)
    t = np.arange(n) / SR
    rattle = _lowpass(rng.standard_normal(n), 5000) * np.exp(-((t - 0.05) / 0.05) ** 2) * 0.5
    bell = (np.sin(2 * np.pi * 2349 * t) + 0.5 * np.sin(2 * np.pi * 3136 * t)) * np.exp(-(t - 0.12).clip(0) * 6) * (t > 0.12)
    x = rattle + bell * 0.7
    return (x / np.abs(x).max() * 0.45).astype(np.float32)


def blip(dur=0.08):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1400 * t) * _env(n, 0.002, 0.02)
    return (x * 0.35).astype(np.float32)


def sweep_down(dur=0.7):
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    f = 700 * (1 - t) ** 1.5 + 90
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - t) ** 0.6 * np.minimum(1, t / 0.03)
    return (x / np.abs(x).max() * 0.4).astype(np.float32)


def ping(dur=1.6):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1046.5 * t) * 0.8 + np.sin(2 * np.pi * 1568 * t) * 0.25) * np.exp(-t * 3.0)
    x *= _env(n, 0.003)
    return (x / np.abs(x).max() * 0.3).astype(np.float32)


SFX = dict(BASE)
SFX.update(riser=riser, impact=impact, alert=alert, coin=coin, cash=cash, blip=blip, sweep_down=sweep_down, ping=ping)

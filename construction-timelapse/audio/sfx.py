"""Procedural construction sound-effects library (numpy/scipy, 48 kHz, no samples).

Every generator returns a float32 array: mono (n,) or stereo (n, 2), roughly peak-normalised
to ~1.0 so the mixer can set levels in dB.
"""
import numpy as np
from scipy import signal

SR = 48000


def rng_for(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def n_of(dur):
    return max(1, int(round(dur * SR)))


def t_of(n):
    return np.arange(n) / SR


# ----------------------------------------------------------------------------- filters
def _sos(kind, f, order=2):
    nyq = SR / 2
    if kind == 'band':
        lo, hi = f
        lo = max(10.0, lo) / nyq
        hi = min(hi, nyq * 0.98) / nyq
        return signal.butter(order, [lo, hi], btype='band', output='sos')
    return signal.butter(order, min(f, nyq * 0.98) / nyq, btype=kind, output='sos')


def lp(x, f, order=2):
    return signal.sosfilt(_sos('low', f, order), x, axis=0)


def hp(x, f, order=2):
    return signal.sosfilt(_sos('high', f, order), x, axis=0)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos('band', (lo, hi), order), x, axis=0)


def peak_eq(x, f, gain_db, q=1.0):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f / SR
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    return signal.lfilter(b, a, x, axis=0)


def shelf_low(x, f, gain_db):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f / SR
    alpha = np.sin(w0) / 2 * np.sqrt(2)
    cw = np.cos(w0)
    b = [A * ((A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha), 2 * A * ((A - 1) - (A + 1) * cw), A * ((A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha)]
    a = [(A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha, -2 * ((A - 1) + (A + 1) * cw), (A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha]
    return signal.lfilter(b, a, x, axis=0)


# ------------------------------------------------------------------------------ noise
def white(n, r):
    return r.standard_normal(n).astype(np.float64)


def pink(n, r):
    X = np.fft.rfft(r.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    f[0] = f[1]
    X /= np.sqrt(f)
    y = np.fft.irfft(X, n)
    return y / (np.std(y) + 1e-9)


def brown(n, r):
    y = np.cumsum(r.standard_normal(n))
    y = hp(y, 18)
    return y / (np.std(y) + 1e-9)


def smooth_noise(n, rate_hz, r):
    """Band-limited random control signal in [-1, 1] changing at ~rate_hz."""
    k = max(4, int(n / SR * rate_hz) + 4)
    pts = r.uniform(-1, 1, k)
    x = np.linspace(0, k - 3, n)
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    return pts[i] * (1 - f) + pts[i + 1] * f


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def fade(x, fin=0.005, fout=0.02):
    n = len(x)
    a, b = min(n, n_of(fin)), min(n, n_of(fout))
    w = np.ones(n)
    if a > 0:
        w[:a] = np.linspace(0, 1, a)
    if b > 0:
        w[n - b:] *= np.linspace(1, 0, b)
    return x * (w[:, None] if x.ndim == 2 else w)


def exp_env(n, tau, delay=0.0):
    t = t_of(n) - delay
    e = np.exp(-np.maximum(t, 0) / max(tau, 1e-4))
    e[t < 0] = 0
    return e


def stereo(x, pan=0.0, width=0.0, r=None):
    """Equal-power pan; width adds a decorrelated short delay to the far side."""
    if x.ndim == 2:
        return x
    p = (pan + 1) * np.pi / 4
    L, R = np.cos(p) * x, np.sin(p) * x
    if width > 0:
        d = n_of(0.004 + 0.008 * width)
        R = np.concatenate([np.zeros(d), R[:-d]]) * (1 - 0.3 * width) + R * 0.3 * width
    return np.stack([L, R], axis=1)


def slowmo(x, factor):
    """Tape-style slow motion: stretch by 1/factor and pitch down (factor < 1)."""
    if factor >= 0.999:
        return x
    from fractions import Fraction
    fr = Fraction(factor).limit_denominator(40)
    up, down = fr.denominator, fr.numerator
    return signal.resample_poly(x, up, down, axis=0)


def saturate(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


# ---------------------------------------------------------------------- reverb (IR)
_IR_CACHE = {}


def reverb_ir(seconds=1.2, damp=3500, seed=7, early=True):
    key = (seconds, damp, seed, early)
    if key in _IR_CACHE:
        return _IR_CACHE[key]
    r = rng_for(seed)
    n = n_of(seconds)
    t = t_of(n)
    ir = np.zeros((n, 2))
    for c in range(2):
        nz = r.standard_normal(n) * np.exp(-t / (seconds / 6.9))
        nz = lp(nz, damp) * 0.6 + nz * 0.4 * np.exp(-t * 8)
        ir[:, c] = nz
    if early:
        for _ in range(10):
            d = r.uniform(0.008, 0.07)
            i = n_of(d)
            if i < n:
                ir[i, :] += r.uniform(0.2, 0.6) * np.array([r.uniform(0.6, 1), r.uniform(0.6, 1)])
    ir /= np.sqrt(np.sum(ir ** 2) / 2)
    _IR_CACHE[key] = ir
    return ir


def reverb(x, wet=0.25, seconds=1.2, damp=3500, seed=7):
    xs = stereo(x) if x.ndim == 1 else x
    ir = reverb_ir(seconds, damp, seed)
    out = np.zeros((len(xs) + len(ir) - 1, 2))
    for c in range(2):
        out[:, c] = signal.fftconvolve(xs[:, c], ir[:, c])
    dry = np.zeros_like(out)
    dry[:len(xs)] = xs
    return dry * (1 - wet * 0.5) + out * wet * 0.35


# ------------------------------------------------------------------- modal objects
def modal(freqs, decays, amps, dur, r, strike=0.002, noise=0.15, jitter=0.02):
    n = n_of(dur)
    t = t_of(n)
    y = np.zeros(n)
    for f, d, a in zip(freqs, decays, amps):
        f = f * (1 + r.uniform(-jitter, jitter))
        if f >= SR / 2 * 0.95:
            continue
        y += a * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28)) * np.exp(-t / d)
    if noise > 0:
        k = n_of(0.02)
        tr = r.standard_normal(k) * np.exp(-t_of(k) / strike)
        y[:k] += noise * hp(tr, 800) * np.max(np.abs(amps))
    att = n_of(0.0008)
    y[:att] *= np.linspace(0, 1, att)
    return y


def steel_clank(r, f0=None, dur=1.2, bright=1.0):
    f0 = f0 or r.uniform(180, 420)
    ratios = np.array([1, 2.76, 5.40, 8.93, 13.34, 18.64])
    dec = np.array([0.55, 0.35, 0.22, 0.14, 0.09, 0.06]) * r.uniform(0.7, 1.3)
    amp = np.array([1, 0.7, 0.55, 0.4, 0.3, 0.2]) * np.array([1, 1, bright, bright, bright, bright])
    y = modal(f0 * ratios, dec, amp, dur, r, noise=0.4)
    return norm(y)


def tube_clang(r, dur=1.4):
    f0 = r.uniform(380, 720)
    ratios = np.array([1, 2.32, 4.11, 6.18, 8.7, 11.4])
    y = modal(f0 * ratios, np.array([0.9, 0.6, 0.38, 0.25, 0.16, 0.1]) * r.uniform(0.7, 1.2), np.array([1, 0.8, 0.6, 0.45, 0.3, 0.2]), dur, r, noise=0.5)
    return norm(y)


def rebar_clink(r):
    f0 = r.uniform(900, 1800)
    ratios = np.array([1, 2.76, 5.40, 8.93])
    y = modal(f0 * ratios, np.array([0.18, 0.1, 0.06, 0.04]) * r.uniform(0.6, 1.4), np.array([1, 0.7, 0.5, 0.3]), 0.35, r, noise=0.3)
    return norm(y)


def wood_knock(r, f0=None, dur=0.25):
    f0 = f0 or r.uniform(170, 380)
    y = modal(f0 * np.array([1, 2.05, 3.3, 4.9]), np.array([0.05, 0.035, 0.022, 0.015]) * r.uniform(0.7, 1.5), np.array([1, 0.6, 0.4, 0.25]), dur, r, noise=0.8, strike=0.003)
    n = len(y)
    body = lp(white(n, r), 600) * exp_env(n, 0.018)
    return norm(y + 0.6 * body)


def hammer_hit(r, on='wood'):
    if on == 'steel':
        y = steel_clank(r, f0=r.uniform(600, 1100), dur=0.6, bright=1.3)
        k = wood_knock(r, f0=r.uniform(250, 400), dur=0.15)
        n = max(len(y), len(k))
        out = np.zeros(n)
        out[:len(y)] += y * 0.8
        out[:len(k)] += k * 0.5
        return norm(out)
    y = wood_knock(r)
    if r.random() < 0.5:  # nail ring
        ring = modal([r.uniform(2800, 4200), r.uniform(5200, 7400)], [0.05, 0.03], [0.3, 0.2], 0.2, r, noise=0)
        y[:len(ring)] += ring
    return norm(y)


def nail_gun(r):
    n = n_of(0.35)
    t = t_of(n)
    burst = bp(white(n, r), 900, 5000) * exp_env(n, 0.012)
    thump = np.sin(2 * np.pi * (110 + 60 * np.exp(-t / 0.01)) * t) * exp_env(n, 0.03)
    click = modal([r.uniform(3800, 5200), r.uniform(7000, 9000)], [0.012, 0.008], [1, 0.6], 0.35, r, noise=0)
    hiss = hp(white(n, r), 3500) * exp_env(n, 0.07, delay=0.01) * 0.35
    knock = wood_knock(r, f0=r.uniform(250, 420), dur=0.35)
    y = 0.9 * burst + 1.0 * thump + 0.5 * click + hiss
    y[:len(knock)] += 0.7 * knock[:n]
    return norm(y)


def tile_clack(r):
    n = n_of(0.25)
    click = bp(white(n, r), 2000, 7000) * exp_env(n, 0.004)
    ring = modal([r.uniform(1500, 2400), r.uniform(2900, 3800)], [0.03, 0.02], [0.6, 0.4], 0.25, r, noise=0)
    knock = lp(white(n, r), 300) * exp_env(n, 0.02)
    return norm(click + ring + 0.8 * knock)


def glass_land(r):
    n = n_of(2.2)
    t = t_of(n)
    thud = lp(white(n, r), 160) * exp_env(n, 0.09) * 1.4 + np.sin(2 * np.pi * 52 * t) * exp_env(n, 0.18)
    sq_n = n_of(0.22)
    st = t_of(sq_n)
    f = 700 + 500 * (st / st[-1]) + 60 * np.sin(2 * np.pi * 38 * st)
    squeak = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(sq_n) * 0.25
    ring = modal([2130, 3420, 5610, 7930], [0.9, 0.7, 0.5, 0.4], [0.18, 0.14, 0.1, 0.07], 2.2, r, noise=0)
    y = thud + ring
    d = n_of(0.05)
    y[d:d + sq_n] += squeak
    return norm(y)


def earth_impact(r, big=1.0):
    n = n_of(2.4)
    t = t_of(n)
    f = 30 + 45 * np.exp(-t / 0.09)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * exp_env(n, 0.38) * 1.2
    thud = lp(white(n, r), 220) * exp_env(n, 0.09) * 1.6
    crunch = np.zeros(n)
    # granular crunch: many tiny grains in the first 0.45 s
    for _ in range(int(260 * big)):
        st = int(abs(r.normal(0, 0.11)) * SR)
        L = n_of(r.uniform(0.002, 0.008))
        if st + L >= n:
            continue
        g = r.standard_normal(L) * np.exp(-np.arange(L) / (L / 3)) * r.uniform(0.2, 1)
        crunch[st:st + L] += g
    crunch = bp(crunch, 250, 3500) * 1.2
    # debris raining down
    deb = np.zeros(n)
    for _ in range(int(80 * big)):
        st = int(r.uniform(0.12, 1.7) * SR)
        L = n_of(r.uniform(0.004, 0.02))
        if st + L >= n:
            continue
        g = r.standard_normal(L) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(0.1, 0.6) * np.exp(-(st / SR) * 1.2)
        deb[st:st + L] += g
    deb = bp(deb, 1200, 7000)
    teeth = steel_clank(r, f0=r.uniform(240, 330), dur=0.8, bright=0.8) * 0.25
    y = sub + thud + crunch + deb * 0.7
    y[:len(teeth)] += teeth[:n]
    return norm(saturate(norm(y), 1.4))


def debris_spill(r, dur=1.2):
    """Dirt and stones pouring from a bucket into a truck bed."""
    n = n_of(dur)
    t = t_of(n)
    env = np.minimum(1, t / 0.08) * np.exp(-np.maximum(t - 0.3, 0) / 0.35)
    rumble = lp(brown(n, r), 300) * env
    grains = np.zeros(n)
    for _ in range(500):
        st = int(r.uniform(0, dur * 0.85) * SR)
        L = n_of(r.uniform(0.002, 0.012))
        if st + L >= n:
            continue
        grains[st:st + L] += r.standard_normal(L) * np.exp(-np.arange(L) / (L / 3)) * r.uniform(0.1, 1)
    grains = bp(grains, 400, 5000) * env
    bed = steel_clank(r, f0=r.uniform(90, 140), dur=1.0, bright=0.5) * 0.35
    y = rumble * 1.2 + grains
    y[:len(bed)] += bed[:n]
    return norm(y)


# --------------------------------------------------------------------- continuous
def diesel(n, rpm, load, r, cyl=6, bright=1.0):
    """Diesel engine: rpm/load are per-sample arrays."""
    f_fire = rpm / 60.0 * cyl / 2.0
    ph = np.cumsum(f_fire / SR)
    pulse = np.abs(np.sin(np.pi * ph)) ** 10
    cyc = np.floor(ph).astype(np.int64)
    jit = 0.7 + 0.6 * r.random(4096)
    pulse = pulse * jit[cyc % 4096]
    pulse -= lp(pulse, 15)
    half = np.sin(np.pi * ph + 0.3) * 0.25
    body = lp(pulse + half * 0.4, 700 + 900 * bright)
    body = peak_eq(body, 110, 6, 0.8)
    body = peak_eq(body, 450, 4, 1.2)
    clat = bp(white(n, r), 1200, 5200) * (0.25 + pulse) * (0.3 + load) * 0.25 * bright
    turbo_f = 1800 + 2400 * lp(load, 3)
    turbo = np.sin(2 * np.pi * np.cumsum(turbo_f) / SR) * 0.03 * load * bright
    exhaust = lp(brown(n, r), 160) * (0.4 + 0.6 * load) * 0.6
    y = body * (0.6 + 0.6 * load) + clat + turbo + exhaust
    return y / (np.std(y) * 4 + 1e-9)


def hydraulic(n, act, r):
    act = lp(np.clip(act, 0, 1), 12)
    f0 = 260 + 220 * act
    ph = np.cumsum(f0) / SR * 2 * np.pi
    tone = np.sin(ph) + 0.5 * np.sin(2 * ph + 0.4) + 0.25 * np.sin(3 * ph + 1.1)
    hiss = bp(white(n, r), 1800, 6500) * 0.35
    y = (tone * 0.4 + hiss) * act
    return y / 2.5


def electric_motor(n, speed, r):
    s = lp(np.clip(speed, 0, 1), 6)
    f0 = 85 + 140 * s
    ph = np.cumsum(f0) / SR * 2 * np.pi
    y = np.sin(ph) * 0.5 + np.sin(2 * ph) * 0.35 + np.sin(6.2 * ph) * 0.18 + np.sin(9.7 * ph) * 0.08
    gear = bp(white(n, r), 300, 1200) * 0.25
    return (y + gear) * s * 0.6


def winch_rattle(n, speed, r):
    s = np.clip(speed, 0, 1)
    rate = 18 + 60 * s
    ph = np.cumsum(rate) / SR
    ticks = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    k = n_of(0.006)
    kern = r.standard_normal(k) * np.exp(-np.arange(k) / (k / 3))
    y = signal.fftconvolve(ticks, kern)[:n]
    return bp(y, 1500, 7000) * s * 0.5


def concrete_flow(n, r, slow=1.0):
    gl = 0.5 + 0.5 * smooth_noise(n, 5 / slow, r)
    base = lp(brown(n, r), 380 * slow) * (0.5 + 0.7 * gl)
    slosh = bp(white(n, r), 180 * slow, 900 * slow) * (0.2 + 0.8 * np.clip(smooth_noise(n, 9 / slow, r), 0, 1)) * 0.5
    y = base + slosh
    # wet slaps
    for _ in range(int(n / SR * 6 / slow)):
        st = r.integers(0, n - 1)
        L = n_of(r.uniform(0.03, 0.09) / slow)
        if st + L >= n:
            continue
        y[st:st + L] += lp(r.standard_normal(L), 700 * slow) * np.exp(-np.arange(L) / (L / 3)) * r.uniform(0.6, 1.8)
    return y / (np.std(y) * 4 + 1e-9)


def pump_stroke(r, slow=1.0):
    n = n_of(0.6)
    t = t_of(n)
    knock = np.sin(2 * np.pi * 58 * t) * exp_env(n, 0.09) + lp(white(n, r), 200) * exp_env(n, 0.04)
    clunk = modal([118, 309, 561, 922], [0.12, 0.08, 0.05, 0.03], [0.6, 0.4, 0.3, 0.15], 0.6, r, noise=0.2)
    hiss = bp(white(n, r), 2000, 6000) * exp_env(n, 0.12, delay=0.04) * 0.25
    return slowmo(norm(knock + clunk + hiss), slow)


def vibrator(n, r):
    t = t_of(n)
    f = 185 + 6 * np.sin(2 * np.pi * 0.7 * t)
    ph = np.cumsum(f) / SR * 2 * np.pi
    y = np.sign(np.sin(ph)) * 0.3 + np.sin(2 * ph) * 0.3
    y = lp(y, 1600) * (0.8 + 0.2 * np.sin(2 * np.pi * 7 * t))
    return y * 0.5


def welding_arc(n, r, slow=1.0):
    t = t_of(n)
    # crackle: dense random impulses
    lam = 1300 * slow
    cnt = r.poisson(lam * n / SR)
    imp = np.zeros(n)
    pos = r.integers(0, n, cnt)
    imp[pos] = r.lognormal(0, 0.8, cnt)
    k = n_of(0.0025 / slow)
    kern = r.standard_normal(k) * np.exp(-np.arange(k) / (k / 4))
    crackle = bp(signal.fftconvolve(imp, kern)[:n], 900 * slow, 9000 * slow)
    hum_f = 100 * slow
    hum = (np.sin(2 * np.pi * hum_f * t) + 0.5 * np.sin(4 * np.pi * hum_f * t) + 0.3 * np.sin(6 * np.pi * hum_f * t)) * 0.18
    sizzle = hp(white(n, r), 4000 * slow) * (0.5 + 0.5 * smooth_noise(n, 11, r)) * 0.25
    y = crackle / (np.std(crackle) * 3 + 1e-9) + hum + sizzle
    return y * 0.5


def drill(dur, r, kind='drill'):
    n = n_of(dur)
    t = t_of(n)
    env = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.12)
    rpm = 0.6 + 0.4 * np.minimum(1, t / 0.15)
    f0 = (210 if kind == 'drill' else 160) * rpm * (1 + 0.03 * smooth_noise(n, 6, r))
    ph = np.cumsum(f0) / SR * 2 * np.pi
    y = sum(np.sin(k * ph) / k for k in range(1, 9))
    y = lp(y, 3500) + bp(white(n, r), 2000, 6000) * 0.15
    if kind == 'impact':
        y *= 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 34 * t))
        y += hp(white(n, r), 2500) * (np.sin(2 * np.pi * 34 * t) > 0.95) * 0.6
    return norm(y * env)


def grinder(dur, r):
    n = n_of(dur)
    t = t_of(n)
    env = np.minimum(1, t / 0.2) * np.minimum(1, (dur - t) / 0.25)
    f0 = 4600 * (0.8 + 0.2 * np.minimum(1, t / 0.3))
    whine = np.sin(2 * np.pi * np.cumsum(f0) / SR) * 0.25 + np.sin(2 * np.pi * np.cumsum(f0 / 2) / SR) * 0.15
    cut = bp(white(n, r), 1500, 9000) * (0.5 + 0.5 * np.clip(smooth_noise(n, 14, r), 0, 1))
    return norm((whine + cut * 0.6) * env)


def water_stream(n, r, slow=1.0):
    turb = 0.6 + 0.4 * smooth_noise(n, 22 / slow, r)
    jet = bp(white(n, r), 350 * slow, 2600 * slow) * turb
    splash = bp(white(n, r), 900 * slow, 6000 * slow) * np.clip(smooth_noise(n, 9 / slow, r), 0, 1) * 0.6
    y = jet + splash
    # bubbles
    cnt = int(n / SR * 70 / slow)
    for _ in range(cnt):
        st = r.integers(0, n - 1)
        L = n_of(r.uniform(0.02, 0.07) / slow)
        if st + L >= n:
            continue
        f0 = r.uniform(380, 1500) * slow
        tt = np.arange(L) / SR
        f = f0 * (1 + 3.5 * tt / (tt[-1] + 1e-6) * 0.15)
        y[st:st + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (L / SR / 3)) * r.uniform(0.2, 0.8)
    return y / (np.std(y) * 4 + 1e-9)


def footsteps(times, n, r, surface='gravel'):
    y = np.zeros(n)
    for tm in times:
        st = int(tm * SR)
        L = n_of(0.09)
        if st < 0 or st + L >= n:
            continue
        g = np.zeros(L)
        for _ in range(35):
            s = r.integers(0, L - n_of(0.004))
            k = n_of(r.uniform(0.001, 0.004))
            g[s:s + k] += r.standard_normal(k) * np.exp(-np.arange(k) / (k / 3)) * r.uniform(0.2, 1)
        if surface == 'gravel':
            g = bp(g, 900, 7000)
        else:
            g = bp(g, 200, 3000) + lp(r.standard_normal(L), 250) * exp_env(L, 0.015)
        y[st:st + L] += g * r.uniform(0.4, 1)
    return y


def beeper(dur, r, f=1150):
    n = n_of(dur)
    t = t_of(n)
    gate = ((t % 0.9) < 0.45).astype(float)
    gate = lp(gate, 200)
    y = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5))
    return lp(y * gate, 4000) * 0.5


def whoosh(dur, r, f0=300, f1=3000, pan0=-0.7, pan1=0.7, sub=0.5):
    n = n_of(dur)
    t = t_of(n)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    env = env * (1 - np.exp(-t / 0.02))
    base = white(n, r)
    # moving band-pass via short-time processing
    out = np.zeros(n)
    hop = n_of(0.01)
    win = np.hanning(hop * 2)
    for i in range(0, n - hop * 2, hop):
        c = f0 * (f1 / f0) ** (i / n)
        seg = base[i:i + hop * 2]
        seg = bp(seg, c * 0.6, min(c * 1.7, SR / 2 * 0.9))
        out[i:i + hop * 2] += seg * win
    low = lp(white(n, r), 140) * sub
    y = (out / (np.std(out) + 1e-9) * 0.35 + low * 0.5) * env
    pan = np.linspace(pan0, pan1, n)
    p = (pan + 1) * np.pi / 4
    return np.stack([np.cos(p) * y, np.sin(p) * y], axis=1) / 1.2


def riser(dur, r):
    n = n_of(dur)
    t = t_of(n)
    k = t / dur
    f = 180 * (8 ** k)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 + np.sin(2 * np.pi * np.cumsum(f * 1.01) / SR) * 0.12
    nz = bp(white(n, r), 800, 9000) * k ** 2 * 0.5
    y = (tone + nz) * k ** 1.6
    return norm(y)


def boom(r, dur=3.0, f_hi=62, f_lo=28, tail=1.4):
    n = n_of(dur)
    t = t_of(n)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.12)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * exp_env(n, tail * 0.55)
    hit = lp(white(n, r), 900) * exp_env(n, 0.05) * 0.7
    body = lp(brown(n, r), 120) * exp_env(n, 0.5) * 0.5
    return norm(saturate(sub + hit + body, 1.3))


def shing(r, dur=2.5):
    n = n_of(dur)
    y = modal([1830, 2470, 3690, 5120, 7020], [1.1, 0.9, 0.7, 0.5, 0.35], [0.5, 0.4, 0.3, 0.2, 0.12], dur, r, noise=0.6)
    y += hp(white(n, r), 5000) * exp_env(n, 0.25) * 0.4
    return norm(y)


def breaker_clunk(r):
    n = n_of(1.8)
    t = t_of(n)
    knock = np.sin(2 * np.pi * 88 * t) * exp_env(n, 0.06) + lp(white(n, r), 400) * exp_env(n, 0.02)
    click = modal([1180, 2710, 4400], [0.04, 0.03, 0.02], [0.5, 0.35, 0.2], 1.8, r, noise=0.3)
    hum = (np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 100 * t) + 0.25 * np.sin(2 * np.pi * 150 * t)) * np.minimum(1, t / 0.5) * np.exp(-t / 1.4) * 0.12
    return norm(knock + click + hum)


def drone(n, r, base=41.2):
    t = t_of(n)
    y = np.zeros(n)
    for k, (f, a) in enumerate([(base, 1.0), (base * 1.5, 0.45), (base * 2, 0.5), (base * 3.01, 0.15)]):
        for det in (-0.25, 0.25):
            y += a * np.sin(2 * np.pi * (f + det) * t + k)
    sweep = 0.5 + 0.5 * smooth_noise(n, 0.15, r)
    y = lp(y, 300) * (0.6 + 0.4 * sweep)
    return y / (np.std(y) * 3 + 1e-9)


def wind(n, r):
    y = lp(pink(n, r), 700)
    y *= 0.55 + 0.45 * smooth_noise(n, 0.35, r)
    return y / (np.std(y) * 3 + 1e-9)


def birds(n, r, density=0.6):
    y = np.zeros(n)
    t_total = n / SR
    for _ in range(int(t_total * density)):
        st = r.uniform(0, t_total - 1)
        notes = r.integers(2, 7)
        f0 = r.uniform(2400, 5200)
        for j in range(notes):
            L = n_of(r.uniform(0.04, 0.12))
            s = int((st + j * r.uniform(0.07, 0.16)) * SR)
            if s + L >= n:
                break
            tt = np.arange(L) / SR
            f = f0 * (1 + r.uniform(-0.25, 0.3) * tt / tt[-1]) + 300 * np.sin(2 * np.pi * r.uniform(20, 60) * tt)
            y[s:s + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(L) * r.uniform(0.2, 1)
    return y * 0.25


def crickets(n, r, voices=5):
    t = t_of(n)
    y = np.zeros(n)
    for v in range(voices):
        f = r.uniform(3900, 4900)
        rate = r.uniform(2.2, 3.6)
        pulse = (np.sin(2 * np.pi * rate * t + r.uniform(0, 6)) > 0.55).astype(float)
        pulse = lp(pulse, 60)
        am = 0.5 + 0.5 * np.sin(2 * np.pi * r.uniform(28, 40) * t)
        y += np.sin(2 * np.pi * f * t) * pulse * am * r.uniform(0.3, 1)
    return y / (voices * 2)

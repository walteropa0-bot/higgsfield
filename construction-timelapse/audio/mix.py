"""Build the 60 s soundtrack from the renderer's cue sheet.

    python3 mix.py cues.json soundtrack.wav

Layers: ambience, machinery (engines, hydraulics, crane, pump), Foley (tools, impacts,
materials), and cinematic design (dive rush, impacts, whooshes on every transition,
slow-motion swells, finale drone). Slow-motion shots get tape-style pitched-down audio,
fast time-lapse shots get accelerated engines and denser tool activity.
"""
import json
import sys
import numpy as np
import soundfile as sf
from sfx import *  # noqa: F401,F403
import sfx as S

cues = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'cues.json'))
OUT = sys.argv[2] if len(sys.argv) > 2 else 'soundtrack.wav'
DUR = cues['duration']
N = S.n_of(DUR + 0.5)
TS = np.arange(N) / S.SR
F = cues['frames']
FT = np.array([f['T'] for f in F])
R = S.rng_for(20261106)


def ctrl(key, default=0.0, fn=None):
    arr = np.array([(fn(f) if fn else f.get(key, default)) for f in F], float)
    return np.interp(TS, FT, arr)


def frame_at(t):
    i = int(np.clip(round(t * cues['rate']), 0, len(F) - 1))
    return F[i]


# micro-time rate (how fast machines/workers move on screen), per sample
Mv = np.array([f['M'] for f in F])
Mrate_f = np.gradient(Mv, FT)
Mrate_f = np.clip(Mrate_f, 0, 12)
Mrate = np.interp(TS, FT, Mrate_f)
camDist = ctrl('camDist')
close = np.clip((34 - camDist) / 24, 0, 1)
shots = cues['shots']

bus = {k: np.zeros((N, 2)) for k in ('amb', 'mach', 'foley', 'cine', 'verb')}


def db(x):
    return 10 ** (x / 20)


def place(name, x, t, gain_db=0.0, pan=0.0, width=0.3, verb=0.15):
    if t < -1 or t > DUR + 0.5:
        return
    y = S.stereo(x, pan, width) if x.ndim == 1 else x
    s = int(round(t * S.SR))
    a, b = max(0, s), min(N, s + len(y))
    if b <= a:
        return
    seg = y[a - s:b - s] * db(gain_db)
    bus[name][a:b] += seg
    if verb > 0:
        bus['verb'][a:b] += seg * verb


def mrate_at(t):
    return float(np.interp(t, FT, Mrate_f))


def slow_factor(t):
    m = mrate_at(t)
    return 1.0 if m >= 0.95 else float(np.clip(0.35 + 0.65 * m, 0.45, 1.0))


def persp(t):
    return float(np.interp(t, TS[::480], close[::480]))


# --------------------------------------------------------------------- ambience
amb_gain = np.ones(N)
dusk = np.clip((TS - 45.5) / 3.0, 0, 1)
w = S.wind(N, R)
bus['amb'] += S.stereo(w, 0, 0.8) * (db(-17) * (1 - 0.5 * close) * (1 - 0.35 * dusk))[:, None]
b = S.birds(N, R, density=0.5)
bus['amb'] += S.stereo(S.hp(b, 1500), 0.3, 0.9) * (db(-21) * (1 - dusk) * (1 - 0.6 * close))[:, None]
site = S.lp(S.brown(N, R), 140)
site_on = np.clip((TS - 1.0) / 0.5, 0, 1) * (1 - np.clip((TS - 44.5) / 2, 0, 1))
bus['amb'] += S.stereo(site / (np.std(site) * 4), 0, 0.5) * (db(-16) * site_on)[:, None]
cr = S.crickets(N, R, voices=7)
bus['amb'] += S.stereo(cr, -0.2, 1.0) * (db(-15) * dusk)[:, None]
ev_w = S.lp(S.pink(N, R), 2500) * (0.6 + 0.4 * S.smooth_noise(N, 0.2, R))
bus['amb'] += S.stereo(ev_w / (np.std(ev_w) * 4), 0.1, 1.0) * (db(-16) * dusk)[:, None]

# ---------------------------------------------------------------- excavators
ex = np.clip(ctrl('ex1') + 0.7 * ctrl('ex2'), 0, 1.4)
ph = (ctrl('M') / 11.0) % 1.0
load = np.where((ph > 0.12) & (ph < 0.5), 1.0, np.where((ph > 0.5) & (ph < 0.72), 0.6, 0.25))
load = S.lp(load, 6)
acc = np.clip(Mrate / 8, 0, 1)
pitch = np.where(Mrate < 0.95, np.clip(0.4 + 0.6 * Mrate, 0.45, 1.0), 1.0)
pitch = S.lp(pitch, 4)
rpm = (950 + 650 * load + 350 * acc) * pitch
eng = S.diesel(N, rpm, load, R, cyl=6)
bus['mach'] += S.stereo(eng, -0.15, 0.4) * (db(-9) * ex * (0.55 + 0.45 * close))[:, None]
hyd_act = np.clip(np.abs(np.gradient(S.lp(load, 3))) * S.SR * 0.08 + 0.25 * load, 0, 1) * ex
bus['mach'] += S.stereo(S.hydraulic(N, hyd_act, R), 0.1, 0.5) * (db(-14) * (0.5 + 0.5 * close))[:, None]

# ------------------------------------------------------------------- trucks
tr = ctrl('trucks') / 2
truck_rpm = (800 + 700 * np.clip(0.5 + 0.5 * S.smooth_noise(N, 1.5, R), 0, 1)) * (0.8 + 0.3 * acc)
teng = S.diesel(N, truck_rpm, 0.5 + 0.4 * S.smooth_noise(N, 1.2, R), R, cyl=8, bright=0.7)
bus['mach'] += S.stereo(teng, 0.35, 0.6) * (db(-14) * tr)[:, None]

# -------------------------------------------------------------- pump + pour
pump = ctrl('pump')
pour = S.lp(ctrl('pour'), 8)
peng = S.diesel(N, 1300 + 200 * pour, 0.3 + 0.5 * pour, R, cyl=6, bright=0.8)
bus['mach'] += S.stereo(peng, 0.4, 0.5) * (db(-17) * pump)[:, None]
# pump strokes
phase, last = 0.0, 0
for i in range(0, N, 240):
    t = i / S.SR
    if pour[i] > 0.3:
        phase += 240 / S.SR * 1.25 * np.clip(Mrate[i], 0.3, 2.2)
        if int(phase) != last:
            last = int(phase)
            sf_ = slow_factor(t)
            place('mach', S.pump_stroke(R, sf_), t, -6 + 4 * persp(t), pan=0.3, verb=0.25)
flow_slow = np.clip(0.4 + 0.6 * Mrate, 0.5, 1.0)
fl_a = S.concrete_flow(N, R, slow=1.0)
fl_b = S.concrete_flow(N, R, slow=0.55)
slowmix = np.clip((1 - flow_slow) / 0.45, 0, 1)
flow = fl_a * (1 - slowmix) + fl_b * slowmix
bus['foley'] += S.stereo(flow, -0.1, 0.5) * (db(-6) * pour * (0.45 + 0.55 * close))[:, None]
bus['foley'] += S.stereo(S.vibrator(N, R), 0.2, 0.3) * (db(-22) * pour)[:, None]

# --------------------------------------------------------------------- crane
crane = ctrl('crane')
ca, cr_, ch = ctrl('ca'), ctrl('cr'), ctrl('ch')
slew = np.abs(np.gradient(np.unwrap(ca))) * S.SR * cr_
hoist = np.abs(np.gradient(ch)) * S.SR
spd = np.clip(S.lp(slew / 18 + hoist / 6, 3), 0, 1) * crane
bus['mach'] += S.stereo(S.electric_motor(N, spd, R), 0.25, 0.6) * (db(-12) * (0.6 + 0.4 * close))[:, None]
bus['mach'] += S.stereo(S.winch_rattle(N, np.clip(hoist / 6, 0, 1) * crane, R), 0.3, 0.6) * db(-20)

# ---------------------------------------------------------- loader + beeper
ld = ctrl('loader')
leng = S.diesel(N, 1700 + 500 * S.smooth_noise(N, 1.0, R), 0.6 + 0.3 * S.smooth_noise(N, 1.4, R), R, cyl=4, bright=1.1)
bus['mach'] += S.stereo(leng, -0.3, 0.5) * (db(-12) * ld)[:, None]
for t0 in np.arange(41.6, 45.6, 1.7):
    place('mach', S.beeper(0.9, R) * 0.6, t0, -20, pan=-0.4, verb=0.4)
for t0 in (4.2, 5.6):
    place('mach', S.beeper(0.9, R, f=1050) * 0.6, t0, -19, pan=0.5, verb=0.4)

# ------------------------------------------------------------------ welding
weld = ctrl('weld')
arc = S.welding_arc(N, R, slow=0.55)
bus['foley'] += S.stereo(arc, 0.1, 0.4) * (db(-3) * S.lp(weld, 20))[:, None]

# --------------------------------------------------------------- pool water
water = S.lp(ctrl('water'), 6)
wslow = np.clip(0.35 + 0.65 * Mrate, 0.5, 1.0)
w_fast = S.water_stream(N, R, slow=1.0)
w_slow = S.water_stream(N, R, slow=0.55)
wm = np.clip((1 - wslow) / 0.45, 0, 1)
wst = w_fast * (1 - wm) + w_slow * wm
bus['foley'] += S.stereo(wst, -0.15, 0.6) * (db(-4) * water * (0.5 + 0.5 * close))[:, None]

# ----------------------------------------------------------- crew activity
crew = {k: ctrl(None, fn=lambda f, k=k: f['crew'].get(k, 0)) for k in ('hammer', 'nail', 'crouch', 'walk', 'weld', 'guide')}
for i in range(0, N - 480, 480):  # 10 ms steps
    t = i / S.SR
    m = Mrate[i]
    sp = np.clip(m / 4, 0.25, 2.0)
    pc = persp(t)
    lam_h = (crew['hammer'][i] * 2.2 + crew['nail'][i] * 1.4) * sp
    if R.random() < lam_h * 0.01:
        on = 'steel' if R.random() < 0.3 else 'wood'
        place('foley', S.hammer_hit(R, on), t + R.uniform(0, 0.01), -15 + 8 * pc, pan=R.uniform(-0.7, 0.7), verb=0.3)
    lam_c = crew['crouch'][i] * 1.4 * sp
    if R.random() < lam_c * 0.01:
        place('foley', S.rebar_clink(R) * 0.6, t, -22 + 8 * pc, pan=R.uniform(-0.8, 0.8), verb=0.2)
    lam_w = crew['walk'][i] * 1.8 * np.clip(m / 3, 0.3, 2.5)
    if R.random() < lam_w * 0.01:
        fs = S.footsteps([0.0], S.n_of(0.12), R, 'gravel')
        place('foley', fs, t, -24 + 9 * pc, pan=R.uniform(-0.6, 0.6), verb=0.1)

# random power-tool bursts while the shell/fit-out is underway (wide-shot atmosphere)
Dv = ctrl('D')
for i in range(0, N, S.SR // 10):
    t = i / S.SR
    if 18 < Dv[i] < 106 and frame_at(t)['shot'] not in ('weld-slowmo', 'glass-slowmo', 'pool-fill', 'pour-slowmo') and R.random() < 0.11:
        kind = R.choice(['drill', 'impact', 'grinder'], p=[0.45, 0.35, 0.2])
        d = R.uniform(0.25, 0.9)
        x = S.grinder(d, R) if kind == 'grinder' else S.drill(d, R, kind)
        place('foley', x, t, -21 + 5 * persp(t), pan=R.uniform(-0.8, 0.8), verb=0.35)

# --------------------------------------------------------- discrete events
ev = cues['events']
by = {}
for e in ev:
    key = e['type'] + (':' + e['kind'] if 'kind' in e else '') + (':' + e['load'] if 'load' in e else '')
    by.setdefault(key, []).append(e)


def thin(lst, cap):
    """Keep at most `cap` events per second (randomly), preserving distribution."""
    out = []
    times = np.array([e['t'] for e in lst])
    for e in lst:
        local = np.sum(np.abs(times - e['t']) < 0.25) / 0.5
        if R.random() < min(1, cap / max(local, 1e-6)):
            out.append(e)
    return out


def at(e, dt=0.0):
    return e['t'] + dt + R.uniform(-0.004, 0.004)


# bucket strikes: the hook strike is the hero impact
for e in by.get('bucketStrike', []):
    t = e['t']
    if t < 2.0:
        sf_ = 0.55
        place('foley', S.slowmo(S.earth_impact(R, big=1.6), sf_), t - 0.01, -1, pan=0.05, verb=0.35)
        place('cine', S.boom(R, 3.5, 70, 26, 1.8), t - 0.005, -3, pan=0, verb=0.4)
        place('cine', S.whoosh(0.9, R, 2500, 200, 0.4, -0.2, sub=0.9), t - 0.05, -14, verb=0.2)
    else:
        sf_ = slow_factor(t)
        place('foley', S.slowmo(S.earth_impact(R, big=0.8), sf_), t, -9 + 6 * persp(t), pan=R.uniform(-0.3, 0.3), verb=0.3)
for e in by.get('bucketDump', []):
    place('foley', S.slowmo(S.debris_spill(R, 1.3), slow_factor(e['t'])), e['t'], -9 + 5 * persp(e['t']), pan=R.uniform(-0.4, 0.4), verb=0.3)

for e in thin(by.get('piece:rebar', []), 12):
    place('foley', S.rebar_clink(R), at(e), -18 + 7 * persp(e['t']), pan=R.uniform(-0.8, 0.8), verb=0.25)
for e in thin(by.get('piece:scaffold', []) + by.get('remove:scaffold', []), 9):
    place('foley', S.tube_clang(R), at(e), -17 + 6 * persp(e['t']), pan=R.uniform(-0.8, 0.8), verb=0.35)
for e in thin(by.get('piece:plank', []) + by.get('remove:plank', []), 5):
    place('foley', S.wood_knock(R, f0=R.uniform(120, 200), dur=0.3), at(e), -15, pan=R.uniform(-0.6, 0.6), verb=0.3)
for e in thin(by.get('piece:prop', []) + by.get('remove:prop', []), 7):
    place('foley', S.steel_clank(R, f0=R.uniform(500, 900), dur=0.6), at(e), -21 + 6 * persp(e['t']), pan=R.uniform(-0.8, 0.8), verb=0.3)
for e in thin(by.get('piece:paver', []), 11):
    place('foley', S.tile_clack(R), at(e), -15 + 6 * persp(e['t']), pan=R.uniform(-0.8, 0.8), verb=0.2)
for e in thin(by.get('piece:frame', []), 4):
    place('foley', S.drill(R.uniform(0.15, 0.3), R, 'impact'), at(e), -19, pan=R.uniform(-0.6, 0.6), verb=0.3)
for e in by.get('piece:slat', []):
    t = e['t']
    shot = frame_at(t)['shot']
    g = -4 if shot == 'slats-track' else -18
    place('foley', S.nail_gun(R), at(e), g, pan=R.uniform(-0.4, 0.4), verb=0.2)
    if R.random() < 0.7:
        place('foley', S.nail_gun(R), at(e, 0.07), g - 3, pan=R.uniform(-0.4, 0.4), verb=0.2)
for e in by.get('start:formwork', []):
    for k in range(4):
        place('foley', S.hammer_hit(R, 'wood'), at(e, k * 0.06), -14, pan=R.uniform(-0.7, 0.7), verb=0.3)
for e in by.get('lift:formwork', []):
    place('foley', S.steel_clank(R, f0=R.uniform(150, 260), dur=1.2, bright=0.7), at(e), -13, pan=R.uniform(-0.6, 0.6), verb=0.4)
for e in by.get('start:timber', []) + by.get('lift:timber', []) + by.get('start:plywood', []):
    for k in range(2):
        place('foley', S.wood_knock(R, f0=R.uniform(110, 200), dur=0.35), at(e, k * 0.09), -14, pan=R.uniform(-0.6, 0.6), verb=0.3)
for e in by.get('land:glass', []):
    t = e['t']
    hero = frame_at(t)['shot'] == 'glass-slowmo'
    place('foley', S.slowmo(S.glass_land(R), 0.6 if hero else 1.0), at(e), -2 if hero else -14, pan=0.1, verb=0.35)
for e in by.get('craneRelease:form', []) + by.get('craneRelease:beam', []) + by.get('craneRelease:pallet', []) + by.get('craneRelease:rebar', []):
    place('foley', S.steel_clank(R, f0=R.uniform(110, 220), dur=1.0, bright=0.6), at(e), -18 + 5 * persp(e['t']), pan=R.uniform(-0.5, 0.5), verb=0.4)
for e in by.get('start:pour', []) + by.get('start:shotcrete', []):
    place('foley', S.slowmo(S.debris_spill(R, 0.8), slow_factor(e['t'])), e['t'], -14, pan=0, verb=0.3)
for e in by.get('start:membrane', []):
    n = S.n_of(1.6)
    roar = S.lp(S.white(n, R), 900) * (0.6 + 0.4 * S.smooth_noise(n, 12, R)) * np.hanning(n)
    place('foley', S.norm(roar), e['t'], -15, pan=0.2, verb=0.3)
for e in by.get('start:gravel', []):
    place('foley', S.debris_spill(R, 1.5), e['t'], -15, pan=-0.2, verb=0.3)
for e in by.get('start:tile', []):
    for k in range(6):
        place('foley', S.tile_clack(R), at(e, k * 0.11), -17, pan=R.uniform(-0.6, 0.6), verb=0.2)
for e in by.get('start:floor', []):
    for k in range(5):
        place('foley', S.wood_knock(R, f0=R.uniform(160, 260), dur=0.25), at(e, k * 0.08), -20, pan=R.uniform(-0.6, 0.6), verb=0.2)
for e in thin(by.get('start:item', []), 3):
    place('foley', S.wood_knock(R, f0=R.uniform(90, 150), dur=0.3), at(e), -24, pan=R.uniform(-0.5, 0.5), verb=0.3)

# landscaping (not in the cue sheet): tree drops, turf rolls, fence panels coming down
def T_of_D(d, shot=None):
    for f in F:
        if (shot is None or f['shot'] == shot) and f['D'] >= d:
            return f['T']
    return None


for i in range(8):
    t = T_of_D(110.2 + i * 0.6 + 0.45)
    if t is not None:
        n = S.n_of(1.2)
        thud = S.lp(S.white(n, R), 140) * S.exp_env(n, 0.08) * 1.5 + np.sin(2 * np.pi * 48 * np.arange(n) / S.SR) * S.exp_env(n, 0.2)
        place('foley', S.norm(thud), t, -9, pan=R.uniform(-0.6, 0.6), verb=0.35)
        place('foley', S.debris_spill(R, 0.8), t + 0.05, -17, pan=R.uniform(-0.6, 0.6), verb=0.3)
for d in np.arange(109.2, 115.0, 0.18):
    t = T_of_D(d, 'master-landscape')
    if t is not None:
        place('foley', S.wood_knock(R, f0=R.uniform(70, 110), dur=0.3), t, -19, pan=R.uniform(-0.7, 0.7), verb=0.25)
for d in np.arange(113.4, 115.6, 0.09):
    t = T_of_D(d, 'master-landscape')
    if t is not None and R.random() < 0.6:
        place('foley', S.tube_clang(R) * 0.7, t, -21, pan=R.uniform(-0.9, 0.9), verb=0.35)

# wrap-up: loader reversing off site, brooms sweeping the deck, then the sunset swell
place('mach', S.beeper(1.8, R, f=1100) * 0.7, 44.1, -17, pan=-0.5, verb=0.45)
for k in range(9):
    n = S.n_of(0.35)
    sweep = S.bp(S.white(n, R), 1500, 7000) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    place('foley', S.norm(sweep), 43.9 + k * 0.24 + R.uniform(0, 0.05), -21, pan=R.uniform(-0.5, 0.5), verb=0.2)
n = S.n_of(2.6)
swell = S.lp(S.pink(n, R), 1800) * np.linspace(0, 1, n) ** 2.2
place('cine', S.norm(swell), 45.9, -17, width=1.0, verb=0.6)
place('cine', S.riser(2.3, R), 46.0, -24, verb=0.5)

# lights at dusk – satisfying breaker clunks, pool "whoom", garden lights
for e in by.get('lightOn', []):
    place('foley', S.breaker_clunk(R), at(e), -9, pan=R.uniform(-0.5, 0.5), verb=0.45)
for e in by.get('poolLight', []):
    place('cine', S.boom(R, 2.5, 90, 40, 1.0), e['t'], -12, verb=0.5)
    place('foley', S.breaker_clunk(R), e['t'], -8, pan=0.2, verb=0.45)
for e in by.get('gardenLight', []):
    place('foley', S.breaker_clunk(R), e['t'], -10, pan=-0.3, verb=0.45)

# --------------------------------------------------------- cinematic design
# FPV dive: wind rush rising into the first impact
dive = S.whoosh(1.15, R, 250, 2600, -0.5, 0.3, sub=0.8)
place('cine', dive, 0.0, -9, verb=0.1)
place('cine', S.riser(1.0, R), 0.05, -20, verb=0.2)
# shake rumble after the hero strike
n = S.n_of(1.2)
rum = S.lp(S.brown(n, R), 90) * S.exp_env(n, 0.35)
place('cine', S.norm(rum), 1.07, -8, verb=0.2)

# transitions: every cut gets a designed whoosh / hit
for s0, s1 in zip(shots[:-1], shots[1:]):
    t = s0['t1']
    kind = s0.get('out') or s1.get('in') or 'cut'
    if kind in ('whip-r', 'whip-l'):
        dirn = 1 if kind == 'whip-r' else -1
        place('cine', S.whoosh(0.42, R, 500, 4200, -0.8 * dirn, 0.8 * dirn, sub=0.6), t - 0.23, -7, verb=0.15)
    elif kind in ('tiltup', 'riseup'):
        place('cine', S.whoosh(0.55, R, 300, 3800, 0, 0, sub=0.7), t - 0.32, -8, verb=0.2)
    elif kind == 'tiltdown':
        place('cine', S.whoosh(0.55, R, 3600, 300, 0, 0, sub=0.7), t - 0.3, -8, verb=0.2)
    elif kind == 'punch':
        place('cine', S.whoosh(0.32, R, 700, 5000, 0, 0, sub=0.5), t - 0.22, -8, verb=0.1)
        place('cine', S.boom(R, 2.0, 80, 35, 0.9), t, -10, verb=0.3)
    elif kind == 'pullback':
        place('cine', S.whoosh(0.5, R, 4200, 400, 0.3, -0.3, sub=0.6), t - 0.25, -9, verb=0.2)
    elif kind == 'flash':
        place('cine', S.shing(R), t - 0.02, -9, verb=0.5)
        place('cine', S.boom(R, 3.0, 66, 28, 1.6), t, -4, verb=0.4)
    elif kind == 'dissolve':
        n = S.n_of(1.6)
        sw = S.bp(S.white(n, R), 300, 6000) * np.sin(np.pi * np.linspace(0, 1, n)) ** 3
        place('cine', S.norm(sw), t - 0.9, -21, width=1.0, verb=0.6)
    elif kind == 'cut':
        place('cine', S.boom(R, 3.0, 55, 26, 1.8), t, -10, verb=0.5)

# slow-motion entries/exits: tape-stop style swells and speed-ramp risers
for t, kind in [(8.42, 'in'), (10.35, 'out'), (15.02, 'in'), (25.02, 'in'), (38.42, 'in'), (39.75, 'out'), (1.62, 'out')]:
    if kind == 'in':
        place('cine', S.whoosh(0.7, R, 2400, 180, 0.2, -0.2, sub=1.0), t - 0.1, -13, verb=0.3)
    else:
        place('cine', S.riser(0.75, R), t, -15, verb=0.2)
        place('cine', S.whoosh(0.6, R, 200, 2600, -0.2, 0.2, sub=0.7), t + 0.15, -13, verb=0.2)

# low cinematic bed: subtle throughout, swelling for the reveal
dr = S.drone(N, R)
dgain = np.full(N, db(-27)) * np.clip(TS / 1.0, 0, 1)
dgain = np.where(TS > 44.5, db(-24) + (db(-11) - db(-24)) * np.clip((TS - 44.5) / 9, 0, 1), dgain)
bus['cine'] += S.stereo(dr, 0, 1.0) * dgain[:, None]
place('cine', S.boom(R, 4.0, 48, 24, 2.6), 56.0, -9, verb=0.6)
n = S.n_of(9.0)
shim = S.modal([523.3, 659.3, 784.0, 1046.5, 1318.5], [3.5, 3.0, 2.6, 2.2, 1.8], [0.5, 0.35, 0.3, 0.2, 0.12], 9.0, R, noise=0) * np.clip(np.linspace(0, 3, n), 0, 1)
place('cine', S.norm(S.lp(shim, 4000)), 51.4, -24, width=1.0, verb=0.8)
lap = S.bp(S.white(N, R), 250, 1600) * np.clip(S.smooth_noise(N, 1.3, R), 0, 1) ** 2
bus['amb'] += S.stereo(lap / (np.std(lap) * 4 + 1e-9), 0.2, 0.8) * (db(-20) * np.clip((TS - 47) / 3, 0, 1))[:, None]

# ------------------------------------------------------------ bus mixdown
verb = S.reverb(bus['verb'], wet=1.0, seconds=1.6, damp=4200, seed=11)[:N]
mix = bus['amb'] * db(0) + bus['mach'] * db(-1) + bus['foley'] * db(0) + bus['cine'] * db(-1) + verb * db(-6)
# tone: deeper low end for the "mechanical" weight, tame harshness
mix = S.shelf_low(mix, 120, 3.0)
mix = S.peak_eq(mix, 3200, -1.5, 0.8)
mix = S.hp(mix, 25)


def compress(x, thr_db=-18, ratio=3.0, att=0.005, rel=0.12):
    lvl = np.sqrt(S.lp(np.mean(x ** 2, axis=1), 30) + 1e-12)
    ldb = 20 * np.log10(lvl)
    over = np.maximum(ldb - thr_db, 0)
    gr = -over * (1 - 1 / ratio)
    g = 10 ** (gr / 20)
    a, r_ = np.exp(-1 / (att * S.SR)), np.exp(-1 / (rel * S.SR))
    out = np.empty_like(g)
    cur = 1.0
    for i in range(0, len(g), 64):
        tgt = g[i]
        k = a if tgt < cur else r_
        cur = tgt + (cur - tgt) * k ** 64
        out[i:i + 64] = cur
    return x * out[:, None]


mix = compress(mix, thr_db=-20, ratio=2.5)
# end: smooth fade on the final second
fade_t = np.clip((DUR - TS) / 1.2, 0, 1)
mix *= fade_t[:, None] ** 1.5
mix = mix[:S.n_of(DUR)]


def lufs(x):
    """ITU-R BS.1770 integrated loudness (48 kHz K-weighting, gated)."""
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * S.SR), int(0.1 * S.SR)
    ms = np.array([np.sum(np.mean(y[i:i + blk] ** 2, axis=0)) for i in range(0, len(y) - blk, hop)])
    L = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[L > -70]
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10
    g2 = ms[(L > -70) & (L > rel)]
    return -0.691 + 10 * np.log10(np.mean(g2))


def limit(x, ceiling=0.86, look=0.004, rel=0.06):
    from scipy.ndimage import maximum_filter1d, minimum_filter1d
    a = np.max(np.abs(x), axis=1)
    w = max(1, int(look * S.SR))
    pk = maximum_filter1d(a, size=2 * w + 1)
    g = np.minimum(1.0, ceiling / (pk + 1e-12))
    g = minimum_filter1d(g, size=2 * w + 1)
    k = np.exp(-1 / (rel * S.SR))
    from scipy.signal import lfilter
    gs = lfilter([1 - k], [1, -k], g - 1) + 1  # smooth release
    gs = np.minimum(gs, g)
    y = x * gs[:, None]
    return np.clip(y, -ceiling, ceiling)


target = -14.0
for it in range(3):
    cur = lufs(mix)
    mix = mix * db(target - cur)
    mix = limit(mix)
print('integrated loudness %.2f LUFS, peak %.3f' % (lufs(mix), np.max(np.abs(mix))))
sf.write(OUT, mix.astype(np.float32), S.SR, subtype='PCM_24')

# report
for k in ('amb', 'mach', 'foley', 'cine'):
    x = bus[k][:S.n_of(DUR)]
    print(f'{k:6s} rms {20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9):6.1f} dB  peak {20 * np.log10(np.max(np.abs(x)) + 1e-9):6.1f} dB')
print('wrote', OUT, len(mix) / S.SR, 's')

#!/usr/bin/env python3
"""A/V sync check.
1) Global: cross-correlate the AAC audio decoded from final.mp4 against the master WAV -> lag must be ~0 samples
   (catches encoder priming / edit-list problems).
2) Local: for salient cues from the timeline, measure the transient onset in the decoded audio and report the
   offset to the cue frame (frame f <-> t = f / 60 s)."""
import json, subprocess, sys, wave, numpy as np

ROOT = __file__.rsplit('/tools/', 1)[0]
SR = 48000

def load_wav(p):
    w = wave.open(p); n = w.getnframes(); raw = w.readframes(n)
    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
    v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
    v = np.where(v >= 1 << 23, v - (1 << 24), v) / 8388607.0
    return v.reshape(-1, 2).mean(axis=1)

def decode(mp4):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-map', '0:a', '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

ref = load_wav(f'{ROOT}/out/mix.wav')
dec = decode(f'{ROOT}/out/final.mp4')
print(f'samples: master {len(ref)}  decoded {len(dec)}  ({len(dec)/SR:.4f} s)')

def lag_at(a, b, start, length=SR * 2, maxlag=4800):
    x = a[start:start + length]; y = b[start:start + length]
    n = 1 << int(np.ceil(np.log2(len(x) + len(y))))
    c = np.fft.irfft(np.fft.rfft(y, n) * np.conj(np.fft.rfft(x, n)), n)
    c = np.concatenate([c[-maxlag:], c[:maxlag + 1]])
    return int(np.argmax(c)) - maxlag

for f0 in (0, 600, 960, 1440):
    print(f'global lag @F{f0}: {lag_at(ref, dec, f0 * 800)} samples')

# local onset check
cues = json.loads(subprocess.run(['node', '-e', "const T=require('" + ROOT + "/src/timeline.js'); console.log(JSON.stringify(T.EVENTS.map(e=>[e.f,e.type])))"],
                                 capture_output=True, text=True, check=True).stdout)
pick = {'impact', 'notif', 'bigImpact', 'cut', 'shatter', 'tap', 'ping', 'beatReturn', 'label'}
hp = np.diff(dec, prepend=0.0)                       # crude high-pass emphasises transients
env = np.sqrt(np.convolve(hp * hp, np.ones(48) / 48, mode='same'))
rows = []
for f, t in cues:
    if t not in pick or f < 0: continue
    c = int(round(f * 800)); a, b = c - 600, c + 600
    seg = env[a:b]
    base = np.median(env[max(0, c - 4800):c - 800]) + 1e-9
    d = np.diff(np.log(seg + base))                  # steepest relative rise = onset
    on = a + int(np.argmax(d))
    rows.append((t, f, (on - c) / SR * 1000))
for t, f, ms in rows:
    print(f'  {t:11s} F{f:>7.2f}  onset offset {ms:+6.1f} ms')
offs = np.array([r[2] for r in rows])
print(f'local onset offsets: median {np.median(offs):+.1f} ms, max |{np.max(np.abs(offs)):.1f}| ms  (1 frame = 16.7 ms)')

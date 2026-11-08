"""Procedural music bed for YT01 (numpy only, 48 kHz stereo): warm pads + soft pluck arpeggio + sub bass,
one chord progression per chapter, convolution reverb. Royalty-free by construction.

Usage (from mix.py): bed = make_bed(duration, sections) with sections = [(t_start, name), ...]
"""
import math

import numpy as np

SR = 48000
BPM = 72
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORD_LEN = 2 * BAR  # 6.67 s per chord

# chord tones as MIDI numbers (pad voicing) + bass root
CH = {
    "Am": ([57, 60, 64, 67], 45), "Am9": ([57, 60, 64, 67, 71], 45), "F": ([53, 57, 60, 64], 41),
    "Fmaj7": ([53, 57, 60, 64], 41), "C": ([55, 60, 64, 67], 48), "Cmaj7": ([55, 59, 64, 67], 48),
    "G": ([55, 59, 62, 67], 43), "Em": ([55, 59, 64, 67], 40), "Dm": ([53, 57, 62, 65], 38),
    "E": ([56, 59, 64, 68], 40), "Bb": ([53, 58, 62, 65], 46),
}
PROG = {
    "intro": ["Am9", "Fmaj7"], "ch1": ["Am", "F", "C", "G"], "ch2": ["F", "G", "Am", "Am"],
    "ch3": ["Am", "Em", "F", "G"], "ch4": ["Dm", "Am", "E", "Am"], "ch5": ["F", "C", "G", "Am"],
    "ch6": ["Am", "G", "F", "E"], "ch7": ["C", "G", "Am", "F"], "end": ["Fmaj7", "Cmaj7"],
}
PLUCK = {"intro": 0.0, "ch1": 1.0, "ch2": 1.0, "ch3": 1.0, "ch4": 0.55, "ch5": 1.0, "ch6": 0.9, "ch7": 1.0, "end": 0.0}

rng = np.random.default_rng(72)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord_plan(duration, sections):
    """list of (t0, t1, chord, section) on a bar grid, progression restarts at each section"""
    out = []
    for i, (ts, name) in enumerate(sections):
        te = sections[i + 1][0] if i + 1 < len(sections) else duration
        prog = PROG[name]
        t, k = ts, 0
        while t < te - 0.01:
            out.append((t, min(te, t + CHORD_LEN), prog[k % len(prog)], name))
            t += CHORD_LEN
            k += 1
    return out


def _pad_note(f0, n, ph):
    tt = np.arange(n) / SR
    x = np.zeros(n)
    for det in (-0.0023, 0.0, 0.0021):
        for h, amp in ((1, 1.0), (2, 0.32), (3, 0.14), (4, 0.06)):
            x += amp * np.sin(2 * np.pi * f0 * (1 + det) * h * tt + ph[h - 1])
    return x


def make_bed(duration, sections):
    n = int(duration * SR) + SR
    pad = np.zeros((n, 2))
    bass = np.zeros(n)
    pl = np.zeros((n, 2))
    xf = 1.6  # cross-fade between chords (s)
    for t0, t1, ch, sec in chord_plan(duration, sections):
        notes, root = CH[ch]
        a, b = int(max(0, t0 - xf / 2) * SR), int(min(duration + 1, t1 + xf / 2) * SR)
        m = b - a
        if m <= 0:
            continue
        env = np.ones(m)
        k = int(xf * SR)
        k = min(k, m // 2)
        env[:k] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k))
        env[-k:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, k))
        trem = 1 + 0.06 * np.sin(2 * np.pi * 0.11 * (np.arange(m) / SR) + rng.uniform(0, 6))
        for ci in range(2):
            acc = np.zeros(m)
            for note in notes:
                acc += _pad_note(hz(note), m, rng.uniform(0, 2 * np.pi, 4))
            pad[a:b, ci] += acc * env * trem / len(notes)
        tt = np.arange(m) / SR
        bass[a:b] += (np.sin(2 * np.pi * hz(root) * tt) + 0.18 * np.sin(4 * np.pi * hz(root) * tt)) * env
        # pluck arpeggio, 8th notes
        lvl = PLUCK[sec]
        if lvl > 0:
            seq = notes + [notes[-1] + 12] + list(reversed(notes[1:]))
            step = BEAT / 2
            j = 0
            tp = t0
            while tp < t1 - 0.05:
                f0 = hz(seq[j % len(seq)] + 12)
                L = int(1.6 * SR)
                i0 = int(tp * SR)
                if i0 + L > n:
                    L = n - i0
                ttp = np.arange(L) / SR
                x = (np.sin(2 * np.pi * f0 * ttp) + 0.28 * np.sin(4 * np.pi * f0 * ttp) + 0.08 * np.sin(6 * np.pi * f0 * ttp))
                x *= np.minimum(1, ttp / 0.004) * np.exp(-ttp / 0.32) * lvl * (0.85 if j % 2 else 1.0)
                pan = 0.5 + 0.28 * math.sin(j * 1.7)
                pl[i0:i0 + L, 0] += x * (1 - pan)
                pl[i0:i0 + L, 1] += x * pan
                j += 1
                tp += step
    pad /= max(1e-9, np.abs(pad).max())
    bass /= max(1e-9, np.abs(bass).max())
    pl /= max(1e-9, np.abs(pl).max())
    dry = pad * 0.55 + bass[:, None] * 0.28 + pl * 0.22
    wet = reverb(pad * 0.5 + pl * 0.5)
    out = dry * 0.78 + wet * 0.32
    # gentle fade in / out
    fi, fo = int(2.5 * SR), int(5.0 * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    end = int(duration * SR)
    out = out[:end]
    out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return (out / max(1e-9, np.abs(out).max()) * 0.89).astype(np.float32)


def reverb(x, secs=2.8, tau=0.85):
    L = int(secs * SR)
    t = np.arange(L) / SR
    out = np.zeros_like(x)
    for c in range(x.shape[1]):
        ir = rng.standard_normal(L) * np.exp(-t / tau)
        ir = np.convolve(ir, np.ones(24) / 24, mode="same")  # soften highs
        ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        out[:, c] = _fftconv(x[:, c], ir)[: len(x)]
    return out


def _fftconv(sig, ir, block=1 << 19):
    nfft = 1 << int(math.ceil(math.log2(block + len(ir) - 1)))
    H = np.fft.rfft(ir, nfft)
    out = np.zeros(len(sig) + len(ir) - 1)
    for s in range(0, len(sig), block):
        seg = sig[s:s + block]
        y = np.fft.irfft(np.fft.rfft(seg, nfft) * H, nfft)[: len(seg) + len(ir) - 1]
        out[s:s + len(y)] += y
    return out


if __name__ == "__main__":
    import subprocess
    import sys
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    bed = make_bed(dur, [(0, "intro"), (dur * 0.2, "ch1"), (dur * 0.5, "ch4"), (dur * 0.8, "end")])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    sys.argv[2] if len(sys.argv) > 2 else "music_test.wav"], input=bed.tobytes(), check=True)

"""YT01 audio mix: ElevenLabs voice parts + procedural music bed + SFX -> two-pass loudnorm (-14 LUFS, TP -1.5).

python3 mix.py out.wav            final mix (needs voice/part{n}.mp3 + transcripts)
python3 mix.py out.wav preview    music + SFX only (no voice yet)
python3 mix.py mux video.mp4 audio.wav out.mp4
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

SR = 48000


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def measure(x):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       input=np.ascontiguousarray(x, np.float32).tobytes(), capture_output=True).stderr.decode()
    return json.loads(r[r.rindex("{"):])


def ff_filter(x, af):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", af,
                          "-f", "f32le", "-ar", str(SR), "-ac", "2", "-"],
                         input=np.ascontiguousarray(x, np.float32).tobytes(), capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
    return y[:len(x)] if len(y) >= len(x) else np.pad(y, ((0, len(x) - len(y)), (0, 0)))


def to_lufs(x, target):
    m = measure(x)
    return x * 10 ** ((target - float(m["input_i"])) / 20)


def sfx_bus(events, dur):
    from sfx import _env
    from sfx3 import SFX
    n = int(dur * SR)
    buf = np.zeros(n, np.float32)
    cache = {}
    for t, name, g in events:
        if name not in cache:
            cache[name] = SFX[name]()
        s = cache[name]
        i0 = int(t * SR)
        k = min(len(s), n - i0)
        if k > 0 and i0 >= 0:
            buf[i0:i0 + k] += s[:k] * g
    buf /= max(1e-6, np.abs(buf).max())
    return np.stack([buf, buf], axis=1)


def voice_bus(tl, dur):
    n = int(dur * SR)
    out = np.zeros((n, 2), np.float32)
    for p, off in zip(sorted({tk["part"] for tk in tl.toks}), tl.part_offsets):
        v = decode(os.path.join(HERE, "voice", f"part{p}.mp3"))
        i0 = int(off * SR)
        k = min(len(v), n - i0)
        out[i0:i0 + k] += v[:k]
    return out


def sections(S):
    secs = [(0.0, "intro")]
    for t0, (num, _) in S.CHAPTERS:
        secs.append((t0, f"ch{num}"))
    secs.append((S.T("That won't tell you which stock to buy."), "end"))
    return secs


def loudnorm_write(x, out):
    m = measure(x)
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", af,
                    "-ar", str(SR), out], input=np.ascontiguousarray(x, np.float32).tobytes(), check=True)
    print("final", measure(decode(out))["input_i"], "LUFS")


def main(out, preview=False):
    import scenes as S
    import music
    dur = S.DUR
    bed = music.make_bed(dur, sections(S))
    # leave room for the voice: no rumble, a soft dip in the voice's fundamental range
    bed = ff_filter(bed, "highpass=f=45,equalizer=f=320:t=q:w=1.2:g=-5,equalizer=f=2800:t=q:w=1:g=1.5")
    fx = sfx_bus(S.events(), dur)
    n = min(len(bed), len(fx))
    if preview:
        mix = to_lufs(bed[:n], -20.0) + to_lufs(fx[:n], -21.0)
    else:
        v = voice_bus(S.TL, dur)[:n]
        mix = to_lufs(v, -16.0) + to_lufs(bed[:n], -31.0) + to_lufs(fx[:n], -26.0)
    loudnorm_write(mix, out)


def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "320k", "-ar", str(SR), "-shortest", "-movflags", "+faststart",
                    out], check=True)


if __name__ == "__main__":
    if sys.argv[1] == "mux":
        mux(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main(sys.argv[1], preview=len(sys.argv) > 2 and sys.argv[2] == "preview")

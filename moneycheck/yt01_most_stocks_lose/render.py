"""YT01 render CLI.

python3 render.py sheet out.png [t1 t2 ...]   contact sheet (no times: two frames per scene)
python3 render.py frame out.png t             single full-size frame
python3 render.py video out.mp4                full video (no audio)
python3 render.py info                         timeline, chapters, events
"""
import os
import sys
from multiprocessing import Pool

from PIL import Image

import scenes as S
import lib16 as L


OFFSET = int(os.environ.get("YT_OFFSET", "0"))


def fb(i):
    return L.render_frame((i + OFFSET) / L.FPS, S.SCENES, S.overlay).tobytes()


def thumb(ts):
    return L.render_frame(ts, S.SCENES, S.overlay).resize((480, 270), Image.LANCZOS)


def auto_times():
    ts = []
    for t0, t1, s in S.TIMELINE:
        d = t1 - t0
        ts += [t0 + 0.45 * d, t0 + 0.85 * d] if d > 3 else [t0 + 0.6 * d]
    return ts


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "info":
        print("mode", S.TL.mode, "duration", round(S.DUR, 2), "scenes", len(S.SCENES))
        for t0, t1, s in S.TIMELINE:
            print(f"{t0:7.2f} {t1 - t0:6.2f}  {s['fn'].__name__}  {s['phrase'][:50]}")
        for t, c in S.chapters_for_description():
            print(f"{int(t // 60)}:{int(t % 60):02d} {c}")
        print(len(S.events()), "sound events")
    elif mode == "sheet":
        times = [float(x) for x in sys.argv[3:]] or auto_times()
        with Pool(4) as pool:
            th = pool.map(thumb, times)
        L.contact_sheet(th, times, sys.argv[2], cols=6)
    elif mode == "frame":
        L.render_frame(float(sys.argv[3]), S.SCENES, S.overlay).save(sys.argv[2])
    elif mode == "video":
        nf = int(round(S.DUR * L.FPS))
        L.encode(fb, nf, sys.argv[2])
        print("done", sys.argv[2], nf, "frames")
    elif mode == "bench":  # YT_OFFSET=<first frame> python3 render.py bench out.mp4 <frames>
        import time
        n = int(sys.argv[3])
        t0 = time.time()
        L.encode(fb, n, sys.argv[2])
        fps = n / (time.time() - t0)
        print(f"{fps:.1f} fps -> full video ~{S.DUR * L.FPS / fps / 60:.0f} min")

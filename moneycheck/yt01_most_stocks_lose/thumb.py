"""YT01 YouTube thumbnail (1280x720 JPG, < 2 MB): big claim left, crowd of losing stocks + a few glowing winners right."""
import math
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import lib16 as L  # noqa: E402
from lib16 import W, H, WHITE, GOLD, GOLD_HI, RED, RED_HI, NAVY, MUTED, qmix  # noqa: E402


def make(out):
    f = L.F(0.0)
    f.halo(1430, 560, 620, RED, 0.22, sy=0.8)
    gold = {(1, 2), (3, 5), (2, 8)}
    for r in range(5):
        for c in range(10):
            x = 1000 + c * 92 + (r % 2) * 46
            y = 330 + r * 150
            if (r, c) in gold:
                continue
            f.pawn(x, y + 60, 92, qmix(WHITE, RED, 0.75), 0.9)
    for r, c in gold:
        x = 1000 + c * 92 + (r % 2) * 46
        y = 330 + r * 150
        f.halo(x, y + 10, 150, GOLD, 0.8)
        f.pawn(x, y + 75, 130, GOLD_HI, 1.0)
    f.text(90, 300, "MOST", 210, WHITE, 1.0, "black", anchor="lm")
    f.text(90, 500, "STOCKS", 210, WHITE, 1.0, "black", anchor="lm")
    f.text(90, 715, "LOSE.", 230, RED_HI, 1.0, "black", anchor="lm")
    f.pill(90 + f.twidth("100 YEARS OF DATA", 44, "xb", 0.14) / 2 + 42, 900, "100 YEARS OF DATA", 44, 1.0, fill=GOLD, tc=NAVY,
           track=0.14)
    im = L.post(f.img, 0.0, bloom=0.5)
    L.watermark(im)
    im.resize((1280, 720), Image.LANCZOS).save(out, quality=92)


if __name__ == "__main__":
    make(sys.argv[1])

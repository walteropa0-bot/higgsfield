import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
exec(open('tools/analyze.py').read().split('for p in sys.argv')[0])
x = load(sys.argv[1]).mean(axis=1); out = sys.argv[2]
sr = 48000; hop = 400; nfft = 4096; win = np.hanning(nfft)
frames = (len(x) - nfft) // hop
fr = np.fft.rfftfreq(nfft, 1/sr)
H = 420; fmin, fmax = 30, 16000
rows = np.geomspace(fmin, fmax, H)[::-1]
idx = np.clip(np.searchsorted(fr, rows), 1, len(fr)-1)
img = np.zeros((H, frames))
for i in range(frames):
    seg = x[i*hop:i*hop+nfft] * win
    sp = np.abs(np.fft.rfft(seg)) / (nfft/4)
    img[:, i] = 20*np.log10(sp[idx] + 1e-9)
img = np.clip((img + 90) / 90, 0, 1)
# colour map (black -> orange -> cream)
c0 = np.array([14,14,14]); c1 = np.array([255,91,31]); c2 = np.array([242,238,232])
rgb = np.where(img[...,None] < 0.6, c0 + (c1-c0)*(img[...,None]/0.6), c1 + (c2-c1)*((img[...,None]-0.6)/0.4)).astype(np.uint8)
im = Image.fromarray(rgb).resize((1800, H))
canvas = Image.new('RGB', (1860, H + 40), (14,14,14)); canvas.paste(im, (50, 30))
d = ImageDraw.Draw(canvas); fnt = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Bold.otf', 15)
for f, name in [(0,'HOOK'),(120,'01'),(360,'02'),(600,'03'),(720,'peak'),(840,'04'),(960,'05'),(1200,'06'),(1320,'07'),(1440,'beat'),(1500,'END'),(1770,'out')]:
    xx = 50 + int(f/1800*1800); d.line([(xx, 30), (xx, H+30)], fill=(80,200,255), width=1); d.text((xx+3, 8), name, fill=(255,220,120), font=fnt)
for hz in [50,100,200,500,1000,2000,5000,10000]:
    y = 30 + int(np.interp(np.log(hz), np.log(rows[::-1]), np.arange(H)[::-1]))
    d.text((2, y-8), str(hz), fill=(200,200,200), font=fnt)
canvas.save(out); print(out)

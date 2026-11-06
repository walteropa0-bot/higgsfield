import sys, os, glob
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1]; out = sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 6
files = sorted(glob.glob(os.path.join(d, 'f*.png')))
tw, th = 300, 533
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * tw, rows * (th + 26)), (40, 40, 40))
fnt = ImageFont.truetype('/usr/share/fonts/opentype/inter/Inter-Bold.otf', 20)
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert('RGB').resize((tw, th), Image.LANCZOS)
    x, y = (i % cols) * tw, (i // cols) * (th + 26)
    sheet.paste(im, (x, y + 26))
    dr.text((x + 6, y + 2), os.path.basename(f)[1:-4], fill=(255, 200, 80), font=fnt)
sheet.save(out)
print(out, sheet.size)

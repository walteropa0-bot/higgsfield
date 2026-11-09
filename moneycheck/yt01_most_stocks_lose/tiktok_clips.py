"""TikTok clips from the YT01 long video (owner request, 9.11.2026).

Three vertical 9:16 cuts (1080x1920) of the finished long video. The 16:9 frame sits centred on a blurred copy of
itself, with a hook text in the first 3 s. No new footage and no new audio: voice and music are the long video's mix
(-14 LUFS). Cut points are phrases of the script (tl.py, voice timing), not seconds.

Usage: python3 tiktok_clips.py SOURCE.mp4 OUTDIR
  SOURCE: the 1920x1080 render of YT01 (e.g. the handy 1080p copy).
  OUTDIR: clips, covers and hook images. Also writes tiktok_clips_upload.txt next to this file.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import tl

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
NAVY = (11, 20, 38)
GOLD = (245, 215, 110)
WHITE = (255, 255, 255)
PAD_IN, PAD_OUT = 0.3, 0.5  # breathing room before the first and after the last phrase (s)

CLIPS = [
    dict(slug="1_most_stocks_lose", start="Here's a fact", end="show you how that works",
         hook=[("MOST STOCKS", WHITE, 150), ("LOSE MONEY.", GOLD, 150)]),
    dict(slug="2_only_3_7_percent", start="Over the century, the US stock market created",
         end="a few dozen did most of the heavy lifting",
         hook=[("ONLY 3.7%", GOLD, 210), ("CREATED ALL THE WEALTH", WHITE, 80)]),
    dict(slug="3_coin_flip", start="Imagine a stock that flips a coin every year", end="That's sixty-two percent",
         hook=[("A COIN-FLIP MARKET", WHITE, 110), ("62% LOSE MONEY", GOLD, 150)]),
]

CAPTIONS = {
    "1_most_stocks_lose": (
        "Most stocks lose money. The market still wins. 📉📈\n"
        "Over the last 100 years, the typical US stock lost money. Full breakdown on my profile.\n"
        "Source: Hendrik Bessembinder (2026), 29,754 US stocks, 1926–2025.\n"
        "Not financial advice – for educational purposes only.\n"
        "#investing #stockmarket #personalfinance #moneycheck #education"),
    "2_only_3_7_percent": (
        "Only 3.7% of companies created ALL the stock market wealth. 📊\n"
        "US stocks 1926–2025: about $91 trillion of net wealth, and 3.7% of the companies made all of it. "
        "Full breakdown on my profile.\n"
        "Source: Hendrik Bessembinder (2026), 29,081 companies.\n"
        "Not financial advice – for educational purposes only.\n"
        "#investing #stockmarket #personalfinance #moneycheck #education"),
    "3_coin_flip": (
        "A coin-flip market: 62% of the stocks lose money. 🪙\n"
        "Our own calculation: 1,024 stocks, 10 years, +50% or −40% per year. Toy model: no crashes, no fees, "
        "no taxes. Full breakdown on my profile.\n"
        "Own calculation, not a forecast.\n"
        "Not financial advice – for educational purposes only.\n"
        "#investing #stockmarket #math #moneycheck #education"),
}


def fit(text, size, max_w=900):
    """largest font size <= size whose text fits max_w px (Inter Black)"""
    while size > 24:
        font = ImageFont.truetype(FONT, size)
        box = font.getbbox(text, stroke_width=5)
        if box[2] - box[0] <= max_w:
            return font, box
        size -= 2
    raise ValueError(f"hook text too wide: {text!r}")


def hook_png(lines, out_png, top=300):
    """transparent 1080x1920 layer with the hook text, centred, outlined in navy"""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = top
    for text, color, size in lines:
        font, (l, t, r, b) = fit(text, size)
        x = (1080 - (r - l)) / 2 - l
        draw.text((x, y - t), text, font=font, fill=color + (255,), stroke_width=5, stroke_fill=NAVY + (255,))
        y += (b - t) + 24
    img.save(out_png)


def cut(src, start, dur, hook, out_mp4):
    """one vertical clip: blurred 16:9 background, centred frame, hook for 3 s, fade to black at the end"""
    fade_at = dur - 0.5
    fc = (
        "[0:v]split=2[s1][s2];"
        "[s1]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=luma_radius=40:luma_power=3,eq=brightness=-0.10[bg];"
        "[s2]scale=1080:-2[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[v0];"
        "[1:v]format=rgba,fade=t=out:st=2.8:d=0.4:alpha=1[hk];"
        f"[v0][hk]overlay=0:0,fade=t=out:st={fade_at:.2f}:d=0.5[v]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
        "-loop", "1", "-framerate", "30", "-i", hook,
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a:0",
        "-af", f"afade=t=out:st={fade_at:.2f}:d=0.5",
        "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "4M", "-bufsize", "8M",
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", out_mp4,
    ], check=True)


def cover(mp4, out_jpg, t=1.5):
    """cover = the frame under the hook text"""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t}", "-i", mp4,
                    "-frames:v", "1", "-q:v", "2", out_jpg], check=True)


def write_upload_text(report):
    lines = [
        "MONEYCHECK – TIKTOK CLIPS FROM THE LONG VIDEO (YT01)",
        "=" * 52,
        "Each clip is a cut of the long video: same voice, same music, same sources.",
        "Files: moneycheck_tiktok_<n>.mp4 (1080x1920, 30 fps) and moneycheck_tiktok_<n>_cover.jpg",
        "",
    ]
    for n, (slug, start, end, dur) in enumerate(report, 1):
        lines += [
            f"CLIP {n} – moneycheck_tiktok_{slug}.mp4 ({dur:.0f} s, long video {start:.0f}–{end:.0f} s)",
            "Caption:",
            CAPTIONS[slug],
            "",
        ]
    lines += [
        "TIKTOK CHECKLIST (every clip)",
        "• AI-generated content: ON (AI narration)",
        "• Cover: the matching _cover.jpg, or pick the frame at about 1.5 s",
        "• Watch the clip once before posting (Claude cannot hear the voice)",
        "• Caption keeps \"Not financial advice – for educational purposes only.\"",
        "• Pin one comment with a question (see the comment options from earlier)",
        "",
    ]
    with open(os.path.join(HERE, "tiktok_clips_upload.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    TL = tl.Timeline("voice")
    report = []
    for n, c in enumerate(CLIPS, 1):
        i0, _ = TL.find(c["start"])
        _, i1 = TL.find(c["end"])
        start = TL.st[i0] - PAD_IN
        end = TL.en[i1] + PAD_OUT
        dur = end - start
        base = os.path.join(outdir, f"moneycheck_tiktok_{c['slug']}")
        hook_png(c["hook"], base + "_hook.png")
        cut(src, start, dur, base + "_hook.png", base + ".mp4")
        cover(base + ".mp4", base + "_cover.jpg")
        report.append((c["slug"], start, end, dur))
        print(f"clip {n}: {start:.2f}-{end:.2f} s ({dur:.1f} s) -> {base}.mp4")
    write_upload_text(report)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

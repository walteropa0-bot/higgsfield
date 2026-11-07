#!/usr/bin/env bash
# Assemble the final 60 s vertical video from rendered frames + synthesized soundtrack.
#   ./assemble.sh            -> out/villa-timelapse-60s-9x16.mp4
# Grade: gentle contrast/saturation, warm highlights / cool shadows, light sharpening,
# subtle vignette and temporal film grain (hides CG cleanliness, adds "shot on camera" texture).
set -euo pipefail
cd "$(dirname "$0")"
FRAMES=out/frames
OUT=out/villa-timelapse-60s-9x16.mp4
n=$(ls "$FRAMES" | wc -l)
if [ "$n" -lt 1800 ]; then echo "only $n/1800 frames rendered" >&2; exit 1; fi

VF="eq=contrast=1.06:saturation=1.12,\
colorbalance=rh=0.025:gh=0.008:bh=-0.02,\
unsharp=5:5:0.35:5:5:0,\
vignette=angle=PI/12,\
noise=c0s=5:c0f=t,\
format=yuv420p"

ffmpeg -y -hide_banner -loglevel warning -stats \
  -framerate 30 -i "$FRAMES/f%05d.jpg" \
  -i audio/soundtrack.wav \
  -vf "$VF" \
  -c:v libx264 -preset slow -crf 19 -maxrate 7M -bufsize 14M -profile:v high -level 4.2 -tune film \
  -r 30 -g 60 \
  -af "volume=-0.2dB,alimiter=limit=0.78:level=false:attack=2:release=60" -c:a aac -b:a 320k -ar 48000 \
  -movflags +faststart -shortest \
  -metadata title="Villa construction time-lapse (60s)" \
  "$OUT"

ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_name,width,height,r_frame_rate -of compact "$OUT"
ffmpeg -y -hide_banner -loglevel error -i audio/soundtrack.wav -af "volume=-0.2dB,alimiter=limit=0.78:level=false:attack=2:release=60" -c:a aac -b:a 320k audio/soundtrack.m4a
# poster frame (completed villa at blue hour)
ffmpeg -y -hide_banner -loglevel error -ss 59.5 -i "$OUT" -frames:v 1 -q:v 2 out/poster.jpg
echo "done: $OUT"

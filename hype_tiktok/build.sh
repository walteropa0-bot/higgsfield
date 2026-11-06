#!/usr/bin/env bash
# Full pipeline: synth audio -> headless render -> mux -> verify.
#   ./build.sh            (everything)
#   ./build.sh mux        (only mux + verify, re-using out/video_noaudio.mp4 and out/mix.wav)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out check

if [[ "${1:-all}" == "all" ]]; then
  echo "== 1/4 audio synthesis"
  node tools/synth.js
  echo "== 2/4 headless render (1800 frames)"
  node tools/render.js --range=0-1799 --out=out/video_noaudio.mp4 --workers=4
fi

echo "== 3/4 mux (AAC 320k, 48 kHz, stereo, faststart)"
ffmpeg -y -hide_banner -loglevel error \
  -i out/video_noaudio.mp4 -i out/mix.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy \
  -c:a aac -b:a 320k -ar 48000 -ac 2 \
  -movflags +faststart -metadata title="Die Achterbahn einer Hype-Aktie" \
  out/final.mp4

echo "== 4/4 verify"
node tools/verify.js

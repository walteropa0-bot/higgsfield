#!/bin/bash
# Render all 1800 frames in two parallel headless-Chromium processes (resumable).
cd "$(dirname "$0")/../render"
node render.mjs --out ../out/frames --from 0 --to 900 --resume > ../out/logs/render_a.log 2>&1 &
A=$!
node render.mjs --out ../out/frames --from 900 --to 1800 --resume > ../out/logs/render_b.log 2>&1 &
B=$!
wait $A $B
echo "render done: $(ls ../out/frames | wc -l) frames"

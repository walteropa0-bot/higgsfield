# Extreme construction time-lapse: modern villa (60 s, 9:16)

A 60-second vertical (1080x1920, 30 fps) construction time-lapse of a modern hillside villa with
an infinity pool, from empty plot to a finished house glowing at blue hour. Everything is generated
locally: the picture is rendered as procedural 3D (three.js in headless Chromium) and the sound is
synthesized from code. No stock footage, samples or paid AI credits are used.

- **Video:** `out/villa-timelapse-60s-9x16.mp4` (H.264 + AAC 320k, -14 LUFS)
- **Soundtrack only:** `audio/soundtrack.m4a` (AAC 320k; `audio/mix.py` regenerates the 24-bit WAV master in about 20 s)
- **Full-motion AI version:** see `PROMPT_KIT.md` (same edit, shot by shot)

## What happens on screen

| Time | Shot | What changes |
|------|------|--------------|
| 0–2.4 s | FPV dive onto the site | hook: excavator bucket strike, slow motion, debris, speed ramp |
| 2.4–6.6 s | drone orbit | pits dug, trucks hauling, crane erected |
| 6.6–8.4 s | top-down | gravel, edge forms, rebar mats |
| 8.4–10.8 s | slab-level close-up | slow-motion concrete pour |
| 10.8–15.0 s | drone orbit | formwork walls, props, deck, first-floor slab |
| 15.0–16.8 s | low angle | slow-motion welding spark shower, arc flash |
| 16.8–21.2 s | low-angle dolly | upper walls, scaffolding, crane loads, roof deck |
| 21.2–25.0 s | rotating top-down | roof pour, membrane |
| 25.0–27.4 s | close-up | slow-motion glass panel lowered by crane |
| 27.4–31.8 s | drone orbit | frames, glazing, teak screen, white roof |
| 31.8–33.8 s | tracking | teak slats snapping in |
| 33.8–38.4 s | drone orbit | scaffold and crane removed, deck pavers, pool tiles |
| 38.4–41.0 s | pool edge | slow-motion pool fill, then fast |
| 41.0–46.0 s | drone pull-back | lawn, olive trees, site cleared |
| 46.0–52.0 s | ground level | sunset time-lapse, lights switch on room by room |
| 52.0–60.0 s | finale | blue-hour glide and rising reveal of the finished villa |

Motion design: speed ramps inside every shot (slow start, fast middle), 5–10x micro-motion for
workers and machines on top of the compressed build schedule, motion trails and directional smear
on fast-moving workers and machinery (`render/src/ghosts.js`: each moving object is re-posed a few
milliseconds earlier and drawn as faint copies, so static objects stay sharp), sub-frame motion blur
on the dive and every whip/punch/tilt transition, camera shake on impact, cloud shadows racing
across the site, depth of field on close-ups, and a film grade with grain and vignette.

## Layout

```
render/            three.js scene + headless renderer
  src/shots.js     the edit: 17 shots, camera paths, speed ramps, transitions
  src/villa.js     every building element with its build schedule (days 0-120)
  src/machines.js  excavators, trucks, mixers, boom pump, tower crane, loader
  src/workers.js   crew simulation (instanced figures)
  src/fx.js        dirt, dust, sparks, concrete stream, water
  src/ghosts.js    motion trails for fast workers and machinery
  src/terrain.js, vegetation.js, sky.js, textures.js
  render.mjs       renders frames / stills
  cues.mjs         exports the sound cue sheet from the same timeline
audio/
  sfx.py           procedural sound-effects library (engines, impacts, tools, water, whooshes...)
  mix.py           cue sheet -> mastered soundtrack
  cues.json        every on-screen action with its time
assemble.sh        frames + soundtrack -> final MP4 (grade, grain, loudness-safe limiter)
PROMPT_KIT.md      prompts for a photoreal AI-video version of the same edit
```

## Rebuild

```bash
cd render && npm install                       # three.js + n8ao (Playwright/Chromium preinstalled)
node render.mjs --still 1.06,30,59.9 --scale 0.5 --out ../out/stills   # quick look
../out/render_all.sh                           # all 1800 frames (about 2 h on 4 CPU cores, resumable)
node cues.mjs ../audio/cues.json
cd ../audio && python3 mix.py cues.json soundtrack.wav   # needs numpy, scipy, soundfile
cd .. && ./assemble.sh
```

Rendering uses SwiftShader (CPU WebGL), about 4.5 s per frame at full resolution with ambient
occlusion. `render.mjs --resume` skips frames that already exist.

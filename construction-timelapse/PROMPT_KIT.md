# Prompt kit: full-motion AI version

The video in `out/` is a CGI render made in this repo. If you later want a photoreal AI-generated
version (Veo 3.1, Kling 3/4, Seedance 2.5, Higgsfield, etc.), this kit follows the same edit,
timing and sound design. Every shot below matches a shot in `render/src/shots.js`, so you can
replace the CGI shots one by one and keep the soundtrack.

## 1. Design anchor (paste into every prompt)

> A modern two-story luxury villa on a gently sloping Mediterranean hillside. White board-formed
> concrete walls, floor-to-ceiling glass on both floors, an upper floor that cantilevers 5 m to the
> east over a covered terrace, a thin flat roof slab with deep overhangs, vertical teak slat
> screens on the upper-left facade and the garage wing. A 16 x 4 m infinity pool with aqua glass
> mosaic and a travertine deck faces south over a valley. Around the plot: golden summer grass,
> olive trees, a row of tall cypresses behind the house, rolling hills with patchwork fields.
> Yellow tower crane behind the house. Workers in orange and lime hi-vis vests and white helmets.

Consistency tips:
- Generate one keyframe still per build stage from the **same master drone angle** first
  (high, about 45 degrees down, from the south-west), then animate between consecutive stills with
  first/last-frame video generation. This keeps the building identical from shot to shot.
- Keep clips at 8 s or less and reuse the anchor text word for word.
- Negative prompt: `no morphing, no flicker, no extra floors, no text, no watermark, no distorted hands`.

## 2. Shot list (60 s, 9:16, 30 fps)

| # | Time | Shot | Prompt (add the design anchor) | Sound |
|---|------|------|--------------------------------|-------|
| 1 | 0.0–2.4 | FPV dive + impact | FPV drone dives fast from high above the valley down to an empty hillside plot where a yellow excavator slams its bucket into the soil; slow motion as dirt clods and dust explode; camera shake; then speed ramps up as the boom lifts and swings to a red dump truck; whip tilt up to the sky. | wind rush riser, deep sub boom, earth crunch, debris rain, diesel roar |
| 2 | 2.4–6.6 | Master orbit, excavation | High drone orbit, extreme time-lapse: the house pit and pool pit are dug in seconds, dump trucks race in and out, spoil piles grow, the tower crane mast rises section by section, cloud shadows sweep the site. | accelerated diesels, hydraulics, bucket hits, truck reverse beepers |
| 3 | 6.6–8.4 | Top-down rebar | Straight-down aerial, slowly rotating: a gravel bed, timber edge forms and a dense steel rebar mat are laid in seconds by a crew moving at high speed. | rebar clinks, footsteps on gravel, punch-in whoosh |
| 4 | 8.4–10.8 | Slow-motion pour | Low close-up at slab level: grey wet concrete pours from a pump-truck hose onto the rebar, glossy wave spreading, workers screeding, slow motion then speed ramp. | thick wet pour, pump strokes, vibrator buzz, tape-slow swell |
| 5 | 10.8–15.0 | Master orbit, walls | Drone orbit from the south-east: yellow wall formwork rises, is stripped to reveal board-formed concrete, shoring props sprout and a plywood deck slides across, the crane swings formwork panels. | hammering, steel clanks, crane motor, drills |
| 6 | 15.0–16.8 | Slow-motion sparks | Ground-level looking up at the cantilever slab edge: a welder joins a steel beam, a shower of orange sparks rains down in slow motion against the sky; ends on a bright arc flash. | slowed arc crackle and buzz, spark sizzle, flash hit |
| 7 | 16.8–21.2 | Low-angle crane reveal | Wide low angle dolly-in and tilt-up: the upper floor walls rise inside green-netted scaffolding, the crane jib sweeps overhead carrying loads, the roof deck appears. | crane winch, scaffold clangs, hammering |
| 8 | 21.2–25.0 | Top-down roof | Rotating bird's-eye: roof rebar, concrete pour sweeping across the roof, dark membrane rolling out, pool shell finished. | pump strokes, pour, roofing torch roar |
| 9 | 25.0–27.4 | Slow-motion glass | A large framed glass panel is lowered by the crane into the upper-floor opening while two workers guide it; it settles gently in slow motion. | slow winch, rubber squeak, soft heavy thud, glass ring |
| 10 | 27.4–31.8 | Master orbit, glazing | Drone orbit: window frames and glass panels drop in one after another, teak slats appear, the roof turns white. | glass thuds, impact drivers, crane |
| 11 | 31.8–33.8 | Tracking slats | Camera tracks along the garage wing as teak slats snap into place one after another, sunlight striping through. | rapid pneumatic nail-gun bursts |
| 12 | 33.8–38.4 | Master orbit, finishing | Scaffolding is stripped from the top down, the crane is dismantled, the deck screed and travertine pavers are laid in a sweeping wave, the pool is tiled. | scaffold tube clangs, tile clacks, grinder |
| 13 | 38.4–41.0 | Slow-motion pool fill | Low angle at the pool edge: a hose arcs water into the aqua mosaic pool, slow-motion splash, then the water level rises fast. | slowed water jet and bubbles, rising rush |
| 14 | 41.0–46.0 | Master pull-back, landscaping | Drone pull-back: turf rolls laid in stripes, olive trees lowered into place, fence and site cabins vanish, the last loader drives away. | loader + beeper, soft thuds, birds |
| 15 | 46.0–52.0 | Sunset lights-on | Ground-level 3/4 view across the pool as the sun sets in time-lapse; interior lights switch on room by room, then the pool lights and garden uplights. | crickets, evening air, breaker clunks, pool "whoom" |
| 16 | 52.0–56.0 | Finale glide | Blue hour, slow low glide across the lawn toward the pool corner, warm interiors reflected in the water. | drone swell, water lapping |
| 17 | 56.0–60.0 | Finale rise | Rising crane pull-back revealing the finished villa glowing at blue hour above the valley; hold on the final frame. | low reveal boom, shimmer, fade out |

## 3. Assembly

1. Export each generated clip at 1080x1920, 30 fps, trimmed to the durations above, as
   `clips/01.mp4` ... `clips/17.mp4`.
2. Join them in order with the same soundtrack:

```bash
ls clips/*.mp4 | sed "s/^/file '/; s/$/'/" > list.txt
ffmpeg -f concat -safe 0 -i list.txt -i audio/soundtrack.wav -map 0:v -map 1:a \
  -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k -shortest ai-version.mp4
```

3. If a model generates its own audio, keep it under the provided soundtrack (about -8 dB) for
   extra realism; the transition whooshes and impacts in `audio/soundtrack.wav` are timed to these
   cut points.

## 4. Sound cue sheet

`audio/cues.json` lists every on-screen action with its time in seconds: bucket strikes and
dumps, crane lowers and releases, formwork lifts, every rebar bar, scaffold tube, paver and slat
that appears, glass landings, pours, welding, pool filling, each light switching on and every
cut. `audio/mix.py` turns it into the soundtrack; you can feed the same timings to any SFX library.

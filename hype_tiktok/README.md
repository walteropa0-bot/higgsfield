# „Die Achterbahn einer Hype-Aktie“ – 30-s-TikTok ($HYPE)

Premium-Motion-Design im Swiss/SaaS-Look. Ein orangener Ball (der Kurs) rollt die Chartkurve einer fiktiven Hype-Aktie entlang, durch sieben Gefühlsphasen eines Traders. Bild und Ton werden vollständig per Code erzeugt: keine Fremd-Samples, keine echten Firmen, Logos oder Kurse.

## Lieferumfang (`out/`)

| Datei | Inhalt |
|---|---|
| `final.mp4` | 1080×1920, 60 fps CFR, 1800 Frames, 30,000 s, H.264 High (CRF 16, yuv420p, BT.709), faststart, AAC 320 kbps / 48 kHz / Stereo |
| `music.wav` | Musik-Stem (24 bit / 48 kHz), gegen einen Trend-Sound tauschbar |
| `sfx.wav` | SFX-Stem (24 bit / 48 kHz), alle Sounds framegenau zu den Visuals |
| `mix.wav` | Gemasterte Tonspur, identisch mit dem Audio im MP4 vor der AAC-Kodierung |
| `caption.txt` | Caption mit 5 Hashtags |
| `kontrollframes.png` | Die vollsten Momente aus dem finalen Encode, mit eingezeichneten Safe Zones |

Die Stems haben dieselben relativen Pegel wie im Mix, mit gemeinsamem Trim auf −1 dBFS Peak. Musik + SFX ergeben vor dem Master-Limiter den Mix. Wer die Musik tauscht, legt `sfx.wav` unter den Trend-Sound und gleicht den Pegel nach Gehör an.

## Geprüfte Werte (`node tools/verify.js`)

```
PASS  video codec H.264 High                     h264 / High / level 50
PASS  1080x1920                                  1080x1920
PASS  yuv420p                                    yuv420p
PASS  60 fps constant                            r=60/1 avg=60/1
PASS  1800 frames                                nb_read_frames=1800
PASS  video duration 30.0 s                      video 30.000000s
PASS  container duration 30.0 s                  format 30.000000s
PASS  BT.709 tagged                              bt709/bt709/bt709
PASS  audio AAC 48 kHz stereo                    aac 48000 Hz 2ch
PASS  audio ~320 kbps                            325347 bps
PASS  faststart (moov before mdat)               moov@36 mdat@49254
PASS  loudness ≈ -14 LUFS (±0.5)                 -14 LUFS
PASS  true peak <= -1 dBTP                       -1.5 dBTP
PASS  loop: frame 1799 == frame 0 (encoded PSNR) PSNR 45.77 dB
```

Weitere Prüfungen:

- **Loop:** Die Quell-Frames 0 und 1799 sind bitidentisch (gleicher MD5). Der Ball schwebt in den letzten Frames in seinen Apex aus, deshalb ist der doppelte Frame an der Naht unsichtbar. Der Ton wird zirkulär gemischt: Hall- und Delay-Fahnen vom Ende laufen in den Anfang.
- **A/V-Sync** (`python3 tools/synccheck.py`): Der globale Versatz zwischen dekodiertem AAC und Master liegt an vier Stellen bei 0 Samples, das AAC-Priming wird also per Edit-List korrekt kompensiert. Die Onsets markanter Cues weichen im Median um +0,1 ms ab, maximal um 12 ms, also unter einem Frame. Der Audio-Stream ist exakt 1.440.000 Samples lang.
- **Safe Zones** (`node tools/audit.js`): Über alle 1800 Frames protokollieren gut 35.000 Element-Boxen (Texte, Karten, Labels, Zähler, Button, Chip) ihre Lage. Ergebnis: 0 Verletzungen der Zonen oben 150 / unten 450 / links 60 / rechts 150 px und 0 Überlappungen zwischen Elementen.
- **Event-Dichte:** Zwischen zwei neuen Ereignissen liegt nie mehr als 1,0 s.

## Aufbau

```
src/timeline.js   EINE Datei steuert Bild UND Ton: Phasen, Kursverlauf, Ballphysik, Kamera-Keys,
                  Texte und Stagger-Konstanten, Musik-Arrangement und alle Cue-Events (Frame-genau)
src/lib.js        deterministische Mathematik: Springs (Steifigkeit 180 / Dämpfung 12 u. a.),
                  Custom-Bezier-Easing, Seeds/RNG, Noise
src/scene.js      Canvas2D-Renderer mit echter Perspektivkamera (Parallax in 3 Ebenen, Dolly-Zoom,
                  3D-Kippung). Glow-Pass, Motion Blur per temporalem Supersampling, Post-FX
                  (RGB-Split, Glitch, Entsättigung, Vignette, Filmkorn)
src/index.html    Render-Host für Headless Chromium
tools/render.js   N parallele Chromium-Worker -> Reorder-Puffer -> rawvideo-Pipe -> ffmpeg/x264
tools/synth.js    Synthesizer (Drums, Bass, Pads, Stabs, alle SFX), Mixing, Mastering (BS.1770-Loudness,
                  True-Peak-Limiter, zirkuläres Hall/Delay für den nahtlosen Loop)
tools/dsp.js      Oszillatoren, TPT-SVF-Filter, FDN-Hall, Ping-Pong-Delay, Kompressor, Limiter, WAV-Writer
tools/verify.js   ffprobe-/ebur128-Abnahme · tools/audit.js Safe-Zone-Audit · tools/synccheck.py Sync
build.sh          komplette Pipeline: ./build.sh (alles) bzw. ./build.sh mux (nur Mux + Prüfung)
```

Zeit wird ausschließlich über den Frame-Index geführt (t = f/60). Alle Zufälle haben feste Seeds, Echtzeit-Timer gibt es nicht. Jeder Frame lässt sich deshalb einzeln und reproduzierbar rendern, auch parallel. Frame 1799 wird als Frame 0 gerendert, die Pre-Roll-Phase (Hook-Zeit −17…0) liegt am Dateiende.

## Neu bauen

Voraussetzungen: Node 22, Playwright mit Chromium, ffmpeg (libx264), Python 3 mit numpy und Pillow (nur für die Prüf-Tools) sowie die Schriften Inter und Inter Display.

```bash
./build.sh                                                # Audio + 1800 Frames + Mux + Prüfung (~6–8 min auf 4 Kernen)
node tools/render.js --frames=0,720,960 --png=check/x     # einzelne Kontrollframes
node tools/render.js --frames=760 --png=check/x --safe    # mit Safe-Zone-Overlay
node tools/audit.js                                       # Safe-Zone- und Überlappungs-Audit
```

# Moneycheck – Video-Skripte

Englische Finanz-Shorts (TikTok / YouTube Shorts), 1080×1920, 30 fps. Regeln und Stil: siehe `../CLAUDE.md`.

| Datei | Inhalt |
|---|---|
| `lib10.py` | Zeichen-Bibliothek im Premium-Look: 2×-Supersampling, echte Transparenz, Kamera mit Zoom, Bloom, Korn. Männchen (`pawn`), Pill-Labels, Münzen, Geldscheine, Geld-Explosion, Funkeln, Flagge, Stoppuhr, Spotlight |
| `render10.py` | Short #8 („Your portfolio is down 30%“) als Vorlage: 13 Szenen, Timeline `SHOTS`, Übergänge, Wackler, Rot-Tönung, Cover |
| `render11.py`, `mix11.py` | Short #9 (Markt-News + Checkliste als Mine): Männchen mit Helm und Spitzhacke gräbt durch 5 Schichten, Kamera folgt, Diamanten am Ende. Dazu Heatmap, Chip-Icon, Aktien-Karten, Rechenzentrum, Wahlurne |
| `render12.py`, `mix12.py` | Short #10 (20 s, Viral-Loop): 99-%-Ring mit Lichtlauf, Geburtstagskuchen, Sanduhr mit Strahlen, Aktien-Zertifikat, wachsendes Männchen mit Münzspur, Vermögenskurve, die nach 50 explodiert, Geldregen |
| `render13.py`, `mix13.py` | Short #11 (20 s): „$100/Monat mit 20 = $500/Monat mit 40“ – Vergleichskarten, Wettrennen-Chart, gestapelte Balken (eingezahlt vs. Zinseszins), Millionen-Zähler mit Zoom-out. Rechnung: 7 %/Jahr, monatlich |
| `mix10.py` | Soundmix: Stimme + ca. 200 Effekte an den exakten Wort-Zeiten, danach -14 LUFS |
| `sfx.py`, `sfx2.py`, `sfx3.py` | Synthetische Effekte (whoosh, pop, tick, ding, bass, riser, impact, alert, coin, cash, blip, sweep_down, ping, vroom, sparkle, flutter, puff) |
| `captions2.py` | Wortgenaue Untertitel (nur wenn gewünscht) |
| `short08_example/` … `short11_example/` | `words.json` und `upload_text.txt` von Short #8 bis #11 |
| `assets/moneycheck_profile.png` | Profilbild |

## Neues Video in 7 Schritten
1. Skript schreiben: Englisch, 60–75 s, Hook → 3–5 Punkte mit korrekten Zahlen → Höhepunkt → Loop. Keine Anlageempfehlungen.
2. Stimme mit ElevenLabs (`creative_generate_speech`): `eleven_v4`, Stimme Samara X `19STyYD15bswVz51nqLf`,
   `generations_count=1`, vorher `estimate_only`. Danach die MP3 als `voice.mp3` herunterladen.
3. Wort-Zeiten holen: `creative_add_flow_asset_node` mit der generation_id, dann `creative_transcribe_audio`
   (`eleven_scribe_v1`, 0 Credits). Daraus `words.json` schreiben: Liste aus `{"text", "start", "end"}` ohne `[tags]`.
4. Arbeitsordner anlegen, `lib10.py` und `sfx*.py` hineinkopieren, `render10.py` kopieren und die Szenen umbauen.
   Jede Szene ist eine Funktion `szene(f, t)`. Zeiten immer mit `at("wort", n)`, nie geschätzt.
5. Prüfen und rendern:
   `python3 render10.py sheet sheet.png 1 5 9 …` (Kontaktbogen ansehen), dann `python3 render10.py video`
   und `python3 render10.py cover`. Etwa 0,2 s pro Bild, 4 Prozesse.
6. Ton: `mix10.py` anpassen (Effekte an `at(...)`), dann `python3 mix10.py`. Danach zweistufig auf -14 LUFS normalisieren
   und zusammenführen:
   ```
   ffmpeg -i voice_sfx.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null -   # Werte ablesen
   ffmpeg -i voice_sfx.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:offset=..:linear=true" -ar 48000 -ac 2 voice_sfx_n.wav
   ffmpeg -i video_noaudio.mp4 -i voice_sfx_n.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart final.mp4
   ```
7. `upload_text.txt` schreiben: Titel, Beschreibung mit Quellen, „Not financial advice – for educational purposes only.“,
   Hashtags, Hinweis auf die KI-Kennzeichnung.

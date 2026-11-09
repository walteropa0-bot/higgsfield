# Moneycheck – Video-Skripte

Englische Finanz-Shorts (TikTok / YouTube Shorts), 1080×1920, 30 fps. Regeln und Stil: siehe `../CLAUDE.md`.

| Datei | Inhalt |
|---|---|
| `lib10.py` | Zeichen-Bibliothek im Premium-Look: 2×-Supersampling, echte Transparenz, Kamera mit Zoom, Bloom, Korn. Männchen (`pawn`), Pill-Labels, Münzen, Geldscheine, Geld-Explosion, Funkeln, Flagge, Stoppuhr, Spotlight |
| `render10.py` | Short #8 („Your portfolio is down 30%“) als Vorlage: 13 Szenen, Timeline `SHOTS`, Übergänge, Wackler, Rot-Tönung, Cover |
| `render11.py`, `mix11.py` | Short #9 (Markt-News + Checkliste als Mine): Männchen mit Helm und Spitzhacke gräbt durch 5 Schichten, Kamera folgt, Diamanten am Ende. Dazu Heatmap, Chip-Icon, Aktien-Karten, Rechenzentrum, Wahlurne |
| `render12.py`, `mix12.py` | Short #10 (20 s, Viral-Loop): 99-%-Ring mit Lichtlauf, Geburtstagskuchen, Sanduhr mit Strahlen, Aktien-Zertifikat, wachsendes Männchen mit Münzspur, Vermögenskurve, die nach 50 explodiert, Geldregen |
| `render13.py`, `mix13.py` | Short #11 (20 s): „$100/Monat mit 20 = $500/Monat mit 40“ – Vergleichskarten, Wettrennen-Chart, gestapelte Balken (eingezahlt vs. Zinseszins), Millionen-Zähler mit Zoom-out. Rechnung: 7 %/Jahr, monatlich |
| `eng14.py`, `week_nov7/` | Ohne Stimme: Text-Animationen in 1440×2560 (schärfer als 1080p). Szenen als „Beats“ mit Überblendung, Loop zurück zum Anfang, Soundeffekte + -14 LUFS + Mux in einem Befehl (`python3 v1_buffett.py video`). Sechs Wochen-Videos als Vorlage |
| `lib16.py`, `yt01_most_stocks_lose/` | **Lange YouTube-Videos (16:9)**: 1920×1080-Design, 2× gezeichnet, Ausgabe 2560×1440. Szenen hängen an Wörtern des Skripts (Vorschau ohne Stimme möglich), Kapitel-Label, Quellenzeile, eigene Musik, Thumbnail, Upload-Text mit Kapitelmarken. Vorlage für weitere lange Videos (siehe README dort) |
| `voice_local.py` | Stimme und Wort-Zeiten lokal: Kokoro (Apache-2.0) über sherpa-onnx, Zeiten über Zipformer-Erkennung. `speak skript.txt voice.mp3 words.json` |
| `voicestudio_tts.py` | Optional, für Voice Studio auf dem eigenen Rechner (lokale API). Nicht in der Cloud-Umgebung |
| `lib20.py` | **Animations-Engine im cryothum-Stil (seit 8.11.2026)**: Weltkamera mit Stationen statt Überblendungen, Punktraster in Weltkoordinaten, Linien-Icons (Fenster, Button, Cursor, Schalter, Karte mit Häkchen, Zahlenbox, Monitor, Schreibtisch, Gebäude, Handy, Tasche, Schuh, Chart, Benachrichtigung), Männchen mit Armen, `hit()`-Timing, `headline()`-Ebene, Render mit 4 Prozessen |
| `mix20.py` | Ton für lib20-Videos: alle Effekte aus `sfx3.py` plus click, toggle, typing, notif, kaching, swish, thud, mallet; Mix Stimme −16 / Effekte −25 LUFS → −14 LUFS; `mux()`; `handy()` macht die kleine Handy-Version zum Speichern in der Galerie |
| `nov8/c_lucky_pick.py`, `nov8/d_two_paths.py` | Vorlagen im neuen Stil: Video C (1 Aktie → reich? 29.081-Punkte-Raster, Bessembinder 2026), Video D (Jake gibt aus, Emma investiert $300/Monat, eigene Rechnung 7 %) |
| `mix10.py` | Soundmix: Stimme + ca. 200 Effekte an den exakten Wort-Zeiten, danach -14 LUFS |
| `sfx.py`, `sfx2.py`, `sfx3.py` | Synthetische Effekte (whoosh, pop, tick, ding, bass, riser, impact, alert, coin, cash, blip, sweep_down, ping, vroom, sparkle, flutter, puff) |
| `captions2.py` | Wortgenaue Untertitel (nur wenn gewünscht) |
| `short08_example/` … `short11_example/` | `words.json` und `upload_text.txt` von Short #8 bis #11 |
| `assets/moneycheck_profile.png` | Profilbild |

## Neues Video in 7 Schritten
1. Skript schreiben: Englisch, 60–75 s, Hook → 3–5 Punkte mit korrekten Zahlen → Höhepunkt → Loop. Keine Anlageempfehlungen.
2. Stimme und Wort-Zeiten in einem Schritt: `python3 voice_local.py speak skript.txt voice.mp3 words.json` (Stimme `af_heart`).
3. `words.json` enthält jedes Skript-Wort mit Start- und Endzeit. Szenen und Soundeffekte hängen an diesen Zeiten.
4. Szenen schreiben: `nov8/c_lucky_pick.py` oder `nov8/d_two_paths.py` kopieren (Engine `lib20.py`, Ton `mix20.py`). Stationen in
   der Welt anlegen, Kamera mit `Cam` von Station zu Station fahren lassen (Ankunft = erstes Wort der Station), jede Einblendung
   mit `hit(t, T("wort"))` fertig zum Wort, Überschriften mit `headline()`. Keine Überblendungen.
5. Prüfen und rendern: `python3 c_lucky_pick.py sheet sheet.png 0 1.5 3 …` (Kontaktbogen ansehen, Loop: erstes = letztes Bild),
   dann `python3 c_lucky_pick.py video` (Bild, Ton, Mux in einem Schritt) und `cover`.
6. Ton: `mix10.py` anpassen (Effekte an `at(...)`), dann `python3 mix10.py`. Danach zweistufig auf -14 LUFS normalisieren
   und zusammenführen:
   ```
   ffmpeg -i voice_sfx.wav -af loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json -f null -   # Werte ablesen
   ffmpeg -i voice_sfx.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11:measured_I=..:measured_TP=..:measured_LRA=..:measured_thresh=..:offset=..:linear=true" -ar 48000 -ac 2 voice_sfx_n.wav
   ffmpeg -i video_noaudio.mp4 -i voice_sfx_n.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart final.mp4
   ```
7. `upload_text.txt` schreiben: Titel, Beschreibung mit Quellen, „Not financial advice – for educational purposes only.“,
   Hashtags, Hinweis auf die KI-Kennzeichnung.

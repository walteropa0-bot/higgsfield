# YT01 – „Most Stocks Lose Money. So Why Does the Market Go Up?“ (YouTube, 16:9, ca. 9:20)

Erstes langes YouTube-Video. Animationen in 2560×1440 (`../lib16.py`). Alle Szenen hängen an Wörtern aus `script.txt`
(`tl.py`). Deshalb rendert das Video ohne Stimme mit geschätzten Zeiten (Vorschau) und mit Stimme an den echten Wort-Zeiten.

| Datei | Inhalt |
|---|---|
| `script.txt` | Sprechertext in 4 Teilen (je eine Aufnahme mit Voice Studio), ca. 8.500 Zeichen |
| `tl.py` | Skript → Wort-Zeiten (Schätzung oder `voice/part{n}_words.json`) → `T("phrase")`. `python3 tl.py part 2` gibt Teil 2 aus |
| `scenes.py` | 54 Szenen, 7 Kapitel, Quellenzeile pro Szene, Soundeffekte pro Szene |
| `render.py` | `info` · `sheet out.png [t…]` · `frame out.png t` · `video out.mp4` (ca. 37 min) |
| `music.py` | Eigene Hintergrundmusik (numpy): Flächen, Arpeggio, Bass, Hall; eine Akkordfolge pro Kapitel |
| `mix.py` | Stimme −16 LUFS + Musik −31 + Effekte −26 → zweistufig auf −14 LUFS. `preview` = ohne Stimme. `mux` |
| `thumb.py` | YouTube-Thumbnail 1280×720 |
| `upload.py` | `upload_text.txt` mit Kapitelmarken aus der aktuellen Timeline, Quellen, Tags |
| `coinmarket.py` | Eigene Rechnung „Münzwurf-Markt“ (1.024 Aktien, ±50/−40 %, Portfolio-Simulation) |
| `data/sp500_tbill_1928_2025.json` | Jahresrenditen S&P 500 / T-Bills (Damodaran, NYU Stern, Jan 2026) für die echten Kurven |

## Stimme einsetzen (Voice Studio, lokal)
1. Voice Studio auf dem Rechner starten. Die Profil-ID steht in `../../CLAUDE.md` (Abschnitt Ton).
2. Für jeden Teil n = 1…4: `python3 tl.py part n > part{n}.txt`, dann
   `python3 ../voicestudio_tts.py speech part{n}.txt voice/part{n}.mp3 --voice <PROFIL-ID>` (genau eine Aufnahme pro Teil).
3. Wort-Zeiten: `python3 ../voicestudio_tts.py words voice/part{n}.mp3 voice/part{n}_words.json`.
4. `python3 render.py info` (muss `mode voice` zeigen), Kontaktbogen prüfen, dann:
   ```
   python3 render.py video video.mp4
   python3 mix.py audio.wav
   python3 mix.py mux video.mp4 audio.wav moneycheck_yt01_most_stocks_lose.mp4
   python3 upload.py upload_text.txt
   ```

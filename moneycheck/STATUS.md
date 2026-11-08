# Moneycheck – Stand und offene Aufgaben (Stand 8.11.2026)

Regeln und Stil: `../CLAUDE.md` · Dateien und Workflow: `README.md` · Prompt für einen neuen Chat: `PROMPT_NEUER_CHAT.txt`

## Fertig
| Video | Ordner | Stand |
|---|---|---|
| Shorts #8–#11 | `render10.py` … `render13.py` | fertig, hochgeladen vom Nutzer |
| 6 Wochen-Videos (Sa 7.11. – Do 12.11.) | `week_nov7/` | fertig, ohne Stimme (Text-Animation, `eng14.py`) |
| **YT01** – „Most Stocks Lose Money. So Why Does the Market Go Up?“ (YouTube, 16:9, 9:18) | `yt01_most_stocks_lose/` | Animation, Musik, Thumbnail, Upload-Text fertig; Vorschau ohne Stimme geliefert. **Stimme fehlt** |
| **Video A** – „$5 a day: piggy bank vs. stock market“ (25 s, ohne Stimme) | `nov8/a_piggy_vs_stocks.py` | fertig geliefert |
| **Video B** – „How much money do you need to stop working?“ (25 s, 25x-/4-%-Regel) | `nov8/b_25x_rule.py` | fertig ohne Stimme geliefert. **Stimme fehlt** |

## Offen (wartet auf den Nutzer)
1. **Stimme per Voice Studio (lokal, seit 8.11.):** ElevenLabs ist abgelöst (Gratis-Konto gesperrt). Voice Studio auf dem Rechner
   starten, dann im Ordner `moneycheck/`: `python3 voicestudio_tts.py candidates kandidaten/`. Anhören: drei weibliche Test-Stimmen
   (A britisch, B US, C US tief). Die beste als Profil in Voice Studio speichern und die Profil-ID an Claude schicken; sie kommt dann
   in `../CLAUDE.md` (Abschnitt Ton).
2. **Lizenz vor Monetarisierung:** Laut Lizenzliste ist kein Voice-Studio-Modell kommerziell freigegeben (OmniVoice: CC-BY-NC).
   Bis das geklärt ist, nur Test- und Vorschau-Material. Die Modell-Karte der gewählten Engine auf Hugging Face prüfen.
3. **YT01-Stimme (4 Teile):** im Ordner `yt01_most_stocks_lose/`: `python3 tl.py part n > part{n}.txt`, dann
   `python3 ../voicestudio_tts.py speech part{n}.txt voice/part{n}.mp3 --voice <ID>` und
   `python3 ../voicestudio_tts.py words voice/part{n}.mp3 voice/part{n}_words.json`. Danach neu rendern (ca. 37 min) und mischen.
4. **Video-B-Stimme** (im Ordner `nov8/`): `python3 ../voicestudio_tts.py speech b_script.txt b_voice.mp3 --voice <ID>`, dann
   `python3 ../voicestudio_tts.py words b_voice.mp3 b_words.json`, danach `python3 b_25x_rule.py video` und `cover` im Ausgabeordner.

## Wichtige Erkenntnisse
- TikTok-Länge: sehr kurze Clips werden am häufigsten zu Ende geschaut, 30–90 s bringen die meisten Interaktionen
  (Fanpage Karma, 32.000 TikToks); Creator Rewards zahlt erst ab 1 Minute.
- Posting-Zeiten (US-Publikum, deutsche Zeit): So 15 Uhr, Mo 19 Uhr, Di–Do 20–24 Uhr (Buffer 7,1 Mio. Posts; Sprout Social).
  Am besten: TikTok Studio → Follower-Aktivität.
- YouTube-Monetarisierung: 1.000 Abos + 4.000 Std. (12 Mon.) oder 10 Mio. Shorts-Aufrufe (90 Tage); ab 1.2.2027 laut Berichten
  8.000 Std. bzw. 20 Mio. Regel gegen „inauthentische“ Massenware → jedes Video eigenständig (siehe CLAUDE.md).
- Cloud-Umgebung „higgsfield“ erlaubt die Recherche-Seiten (ASU, CFA Institute, J.P. Morgan, NYU Stern, WealthManagement, SSRN, S&P). S&P und SSRN blocken automatische Abrufe – nicht umgehen. Stimmen laufen lokal über Voice Studio; huggingface.co ist in dieser Umgebung nicht erreichbar.

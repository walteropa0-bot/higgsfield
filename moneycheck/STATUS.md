# Moneycheck – Stand und offene Aufgaben (Stand 8.11.2026)

Regeln und Stil: `../CLAUDE.md` · Dateien und Workflow: `README.md` · Prompt für einen neuen Chat: `PROMPT_NEUER_CHAT.txt`

## Fertig
| Video | Ordner | Stand |
|---|---|---|
| Shorts #8–#11 | `render10.py` … `render13.py` | fertig, hochgeladen vom Nutzer |
| 6 Wochen-Videos (Sa 7.11. – Do 12.11.) | `week_nov7/` | fertig, ohne Stimme (Text-Animation, `eng14.py`) |
| **YT01** – „Most Stocks Lose Money. So Why Does the Market Go Up?“ (YouTube, 16:9, 9:38) | `yt01_most_stocks_lose/` | mit Stimme (Kokoro) gerendert und geliefert (8.11.), Kapitelmarken aktualisiert |
| **Video A** – „$5 a day: piggy bank vs. stock market“ (25 s, ohne Stimme) | `nov8/a_piggy_vs_stocks.py` | fertig geliefert |
| **Video B** – „How much money do you need to stop working?“ (25 s, 25x-/4-%-Regel) | `nov8/b_25x_rule.py` | mit Stimme geliefert (Kokoro), Cover-Zahl korrigiert ($1,000,000) |
| **Video C** – „One lucky pick“ (36 s, cryothum-Stil, 29.081-Punkte-Raster) | `nov8/c_lucky_pick.py` | fertig geliefert, Upload-Text in `nov8/upload_texts_nov8.txt` |
| **Video D** – „Same job, same paycheck“ (31 s, Jake vs. Emma, $300/Monat) | `nov8/d_two_paths.py` | fertig geliefert, Upload-Text in `nov8/upload_texts_nov8.txt` |

## Offen (wartet auf den Nutzer)
1. **Hörprobe und Upload:** Videos B, C, D und YT01 sind geliefert (Kokoro-Stimme af_heart). Vor dem Upload kurz reinhören und
   die KI-Kennzeichnung setzen (TikTok „AI-generated content“, YouTube „Altered or synthetic content“). Upload-Texte:
   `nov8/upload_texts_nov8.txt` (B, C, D) und `yt01_most_stocks_lose/upload_text.txt` (YT01, mit Kapitelmarken).
2. **Monetarisierung:** Die Kokoro-Stimme ist Apache-2.0 und darf verwendet werden. Voice-Studio-Modelle bleiben gesperrt.
3. **Nächste Videos:** im neuen Stil (`lib20.py`, Vorlagen `nov8/c_lucky_pick.py`, `nov8/d_two_paths.py`); der Nutzer schickt
   eventuell weitere cryothum-Beispiele.

## Wichtige Erkenntnisse
- TikTok-Länge: sehr kurze Clips werden am häufigsten zu Ende geschaut, 30–90 s bringen die meisten Interaktionen
  (Fanpage Karma, 32.000 TikToks); Creator Rewards zahlt erst ab 1 Minute.
- Posting-Zeiten (US-Publikum, deutsche Zeit): So 15 Uhr, Mo 19 Uhr, Di–Do 20–24 Uhr (Buffer 7,1 Mio. Posts; Sprout Social).
  Am besten: TikTok Studio → Follower-Aktivität.
- YouTube-Monetarisierung: 1.000 Abos + 4.000 Std. (12 Mon.) oder 10 Mio. Shorts-Aufrufe (90 Tage); ab 1.2.2027 laut Berichten
  8.000 Std. bzw. 20 Mio. Regel gegen „inauthentische“ Massenware → jedes Video eigenständig (siehe CLAUDE.md).
- Cloud-Umgebung „higgsfield“ erlaubt die Recherche-Seiten (ASU, CFA Institute, J.P. Morgan, NYU Stern, WealthManagement, SSRN, S&P). S&P und SSRN blocken automatische Abrufe – nicht umgehen. Stimmen laufen lokal (Kokoro über sherpa-onnx; Modelle von GitHub-Releases, Hugging Face ist hier gesperrt).

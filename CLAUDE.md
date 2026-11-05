# Moneycheck – Video-Projekt (Notizen für Claude)

Kanal/Brand: **Moneycheck** (finanzielle Tipps, Englisch, USA-Zielgruppe 18–35).
Wenn der Name sich ändert, diese Datei anpassen.

## Stil
- Format: 9:16, 1080×1920, 30 fps
- Hintergrund: Navy (ca. #0B1426 bis #142442 mit leichtem Verlauf), Punktraster dezent
- Akzent: Gold (#D4AF37, hell #F5D76E), Text Weiß, Sekundärtext Grau-Blau (#8C9BB9)
- Geld/Gewinne immer **Grün** (#2ECC71), Verluste/Crash **Rot** (#EF5350)
- Schrift: Inter (Black / ExtraBold / SemiBold)
- Animierte Zahlen, Balken- und Liniendiagramme, Kinetic Typography
- **Premium-Look seit Short #8** (Nutzer will ihn „qualitativ und hochwertig“), angelehnt an den TikTok-Kanal cryothum,
  aber in unseren Farben: leuchtende „Männchen“ (Bauern-Figur: runder Kopf, abgerundeter Körper), kleine Pill-Labels
  mit gesperrten Großbuchstaben, gestrichelte Linien, Spotlight-Kegel, Bloom-Glow, feines Korn, viele Szenenwechsel
  (ca. alle 3–6 s), Kamerafahrten. Umsetzung: `moneycheck/lib10.py` (2×-Supersampling, echte Transparenz, Bloom).
- Untertitel nur, wenn der Nutzer sie will (Short #8 ausdrücklich OHNE Untertitel). Falls ja:
  - Inter SemiBold ca. 46 px, weiß mit dünner dunkler Kontur, KEINE Box
  - max. 5 Wörter pro Einblendung, eine Zeile wenn möglich, sonst zwei ausgeglichene Zeilen
  - genau ein aktives Wort in Gold, Wechsel exakt, wenn die nächsten Wörter gesprochen werden
  - Position ca. y = 1405 (unteres Drittel, über der TikTok-Oberfläche)
- Fortschrittsbalken oben
- Wichtige Inhalte zwischen y ≈ 250 und 1450 und links von x ≈ 950 halten (TikTok-Oberfläche)

## Aufbau eines Shorts
1. Hook (0–2 s): überraschende Zahl oder Frage
2. Versprechen: warum bis zum Ende dranbleiben
3. Hauptteil: 3–5 Punkte mit Zahlen/Beispielen
4. Höhepunkt: wertvollster Tipp zuletzt
5. Schluss: Loop zurück zum Anfang (letztes Bild = erstes Bild) + „Follow for more“
Länge: 60–75 Sekunden (TikTok vergütet erst Videos über 1 Minute)

## Ton
- ElevenLabs, Modell `eleven_v4`
- Frauenstimme (Nutzerwunsch, hochwertig): **Samara X – Smooth Classy British** (`19STyYD15bswVz51nqLf`), seit Short #8.
  Die frühere Frauenstimme `E8FfddrREO3vtyNsTKnh` gefiel dem Nutzer NICHT.
- Männerstimme: **Brian** (`nPczCjzI2devNBz1zQrb`)
- Immer nur eine Aufnahme erzeugen (Credits sparen, `generations_count=1`), Kostenschätzung vorher mit `estimate_only`
  (ca. 1 Credit pro Zeichen, ~1000 Credits für 64 s)
- Audio mischen auf **-14 LUFS** (YouTube/TikTok), zweistufiges loudnorm
- Viele Soundeffekte, Geld muss man hören: coin, cash, ding, sparkle, whoosh, pop, tick, swoosh_up, bass, impact,
  sweep_down, riser (`moneycheck/sfx*.py`, `mix10.py`)

## Wasserzeichen (in jedem Video)
- Text: **Moneycheck**
- Klein, schlicht, unten rechts (ca. x = 1020, y = 1700), Weiß mit ca. 60 % Deckkraft
- Nicht in den Untertitelbereich legen

## Pflicht in jeder Beschreibung
- „Not financial advice – for educational purposes only.“
- Keine konkreten Aktien-, Krypto- oder Produktempfehlungen
- Nur korrekte, allgemein gültige Zahlen und Fakten, Quellen in der Beschreibung nennen

## Profilbild
- `moneycheck/assets/moneycheck_profile.png` (Dollar mit Haken-Abzeichen, Gold auf Navy)

## Arbeitsablauf
- Skripte liegen im Repo unter `moneycheck/` (siehe `moneycheck/README.md`). Das Scratchpad ist nach jeder Sitzung weg.
  Vorlage für neue Videos: `render10.py` (Szenen + Timeline + Cover) mit `lib10.py`, Ton: `mix10.py`.
- Upload-Text (Titel, Beschreibung, Hashtags) wird pro Video als `upload_text.txt` geschrieben
- Ein Video pro Tag. Der Nutzer lädt selbst hoch.
- Nach der Sprachaufnahme die Aufnahme mit ElevenLabs transkribieren
  (`creative_add_flow_asset_node` mit der generation_id, dann `creative_transcribe_audio`, Modell `eleven_scribe_v1`;
  0 Credits). Die Wort-Zeitstempel als `words.json` speichern (ohne `[tags]`).
- ALLE Szenen-Anker und Soundeffekte an die exakten Wort-Zeiten hängen (`at("wort", n)` in render10.py/mix10.py),
  nie an Schätzwerte oder reine Pausen-Erkennung (`align.py` hat bei Short #5 Sätze verschoben).
- Vor dem Rendern Kontaktbögen prüfen (`python3 render10.py sheet sheet.png 1.0 5.0 …`), dann `video`, `mix10.py`, muxen.

## Cover
- Bei jedem neuen Video direkt ein Cover mit erstellen (1080×1920, gleicher Stil, Wasserzeichen Moneycheck unten rechts).
- Vorlage: `cover()` in `moneycheck/render10.py`. Titel auf dem Cover kurz und groß, eine Hauptzahl oben.

## KI-Kennzeichnung
- KI-Stimme immer als KI-generiert kennzeichnen (Haken bei TikTok „AI-generated content“, YouTube „Altered or synthetic content“).

## Keine Anlageberatung
- Keine konkreten Aktien-, ETF- oder Kurs-Empfehlungen, auch nicht auf Wunsch. Stattdessen allgemeine Bildung und Verhaltensregeln.

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
- **Animationsstil seit 8.11.2026 (Nutzerwunsch, gilt ab jetzt immer): cryothum-Stil in unseren Farben.** Engine
  `moneycheck/lib20.py`, Vorlagen `nov8/c_lucky_pick.py` und `nov8/d_two_paths.py`:
  - Eine Welt, eine Kamera: Stationen liegen nebeneinander, die Kamera fährt dazwischen. Keine Überblendung zweier Bilder.
    Das Punktraster bewegt sich mit der Kamera.
  - Linien-Icons wie bei cryothum (Browserfenster, Button mit Klick-Cursor, Schalter „ON“, Karte mit Kopfzeile und Häkchen,
    Zahlenbox, Monitor und Schreibtisch, Bürogebäude, Handy, Tasche, Schuh, Chart, Benachrichtigung), Männchen mit Armen.
  - **Hit-Timing:** Jede Einblendung ist fertig, wenn ihr Wort beginnt (`hit(t, T("wort"))`), nie danach (Video B hing nach).
  - Überschriften und große Zahlen liegen in der Bildschirm-Ebene: Sie verlassen das Bild vor jeder Kamerafahrt und landen mit
    dem ersten Wort der neuen Station (`headline()`), damit sich an Szenen-Enden nichts überlagert.
  - Zahlenbilder möglichst maßstabsgetreu (Video C: ein Punkt pro Firma, 29.081 Punkte). Letztes Bild = erstes Bild (Loop).
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
Länge: 60–75 Sekunden (TikTok vergütet erst Videos über 1 Minute). Kurze Viral-Videos (20–30 s) nur, wenn der Nutzer es will.

## Ton
- **Stimme: Kokoro, lokal** (seit 8.11.2026). Erzeugt wird auf dem eigenen Rechner, ohne Cloud und ohne Abo, mit dem Modell
  Kokoro-82M (Apache-2.0) über sherpa-onnx. Stimme: `af_heart` (weibliche US-Stimme). ElevenLabs ist nicht mehr im Einsatz.
- Befehl im Ordner `moneycheck/`: `python3 voice_local.py speak skript.txt voice.mp3 words.json`; für Shorts zusätzlich
  `--pause 0.18 --para 0.3 --speed 1.05` (sonst zu lange Pausen). Einmalige Installation:
  `pip install sherpa-onnx numpy cmudict` und ffmpeg. Die Modelle (ca. 700 MB) lädt das Skript beim ersten Lauf von GitHub.
- Wort-Zeiten kommen mit: Satzanfänge exakt aus der Erzeugung (dort beginnt das Audio), übrige Wörter aus der Erkennung
  (Zipformer, Apache-2.0), korrigiert um ihren gemessenen Versatz (ca. +80 ms) und auf Einsätze im Signal eingerastet.
  Szenen und Soundeffekte hängen an diesen Zeiten, nicht an Schätzungen.
- Aussprache: Wörter, die das Kokoro-Lexikon nicht kennt, kommen aus CMUdict. Namen und Sonderfälle stehen in
  `moneycheck/pronunciations.txt`. Fehlt eine Aussprache, bricht der Lauf ab, statt Wörter wegzulassen.
- **Lizenz:** Kokoro-82M ist Apache-2.0 (Lizenztext im Modellpaket) und darf in monetarisierten Videos verwendet werden.
  Die Voice-Studio-Modelle sind in der Lizenzliste nicht als kommerziell freigegeben (OmniVoice: CC-BY-NC) und bleiben dafür gesperrt.
- Claude kann die Stimme nicht hören. Vor dem Upload kurz anhören.
- Genau 1 Take pro Teil. Fehler melden, nicht stillschweigend wiederholen.
- Audio mischen auf **-14 LUFS** (YouTube/TikTok), zweistufiges loudnorm
- Ohne Stimme (Vorschau, Test): Text-Animation mit `moneycheck/eng14.py` (1440×2560, kurze Sätze groß eingeblendet); der Nutzer legt in TikTok einen Sound darunter.
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
  Vorlage für neue Videos: `nov8/c_lucky_pick.py` oder `nov8/d_two_paths.py` mit `lib20.py`, Ton: `mix20.py`.
- Upload-Text (Titel, Beschreibung, Hashtags) wird pro Video als `upload_text.txt` geschrieben
- Ein Video pro Tag. Der Nutzer lädt selbst hoch.
- **Originalität (Pflicht, Stand 6.11.2026):** Jedes Video bekommt ein eigenes Thema, eigene Berechnung oder eigenes Beispiel,
  klare Quellen und eine eigene Erzählweise. Keine Kopie einer Vorlage mit nur geänderten Zahlen. Ziel: keine Nachteile durch
  YouTube-Monetarisierung (Regel gegen „inauthentische“ Massenware) und keine Reichweitenverluste bei TikTok.
- **Stil-Regel:** Wiedererkennbar bleiben über Logo, Farben, Schrift, Intro und Wasserzeichen. Format, Vorlage, Hook, Länge
  und Erzählweise dürfen sich ändern. Fortschritt wird an Zuschauerbindung, Shares und Follower-Zuwachs gemessen.
- Die Wort-Zeiten (`words.json`) entstehen beim Sprechen mit `voice_local.py speak`. Nichts muss separat transkribiert werden.
- ALLE Szenen-Anker und Soundeffekte an die exakten Wort-Zeiten hängen (`at("wort", n)` in render10.py/mix10.py),
  nie an Schätzwerte oder reine Pausen-Erkennung (`align.py` hat bei Short #5 Sätze verschoben).
- Vor dem Rendern Kontaktbögen prüfen (`python3 render10.py sheet sheet.png 1.0 5.0 …`), dann `video`, `mix10.py`, muxen.

## Lange YouTube-Videos (16:9), seit YT01
- Engine `moneycheck/lib16.py`, Vorlage `moneycheck/yt01_most_stocks_lose/` (README dort). Ausgabe 2560×1440, 30 fps
  (YouTube gibt 1440p-Uploads einen besseren Codec). x264 `fast`, crf 16, statisches Korn (wechselndes Korn bremst den Encoder).
- Länge ab 8 Minuten (Mid-Roll-Werbung möglich), Kapitel im Video (Kapitelkarte + Label oben links) und als Zeitstempel in der
  Beschreibung (erster Zeitstempel 0:00), Quellenzeile unten links pro Szene, 12 s Endkarte für YouTube-Endbildschirm-Elemente.
- Szenen hängen an Phrasen des Skripts (`T("phrase")`), nicht an Sekunden. Ohne Stimme rendert dieselbe Szenenliste mit
  geschätzten Zeiten als Vorschau.
- Thumbnail 1280×720 (< 2 MB), wenige große Wörter.
- Recherche: Die Umgebung „higgsfield“ erlaubt die Studien-Seiten (ASU, CFA Institute, J.P. Morgan, NYU Stern,
  WealthManagement, SSRN, S&P). S&P und SSRN blocken automatische Abrufe; Bot-Sperren nicht umgehen, stattdessen
  zwei unabhängige Berichte über den Bericht nutzen und das kennzeichnen.

## Cover
- Bei jedem neuen Video direkt ein Cover mit erstellen (1080×1920, gleicher Stil, Wasserzeichen Moneycheck unten rechts).
- Vorlage: `cover()` in `moneycheck/render10.py`. Titel auf dem Cover kurz und groß, eine Hauptzahl oben.

## KI-Kennzeichnung
- KI-Stimme immer als KI-generiert kennzeichnen (Haken bei TikTok „AI-generated content“, YouTube „Altered or synthetic content“).

## Keine Anlageberatung
- Keine konkreten Aktien-, ETF- oder Kurs-Empfehlungen, auch nicht auf Wunsch. Stattdessen allgemeine Bildung und Verhaltensregeln.

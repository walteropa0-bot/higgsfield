# Moneycheck – Video-Projekt (Notizen für Claude)

Kanal/Brand: **Moneycheck** (finanzielle Tipps, Englisch, USA-Zielgruppe 18–35).
Wenn der Name sich ändert, diese Datei anpassen.

## Stil
- Format: 9:16, 1080×1920, 30 fps
- Hintergrund: Navy (ca. #0B1426 bis #142442 mit leichtem Verlauf), Grid-Linien dezent
- Akzent: Gold (#D4AF37, hell #F5D76E), Text Weiß, Sekundärtext Grau-Blau (#8C9BB9)
- Schrift: Inter (Black / ExtraBold / SemiBold)
- Animierte Zahlen, Balken- und Liniendiagramme, Kinetic Typography
- Untertitel: Wort-für-Wort-Hervorhebung in Gold, unten im Drittel
- Fortschrittsbalken oben

## Aufbau eines Shorts
1. Hook (0–2 s): überraschende Zahl oder Frage
2. Versprechen: warum bis zum Ende dranbleiben
3. Hauptteil: 3–5 Punkte mit Zahlen/Beispielen
4. Höhepunkt: wertvollster Tipp zuletzt
5. Schluss: Loop zurück zum Anfang + „Follow for more“
Länge: 60–75 Sekunden

## Ton
- ElevenLabs, Stimme: **Brian** (`nPczCjzI2devNBz1zQrb`), Modell `eleven_v4`
- Immer nur eine Aufnahme erzeugen (Credits sparen), Kostenschätzung vorher mit `estimate_only`
- Audio mischen auf **-14 LUFS** (YouTube/TikTok)
- Soundeffekte dezent: whoosh, pop, tick, ding, swoosh_up, bass

## Wasserzeichen (in jedem Video)
- Text: **Moneycheck**
- Klein, schlicht, unten rechts, Weiß mit ca. 60 % Deckkraft
- Nicht in den Untertitelbereich legen

## Pflicht in jeder Beschreibung
- „Not financial advice – for educational purposes only.“
- Keine konkreten Aktien-, Krypto- oder Produktempfehlungen
- Nur korrekte, allgemein gültige Zahlen und Fakten

## Profilbild
- `scratchpad/profile/moneycheck_profile.png` (Dollar mit Haken-Abzeichen, Gold auf Navy)

## Arbeitsablauf
- Projekt-Skripte liegen im Scratchpad unter `short02/` (render.py, mix.py, sfx.py) und `short03/` (render2.py, mix2.py, align.py, timing.py, phrases.py)
- Upload-Text (Titel, Beschreibung, Hashtags) wird pro Video als `upload_text.txt` geschrieben
- Ein Video pro Tag. Der Nutzer lädt selbst hoch.
- Vor dem Rendern die Sprachaufnahme über `align.py` den echten Sprechpausen zuordnen, nicht mit Schätzwerten arbeiten.

## Qualität (Nutzerwunsch)
- Videos sollen noch sauberer wirken, aber nicht überladen: weniger Elemente gleichzeitig, mehr Weißraum, klare Hierarchie.
- Das Schema (Farben, Schrift, Aufbau, Loop, Stimme, Wasserzeichen) bleibt unverändert.
- Keine konkreten Aktien-, ETF- oder Kurs-Empfehlungen, auch nicht auf Wunsch. Stattdessen allgemeine Bildung und Verhaltensregeln.

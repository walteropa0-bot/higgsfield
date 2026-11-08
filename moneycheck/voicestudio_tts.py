#!/usr/bin/env python3
"""Moneycheck-Stimme über die lokale Voice-Studio-API.

Voice Studio läuft auf deinem Rechner (Standard: http://localhost:3900). Dieses Skript spricht nur
mit dieser API. Modelle, Stimmen und Audio bleiben auf deinem Rechner.

  python3 voicestudio_tts.py health
  python3 voicestudio_tts.py voices
  python3 voicestudio_tts.py candidates kandidaten/
  python3 voicestudio_tts.py speech part1.txt voice/part1.mp3 --voice <PROFIL-ID>
  python3 voicestudio_tts.py words voice/part1.mp3 voice/part1_words.json

Endung .mp3 erzeugt MP3, sonst WAV. Wort-Zeiten liefert Voice Studio selbst (Transkription mit Wort-Zeitstempeln).
Andere Adresse: Umgebungsvariable VOICESTUDIO_URL.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

BASE = os.environ.get("VOICESTUDIO_URL", "http://localhost:3900").rstrip("/")
TIMEOUT = 1800  # Erzeugung auf dem Rechner kann lange dauern

# Weibliche Test-Stimmen; Beschreibungen aus dem Voice-Design-Vokabular von Voice Studio.
CANDIDATES = {
    "A_britisch_jung": "female, young adult, moderate pitch, british accent",
    "B_amerikanisch_jung": "female, young adult, moderate pitch, american accent",
    "C_amerikanisch_tief": "female, middle-aged, low pitch, american accent",
}
TEST_TEXT = (
    "This is a voice test for Moneycheck. Money is easier to understand "
    "when you look at the numbers, one step at a time."
)


def call(path, body=None, content_type=None):
    req = urllib.request.Request(BASE + path, data=body)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        sys.exit(f"Voice Studio meldet HTTP {e.code} bei {path}: {detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Voice Studio ist unter {BASE} nicht erreichbar ({e.reason}). Läuft die App?")


def speech(text, out, voice, instruct=None):
    fmt = "mp3" if out.lower().endswith(".mp3") else "wav"
    body = {"model": "tts-1", "voice": voice, "input": text, "response_format": fmt}
    if instruct:
        body["instruct"] = instruct
    audio = call("/v1/audio/speech", json.dumps(body).encode(), "application/json")
    if fmt == "wav":
        ok = audio[:4] == b"RIFF"
    else:
        ok = audio[:3] == b"ID3" or audio[:1] == b"\xff"
    if not ok:
        sys.exit(f"Keine Audio-Datei erhalten: {audio[:200]!r}")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(audio)
    print(f"geschrieben: {out} ({len(audio) // 1024} KB, {fmt})")


def multipart(fields, path):
    sep = uuid.uuid4().hex.encode()
    parts = []
    for name, value in fields:
        parts += [b"--" + sep, f'Content-Disposition: form-data; name="{name}"'.encode(), b"", value.encode()]
    with open(path, "rb") as f:
        data = f.read()
    filename = os.path.basename(path)
    parts += [
        b"--" + sep,
        f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode(),
        b"Content-Type: application/octet-stream",
        b"",
        data,
        b"--" + sep + b"--",
        b"",
    ]
    return b"\r\n".join(parts), f"multipart/form-data; boundary={sep.decode()}"


def words(audio, out_json):
    fields = [
        ("model", "whisper-1"),
        ("language", "en"),
        ("response_format", "verbose_json"),
        ("timestamp_granularities[]", "word"),
    ]
    data, ctype = multipart(fields, audio)
    result = json.loads(call("/v1/audio/transcriptions", data, ctype))
    items = result.get("words")
    if items is None:
        items = [w for seg in result.get("segments", []) for w in seg.get("words", [])]
    out = []
    for w in items:
        text = str(w.get("word", w.get("text", ""))).strip()
        if not text or (text.startswith("[") and text.endswith("]")):
            continue  # Tags wie [laughs] gehören nicht in die Wortliste
        out.append({"text": text, "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)})
    if not out:
        sys.exit("Keine Wort-Zeiten erhalten. Ist in Voice Studio ein Transkriptionsmodell installiert?")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{len(out)} Wörter -> {out_json}")


def candidates(outdir):
    os.makedirs(outdir, exist_ok=True)
    for name, tags in CANDIDATES.items():
        speech(TEST_TEXT, os.path.join(outdir, f"cand_{name}.wav"), voice="alloy", instruct=tags)
        print(f"  {name}: {tags}")


def main():
    p = argparse.ArgumentParser(description="Moneycheck-Stimme über die lokale Voice-Studio-API")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="prüft, ob Voice Studio läuft")
    sub.add_parser("voices", help="zeigt Stimmprofile und Engines")
    c = sub.add_parser("candidates", help="drei weibliche Test-Stimmen zum Anhören")
    c.add_argument("outdir")
    s = sub.add_parser("speech", help="eine Aufnahme aus einer Textdatei")
    s.add_argument("textfile")
    s.add_argument("out", help="Ziel, .mp3 oder .wav")
    s.add_argument("--voice", required=True, help="Profil-ID der gewählten Stimme")
    s.add_argument("--instruct", help="nur ohne Profil: Stimm-Beschreibung")
    w = sub.add_parser("words", help="Wort-Zeiten einer Aufnahme als JSON")
    w.add_argument("audio")
    w.add_argument("out")
    a = p.parse_args()
    if a.cmd == "health":
        print(call("/health").decode("utf-8", "replace")[:300])
    elif a.cmd == "voices":
        print(json.dumps(json.loads(call("/v1/audio/voices")), ensure_ascii=False, indent=1)[:4000])
    elif a.cmd == "candidates":
        candidates(a.outdir)
    elif a.cmd == "speech":
        with open(a.textfile, encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            sys.exit("Die Textdatei ist leer.")
        speech(text, a.out, a.voice, a.instruct)
    elif a.cmd == "words":
        words(a.audio, a.out)


if __name__ == "__main__":
    main()

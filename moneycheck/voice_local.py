#!/usr/bin/env python3
"""Moneycheck-Stimme lokal (ohne Cloud, ohne Abo).

  python3 voice_local.py speak skript.txt voice.mp3 words.json [--voice af_heart]

Sprache: Kokoro-82M (Apache-2.0) über sherpa-onnx, CPU. Wort-Zeiten: Zipformer-Erkennung (Apache-2.0).
Jedes Skript-Wort bekommt die Zeit seines gesprochenen Wortes. words.json enthält genau die Skript-Tokens
(gleiche Schreibweise, gleiche Reihenfolge), damit tl.py und b_25x_rule.py ohne Umbau zuordnen.
Wörter, die das Kokoro-Lexikon nicht kennt, bekommen eine Aussprache aus CMUdict (pip install cmudict);
fehlt auch dort eine Aussprache, bricht der Lauf ab, statt Wörter stillschweigend wegzulassen.
Installation: pip install sherpa-onnx numpy cmudict   (ffmpeg muss installiert sein)
Modelle liegen in moneycheck/.models/ (ignoriert) und werden beim ersten Lauf von GitHub geladen.
"""
import argparse
import difflib
import functools
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.request
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("MONEYCHECK_MODELS", os.path.join(HERE, ".models"))
MODELS = {
    "kokoro": ("https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2",
               "kokoro-multi-lang-v1_0"),
    "asr": ("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
            "sherpa-onnx-zipformer-en-2023-06-26.tar.bz2", "sherpa-onnx-zipformer-en-2023-06-26"),
}
SPEAKERS = {"af_heart": 3, "af_bella": 2, "af_nicole": 6, "af_sarah": 9, "bf_emma": 21}  # speaker2id des Modells
PAUSE_SENTENCE, PAUSE_PARAGRAPH = 0.35, 0.7
MAX_CHARS = 280  # lange Sätze an Kommas teilen (Kontextlänge von Kokoro)


def ensure_model(name):
    url, folder = MODELS[name]
    target = os.path.join(MODEL_DIR, folder)
    if not os.path.isdir(target):
        os.makedirs(MODEL_DIR, exist_ok=True)
        archive = os.path.join(MODEL_DIR, folder + ".tar.bz2")
        print(f"lade {folder} ...", file=sys.stderr)
        urllib.request.urlretrieve(url, archive)
        with tarfile.open(archive, "r:bz2") as tar:
            try:
                tar.extractall(MODEL_DIR, filter="data")
            except TypeError:  # Python < 3.12
                tar.extractall(MODEL_DIR)
        os.remove(archive)
    return target


# ---------- Skript -> gesprochene Wörter ----------
ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen").split()
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def cardinal(n):
    if n < 20:
        return [ONES[n]]
    if n < 100:
        return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [ONES[n // 100], "hundred"] + (cardinal(n % 100) if n % 100 else [])
    for value, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand")):
        if n >= value:
            return cardinal(n // value) + [name] + (cardinal(n % value) if n % value else [])
    raise ValueError(n)


def year(n):
    hi, lo = divmod(n, 100)
    if 2000 <= n <= 2009:
        return ["two", "thousand"] + ([ONES[lo]] if lo else [])
    if lo == 0:
        return cardinal(hi) + ["hundred"]
    if lo < 10:
        return cardinal(hi) + ["oh", ONES[lo]]
    return cardinal(hi) + cardinal(lo)


def number_piece(piece):
    """'$5', '3.7%', '2025', '500' -> gesprochene Wörter (None, wenn es keine Zahl ist)."""
    m = re.fullmatch(r"(\$?)(\d[\d,]*)(?:\.(\d+))?(%?)", piece)
    if not m:
        return None
    dollar, whole, frac, pct = m.groups()
    n = int(whole.replace(",", ""))
    if dollar:
        return cardinal(n) + ["dollar" if n == 1 else "dollars"]
    if frac:
        words = cardinal(n) + ["point"] + [ONES[int(d)] for d in frac]
    elif len(whole) == 4 and "," not in whole and 1100 <= n <= 2099:
        words = year(n)
    else:
        words = cardinal(n)
    return words + (["per", "cent"] if pct else [])


CONTRACTIONS = {
    "what's": "what is", "that's": "that is", "it's": "it is", "there's": "there is", "here's": "here is",
    "let's": "let us", "who's": "who is", "he's": "he is", "she's": "she is",
    "don't": "do not", "doesn't": "does not", "didn't": "did not", "isn't": "is not", "aren't": "are not",
    "wasn't": "was not", "weren't": "were not", "won't": "will not", "can't": "can not",
    "couldn't": "could not", "wouldn't": "would not", "shouldn't": "should not", "you're": "you are",
    "they're": "they are", "we're": "we are", "i'm": "I am", "i'll": "I will", "you'll": "you will",
    "they'll": "they will", "we'll": "we will", "you've": "you have", "they've": "they have",
    "we've": "we have", "i've": "I have", "i'd": "I would", "you'd": "you would", "they'd": "they would",
}


def _plain(word):
    """Kürzungen ausschreiben, Besitz-Apostroph entfernen (Buffett's -> Buffetts)."""
    low = word.lower()
    if low in CONTRACTIONS:
        return CONTRACTIONS[low]
    return word.replace("'", "")


def spoken_words(token):
    core = re.sub(r"^[\"“”„‘’'(\[{*_]+|[\"“”‘’'\]\)}*_.,;:!?]+$", "", token)
    if not core:
        return []
    if core.replace(".", "") == "S&P":
        return ["S", "and", "P"]
    out = []
    for piece in re.split(r"[-–—/]", core):
        piece = piece.replace("’", "'").replace("&", " and ")
        if re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]?", piece):  # U.S.
            piece = " ".join(c for c in piece if c.isalpha())
        num = number_piece(piece.strip(".,;:!?"))
        if num is not None:
            out += num
            continue
        for w in piece.split():
            w = re.sub(r"[^A-Za-z0-9'\s]", "", w)
            if w.isupper() and 2 <= len(w) <= 4 and w.isalpha():  # Abkürzungen buchstabieren: US, ETF, CEO
                out += list(w)
            elif w:
                out += _plain(w).split()
    return [w for w in out if w]


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def build_units(text):
    units = []
    for line in text.splitlines():
        toks = line.split()
        for i, tok in enumerate(toks):
            m = re.search(r"([,;:.!?])[\"”’)]*$", tok)
            units.append(dict(tok=tok, words=spoken_words(tok), punct=m.group(1) if m else "",
                              sent_end=bool(re.search(r"[.!?][\"”’)]*$", tok)) or i == len(toks) - 1,
                              para_end=i == len(toks) - 1))
    return units


def sentences(units, pause_s=PAUSE_SENTENCE, pause_p=PAUSE_PARAGRAPH):
    """Sätze für die Sprachausgabe: (Text, Pause danach, Index des ersten gesprochenen Wortes)."""
    out, cur, first, count = [], [], 0, 0
    for u in units:
        if not cur:
            first = count
        if u["words"]:  # Kommas bleiben für die Sprechpausen, ? und ! für die Betonung
            cur += u["words"][:-1] + [u["words"][-1] + ("," if u["punct"] in (",", ";", ":") else "")]
        count += len(u["words"])
        if u["sent_end"] and cur:
            end = u["punct"] if u["punct"] in ("?", "!") else "."
            out.append((" ".join(cur).rstrip(",") + end, pause_p if u["para_end"] else pause_s, first))
            cur = []
    if cur:
        out.append((" ".join(cur) + ".", pause_p, first))
    final = []
    for s, pause, first in out:  # zu lange Sätze an Kommas teilen
        while len(s) > MAX_CHARS and "," in s[:MAX_CHARS]:
            cut = s.rfind(",", 0, MAX_CHARS)
            head = s[: cut + 1]
            final.append((head, 0.15, first))
            first += len(head.split())
            s = s[cut + 1:].strip()
        final.append((s, pause, first))
    return final


# ---------- Aussprache-Lexikon ----------
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
ARPA = {"AA": "ɑ", "AE": "æ", "AO": "ɔ", "AW": "W", "AY": "I", "EH": "ɛ", "EY": "A", "IH": "ɪ", "IY": "i",
        "OW": "O", "OY": "Y", "UH": "ʊ", "UW": "u", "B": "b", "CH": "ʧ", "D": "d", "DH": "ð", "F": "f",
        "G": "ɡ", "HH": "h", "JH": "ʤ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p",
        "R": "ɹ", "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w", "Y": "j", "Z": "z", "ZH": "ʒ"}


def arpa_tokens(phones):
    """CMUdict-Phoneme (ARPAbet) -> Kokoro-Zeichen; Betonung steht direkt vor dem Vokal wie im Lexikon."""
    out = []
    for ph in phones:
        base, stress = (ph[:-1], ph[-1]) if ph[-1].isdigit() else (ph, "0")
        if base in VOWELS and stress in "12":
            out.append("ˈ" if stress == "1" else "ˌ")
        if base == "AH":
            out.append("ʌ" if stress in "12" else "ə")
        elif base == "ER":
            out += ["ɜ", "ɹ"] if stress in "12" else ["ɚ"]
        else:
            out.append(ARPA[base])
    return out


def lexicon_keys(paths):
    keys = set()
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if parts:
                    keys.add(parts[0].lower())
    return keys


def manual_pronunciations():
    path = os.path.join(HERE, "pronunciations.txt")
    out = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split("#")[0].split()
                if len(parts) > 1:
                    out[parts[0].lower()] = parts[1:]
    return out


MANUAL = manual_pronunciations()


def cmu_pron(word, cmu):
    w = word.lower()
    if w in MANUAL:
        return MANUAL[w]
    if w in cmu:
        return cmu[w][0]
    if w.endswith("s") and len(w) > 2:  # Plural und Besitz über den Stamm (Bessembinders -> Bessembinder + z)
        stem = w[:-1]
        base = MANUAL.get(stem) or (cmu[stem][0] if stem in cmu else None)
        if base:
            return base + (["S"] if base[-1].rstrip("012") in ("P", "T", "K", "F", "TH") else ["Z"])
    return None


def custom_lexicon(words, base_paths, out_path, allowed):
    """Schreibt Aussprachen für alle Wörter, die das Kokoro-Lexikon nicht kennt. Gibt die Anzahl zurück."""
    import cmudict
    known, cmu = lexicon_keys(base_paths), cmudict.dict()
    lines, missing, seen = [], [], set()
    for w in words:
        key = w.lower()
        if key in known or key in seen:
            continue
        seen.add(key)
        phones = cmu_pron(w, cmu)
        toks = arpa_tokens(phones) if phones else None
        if not toks or any(t not in allowed for t in toks):
            missing.append(w)
            continue
        lines.append(f"{key} {' '.join(toks)}")
        if w != key:
            lines.append(f"{w} {' '.join(toks)}")
    if missing:
        raise SystemExit("Keine Aussprache für: " + ", ".join(sorted(set(missing))))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return len(seen) - len(missing), sorted({w for w in seen if w not in known})


# ---------- Sprache und Erkennung ----------
def synthesize(sents, voice, lexicon, speed=1.0):
    """Spricht Satz für Satz. Gibt Audio, Abtastrate und die exakten Satzanfänge zurück:
    [(Index des ersten Wortes, Sekunde, ab der das Audio des Satzes hörbar ist)]."""
    import sherpa_onnx
    k = ensure_model("kokoro")
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=f"{k}/model.onnx", voices=f"{k}/voices.bin", tokens=f"{k}/tokens.txt",
                data_dir=f"{k}/espeak-ng-data", dict_dir=f"{k}/dict", lexicon=lexicon),
            num_threads=4, provider="cpu"),
        max_num_sentences=1)
    tts = sherpa_onnx.OfflineTts(cfg)
    chunks, anchors, pos, sr = [], [], 0, 24000
    for text, pause, first in sents:
        audio = tts.generate(text, sid=SPEAKERS[voice], speed=speed)
        if len(audio.samples) == 0:
            raise SystemExit(f"Kein Audio für: {text[:80]!r}")
        sr = audio.sample_rate
        x = np.asarray(audio.samples, dtype=np.float32)
        loud = np.flatnonzero(np.abs(x) > 0.02 * max(float(np.abs(x).max()), 1e-6))
        anchors.append((first, (pos + (int(loud[0]) if len(loud) else 0)) / sr))
        gap = np.zeros(int(pause * sr), dtype=np.float32)
        chunks += [x, gap]
        pos += len(x) + len(gap)
    return np.concatenate(chunks), sr, anchors


def recognize(samples, sr):
    import sherpa_onnx
    a = ensure_model("asr")

    def pick(pattern):
        return sorted(os.path.join(a, x) for x in os.listdir(a) if re.search(pattern, x))[0]

    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=pick(r"^encoder.*int8.*\.onnx$"), decoder=pick(r"^decoder.*int8.*\.onnx$"),
        joiner=pick(r"^joiner.*int8.*\.onnx$"), tokens=f"{a}/tokens.txt", num_threads=4,
        decoding_method="greedy_search")
    s = rec.create_stream()
    s.accept_waveform(sr, samples)
    rec.decode_stream(s)
    words = []
    for tok, t in zip(s.result.tokens, s.result.timestamps):
        tok = tok.replace("▁", " ")
        if tok.startswith(" ") or not words:
            words.append({"text": tok.strip(), "start": float(t)})
        else:
            words[-1]["text"] += tok
    return [w for w in words if w["text"]]


# ---------- Zuordnung ----------
@functools.lru_cache(maxsize=None)
def _sim(a, b):
    """Ähnlichkeit zweier normalisierter Wörter (1.0 = gleich). Kurze Wörter nur exakt."""
    if a == b:
        return 1.0
    if len(a) < 4 or len(b) < 4:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def align_dp(a, b, thr=0.6):
    """Ausrichtung Skriptwörter (a) <-> Erkennungswörter (b): 1:1, 2:1 (zusammengeschrieben) und 1:2 (getrennt)."""
    n, m = len(a), len(b)
    NEG = float("-inf")
    S = [[NEG] * (m + 1) for _ in range(n + 1)]
    P = [[None] * (m + 1) for _ in range(n + 1)]
    S[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            cur = S[i][j]
            if cur == NEG:
                continue
            if i < n and cur - 0.5 > S[i + 1][j]:  # Skriptwort ohne Erkennung
                S[i + 1][j], P[i + 1][j] = cur - 0.5, ("gap", i, j)
            if j < m and cur - 0.2 > S[i][j + 1]:  # Erkennungswort ohne Skriptwort
                S[i][j + 1], P[i][j + 1] = cur - 0.2, ("skip", i, j)
            if i < n and j < m:
                sc = _sim(a[i], b[j])
                if sc >= thr and cur + sc > S[i + 1][j + 1]:
                    S[i + 1][j + 1], P[i + 1][j + 1] = cur + sc, ("11", i, j)
            if i + 1 < n and j < m:
                sc = _sim(a[i] + a[i + 1], b[j])
                if sc >= thr and cur + sc > S[i + 2][j + 1]:
                    S[i + 2][j + 1], P[i + 2][j + 1] = cur + sc, ("21", i, j)
            if i < n and j + 1 < m:
                sc = _sim(a[i], b[j] + b[j + 1])
                if sc >= thr and cur + sc > S[i + 1][j + 2]:
                    S[i + 1][j + 2], P[i + 1][j + 2] = cur + sc, ("12", i, j)
    pairs = []
    i, j = n, m
    while (i, j) != (0, 0):
        kind, pi, pj = P[i][j]
        if kind == "11":
            pairs.append(([pi], [pj]))
        elif kind == "21":
            pairs.append(([pi, pi + 1], [pj]))
        elif kind == "12":
            pairs.append(([pi], [pj, pj + 1]))
        i, j = pi, pj
    pairs.reverse()
    return pairs


def _onsets(x, sr, hop_s=0.005, quiet_s=0.04, db=-38.0):
    """Einsätze im Signal: erster lauter 5-ms-Rahmen nach mindestens 40 ms Stille. Gibt Zeiten und Lückenlängen zurück."""
    hop = max(1, int(hop_s * sr))
    env = np.sqrt(np.convolve(np.asarray(x, np.float32) ** 2, np.ones(hop) / hop, mode="same"))[::hop]
    quiet = env < float(env.max()) * 10 ** (db / 20)
    ons_t, ons_gap, run = [], [], 10 ** 6
    need = int(round(quiet_s / hop_s))
    for i, q in enumerate(quiet):
        if q:
            run += 1
        else:
            if run >= need:
                ons_t.append(i * hop_s)
                ons_gap.append(run * hop_s)
            run = 0
    return np.array(ons_t), np.array(ons_gap)


def align(units, asr, anchors=(), samples=None, sr=None):
    spoken = [(i, w) for i, u in enumerate(units) for w in u["words"]]
    a = [norm(w) for _, w in spoken]
    b = [norm(w["text"]) for w in asr]
    start = [None] * len(a)
    direct = [False] * len(a)
    for s_idx, t_idx in align_dp(a, b):
        t0 = asr[t_idx[0]]["start"]
        start[s_idx[0]], direct[s_idx[0]] = t0, True
        if len(s_idx) == 2:  # zwei Skriptwörter auf einem Erkennungswort: das zweite wird geschätzt
            nxt = asr[t_idx[-1] + 1]["start"] if t_idx[-1] + 1 < len(asr) else t0 + 0.3
            start[s_idx[1]] = t0 + 0.5 * (nxt - t0)
    matched = sum(direct)
    interpolated = 0
    known = [i for i, t in enumerate(start) if t is not None]
    for i in range(len(start)):
        if start[i] is not None and direct[i]:
            continue
        interpolated += 1
        if start[i] is not None:
            continue
        prev = max((k for k in known if k < i), default=None)
        nxt = min((k for k in known if k > i), default=None)
        if prev is not None and nxt is not None:
            t0, t1 = start[prev], start[nxt]
            start[i] = t0 + (t1 - t0) * (i - prev) / (nxt - prev)
        elif prev is not None:
            start[i] = start[prev] + 0.3 * (i - prev)
        else:
            start[i] = 0.3 * i
    # Satzanfänge sind exakt bekannt (dort beginnt das Audio des Satzes). Die Erkennung setzt Wörter zu früh an
    # (gemessen: ca. 85 ms mitten im Satz, ca. 170 ms nach Pausen). Der Versatz wird pro Datei mitten im Satz an
    # Wörtern mit hörbarer Lücke davor gemessen; danach rastet jedes Wort auf einen Einsatz im Signal ein,
    # wenn einer innerhalb von 60 ms liegt.
    anchor_idx = {i for i, _ in anchors if i < len(start)}
    shift, snapped = 0.0, 0
    if samples is not None:
        ons_t, ons_gap = _onsets(samples, sr)
        if len(ons_t):
            d = []
            for i in range(len(start)):
                if i in anchor_idx or not direct[i]:
                    continue
                k = int(np.searchsorted(ons_t, start[i] - 0.12))
                if k < len(ons_t) and ons_t[k] < start[i] + 0.30 and ons_gap[k] < 0.25:
                    d.append(ons_t[k] - start[i])
            shift = float(np.median(d)) if len(d) >= 5 else 0.0
            for i in range(len(start)):
                if i in anchor_idx:
                    continue
                t = start[i] + shift
                k = int(np.searchsorted(ons_t, t - 0.06))
                if k < len(ons_t) and abs(ons_t[k] - t) <= 0.06:
                    t, snapped = float(ons_t[k]), snapped + 1
                start[i] = t
    for i, t in anchors:
        if i < len(start):
            start[i] = t
    for i in range(1, len(start)):  # Reihenfolge erhalten
        start[i] = max(start[i], start[i - 1] + 0.03)
    ends = []
    for i in range(len(start)):
        nxt_start = start[i + 1] if i + 1 < len(start) else start[i] + 0.5
        ends.append(max(start[i] + 0.08, min(nxt_start, start[i] + 1.0)))
    tok_times = {}
    for idx, (ui, _) in enumerate(spoken):
        s0, e0 = tok_times.get(ui, (start[idx], ends[idx]))
        tok_times[ui] = (min(s0, start[idx]), max(e0, ends[idx]))
    out = []
    for ui, u in enumerate(units):
        if ui in tok_times and norm(u["tok"]):
            s0, e0 = tok_times[ui]
            out.append({"text": u["tok"], "start": round(s0, 3), "end": round(e0, 3)})
    return out, len(a), matched, interpolated, shift, len(anchor_idx), snapped


def write_mp3(samples, sr, path):
    wav = path + ".tmp.wav"
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-codec:a", "libmp3lame", "-b:a", "192k", path],
                   check=True)
    os.remove(wav)


def speak(src, out_mp3, out_words, voice, pause_s=PAUSE_SENTENCE, pause_p=PAUSE_PARAGRAPH, speed=1.0):
    text = open(src, encoding="utf-8").read()
    units = build_units(text)
    sents = sentences(units, pause_s, pause_p)
    all_words = [w for u in units for w in u["words"]]
    print(f"{len(sents)} Sätze, {len(all_words)} gesprochene Wörter", file=sys.stderr)
    k = ensure_model("kokoro")
    base = [f"{k}/lexicon-us-en.txt", f"{k}/lexicon-gb-en.txt"]
    allowed = {l.split()[0] for l in open(f"{k}/tokens.txt", encoding="utf-8") if l.strip()}
    extra = os.path.join(MODEL_DIR, f"oov-lexicon-{os.path.basename(out_words)}.txt")
    n_extra, added = custom_lexicon(all_words, base, extra, allowed)
    lexicon = ",".join(base + ([extra] if n_extra else []))
    if added:
        print(f"Zusatz-Aussprache für {len(added)} Wörter: {', '.join(added)}", file=sys.stderr)
    samples, sr, anchors = synthesize(sents, voice, lexicon, speed)
    print(f"Audio: {len(samples) / sr:.1f} s", file=sys.stderr)
    asr = recognize(samples, sr)
    words, n_spoken, matched, interpolated, shift, n_anchor, snapped = align(units, asr, anchors, samples, sr)
    with open(out_words, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    write_mp3(samples, sr, out_mp3)
    print(f"Wort-Liste: {len(words)} Einträge -> {out_words}")
    print(f"Erkennung bestätigt {matched}/{n_spoken} gesprochene Wörter ({100 * matched / max(n_spoken, 1):.1f} %), "
          f"Zeit geschätzt: {interpolated}")
    print(f"Satzanfänge exakt gesetzt: {n_anchor}, Erkennung um {shift * 1000:+.0f} ms korrigiert, "
          f"auf Signal-Einsätze eingerastet: {snapped}")
    print(f"MP3: {out_mp3}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Moneycheck-Stimme lokal (Kokoro + Zipformer)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("speak", help="Skript-Textdatei -> MP3 + words.json")
    sp.add_argument("src")
    sp.add_argument("out_mp3")
    sp.add_argument("out_words")
    sp.add_argument("--voice", default="af_heart", choices=sorted(SPEAKERS))
    sp.add_argument("--pause", type=float, default=PAUSE_SENTENCE, help="Pause nach Sätzen (s); Shorts: 0.18")
    sp.add_argument("--para", type=float, default=PAUSE_PARAGRAPH, help="Pause nach Zeilen (s); Shorts: 0.3")
    sp.add_argument("--speed", type=float, default=1.0, help="Sprechtempo; Shorts: 1.05")
    a = ap.parse_args()
    speak(a.src, a.out_mp3, a.out_words, a.voice, a.pause, a.para, a.speed)

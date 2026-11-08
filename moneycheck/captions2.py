"""Smaller, cleaner captions that follow the narrator word by word.

Word timing, best source first:
  1. words.json  - exact per-word start/end from speech recognition (free), matched to the script
  2. fallback    - per chunk: words spread over the real speech (micro-pauses detected in voice.mp3),
                   weighted by syllables, boundaries after punctuation snapped to pauses

Style: Inter SemiBold 46 px, white with a thin dark outline, no box, max 2 short lines (<= 5 words per card),
active word in gold, cards switch exactly when the next words are spoken.
"""
import difflib
import json
import os
import re
import subprocess

from lib10 import W, GOLD_HI, WHITE, clamp, font as _font

F_SB = "sb"


def font(path, size):
    return _font(path, size)


def mix(c1, c2, a):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * a) for i in range(3))

FONT_SIZE = 46
MAX_WORDS = 5
MAX_LINE = 26           # characters per line
Y = 1405                # centre of the caption block
OUTLINE = (6, 10, 20)


def _norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("&", "and"))


def _syllables(w):
    t = w.lower()
    digits = re.sub(r"\D", "", t)
    if digits:
        return max(1, int(round(len(digits) * 1.3)))
    letters = re.sub(r"[^a-z]", "", t)
    if not letters:
        return 1
    if w.isupper() and len(letters) <= 4:          # U.S., UAE, S&P ...
        return len(letters)
    groups = re.findall(r"[aeiouy]+", letters)
    n = len(groups) - (1 if letters.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def _speech_intervals(mp3, dur):
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", mp3, "-af", "silencedetect=noise=-36dB:d=0.07",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    out, cur = [], 0.0
    for s, e in zip(st, en):
        if s - cur > 0.03:
            out.append((cur, s))
        cur = e
    if dur - cur > 0.03:
        out.append((cur, dur))
    return out


def fallback_words(segs, mp3="voice.mp3"):
    dur = max(e for _, e, _ in segs) + 0.5
    speech = _speech_intervals(mp3, dur)
    words = []
    for s, e, txt in segs:
        toks = txt.split()
        ivs = [(max(a, s), min(b, e)) for a, b in speech if b > s and a < e]
        ivs = [iv for iv in ivs if iv[1] - iv[0] > 0.02] or [(s, e)]
        cum, acc = [], 0.0
        for a, b in ivs:
            cum.append(acc)
            acc += b - a
        total = acc
        edges = cum[1:]
        wts = [_syllables(w) for w in toks]
        left = sum(wts)
        pos = 0.0
        bounds = [0.0]
        for w, k in zip(toks[:-1], wts[:-1]):
            b = pos + (total - pos) * k / left
            if w[-1:] in ",.?!:;" and edges:
                near = min(edges, key=lambda x: abs(x - b))
                if abs(near - b) < 0.35 and near > pos:
                    b = near
            bounds.append(b)
            pos = b
            left -= k
        bounds.append(total)

        def real(x):
            for (a, bb), c in zip(ivs, cum):
                if x <= c + (bb - a) + 1e-9:
                    return a + (x - c)
            return ivs[-1][1]

        for i, w in enumerate(toks):
            words.append({"w": w, "start": round(real(bounds[i] + 1e-6), 3), "end": round(real(bounds[i + 1]), 3)})
    return words


def exact_words(segs, path="words.json"):
    """Match the transcript words (with timestamps) to the script words; unmatched words get interpolated."""
    tr = json.load(open(path))
    tr = [x for x in tr if _norm(x.get("text", x.get("word", "")))]
    script = [w for _, _, txt in segs for w in txt.split()]
    a = [_norm(w) for w in script]
    b = [_norm(x.get("text", x.get("word", ""))) for x in tr]
    times = [None] * len(script)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            x = tr[blk.b + k]
            times[blk.a + k] = (float(x["start"]), float(x["end"]))
    fb = fallback_words(segs)
    words = []
    for i, w in enumerate(script):
        st, en = times[i] if times[i] else (fb[i]["start"], fb[i]["end"])
        words.append({"w": w, "start": st, "end": en})
    return words


def load_words(segs):
    if os.path.exists("words.json"):
        return exact_words(segs), "exact"
    return fallback_words(segs), "estimated"


def build_cards(segs, words):
    """Group words into short caption cards (never across chunk boundaries)."""
    cards, i = [], 0
    for s, e, txt in segs:
        n = len(txt.split())
        cw = words[i:i + n]
        i += n
        cur = []
        for k, w in enumerate(cw):
            cur.append(w)
            line_len = len(" ".join(x["w"] for x in cur))
            end_clause = w["w"][-1:] in ",.?!:;" and len(cur) >= 2
            if len(cur) >= MAX_WORDS or line_len > MAX_LINE * 2 - 8 or (end_clause and k < len(cw) - 1):
                cards.append(cur)
                cur = []
        if cur:
            cards.append(cur)
    out = []
    for j, c in enumerate(cards):
        start = c[0]["start"] - 0.04
        nxt = cards[j + 1][0]["start"] - 0.04 if j + 1 < len(cards) else c[-1]["end"] + 0.6
        end = min(nxt, c[-1]["end"] + 0.6)
        out.append((start, end, c))
    return out


def _lines(words, f):
    """One line if it fits, otherwise two balanced lines (no single orphan word)."""
    full = " ".join(x["w"] for x in words)
    if len(full) <= MAX_LINE + 6 or len(words) < 3:
        return [words]
    best, best_k = None, 1
    for k in range(1, len(words)):
        a = len(" ".join(x["w"] for x in words[:k]))
        b = len(" ".join(x["w"] for x in words[k:]))
        score = max(a, b) + (6 if k == len(words) - 1 or k == 1 else 0)
        if best is None or score < best:
            best, best_k = score, k
    return [words[:best_k], words[best_k:]]


class Captions:
    def __init__(self, segs):
        self.words, self.source = load_words(segs)
        self.cards = build_cards(segs, self.words)

    def draw(self, d, t):
        card = None
        for st, en, c in self.cards:
            if st <= t < en:
                card = (st, en, c)
        if card is None:
            return
        st, en, c = card
        a = clamp((t - st) / 0.08) * clamp((en - t) / 0.1)
        if a <= 0.01:
            return
        f = font(F_SB, FONT_SIZE)
        sp = f.getlength(" ")
        lines = _lines(c, f)
        lh = FONT_SIZE * 1.32
        top = Y - lh * len(lines) / 2 + lh / 2
        # exactly one highlighted word: the last one that has started (and is still being spoken)
        started = [w for w in c if w["start"] - 0.03 <= t]
        hot = started[-1] if started and t < started[-1]["end"] + 0.25 else None
        for li, ln in enumerate(lines):
            widths = [f.getlength(w["w"]) for w in ln]
            x = W / 2 - (sum(widths) + sp * (len(ln) - 1)) / 2
            y = top + li * lh
            for w, ww in zip(ln, widths):
                colr = GOLD_HI if w is hot else WHITE
                d.text((x, y), w["w"], font=f, fill=mix(OUTLINE, colr, a), anchor="lm",
                       stroke_width=4, stroke_fill=mix((16, 28, 54), OUTLINE, a))
                x += ww + sp

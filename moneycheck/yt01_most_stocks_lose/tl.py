"""Timeline for YT01: script tokens -> word times -> phrase anchors.

Word times come from the Voice Studio transcripts (voice/part{n}_words.json + voice/part{n}.mp3) when they exist,
otherwise from an estimate (preview without voice). Script tokens are aligned to transcript words with difflib,
so numbers spoken as words but transcribed as digits (or the reverse) just get interpolated times.
"""
import difflib
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE = os.path.join(HERE, "voice")
LEAD_IN = 0.8      # silence before the first word
PART_GAP = 0.6     # silence between voice parts
TAIL = 12.0        # end card after the last word (room for YouTube end-screen elements)


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def load_script():
    txt = open(os.path.join(HERE, "script.txt"), encoding="utf-8").read()
    chunks = re.split(r"=== PART (\d+) ===\n", txt)
    toks = []
    for i in range(1, len(chunks), 2):
        part = int(chunks[i])
        for line in chunks[i + 1].strip().split("\n"):
            words = [w for w in line.split() if norm(w)]
            for wi, w in enumerate(words):
                toks.append(dict(w=w, n=norm(w), part=part, para_end=wi == len(words) - 1))
    for i, tk in enumerate(toks):
        tk["part_end"] = i == len(toks) - 1 or toks[i + 1]["part"] != tk["part"]
    return toks


def _pause(tk):
    w = tk["w"].rstrip('"”')
    p = 0.0
    if w.endswith((".", "?", "!")):
        p = 0.42
    elif w.endswith((",", ";", ":")):
        p = 0.17
    if tk["para_end"]:
        p += 0.3
    return p


def estimate(toks, target=None):
    durs = [0.058 * len(tk["n"]) + 0.085 for tk in toks]
    pauses = [_pause(tk) for tk in toks]
    if target:
        k = (target - sum(pauses) - LEAD_IN) / sum(durs)
        durs = [d * k for d in durs]
    st, en, t = [], [], LEAD_IN
    for tk, d, p in zip(toks, durs, pauses):
        st.append(t)
        en.append(t + d)
        t += d + p
        if tk["part_end"]:
            t += PART_GAP
    return st, en


def _probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(out)


def from_voice(toks):
    """global word times from the per-part transcripts; returns (starts, ends, part_offsets, part_durations)"""
    parts = sorted({tk["part"] for tk in toks})
    st = [None] * len(toks)
    en = [None] * len(toks)
    offs, durs = [], []
    off = LEAD_IN
    for p in parts:
        audio = os.path.join(VOICE, f"part{p}.mp3")
        words = json.load(open(os.path.join(VOICE, f"part{p}_words.json")))
        words = [w for w in words if norm(w["text"])]
        dur = _probe(audio)
        offs.append(off)
        durs.append(dur)
        idx = [i for i, tk in enumerate(toks) if tk["part"] == p]
        a = [toks[i]["n"] for i in idx]
        b = [norm(w["text"]) for w in words]
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                gi = idx[blk.a + k]
                w = words[blk.b + k]
                st[gi], en[gi] = off + w["start"], off + w["end"]
        # interpolate unmatched runs by character length
        known = [j for j, gi in enumerate(idx) if st[gi] is not None]
        for j, gi in enumerate(idx):
            if st[gi] is not None:
                continue
            prev = max([k for k in known if k < j], default=None)
            nxt = min([k for k in known if k > j], default=None)
            t0 = en[idx[prev]] if prev is not None else off
            t1 = st[idx[nxt]] if nxt is not None else off + dur
            lo = prev + 1 if prev is not None else 0
            hi = nxt if nxt is not None else len(idx)
            run = idx[lo:hi]
            L = sum(len(toks[g]["n"]) + 1 for g in run)
            acc = sum(len(toks[g]["n"]) + 1 for g in run[:j - lo])
            st[gi] = t0 + (t1 - t0) * acc / L
            en[gi] = t0 + (t1 - t0) * (acc + len(toks[gi]["n"])) / L
        off += dur + PART_GAP
    return st, en, offs, durs


class Timeline:
    def __init__(self, mode="auto"):
        self.toks = load_script()
        have = all(os.path.exists(os.path.join(VOICE, f"part{p}_words.json"))
                   for p in {tk["part"] for tk in self.toks})
        self.mode = "voice" if (mode == "voice" or (mode == "auto" and have)) else "estimate"
        if self.mode == "voice":
            self.st, self.en, self.part_offsets, self.part_durs = from_voice(self.toks)
            self.speech_end = self.part_offsets[-1] + self.part_durs[-1]
        else:
            chars = sum(len(tk["w"]) + 1 for tk in self.toks)
            self.st, self.en = estimate(self.toks, target=chars / 15.6)
            self.part_offsets, self.part_durs = None, None
            self.speech_end = self.en[-1] + 0.4
        self.dur = self.speech_end + TAIL
        self.norms = [tk["n"] for tk in self.toks]

    def find(self, phrase, n=1):
        q = [norm(w) for w in phrase.split() if norm(w)]
        hits = 0
        for i in range(len(self.norms) - len(q) + 1):
            if self.norms[i:i + len(q)] == q:
                hits += 1
                if hits == n:
                    return i, i + len(q) - 1
        raise KeyError(f"phrase not in script: {phrase!r} (n={n})")

    def T(self, phrase, n=1):
        return self.st[self.find(phrase, n)[0]]

    def TE(self, phrase, n=1):
        return self.en[self.find(phrase, n)[1]]


if __name__ == "__main__":
    # python3 tl.py part 2   -> prints the exact text of voice part 2 (input for voicestudio_tts.py speech)
    import sys
    txt = open(os.path.join(HERE, "script.txt"), encoding="utf-8").read()
    chunks = re.split(r"=== PART (\d+) ===\n", txt)
    parts = {int(chunks[i]): chunks[i + 1].strip() for i in range(1, len(chunks), 2)}
    if len(sys.argv) > 2 and sys.argv[1] == "part":
        print(parts[int(sys.argv[2])])
    else:
        for k, v in parts.items():
            print(f"part {k}: {len(v)} characters")

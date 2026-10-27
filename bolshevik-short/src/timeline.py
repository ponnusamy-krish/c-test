"""Shared timeline: scene boundaries and word cues derived from the narration."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_T = json.loads((ROOT / "audio/timing.json").read_text())
WORDS = json.loads((ROOT / "build/words.json").read_text()) if (ROOT / "build/words.json").exists() else {}

NARR_END = _T["total"]
TAIL = 1.30                      # silent hold after the last word
TOTAL = round(NARR_END + TAIL, 3)

SEG = {k: (v["start"], v["end"]) for k, v in _T["segments"].items()}
ORDER = ["hook", "crisis", "tsar", "lenin", "october", "civil_war", "consolidation", "end"]

# scene boundaries: each scene starts where its narration segment starts
SCENE = {}
for i, k in enumerate(ORDER):
    t0 = SEG[k][0] if i else 0.0
    t1 = SEG[ORDER[i + 1]][0] if i + 1 < len(ORDER) else TOTAL
    SCENE[k] = (t0, t1)


def word(seg, text, occurrence=0, edge="t0"):
    """Start (t0) or end (t1) time of the n-th word matching `text` (punctuation ignored)."""
    key = text.lower().strip(".,;:!?")
    n = 0
    for w in WORDS[seg]["words"]:
        if w["w"].lower().strip(".,;:!?") == key:
            if n == occurrence:
                return w[edge]
            n += 1
    raise KeyError(f"{text}#{occurrence} not in {seg}")


def which_scene(t):
    for k in ORDER:
        a, b = SCENE[k]
        if a <= t < b:
            return k
    return ORDER[-1]


# October scene cues (used by both the visuals and the sound design)
def oct_pin_times():
    t = word("october", "seized") + 0.10
    return [round(t + 0.38 * i, 3) for i in range(5)]


OCT_PINS = oct_pin_times() if WORDS else []
OCT_PALACE = word("october", "toppled") if WORDS else 0.0

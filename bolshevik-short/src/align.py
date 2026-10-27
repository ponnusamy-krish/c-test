"""LEGACY / HELPER. Only silences() is used (by asr_align.py, to calibrate the recogniser lag).
The weight-based timing in main() was superseded by src/asr_align.py, which writes build/words.json.

Original description: word-level timing for captions and on-screen cues.

Kokoro does not return word timestamps, so words are timed in three steps:
  1. each word gets weight = its phoneme count (espeak, en-gb) plus a pause
     allowance after punctuation;
  2. the segment's real duration is split in proportion to those weights;
  3. internal pauses are located in the audio (energy envelope) and the
     boundaries after punctuation are snapped to them when the number of
     detected pauses matches the punctuation count.
Accuracy is about +-100 ms, which is fine for caption highlighting.
"""
import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
SPOKEN = {"1917": "nineteen seventeen", "1922": "nineteen twenty-two"}
PAUSE = {".": 0.28, ",": 0.14, "?": 0.28, "!": 0.28, ":": 0.2, ";": 0.2}


def silences(x, sr, min_len=0.09, win=0.01):
    """Return [(start, end)] of low-energy gaps strictly inside the clip."""
    n = int(win * sr)
    env = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, "same"))
    thr = max(0.012, env.max() * 0.05)
    quiet = env < thr
    out, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) / sr >= min_len and i > 0.15 * sr and j < len(quiet) - 0.1 * sr:
                out.append((i / sr, j / sr))
            i = j
        else:
            i += 1
    return out


def main():
    timing = json.loads((ROOT / "audio/timing.json").read_text())
    k = Kokoro(str(ROOT / "assets/models/kokoro-v1.0.onnx"), str(ROOT / "assets/models/voices-v1.0.bin"))
    result = {}
    for seg, info in timing["segments"].items():
        x, sr = sf.read(ROOT / f"audio/seg_{seg}.wav")
        dur = len(x) / sr
        words = info["text"].split()
        weights = []
        for w in words:
            core = re.sub(r"[^\w'’-]", "", w)
            core = SPOKEN.get(core, core)
            ph = k.tokenizer.phonemize(core, "en-gb") if core else ""
            wt = max(len(ph.replace("ˈ", "").replace("ˌ", "")), 2) * 1.0
            weights.append(wt)
        punct = [PAUSE.get(w[-1], 0.0) for w in words]
        # time budget excluding the final punctuation pause
        total_pause = sum(punct[:-1])
        unit = (dur - total_pause) / sum(weights)
        t, bounds = 0.0, []
        for w, wt, p in zip(words, weights, punct):
            start = t; end = t + wt * unit
            bounds.append([start, end]); t = end + (p if w is not words[-1] else 0)
        # snap to detected pauses: take the N longest gaps (N = punctuation marks)
        gaps = silences(x, sr, min_len=0.07)
        idx = [i for i, p in enumerate(punct[:-1]) if p > 0.1]
        snapped = False
        if idx and len(gaps) >= len(idx):
            top = sorted(sorted(gaps, key=lambda g: g[0] - g[1])[:len(idx)])   # longest N, chronological
            # accept only if every snap lies within 1.0 s of the estimate
            if all(abs(top[n][0] - bounds[wi][1]) < 1.0 for n, wi in enumerate(idx)):
                for n, wi in enumerate(idx):
                    g0, g1 = top[n]
                    bounds[wi][1] = g0
                    bounds[wi][0] = min(bounds[wi][0], g0 - 0.05)
                    bounds[wi + 1][0] = g1
                snapped = True
        # repair monotonicity
        for i in range(1, len(bounds)):
            bounds[i][0] = max(bounds[i][0], bounds[i - 1][1] if bounds[i - 1][1] <= bounds[i][0] else bounds[i][0])
            bounds[i][1] = max(bounds[i][1], bounds[i][0] + 0.06)
        bounds[-1][1] = dur
        off = info["start"]
        result[seg] = {
            "start": info["start"], "end": info["end"], "snapped": snapped,
            "pauses_found": len(gaps), "pauses_expected": len(idx),
            "words": [{"w": w, "t0": round(off + b[0], 3), "t1": round(off + b[1], 3)}
                      for w, b in zip(words, bounds)],
        }
        print(f"{seg:14s} words={len(words):2d} pauses found/expected={len(gaps)}/{len(idx)} snapped={snapped}")
    (ROOT / "build/words.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()

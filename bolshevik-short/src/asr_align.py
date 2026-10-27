"""Word timing from ASR token timestamps (sherpa-onnx streaming zipformer) -> build/words.json.

The synthesized narration is transcribed; token emission times give word onsets.
A constant recogniser lag is estimated from words that follow measured pauses.
Script words that the ASR hears differently (numerals) are matched via expansion.
"""
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align import silences

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "assets/models/asr/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17"
SPOKEN = {"1917": ["nineteen", "seventeen"], "1922": ["nineteen", "twenty", "two"]}


def recogniser():
    return sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=str(M / "tokens.txt"), encoder=str(M / "encoder-epoch-99-avg-1.onnx"),
        decoder=str(M / "decoder-epoch-99-avg-1.onnx"), joiner=str(M / "joiner-epoch-99-avg-1.onnx"),
        num_threads=2, sample_rate=16000, feature_dim=80, decoding_method="greedy_search", provider="cpu")


def transcribe(rec, x24, lead=None):
    """Transcribe a 24 kHz clip. `lead` (24 kHz) is prepended to warm up the streaming model
    and removed from the returned times."""
    pre = np.zeros(0, np.float32) if lead is None else np.concatenate([lead, np.zeros(int(0.8 * 24000))])
    x = resample_poly(np.concatenate([pre, x24]), 2, 3).astype(np.float32)   # 24k -> 16k
    x = x / np.abs(x).max() * 0.9
    off = len(pre) / 24000.0
    x = np.concatenate([x, np.zeros(16000, np.float32)])
    s = rec.create_stream()
    s.accept_waveform(16000, x)
    s.input_finished()
    while rec.is_ready(s):
        rec.decode_stream(s)
    r = rec.get_result_all(s)
    words, cur = [], None
    for tk, t in zip(r.tokens, r.timestamps):
        t -= off
        if tk.startswith(" ") or cur is None:
            cur = [tk.strip(), t, t]; words.append(cur)
        else:
            cur[0] += tk; cur[2] = t
    return [(w.lower(), a, b) for w, a, b in words if a > -0.05]


def norm(w):
    return re.sub(r"[^a-z']", "", w.lower())


def expand(script_words):
    out = []
    for i, w in enumerate(script_words):
        core = re.sub(r"[^\w'’-]", "", w)
        parts = SPOKEN.get(core) or [p for p in re.split(r"-", core.lower()) if p]
        for p in parts:
            out.append((i, norm(p)))
    return out


def main():
    timing = json.loads((ROOT / "audio/timing.json").read_text())
    rec = recogniser()
    full, _ = sf.read(ROOT / "audio/narration.wav")
    lead, _ = sf.read(ROOT / "audio/seg_end.wav")
    asr = transcribe(rec, full, lead.astype(np.float32))
    print("ASR:", " ".join(w for w, _, _ in asr))
    # whole-script word list
    script, owner = [], []
    for seg, info in timing["segments"].items():
        for i, w in enumerate(info["text"].split()):
            script.append(w); owner.append((seg, i))
    ex = expand(script)
    sm = difflib.SequenceMatcher(None, [w for _, w in ex], [norm(w) for w, _, _ in asr], autojunk=False)
    starts = [None] * len(script); ends = [None] * len(script)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            i = ex[a + k][0]
            s_, e_ = asr[b + k][1], asr[b + k][2]
            starts[i] = s_ if starts[i] is None else min(starts[i], s_)
            ends[i] = e_ if ends[i] is None else max(ends[i], e_)
    print(f"matched {sum(v is not None for v in starts)}/{len(script)} script words")
    # recogniser lag from words that start right after a measured pause
    lags = []
    for seg, info in timing["segments"].items():
        x, sr = sf.read(ROOT / f"audio/seg_{seg}.wav")
        for g0, g1 in silences(x, sr, min_len=0.12):
            g1 += info["start"]
            cand = [s - g1 for s in starts if s is not None and -0.3 < s - g1 < 0.8]
            if cand:
                lags.append(min(cand, key=abs))
    lag = float(np.median(lags)) if lags else 0.0
    print(f"recogniser lag: median {lag:+.3f}s over {len(lags)} pauses (std {np.std(lags):.3f})")
    st = [None if s is None else s - lag for s in starts]
    n = len(script)
    idx = [i for i, s in enumerate(st) if s is not None]
    if idx[0] != 0:
        st[0] = 0.0; idx = [0] + idx
    total = timing["total"]
    for a, b in zip(idx, idx[1:] + [n]):
        t0 = st[a]; t1 = st[b] if b < n else total
        for k in range(a + 1, b):
            st[k] = t0 + (t1 - t0) * (k - a) / (b - a)
    result = {}
    for i, (seg, wi) in enumerate(owner):
        info = timing["segments"][seg]
        r = result.setdefault(seg, {"start": info["start"], "end": info["end"],
                                    "method": "asr-timestamps", "lag": round(lag, 3), "words": []})
        t1 = st[i + 1] - 0.02 if (i + 1 < n and owner[i + 1][0] == seg) else info["end"]
        r["words"].append({"w": script[i], "t0": round(max(st[i], info["start"]), 3),
                           "t1": round(max(t1, st[i] + 0.08), 3), "matched": starts[i] is not None})
    (ROOT / "build/words.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print("written build/words.json")


if __name__ == "__main__":
    main()

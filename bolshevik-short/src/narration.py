"""Generate the Kokoro narration, one WAV per segment, plus a timing map.

Usage: python src/narration.py [--voice bm_george] [--speed 0.95]

Outputs (under audio/):
  seg_<id>.wav   - each narrated segment (24 kHz mono)
  narration.wav  - all segments joined with the pauses defined below
  timing.json    - start/end of each segment inside narration.wav
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
SR = 24000

# (id, text, pause after in seconds). Text is written for the TTS front end:
# "Nicholas II" is spelled out because espeak reads the numeral as "Roman two".
SEGMENTS = [
    ("hook",
     "Russia was one of the world's largest empires. In 1917, a revolutionary "
     "party seized its capital in hours. But taking control of Russia itself "
     "was a much longer struggle.", 0.35),
    ("crisis",
     "World War One drained the empire. Millions died, and bread ran short.",
     0.35),
    ("tsar",
     "In February 1917, strikes and mutinies in Petrograd forced Nicholas the "
     "Second to abdicate. A Provisional Government took over.", 0.35),
    ("lenin",
     "It kept fighting the war. Lenin's Bolsheviks promised peace, land, and "
     "bread, and workers and soldiers listened.", 0.35),
    ("october",
     "On October twenty-fifth, by the old Russian calendar, Bolsheviks seized "
     "Petrograd's key points and toppled the Provisional Government. "
     "November seventh, in the Gregorian calendar.", 0.4),
    ("civil_war",
     "But holding the capital was not holding Russia. Civil war split the "
     "empire between Reds and Whites.", 0.4),
    ("consolidation",
     "By 1922, through war and tight centralised control, the Bolsheviks had "
     "won.", 0.5),
    ("end",
     "The capital fell in hours. Consolidating power took years.", 0.0),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="bm_george")
    ap.add_argument("--speed", type=float, default=0.95)
    ap.add_argument("--lang", default="en-gb")
    ap.add_argument("--out", default=str(ROOT / "audio"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    kokoro = Kokoro(str(ROOT / "assets/models/kokoro-v1.0.onnx"),
                    str(ROOT / "assets/models/voices-v1.0.bin"))

    pieces, timing, cursor = [], {}, 0.0
    for seg_id, text, pause in SEGMENTS:
        samples, sr = kokoro.create(text, voice=args.voice, speed=args.speed,
                                    lang=args.lang)
        assert sr == SR, sr
        # trim leading/trailing silence so pauses are exactly the ones we set
        loud = np.where(np.abs(samples) > 0.01)[0]
        samples = samples[loud[0]:loud[-1] + 1] if len(loud) else samples
        sf.write(out / f"seg_{seg_id}.wav", samples, SR, subtype="PCM_16")
        dur = len(samples) / SR
        timing[seg_id] = {"start": round(cursor, 3),
                          "end": round(cursor + dur, 3),
                          "text": text}
        print(f"{seg_id:14s} {dur:6.2f}s  start={cursor:6.2f}")
        pieces += [samples, np.zeros(int(pause * SR), dtype=samples.dtype)]
        cursor += dur + pause

    full = np.concatenate(pieces)
    sf.write(out / "narration.wav", full, SR, subtype="PCM_16")
    (out / "timing.json").write_text(json.dumps(
        {"voice": args.voice, "speed": args.speed, "total": round(len(full) / SR, 3),
         "segments": timing}, indent=2))
    print(f"TOTAL {len(full) / SR:.2f}s  peak={np.abs(full).max():.3f}")


if __name__ == "__main__":
    main()

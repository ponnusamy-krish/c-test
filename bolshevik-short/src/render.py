"""Parallel 2160x3840 @ 60 fps renderer.

Frames are generated in worker processes in 2-second chunks (120 frames); each chunk is
piped into its own libx264 encode, the chunks are concatenated without re-encoding and the
AAC audio is muxed last. Already-finished chunks are skipped, so an interrupted render resumes.

  python src/render.py                 full 4K render -> build/final_noaudio.mp4 -> output/*.mp4
  RENDER_SCALE=0.25 python src/render.py --draft     small draft (not a deliverable)
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

CHUNK = 120


def encode_cmd(w, h, out):
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", f"{w}x{h}", "-r", "60", "-i", "-",
            "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=bicubic+accurate_rnd+full_chroma_int,format=yuv420p",
            "-c:v", "libx264", "-preset", os.environ.get("X264_PRESET", "medium"), "-crf", os.environ.get("X264_CRF", "17"), "-maxrate", "60M", "-bufsize", "120M",
            "-profile:v", "high", "-level:v", "5.2", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0",
            "-bf", "2", "-threads", "1", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-color_range", "tv", "-an", str(out)]


def work(args):
    ci, chunk_dir, n_total = args
    import engine
    import frame
    out = Path(chunk_dir) / f"chunk_{ci:04d}.mp4"
    if out.exists() and out.stat().st_size > 1000:
        return ci, 0.0
    tmp = out.with_suffix(".part.mp4")
    t0 = time.time()
    p = subprocess.Popen(encode_cmd(engine.W, engine.H, tmp), stdin=subprocess.PIPE)
    for i in range(ci * CHUNK, min((ci + 1) * CHUNK, n_total)):
        p.stdin.write(frame.build_frame(i).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on chunk {ci}")
    tmp.rename(out)
    return ci, time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--frames", type=int, default=0, help="render only the first N frames (testing)")
    ap.add_argument("--skip-scenes", default="", help="comma list of scene names whose chunks are not rendered now")
    ap.add_argument("--assemble", action="store_true", help="concatenate chunks and mux audio (all chunks must exist)")
    ap.add_argument("--keep-choices", action="store_true", help="reuse build/choices.json instead of re-freezing")
    a = ap.parse_args()
    import engine
    import timeline as T
    n_total = a.frames or round(T.TOTAL * 60)
    if not a.draft and (engine.W, engine.H) != (2160, 3840):
        sys.exit("refusing: final render must be 2160x3840 (unset RENDER_SCALE)")
    if os.environ.get("PREVIEW_STANDIN") == "1" and not a.draft:
        sys.exit("refusing: PREVIEW_STANDIN is a layout-preview switch and must not be used for the final render")
    import scenes
    if not a.keep_choices:
        print("frozen asset choices:", scenes.freeze_choices(), flush=True)
    tag = "draft" if a.draft else "final"
    chunk_dir = ROOT / "build" / f"chunks_{tag}"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    n_chunks = (n_total + CHUNK - 1) // CHUNK
    print(f"{engine.W}x{engine.H}  {n_total} frames  {n_chunks} chunks  {a.workers} workers", flush=True)
    skip = set()
    if a.skip_scenes:
        for name in a.skip_scenes.split(","):
            f0, f1 = (round(v * 60) for v in T.SCENE[name])
            skip |= set(range(f0 // CHUNK, (f1 - 1) // CHUNK + 1))
        print("skipping chunks", sorted(skip), flush=True)
    todo = [c for c in range(n_chunks) if c not in skip] if not a.assemble else []
    t0 = time.time(); done = 0
    n_chunks_todo = max(len(todo), 1)
    with Pool(a.workers) as pool:
        for ci, dt in pool.imap_unordered(work, [(c, str(chunk_dir), n_total) for c in todo]):
            done += 1
            el = time.time() - t0
            print(f"chunk {ci:3d} done ({dt:5.0f}s)  {done}/{n_chunks_todo}  elapsed {el/60:5.1f} min  eta {el/done*(n_chunks_todo-done)/60:5.1f} min", flush=True)
    if skip:
        print("partial render finished; run again without --skip-scenes (or with --assemble) to finish", flush=True); return
    missing = [c for c in range(n_chunks) if not (chunk_dir / f"chunk_{c:04d}.mp4").exists()]
    if missing:
        sys.exit(f"cannot assemble: missing chunks {missing}")
    lst = chunk_dir / "list.txt"
    lst.write_text("".join(f"file 'chunk_{c:04d}.mp4'\n" for c in range(n_chunks)))
    silent = ROOT / "build" / f"{tag}_noaudio.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(silent)], check=True)
    if a.frames or a.draft:
        print("draft/partial render:", silent); return
    out_dir = ROOT / "output"; out_dir.mkdir(exist_ok=True)
    final = out_dir / "how_the_bolsheviks_took_power_2160x3840_60fps.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent), "-i", str(ROOT / "audio/mix.wav"),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", "-shortest", str(final)], check=True)
    print("FINAL:", final, f"({final.stat().st_size/1e6:.1f} MB)  total {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()

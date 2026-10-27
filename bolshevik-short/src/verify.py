"""Verify the finished MP4: specs, encoding, audio, sync, and frame-level continuity.

  python src/verify.py [path/to/video.mp4]
Writes build/verify_report.json and build/verify_sheet.jpg (scene-boundary contact sheet).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import timeline as T

video = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output/how_the_bolsheviks_took_power_2160x3840_60fps.mp4"
rep, ok = {}, True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    rep[name] = {"pass": bool(cond), "detail": str(detail)}


pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
                               capture_output=True, text=True).stdout)
v = next(s for s in pr["streams"] if s["codec_type"] == "video")
a = next(s for s in pr["streams"] if s["codec_type"] == "audio")
dur = float(pr["format"]["duration"])
num, den = map(int, v["r_frame_rate"].split("/"))
fps = num / den
check("resolution 2160x3840", (v["width"], v["height"]) == (2160, 3840), f"{v['width']}x{v['height']}")
check("frame rate 60", abs(fps - 60) < 1e-6 and v.get("avg_frame_rate") == "60/1", f"r={v['r_frame_rate']} avg={v.get('avg_frame_rate')}")
check("video codec H.264", v["codec_name"] == "h264", f"{v['codec_name']} {v.get('profile')} level {v.get('level')}")
check("pixel format yuv420p", v["pix_fmt"] == "yuv420p", v["pix_fmt"])
check("duration 55-65 s", 55 <= dur <= 65, f"{dur:.3f} s")
check("audio codec AAC", a["codec_name"] == "aac", f"{a['codec_name']} {a.get('profile')} {a['sample_rate']} Hz {a['channels']} ch {int(a.get('bit_rate', 0))//1000} kbps")
check("audio/video length match", abs(float(a["duration"]) - float(v["duration"])) < 0.05, f"audio {float(a['duration']):.3f} video {float(v['duration']):.3f}")
nb = int(v.get("nb_frames", 0))
check("frame count = duration x 60", nb and abs(nb - round(dur * 60)) <= 2, f"{nb} frames")
check("moov atom first (faststart)", video.read_bytes()[:64].find(b"ftyp") >= 0 and video.read_bytes()[:4096].find(b"moov") >= 0, "")
rep["size_MB"] = round(video.stat().st_size / 1e6, 1); print("file size", rep["size_MB"], "MB; video bitrate", int(v.get("bit_rate", 0)) // 1000, "kbps")

# ---- loudness / clipping
r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-af", "ebur128=peak=true,astats=metadata=1:reset=0", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
li = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]; tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1]
check("integrated loudness -14 +-1 LUFS", abs(float(li) + 14) <= 1.0, f"{li} LUFS")
check("true peak <= -1 dBTP", float(tp) <= -1.0, f"{tp} dBFS")
flat = re.findall(r"Number of samples at full scale:\s*(\d+)|Flat factor:\s*([\d.]+)", r)
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a:0", "-f", "f32le", "-ac", "2", "-ar", "48000", "-"], capture_output=True).stdout
x = np.frombuffer(pcm, np.float32)
check("no clipped audio samples", int((np.abs(x) >= 0.999).sum()) == 0, f"max {np.abs(x).max():.3f}")

# ---- sync: first visual flash vs first audio impact transient
fr = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-frames:v", "30", "-vf", "scale=108:192,format=gray", "-f", "rawvideo", "-"],
                    capture_output=True).stdout
fr = np.frombuffer(fr, np.uint8).reshape(-1, 192, 108).mean(axis=(1, 2))
t_flash = int(np.argmax(fr)) / 60
st = x.reshape(-1, 2).mean(axis=1)
thr = 0.25 * np.abs(st[: 48000]).max()
t_audio = int(np.argmax(np.abs(st[: 48000]) > thr)) / 48000
check("A/V sync at opening impact (|offset| < 50 ms)", abs(t_flash - t_audio) < 0.05, f"visual flash {t_flash*1000:.0f} ms, audio transient {t_audio*1000:.0f} ms")

# ---- continuity scan on a downscaled decode of every frame
w, h = 135, 240
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
lum = F.mean(axis=(1, 2))
d = np.abs(np.diff(F, axis=0)).mean(axis=(1, 2))
black = np.where(lum[3:-3] < 4)[0] + 3
frozen = np.where(d < 0.02)[0]
med, p99 = float(np.median(d)), float(np.percentile(d, 99.5))
spikes = [int(i) for i in np.where(d > max(p99 * 1.0, 18))[0]]
boundaries = {k: round(v[0] * 60) for k, v in T.SCENE.items()}
unexplained = [i for i in spikes if not any(abs(i + 1 - b) <= 4 for b in boundaries.values()) and not (i < 14 or 54 <= i <= 60 or 96 <= i <= 106)]
check("no black frames inside the film", len(black) == 0, f"{len(black)} found")
check("no frozen frames (duplicate consecutive frames)", len(frozen) <= 6, f"{len(frozen)} frames with ~zero motion")
check("no unexplained visual jumps", len(unexplained) == 0, f"median motion {med:.2f}, 99.5th pct {p99:.2f}, unexplained jumps at frames {unexplained[:10]}")
rep["scene_boundary_jumps"] = {k: round(float(d[min(max(b - 1, 0), len(d) - 1)]), 2) for k, b in boundaries.items()}
# contact sheet at scene boundaries and mid-scene
times = []
for k, (t0, t1) in T.SCENE.items():
    times += [t0 + 0.05, (t0 + t1) / 2]
times.append(dur - 0.3)
tiles = []
for t in times:
    im = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=270:480", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                        capture_output=True).stdout
    tiles.append(im)
from PIL import Image
import io
ims = [Image.open(io.BytesIO(b)).convert("RGB") for b in tiles if b]
cols = 9
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (270 * cols, 480 * rows))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * 270, (i // cols) * 480))
sheet.save(ROOT / "build/verify_sheet.jpg", quality=82)
(ROOT / "build/verify_report.json").write_text(json.dumps(rep, indent=2))
print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
sys.exit(0 if ok else 1)

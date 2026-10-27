# How the Bolsheviks Took Over Russia: a 64-second vertical history short

A documentary-style YouTube Shorts / Instagram Reels film, made entirely with Python, OpenCV, Pillow and FFmpeg. No Blender, no 3D, no background music.

> *The capital fell in hours. Consolidating power took years.*

## Deliverables

| What | Where |
|---|---|
| **Final film, 4K** (H.264 High, AAC), 48 Mbps | `output/how_the_bolsheviks_took_power_2160x3840_60fps_48mbps.mp4` (391 MB; delivered in the chat, **not committed to git**: over GitHub's 100 MB limit) |
| 4K high-bitrate master (84 Mbps, straight from the renderer) | `output/how_the_bolsheviks_took_power_2160x3840_60fps.mp4` (681 MB; only on the render machine, produced by `src/render.py`) |
| 1080×1920 60 fps preview of the same film | `output/preview_1080x1920_60fps.mp4` |
| Thumbnail | `output/thumbnail_2160x3840.png`, `output/thumbnail_1080x1920.jpg` |
| Narration script with timings, pronunciation check | `docs/narration_script.md` |
| Kokoro narration WAV (24 kHz) and per-segment WAVs | `audio/narration.wav`, `audio/seg_*.wav`, `audio/timing.json` |
| Final mixed audio (narration + sound design, 48 kHz) | `audio/mix.wav` |
| Archival assets and their manifest | `assets/raw/`, `assets/manifest.json` |
| Sources and licences | `docs/SOURCES.md`, vetting decisions in `docs/ASSET_NOTES.md` |
| Fact-check log (every claim, date and label) | `docs/FACT_CHECK.md` |
| Map methods and what is approximate | `docs/MAP_NOTES.md` |
| Verification report | `docs/VERIFICATION.md` (script: `src/verify.py`) |
| Source code | `src/` |

## What was verified on the finished file

Measured by `src/verify.py` on both 4K files; every check passes on each (the 48 Mbps file is a straight re-encode of the 84 Mbps master with the audio copied unchanged):

| Check | Result |
|---|---|
| Resolution | 2160 × 3840 (9:16) |
| Frame rate | 60 fps constant, 3,870 frames |
| Duration | 64.50 s (target 55–65 s) |
| Video | H.264 High @ L5.2, yuv420p, BT.709, `faststart`; 48 Mbps (delivered file) or 84 Mbps (master) |
| Audio | AAC-LC 48 kHz stereo, 249 kbps |
| Loudness | −14.0 LUFS integrated, true peak −1.5 dBTP, zero clipped samples |
| Sound effects vs voice | effects sit about 19 dB below the narration (ducked while the voice speaks) |
| A/V sync | opening impact: visual flash and audio transient within 1 ms |
| Continuity | no black frames, no frozen frames, no unexplained jumps |

## The film

| Time | Scene | What you see |
|---|---|---|
| 0:00–0:13 | **Hook** | White impact flash, red crowd photographs cutting in, bold title slam, a rapid map zoom from the whole empire to Petrograd, a red pulse, then a pull-back to the empire |
| 0:13–0:18 | An empire in crisis | World War I soldiers, a Petrograd bread queue |
| 0:18–0:27 | The Tsar falls | February 1917 barricades, a date ribbon (23 Feb → 2 Mar, old style), the real *Daily Kennebec Journal* front page "Czar Abdicates" with the Tsar's portrait, the Provisional Government |
| 0:27–0:35 | Lenin's opportunity | A photograph of Lenin, then PEACE / LAND / BREAD slamming in on the narrator's words, each beside a genuine document |
| 0:35–0:46 | The October Revolution | Baedeker's 1914 plan of St Petersburg, pins at the places seized, the Winter Palace, "25 Oct = 7 Nov", the real *Seattle Star* headline "Alex Kerensky overthrown" |
| 0:46–0:53 | The civil war | Animated Red/White map, White offensive arrows, 1919 American Red Cross photographs of both sides |
| 0:53–0:59 | Consolidation | Year ticker 1918 → 1922, front lines flowing, a web of control from Moscow, USSR 30 Dec 1922 |
| 0:59–1:04 | Ending | The opening map again, now red, the closing lines, and the opening zoom replayed into Petrograd |

Narration and timing follow the script in `docs/narration_script.md` (the opening three sentences are exactly as briefed).

## Honest limitations

* **Nobody has listened to the narration.** Pronunciation was checked at phoneme level and by an independent speech recogniser (it transcribed "Petrograd", "Lenin's", "Nicholas the second", "Gregorian" correctly), but the prosody and voice quality of Kokoro `bm_george` have not been auditioned by a human. Listen before publishing. Swapping the voice is one flag (`--voice`).
* **The sound effects are synthesised, not recorded.** Impacts, whooshes, crowd murmur, telegraph-sounder clicks, marching boots and paper rustle are generated in `src/sfx.py`. They are licence-free but less natural than field recordings. Freesound and similar sites were unreachable at first and then needed API keys.
* **The war maps are approximate.** Front lines and territory phases are hand-drawn, simplified and labelled so on screen. The empire outline is assembled from modern borders. See `docs/MAP_NOTES.md`.
* **Not every image I wanted was obtainable.** Wikimedia Commons throttled this session's shared IP, so most of the Commons photographs I had vetted (including a 1917 photo of Lenin) could not be downloaded. They were replaced by verified Library of Congress, Chronicling America and Internet Archive material. Only one Commons image (a bread queue) is in the film. Details in `docs/ASSET_NOTES.md`.
* **The Lenin photograph is from 1920, not 1917.** The Library of Congress dates the Bain negative 1920; the on-screen caption says "published 1920".
* **There is no photograph of the storming of the Winter Palace**, because none exists: the images usually shown are stills from a 1928 film. The film shows the plan of the city instead.
* **"Millions died"** is accurate if civilians are counted; military deaths alone were about 1.7–2 million (see `docs/FACT_CHECK.md`).
* **Caption timing** is accurate to about ±0.15 s.
* **Platform safe zones.** Captions sit at 74% of the frame height, above the area YouTube Shorts and Reels usually cover with their own interface, but check on your device.
* **File size.** The film grain makes the video expensive to encode: the renderer's master is 84 Mbps (681 MB) and the delivered file is 48 Mbps (391 MB). YouTube and Instagram will re-encode either one.

## Reproducing it

Tested on Ubuntu 24.04, 4 CPU cores, 15 GB RAM, no GPU, Python 3.13, FFmpeg 6.1.1 (libx264, aac).

```bash
cd bolshevik-short
python3 -m venv --system-site-packages .venv && . .venv/bin/activate
pip install numpy pillow opencv-python-headless shapely scipy soundfile requests kokoro-onnx sherpa-onnx pypdf

# 1. models (Kokoro TTS: GitHub release; small English ASR used only for caption timing)
mkdir -p assets/models/asr && cd assets/models
curl -L -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -O https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd asr && curl -L https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17.tar.bz2 | tar xj
cd ../../..

# 2. assets: committed under assets/raw. To re-download any that are missing:
python src/refetch_assets.py
# map data: Natural Earth 1:50m countries (assets/maps/ne_50m_admin_0_countries.geojson),
# from https://github.com/nvkelso/natural-earth-vector (geojson/)

# 3. narration (Kokoro) and word timing
python src/narration.py --voice bm_george --speed 1.07
python src/asr_align.py                       # writes build/words.json

# 4. sound design and mix  (-> audio/mix.wav, -14 LUFS)
python src/sfx.py

# 5. geometry caches, then the full 4K 60 fps render (about 25 minutes on 4 cores)
python src/mapdata.py && python src/territory.py
python src/render.py --workers 4              # chunks -> build/chunks_final -> output/*.mp4

# 6. thumbnail, sources document, verification
python src/thumbnail.py
python src/make_docs.py
python src/verify.py
```

Previews while iterating: `RENDER_SCALE=0.25 python src/preview.py out.png 12.3 30.9 41.6` renders frames at one quarter scale. The final render refuses to run at any other scale than 2160×3840.

### Code map

| File | Role |
|---|---|
| `src/narration.py` | Kokoro text-to-speech, segment WAVs and `timing.json` |
| `src/asr_align.py` | Word timings from ASR token timestamps (`align.py` is a legacy helper) |
| `src/timeline.py` | Scene boundaries and word cues shared by visuals and audio |
| `src/engine.py` | 2D engine: easing, text tiles, alpha blits, photo cards, map view, film grain/vignette/flicker |
| `src/common.py` | Map drawing, captions, labels |
| `src/mapdata.py`, `src/territory.py` | Projected map geometry; approximate territory phases morphed with signed-distance fields |
| `src/scenes.py` | The eight scenes |
| `src/frame.py` | Frame assembly, scene dissolves |
| `src/render.py` | Parallel chunked 4K render, concat, AAC mux |
| `src/sfx.py` | Procedural sound effects, ducking, two-pass loudness normalisation |
| `src/commons.py`, `src/loc.py` | Wikimedia Commons / Library of Congress helpers (throttled, with provenance capture) |
| `src/make_docs.py`, `src/verify.py`, `src/thumbnail.py` | Documentation, verification, thumbnail |

## Rights summary

Archive images are public-domain or "no known restrictions" items from the Library of Congress (including Chronicling America and the World Digital Library), the Internet Archive and Wikimedia Commons, each recorded with its source page and rights statement in `docs/SOURCES.md`. Map outlines are Natural Earth (public domain). Narration is Kokoro-82M (Apache-2.0 model). Sound effects are synthesised. Fonts are SIL OFL. There is no music. Rights information comes from the holding institutions and should be re-checked for your jurisdiction before commercial use ("use elsewhere may be restricted by other countries' laws", per the Library of Congress).

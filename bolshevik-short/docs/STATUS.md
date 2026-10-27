# Production status

## Done
- Environment inspected: Ubuntu 24.04, 4 cores, 15 GiB RAM, no GPU, FFmpeg 6.1.1
  (libx264 + aac), Python 3.13 with Pillow, NumPy, onnxruntime. No OpenCV/MoviePy.
- Kokoro TTS set up locally with `kokoro-onnx` (PyPI) + `kokoro-v1.0.onnx` and
  `voices-v1.0.bin` from the kokoro-onnx GitHub release `model-files-v1.0`.
- Narration script written and rendered: `src/narration.py` -> `audio/`
  (`narration.wav`, per-segment WAVs, `timing.json`). Voice `bm_george`, speed 1.07.
- Pronunciation checked at phoneme level: Bolsheviks, Petrograd, Lenin, Tsar,
  Kerensky, Gregorian are fine. "Nicholas II" is mis-read as "Nicholas Roman two",
  so the script says "Nicholas the Second". (Phoneme-level check only: nobody has
  listened to the audio yet.)

## Blocked: network policy denies these hosts (HTTP 403 on CONNECT)
Needed for genuine archival images, map data, sound effects and fact-checking:
- commons.wikimedia.org, upload.wikimedia.org, en.wikipedia.org
- www.loc.gov
- archive.org (and web.archive.org)
- huggingface.co
- freesound.org / cdn.freesound.org
- www.naturalearthdata.com
- also denied: digitalcollections.nypl.org, www.europeana.eu, pixabay.com,
  mixkit.co, sounds.bbcrewind.co.uk, opengameart.org

No archival image, map or sound effect has been downloaded, and none has been
substituted with generated or illustrative material.

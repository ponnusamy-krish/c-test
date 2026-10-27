"""Re-download any missing archive file listed in assets/manifest.json from its recorded URL.

The files are already committed under assets/raw, so this is only needed after a clean clone
without them. Library of Congress TIFF masters (~70 MB each for the Red Cross photographs) are
re-downloaded and downscaled to the same 3600 px JPEGs the film used.
Wikimedia Commons throttles downloads from shared cloud IPs: if the single Commons file
(bread_queue.jpg) fails with HTTP 429, wait and retry, or download it manually from its page_url.
"""
import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
ROOT = Path(__file__).resolve().parent.parent
H = {"User-Agent": "BolshevikShortReproduction/1.0 (educational video; see README)"}
man = json.loads((ROOT / "assets/manifest.json").read_text())
for name, m in man.items():
    dest = ROOT / m["local_file"]
    if dest.exists():
        continue
    url = m.get("file_url")
    if not url:
        print("no URL recorded for", name); continue
    r = requests.get(url, headers=H, timeout=600)
    if r.status_code != 200:
        print(name, "HTTP", r.status_code, "- download manually from", m.get("page_url")); continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    if url.lower().endswith(".tif") and dest.suffix == ".jpg":        # downscaled copy, as used in the film
        im = Image.open(io.BytesIO(r.content)).convert("L")
        im = im.resize((3600, int(im.height * 3600 / im.width)), Image.LANCZOS)
        im.save(dest, quality=93)
    else:
        dest.write_bytes(r.content)
    print("fetched", name)

"""Library of Congress photo search/metadata/download with provenance capture."""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets" / "raw"
MANIFEST = ROOT / "assets" / "manifest.json"
S = requests.Session()
S.headers["User-Agent"] = "BolshevikShortResearch/1.0 (educational video)"
_last = [0.0]


def _get(url, params=None, stream=False, gap=3.0, tries=6):
    delay = 10.0
    for _ in range(tries):
        w = gap - (time.time() - _last[0])
        if w > 0:
            time.sleep(w)
        r = S.get(url, params=params, stream=stream, timeout=120)
        _last[0] = time.time()
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(delay); delay = min(delay * 2, 120); continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"gave up: {url}")


def search(q, n=12):
    d = _get("https://www.loc.gov/photos/", dict(q=q, fo="json", c=n)).json()
    return [dict(title=x.get("title", ""), date=x.get("date", ""), id=x.get("id", ""))
            for x in d.get("results", [])]


def item(url):
    """Item metadata + candidate image files + rights statement."""
    d = _get(url.rstrip("/") + "/", dict(fo="json")).json()
    it = d.get("item", {})
    files = [f for grp in d.get("resources", [{}])[0].get("files", []) for f in grp]
    jpgs = sorted((f for f in files if f.get("mimetype") == "image/jpeg"),
                  key=lambda f: f.get("size", 0))
    tifs = [f for f in files if f.get("mimetype") == "image/tiff"]
    return dict(
        title=it.get("title"), date=it.get("date"), creator=it.get("creators") or it.get("contributor_names"),
        call_number=it.get("call_number"), reproduction_number=it.get("reproduction_number"),
        rights=it.get("rights_advisory") or it.get("rights") or it.get("access_restricted"),
        notes=it.get("notes"), summary=it.get("summary") or it.get("description"),
        source_collection=it.get("part_of") or it.get("collection"),
        page_url=it.get("id") or url, jpgs=[(f["url"], f.get("size"), f.get("width"), f.get("height")) for f in jpgs],
        tif=[(f["url"], f.get("size")) for f in tifs],
    )


def download(meta, name, jpg_index=-1):
    RAW.mkdir(parents=True, exist_ok=True)
    url = meta["tif"][0][0] if meta.get("tif") else meta["jpgs"][jpg_index][0]
    dest = RAW / (f"{name}.tif" if meta.get("tif") else f"{name}.jpg")
    if not dest.exists():
        for attempt in range(4):
            tmp = dest.with_suffix(dest.suffix + ".part")
            try:
                r = _get(url, stream=True, gap=4)
                with open(tmp, "wb") as f:
                    for c in r.iter_content(1 << 20):
                        f.write(c)
                tmp.rename(dest)
                break
            except requests.exceptions.RequestException:
                tmp.unlink(missing_ok=True)
                time.sleep(8 * (attempt + 1))
        else:
            raise RuntimeError(f"download failed after retries: {url}")
    entries = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    entries[name] = {k: v for k, v in meta.items() if k not in ("jpgs", "tif")} | {
        "file_url": url, "local_file": str(dest.relative_to(ROOT)),
        "source": "Library of Congress"}
    MANIFEST.write_text(json.dumps(entries, indent=2, ensure_ascii=False, default=str))
    return dest

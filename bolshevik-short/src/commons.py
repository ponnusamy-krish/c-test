"""Throttled Wikimedia Commons helper: search, inspect metadata, download.

Every download is appended to assets/manifest.json with the fields needed for
the source/licensing manifest (title, page URL, file URL, author, license,
date, description). Nothing is saved without its metadata.
"""
import html
import json
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "assets" / "raw"
MANIFEST = ROOT / "assets" / "manifest.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = "BolshevikShortResearch/1.0 (educational video; contact via claude.ai/code)"

_session = requests.Session()
_session.headers["User-Agent"] = UA
_last = [0.0]


def _get(url, params=None, stream=False, min_gap=2.5, tries=8):
    """GET with a minimum gap between calls and exponential backoff on 429/5xx."""
    delay = 5.0
    for _ in range(tries):
        wait = min_gap - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        r = _session.get(url, params=params, stream=stream, timeout=90)
        _last[0] = time.time()
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(max(delay, float(r.headers.get("Retry-After", 0) or 0)))
            delay = min(delay * 2, 90)
            continue
        r.raise_for_status()
        return r
    raise RuntimeError(f"gave up on {url}")


def _clean(v):
    return html.unescape(re.sub(r"<[^>]+>", "", v or "")).strip()


def info(title):
    """Metadata for one File: title, or None if it does not exist."""
    r = _get(API, dict(action="query", titles=title, prop="imageinfo",
                       iiprop="url|size|mime|extmetadata", format="json"))
    page = next(iter(r.json()["query"]["pages"].values()))
    if "imageinfo" not in page:
        return None
    ii = page["imageinfo"][0]
    m = ii["extmetadata"]
    g = lambda k: _clean(m.get(k, {}).get("value", ""))
    return dict(
        title=page["title"],
        page_url="https://commons.wikimedia.org/wiki/" + page["title"].replace(" ", "_"),
        file_url=ii["url"], width=ii["width"], height=ii["height"], mime=ii["mime"],
        author=g("Artist"), credit=g("Credit"), license=g("LicenseShortName"),
        license_url=g("LicenseUrl"), date=g("DateTimeOriginal") or g("DateTime"),
        description=g("ImageDescription"), categories=g("Categories"),
        restrictions=g("Restrictions"), copyrighted=g("Copyrighted"),
    )


def search(query, n=10):
    r = _get(API, dict(action="query", list="search", srsearch=query,
                       srnamespace=6, srlimit=n, format="json"))
    return [h["title"] for h in r.json()["query"]["search"]]


def download(meta, name, width=None):
    """Save the file (optionally a server-side thumbnail of `width` px) and record it."""
    RAW.mkdir(parents=True, exist_ok=True)
    ext = Path(meta["file_url"]).suffix.lower() or ".jpg"
    dest = RAW / f"{name}{ext}"
    if not dest.exists():
        url = meta["file_url"]
        if width and width < meta["width"]:
            from urllib.parse import quote
            url = ("https://commons.wikimedia.org/wiki/Special:FilePath/"
                   + quote(meta["title"].split(":", 1)[1].replace(" ", "_")) + f"?width={width}")
        r = _get(url, stream=True, min_gap=10, tries=10)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    entries = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    entries[name] = {**meta, "local_file": str(dest.relative_to(ROOT)),
                     "source": "Wikimedia Commons"}
    MANIFEST.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return dest


def category_files(cat, n=60):
    """File titles directly inside a Commons category (no subcategories)."""
    r = _get(API, dict(action="query", list="categorymembers", cmtitle=cat,
                       cmtype="file", cmlimit=n, format="json"))
    return [m["title"] for m in r.json()["query"]["categorymembers"]]


def subcategories(cat, n=50):
    r = _get(API, dict(action="query", list="categorymembers", cmtitle=cat,
                       cmtype="subcat", cmlimit=n, format="json"))
    return [m["title"] for m in r.json()["query"]["categorymembers"]]


def info_many(titles):
    """Metadata for many File: titles in ONE API request (avoids rate limits)."""
    r = _get(API, dict(action="query", titles="|".join(titles), prop="imageinfo",
                       iiprop="url|size|mime|extmetadata", format="json", redirects=1),
             min_gap=12, tries=12)
    out = {}
    for page in r.json()["query"]["pages"].values():
        if "imageinfo" not in page:
            continue
        ii = page["imageinfo"][0]; m = ii["extmetadata"]
        g = lambda k: _clean(m.get(k, {}).get("value", ""))
        out[page["title"]] = dict(
            title=page["title"],
            page_url="https://commons.wikimedia.org/wiki/" + page["title"].replace(" ", "_"),
            file_url=ii["url"], width=ii["width"], height=ii["height"], mime=ii["mime"],
            author=g("Artist"), credit=g("Credit"), license=g("LicenseShortName"),
            license_url=g("LicenseUrl"), date=g("DateTimeOriginal") or g("DateTime"),
            description=g("ImageDescription"), categories=g("Categories"),
            restrictions=g("Restrictions"), copyrighted=g("Copyrighted"))
    return out

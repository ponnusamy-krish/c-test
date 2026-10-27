"""Build docs/SOURCES.md from the manifest and from the files the film actually touches.

A dry pass over the timeline (one frame every 0.25 s at 1/10 scale) records which archive
files are used; unused downloads are reported and removed so the manifest matches the film.
"""
import json
import os
import re
import sys
from pathlib import Path

os.environ["RENDER_SCALE"] = "0.1"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import frame, scenes
import timeline as T

for i in range(0, round(T.TOTAL * 60), 15):
    frame.build_frame(i)
used = sorted(scenes.USED)
man = json.loads((ROOT / "assets/manifest.json").read_text())
src = (ROOT / "src/scenes.py").read_text()
blocks = re.split(r"\n(?=def |# =====)", src)
where = {}
for name in used:
    scs = []
    for b in blocks:
        m_ = re.search(r"^def (\w+)", b, re.M)
        if m_ and f'"{name}"' in b and m_.group(1) in ("hook", "crisis", "tsar", "lenin", "october", "civil_war", "consolidation", "end"):
            scs.append(m_.group(1))
    where[name] = ", ".join(sorted(set(scs))) or "(background plate)"
unused = [k for k in man if k not in used]
lines = ["# Sources, rights and licences", "",
         "Every archive file that appears in the film, as found by a dry pass over the finished timeline. "
         "Machine-readable version: `assets/manifest.json`. Vetting decisions: `docs/ASSET_NOTES.md`.", "",
         "## Archive images and documents", "", "| File | Item | Date | Creator / credit | Source | Rights as stated by the source | Used in |", "|---|---|---|---|---|---|---|"]
def clean(v, n=220):
    v = re.sub(r"<[^>]+>", " ", str(v or "")).replace("|", "/").replace("\n", " ")
    v = re.sub(r"date QS:.*$", "", v).strip()
    v = re.sub(r"^\[['\"]\s*|['\"]\]$", "", v)
    return re.sub(r"\s+", " ", v).strip()[:n]
for name in used:
    m = man.get(name, {})
    title = clean(m.get("title") or m.get("description"), 170)
    url = m.get("page_url") or m.get("id") or ""
    creator = clean(m.get("author") or m.get("creator") or m.get("credit") or (m.get("title") if "Chronicling" in str(m.get("source")) else None) or "unknown / not stated (anonymous photographer or publisher)", 110)
    rights = clean(m.get("rights") or m.get("license") or "see source page", 170)
    lines.append(f"| `{Path(m.get('local_file', name)).name}` | {title} | {clean(m.get('date'), 40)} | {creator} | {m.get('source','')} — <{url}> | {rights} | {where[name]} |")
lines += ["", "Notes on individual items are in `assets/manifest.json` (`note` field): crop regions for newspaper pages, the downscaled copies of the Red Cross TIFF masters, the 1914 plan's printed 'St. Petersburg' name, and the dating caveats."]
lines += ["", "## Other material", "",
          "| Item | Origin | Licence |", "|---|---|---|",
          "| Map geometry (outlines, borders) | Natural Earth 1:50m admin-0 countries, via the `nvkelso/natural-earth-vector` mirror on GitHub | Public domain |",
          "| Narration | Kokoro-82M via `kokoro-onnx` (model files `kokoro-v1.0.onnx`, `voices-v1.0.bin` from the kokoro-onnx GitHub release `model-files-v1.0`), voice `bm_george` | Model released under Apache-2.0 by its authors; generated audio is mine to use |",
          "| Word timing | sherpa-onnx streaming zipformer English model (calibration/alignment only; no audio of it is used) | Apache-2.0 |",
          "| Sound effects (impacts, whooshes, crowd murmur, telegraph-sounder clicks, marching boots, paper rustle, stamp) | **Synthesised procedurally** in `src/sfx.py` from noise and sine components. No third-party recordings were available (Freesound and similar hosts were blocked; see README). | Created for this project; no third-party licence applies |",
          "| Typefaces: Inter Display, Caladea, JetBrains Mono | system fonts on the render machine | SIL Open Font License 1.1 / Apache-2.0 |",
          "| Music | none | n/a |", "",
          "## Downloaded but not used (removed)", ""]
lines += [f"* `{k}`" for k in unused] or ["* none"]
(ROOT / "docs/SOURCES.md").write_text("\n".join(lines) + "\n")
for k in unused:
    f = man[k].get("local_file")
    if f and (ROOT / f).exists():
        (ROOT / f).unlink()
    man.pop(k)
(ROOT / "assets/manifest.json").write_text(json.dumps(man, indent=2, ensure_ascii=False, default=str))
print("used:", used); print("removed:", unused)

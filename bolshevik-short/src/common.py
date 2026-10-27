"""Shared building blocks for the scenes: assets, map helpers, captions, tags."""
import math
from functools import lru_cache

import cv2
import numpy as np

import mapdata
import territory
import timeline as T
from engine import *
from engine import _font

RAW = ROOT / "assets" / "raw"

MD = mapdata.load()
EMP = [r for rs in MD["empire"].values() for r in rs]
NBR = [r for rs in MD["neighbours"].values() for r in rs]
PET = tuple(float(v) for v in mapdata.project(30.31, 59.93))
MOS = tuple(float(v) for v in mapdata.project(37.62, 55.75))

# map palette (BGR)
SEA = INK
NEIGHBOUR, NEIGHBOUR_EDGE = (36, 35, 34), (54, 52, 50)
EMPIRE_FILL, EMPIRE_EDGE = (74, 70, 63), (150, 168, 176)

# wide ("whole empire") camera shared by the opening and the ending
FULL_CX, FULL_CY, FULL_PPK = 653.0, 1250.0, 0.218


def asset(name):
    for ext in (".jpg", ".jpeg", ".png", ".tif"):
        p = RAW / (name + ext)
        if p.exists():
            return p
    raise FileNotFoundError(f"asset '{name}' is missing from assets/raw (never substituted)")


def u(t, t0, dur):
    return seg(t, t0, t0 + dur)


# ---- map drawing -------------------------------------------------------------
_land_cache = {}


def land_mask(view):
    key = (round(view.cx, 2), round(view.cy, 2), round(view.ppk, 5), view.sx, view.sy, K)
    if key not in _land_cache:
        _land_cache.clear()
        m = np.zeros((H, W), np.uint8)
        fill_rings(m, EMP, view, 255)
        _land_cache[key] = m
    return _land_cache[key]


def draw_base_map(cv, view, dim=1.0, grid=True):
    def c(col):
        return tuple(int(v * dim) for v in col)
    fill_rings(cv, NBR, view, c(NEIGHBOUR), c(NEIGHBOUR_EDGE), 1.6)
    fill_rings(cv, EMP, view, c(EMPIRE_FILL), c(EMPIRE_EDGE), 2.0)


def blend_mask(cv, mask, color, opacity=1.0):
    """cv = cv*(1-a) + color*a, a = mask/255*opacity (single pass on the mask's bounding box)."""
    x, y, w, h = cv2.boundingRect(mask)
    if w == 0 or h == 0:
        return
    roi = cv[y:y + h, x:x + w]
    a = mask[y:y + h, x:x + w]
    if opacity < 0.999:
        a = cv2.convertScaleAbs(a, alpha=opacity)
    a3 = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
    col = np.empty_like(roi); col[:] = color
    roi[:] = cv2.add(cv2.multiply(roi, cv2.subtract(np.full_like(a3, 255), a3), scale=1 / 255.0),
                     cv2.multiply(col, a3, scale=1 / 255.0))


def draw_red(cv, view, phase, opacity=0.86, edge=True):
    cs = territory.contours_km(phase)
    m = np.zeros((H, W), np.uint8)
    fill_rings(m, cs, view, 255)
    m = cv2.min(m, land_mask(view))
    blend_mask(cv, m, RED, opacity)
    if edge:
        e = np.zeros((H, W), np.uint8)
        for r in cs:
            cv2.polylines(e, [np.round(view.pts(r) * 16).astype(np.int32)], True, 255,
                          max(int(4 * K), 1), cv2.LINE_AA, 4)
        blend_mask(cv, cv2.min(e, land_mask(view)), PAPER, 0.85)


def view_lock(P, ppk, screen_p, sx=DW / 2, sy=DH / 2):
    """View with scale ppk whose km point P appears at design px screen_p."""
    return MapView(P[0] - (screen_p[0] - sx) / ppk, P[1] - (sy - screen_p[1]) / ppk, ppk, sx, sy)


def graticule(cv, view, alpha=0.18):
    ov = cv
    col = (95, 100, 104)
    for lon in range(0, 190, 10):
        lat = np.linspace(25, 82, 40)
        x, y = mapdata.project(np.full_like(lat, lon), lat)
        p = np.round(view.pts(np.column_stack([x, y]).astype(np.float32)) * 16).astype(np.int32)
        cv2.polylines(ov, [p], False, col, 1, cv2.LINE_AA, 4)
    for la in range(30, 85, 10):
        lon = np.linspace(0, 190, 80)
        x, y = mapdata.project(lon, np.full_like(lon, la))
        p = np.round(view.pts(np.column_stack([x, y]).astype(np.float32)) * 16).astype(np.int32)
        cv2.polylines(ov, [p], False, col, 1, cv2.LINE_AA, 4)


def arrow_km(cv, pts_km, view, color, width, progress=1.0, head=1.0):
    """Polyline arrow growing along its path."""
    pts = np.asarray(pts_km, np.float64)
    seglen = np.hypot(*np.diff(pts, axis=0).T)
    tot = seglen.sum() * clamp(progress)
    if tot <= 0:
        return
    out = [pts[0]]; acc = 0
    for i, L in enumerate(seglen):
        if acc + L >= tot:
            f = (tot - acc) / L
            out.append(pts[i] + (pts[i + 1] - pts[i]) * f); break
        out.append(pts[i + 1]); acc += L
    out = np.array(out)
    p = view.pts(out.astype(np.float32))
    cv2.polylines(cv, [np.round(p * 16).astype(np.int32)], False, color, max(int(width * K), 1), cv2.LINE_AA, 4)
    if progress > 0.12 and len(out) >= 2:
        d = out[-1] - out[-2]
        ang = math.atan2(-d[1], d[0])
        tip = p[-1]; hl = width * 3.2 * K * head
        a1, a2 = ang + math.radians(150), ang - math.radians(150)
        tri = np.array([tip, tip + hl * np.array([math.cos(a1), math.sin(a1)]),
                        tip + hl * np.array([math.cos(a2), math.sin(a2)])])
        cv2.fillPoly(cv, [np.round(tri * 16).astype(np.int32)], color, cv2.LINE_AA, 4)


def marker(cv, view, P, t, color=RED_HI, r=18, pulse=True, ring_color=None):
    x, y = view.pt(*P)
    if pulse:
        for k in range(3):
            ph = ((t * 0.9) + k / 3.0) % 1.0
            circle(cv, x, y, r + ph * r * 5.5, ring_color or color, 3, alpha=max(0.0, 0.8 * (1 - ph)))
    circle(cv, x, y, r * 1.35, INK)
    circle(cv, x, y, r, color)


def label(cv, text, x, y, key="mono", size=54, color=PAPER, track=4, anchor=(0.5, 0.5), alpha=1.0,
          scale=1.0, shadow=10, rot=0.0):
    tile = text_tile(text, key, size, color, track=track, shadow=shadow)
    blit(cv, tile, x, y, scale=scale, rot=rot, alpha=alpha, anchor=anchor)
    return tile


def tag(cv, text, x, y, p=1.0, bg=RED, fg=PAPER, size=60, anchor=(0.5, 0.5), rot=0.0, track=5, key="mono"):
    """Mono label on a solid plate that wipes open."""
    if p <= 0:
        return
    tile = text_tile(text, key, size, fg, track=track)
    h, w = tile.shape[:2]
    padx, pady = 34 * K, 20 * K
    pw, ph = w + 2 * padx, h * 0.62 + 2 * pady
    plate = np.zeros((int(ph), int(pw), 4), np.uint8)
    plate[..., :3] = bg; plate[..., 3] = 255
    cx0, cy0 = int(padx), int((ph - h) / 2)
    comp = plate.copy()
    sub = comp[cy0:cy0 + h, cx0:cx0 + w]
    n = min(h, sub.shape[0]); mw = min(w, sub.shape[1])
    t = tile[:n, :mw]
    inv = (255 - t[..., 3:4]).astype(np.uint16)
    sub[:n, :mw, :3] = np.minimum(t[..., :3].astype(np.uint16) + (sub[:n, :mw, :3].astype(np.uint16) * inv + 127) // 255, 255).astype(np.uint8)
    wipe = int(pw * out_cubic(p))
    comp[:, wipe:, 3] = 0
    comp[:, :, :3] = (comp[:, :, :3].astype(np.uint16) * (comp[:, :, 3:4] > 0)).astype(np.uint8)
    blit(cv, comp, x, y, rot=rot, anchor=(0.0, anchor[1]) if anchor[0] == 0 else anchor, alpha=1.0)


def credit(cv, text, x, y, alpha=1.0, size=40, anchor=(0.5, 0.5), rot=0.0):
    label(cv, text, x, y, key="serif_i", size=size, color=PAPER_DIM, track=0, anchor=anchor, alpha=alpha,
          shadow=8, rot=rot)


# ---- captions ----------------------------------------------------------------
def _build_chunks():
    chunks = []
    for seg_name in T.ORDER:
        if seg_name == "end" or seg_name not in T.WORDS:
            continue
        cur = []
        for w in T.WORDS[seg_name]["words"]:
            cur.append(w)
            last = w["w"][-1]
            if last in ".?!" or (last in ",;:" and len(cur) >= 3) or len(cur) >= 6:
                chunks.append(cur); cur = []
        if cur:
            chunks.append(cur)
    return chunks


CHUNKS = _build_chunks() if T.WORDS else []
CAP_SIZE, CAP_MAXW, CAP_Y = 98, 1780, 2860


@lru_cache(maxsize=None)
def _layout(ci):
    words = [w["w"].upper() for w in CHUNKS[ci]]
    f = _font("xbold", CAP_SIZE * K)
    space = f.getlength(" ") / K * 1.25
    widths = [f.getlength(w) / K for w in words]
    lines, cur, curw = [], [], 0.0
    for i, (w, wd) in enumerate(zip(words, widths)):
        add = wd + (space if cur else 0)
        if cur and curw + add > CAP_MAXW:
            lines.append((cur, curw)); cur, curw = [], 0.0; add = wd
        cur.append(i); curw += add
    lines.append((cur, curw))
    pos = {}
    ny = len(lines)
    for li, (idx, lw) in enumerate(lines):
        x = DW / 2 - lw / 2
        y = CAP_Y + (li - (ny - 1) / 2) * 128
        for i in idx:
            pos[i] = (x + widths[i] / 2, y); x += widths[i] + space
    return words, pos


def draw_caption(cv, t):
    for ci, ch in enumerate(CHUNKS):
        t0, t1 = ch[0]["t0"] - 0.10, ch[-1]["t1"] + 0.16
        if not (t0 <= t < t1):
            continue
        words, pos = _layout(ci)
        fade = min(seg(t, t0, t0 + 0.10), 1 - seg(t, t1 - 0.12, t1))
        for i, w in enumerate(words):
            wt0, wt1 = ch[i]["t0"], ch[i]["t1"]
            active = wt0 - 0.02 <= t < wt1 + 0.03
            spoken = t >= wt1 + 0.03
            col = RED_HI if active else PAPER
            tile = text_tile(w, "xbold", CAP_SIZE, col, shadow=16, stroke=0)
            pop = 1.0 + 0.05 * (1 - seg(t, wt0, wt0 + 0.14)) if active else 1.0
            a = fade * (1.0 if (active or spoken) else 0.5)
            x, y = pos[i]
            blit(cv, tile, x, y, scale=pop, alpha=a)
        return


def active_caption_text(t):
    for ch in CHUNKS:
        if ch[0]["t0"] - 0.10 <= t < ch[-1]["t1"] + 0.16:
            return " ".join(w["w"] for w in ch)
    return ""

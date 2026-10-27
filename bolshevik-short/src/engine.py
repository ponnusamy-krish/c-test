"""2D motion-graphics engine: all drawing is OpenCV/NumPy/Pillow on BGR uint8 frames.

Coordinates passed to every function are in DESIGN space (2160 x 3840).  The
environment variable RENDER_SCALE (default 1) shrinks the real canvas for fast
previews; the final render always uses RENDER_SCALE=1 (2160 x 3840).
"""
import math
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

DW, DH, FPS = 2160, 3840, 60
K = float(os.environ.get("RENDER_SCALE", "1"))
W, H = int(round(DW * K)), int(round(DH * K))

# ---- palette (BGR) --------------------------------------------------------
INK = (16, 17, 18)          # #121110 charcoal
CHAR = (26, 28, 30)
PAPER = (200, 223, 233)     # #E9DFC8 aged paper
PAPER_DIM = (150, 168, 176)
RED = (46, 16, 200)         # #C8102E
RED_HI = (62, 48, 232)      # brighter accent for text on dark
STEEL = (92, 90, 86)

FONTS = {
    "black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
    "xbold": "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf",
    "bold": "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
    "med": "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf",
    "serif": "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf",
    "serif_i": "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf",
    "serif_b": "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf",
    "mono": "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
}


# ---- easing ---------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t); return t * t * (3 - 2 * t)


def out_cubic(t):
    t = clamp(t); return 1 - (1 - t) ** 3


def in_cubic(t):
    t = clamp(t); return t ** 3


def in_out_cubic(t):
    t = clamp(t); return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def out_expo(t):
    t = clamp(t); return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def in_expo(t):
    t = clamp(t); return 0.0 if t <= 0 else 2 ** (10 * t - 10)


def in_out_expo(t):
    t = clamp(t)
    if t in (0.0, 1.0):
        return t
    return 2 ** (20 * t - 10) / 2 if t < .5 else (2 - 2 ** (-20 * t + 10)) / 2


def out_back(t, s=1.70158):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1


def seg(t, t0, t1):
    """Progress 0..1 of t inside [t0, t1]."""
    return clamp((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)


# ---- canvas ----------------------------------------------------------------
def new_canvas(color=INK):
    c = np.empty((H, W, 3), np.uint8); c[:] = color; return c


def px(v):
    """design px -> real px"""
    return v * K


# ---- text ------------------------------------------------------------------
@lru_cache(maxsize=None)
def _font(key, size_px):
    return ImageFont.truetype(FONTS[key], max(int(round(size_px)), 4))


def _premult(rgba):
    a = rgba[..., 3:4].astype(np.uint16)
    out = rgba.copy()
    out[..., :3] = ((rgba[..., :3].astype(np.uint16) * a + 127) // 255).astype(np.uint8)
    return out


@lru_cache(maxsize=512)
def text_tile(text, key="bold", size=100, color=PAPER, track=0.0, stroke=0.0,
              stroke_color=INK, shadow=0.0, pad=0.0):
    """Premultiplied BGRA tile of one line of text. size/track/stroke in design px."""
    f = _font(key, size * K)
    sw = int(round(stroke * K))
    tr = track * K
    if tr:
        widths = [f.getlength(ch) for ch in text]
        total = sum(widths) + tr * (len(text) - 1)
    else:
        total = f.getlength(text)
    asc, desc = f.getmetrics()
    padp = int(round((pad + stroke + shadow * 1.6) * K)) + 4
    w = int(math.ceil(total)) + 2 * padp
    h = asc + desc + 2 * padp
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rgb = (color[2], color[1], color[0])
    src = (stroke_color[2], stroke_color[1], stroke_color[0])

    def paint(draw, fill, ox=0, oy=0, stroke_w=0, stroke_fill=None):
        if tr:
            x = padp + ox
            for ch, cw in zip(text, widths):
                draw.text((x, padp + oy), ch, font=f, fill=fill, stroke_width=stroke_w,
                          stroke_fill=stroke_fill)
                x += cw + tr
        else:
            draw.text((padp + ox, padp + oy), text, font=f, fill=fill, stroke_width=stroke_w,
                      stroke_fill=stroke_fill)

    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        paint(sd, (0, 0, 0, 255), ox=int(shadow * K * .5), oy=int(shadow * K * .8), stroke_w=sw)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow * K * .7))
        a = sh.split()[3].point(lambda v: min(255, int(v * 1.1)))
        sh.putalpha(a)
        layer = Image.alpha_composite(layer, sh)
        d = ImageDraw.Draw(layer)
    paint(d, rgb + (255,), stroke_w=sw, stroke_fill=src + (255,) if sw else None)
    arr = np.asarray(layer)
    bgra = np.dstack([arr[..., 2], arr[..., 1], arr[..., 0], arr[..., 3]])
    return _premult(bgra)


def fit_size(text, key, max_w, hi=600, track=0.0):
    """Largest design-px font size whose width <= max_w (design px)."""
    lo = 10
    while hi - lo > 2:
        mid = (lo + hi) // 2
        f = _font(key, mid * K)
        wd = (sum(f.getlength(c) for c in text) + track * K * (len(text) - 1)) if track else f.getlength(text)
        if wd / K <= max_w:
            lo = mid
        else:
            hi = mid
    return lo


# ---- compositing -----------------------------------------------------------
ALPHA = [1.0]          # global opacity multiplier for blit()/line(); see alpha_scale()


class alpha_scale:
    """with alpha_scale(0.5): ...  -> everything blitted inside is drawn at half opacity."""

    def __init__(self, a):
        self.a = a

    def __enter__(self):
        self.old = ALPHA[0]; ALPHA[0] = self.old * self.a

    def __exit__(self, *exc):
        ALPHA[0] = self.old


def blit(cv, tile, x, y, scale=1.0, rot=0.0, alpha=1.0, anchor=(0.5, 0.5), flags=cv2.INTER_LINEAR):
    """Alpha-blend a premultiplied BGRA tile; (x, y) is where its anchor lands (design px)."""
    alpha = alpha * ALPHA[0]
    if alpha <= 0.002 or scale <= 0:
        return
    h, w = tile.shape[:2]
    ax, ay = anchor[0] * w, anchor[1] * h
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    A = np.array([[scale * c, scale * s], [-scale * s, scale * c]], np.float64)
    p = np.array([x * K, y * K])
    t = p - A @ np.array([ax, ay])
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float64) @ A.T + t
    x0 = max(int(math.floor(corners[:, 0].min())), 0); y0 = max(int(math.floor(corners[:, 1].min())), 0)
    x1 = min(int(math.ceil(corners[:, 0].max())), W); y1 = min(int(math.ceil(corners[:, 1].max())), H)
    if x1 <= x0 or y1 <= y0:
        return
    M = np.hstack([A, (t - np.array([x0, y0]))[:, None]]).astype(np.float32)
    roi = cv2.warpAffine(tile, M, (x1 - x0, y1 - y0), flags=flags,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if alpha < 0.999:
        roi = cv2.convertScaleAbs(roi, alpha=alpha)
    inv = (255 - roi[..., 3:4]).astype(np.uint16)
    dst = cv[y0:y1, x0:x1]
    dst[:] = np.minimum(roi[..., :3].astype(np.uint16) + (dst.astype(np.uint16) * inv + 127) // 255, 255).astype(np.uint8)


def fill_rect(cv, x0, y0, x1, y1, color, alpha=1.0):
    X0, Y0, X1, Y1 = [int(round(v * K)) for v in (x0, y0, x1, y1)]
    X0, Y0, X1, Y1 = max(X0, 0), max(Y0, 0), min(X1, W), min(Y1, H)
    if X1 <= X0 or Y1 <= Y0 or alpha <= 0:
        return
    roi = cv[Y0:Y1, X0:X1]
    if alpha >= 0.999:
        roi[:] = color
    else:
        col = np.empty_like(roi); col[:] = color
        cv2.addWeighted(col, alpha, roi, 1 - alpha, 0, roi)


def line(cv, p0, p1, color, width, alpha=1.0):
    alpha = alpha * ALPHA[0]
    pts = np.array([p0, p1], np.float64) * K
    ov = cv if alpha >= .999 else cv.copy()
    cv2.line(ov, tuple(np.round(pts[0] * 16).astype(int)), tuple(np.round(pts[1] * 16).astype(int)),
             color, max(int(round(width * K)), 1), cv2.LINE_AA, 4)
    if alpha < .999:
        cv2.addWeighted(ov, alpha, cv, 1 - alpha, 0, cv)


# ---- photos ----------------------------------------------------------------
def _duotone_lut(shadow=(14, 15, 17), high=(205, 226, 238), gamma=1.0):
    t = np.linspace(0, 1, 256) ** gamma
    lut = np.zeros((256, 1, 3), np.uint8)
    for ch in range(3):
        lut[:, 0, ch] = np.clip(shadow[ch] + (high[ch] - shadow[ch]) * t, 0, 255)
    return lut


def load_gray(path):
    im = Image.open(path)
    if im.mode in ("I;16", "I"):
        a = np.asarray(im).astype(np.float32); a = (a - a.min()) / max(np.ptp(a), 1) * 255
        im = Image.fromarray(a.astype(np.uint8))
    return ImageOps.autocontrast(im.convert("L"), cutoff=0.6)


def treat_photo(gray, out_w, out_h=None, sharp=True):
    """Upscale a (small) archival photo to out_w and apply a warm duotone grade. -> BGR uint8"""
    w, h = gray.size
    out_h = out_h or int(round(out_w * h / w))
    g = gray.resize((out_w, out_h), Image.LANCZOS)
    if sharp:
        g = g.filter(ImageFilter.UnsharpMask(radius=max(out_w / 700, 1.2), percent=70, threshold=2))
    a = np.asarray(g)
    # gentle S-curve for punch
    x = a.astype(np.float32) / 255
    x = np.clip(0.5 + (x - 0.5) * 1.12, 0, 1)
    a = (x * 255).astype(np.uint8)
    return cv2.applyColorMap(cv2.cvtColor(a, cv2.COLOR_GRAY2BGR), _duotone_lut()) if False else \
        cv2.LUT(cv2.cvtColor(a, cv2.COLOR_GRAY2BGR), _duotone_lut())


def photo_card(name, path, width, border=34, rot_seed=0, red_edge=False, crop=None):
    """Premultiplied BGRA 'print': treated photo, paper border, soft shadow. width in design px."""
    key = CACHE / f"card_{name}_{int(width)}_{int(K*1000)}_{int(border)}_{crop}.npy"
    if key.exists():
        return np.load(key)
    g = load_gray(path)
    if crop:                      # fractions (left, top, right, bottom) trimmed off, e.g. scan borders
        w0, h0 = g.size
        g = g.crop((int(w0 * crop[0]), int(h0 * crop[1]), int(w0 * (1 - crop[2])), int(h0 * (1 - crop[3]))))
        g = ImageOps.autocontrast(g, cutoff=0.4)
    wpx = int(round(width * K)); bpx = int(round(border * K))
    inner_w = wpx - 2 * bpx
    img = treat_photo(g, inner_w)
    ih = img.shape[0]
    # fine film grain baked into the photo
    rng = np.random.default_rng(7 + rot_seed)
    n = rng.normal(0, 7, img.shape[:2]).astype(np.float32)
    img = np.clip(img.astype(np.float32) + n[..., None], 0, 255).astype(np.uint8)
    cw, ch = wpx, ih + 2 * bpx + int(bpx * 0.9)
    card = np.empty((ch, cw, 3), np.uint8); card[:] = PAPER
    # paper fibre noise
    pn = rng.normal(0, 4, (ch, cw)).astype(np.float32)
    card = np.clip(card.astype(np.float32) + pn[..., None], 0, 255).astype(np.uint8)
    card[bpx:bpx + ih, bpx:bpx + inner_w] = img
    if red_edge:
        cv2.rectangle(card, (bpx - 1, bpx - 1), (bpx + inner_w, bpx + ih), RED, max(int(4 * K), 1))
    pad = int(round(90 * K))
    out = np.zeros((ch + 2 * pad, cw + 2 * pad, 4), np.uint8)
    sh = np.zeros((ch + 2 * pad, cw + 2 * pad), np.uint8)
    sh[pad + int(26 * K):pad + ch + int(26 * K), pad + int(10 * K):pad + cw + int(10 * K)] = 215
    sh = cv2.GaussianBlur(sh, (0, 0), 30 * K)
    out[..., 3] = sh
    out[pad:pad + ch, pad:pad + cw, :3] = card
    out[pad:pad + ch, pad:pad + cw, 3] = 255
    out = _premult(out)
    np.save(key, out)
    return out


def cover_plate(path_or_gray, blur=45, dark=0.30, tint=1.0, crop=None):
    """Full-canvas blurred, darkened, duotoned plate from a photo (for backgrounds)."""
    g = path_or_gray if isinstance(path_or_gray, Image.Image) else load_gray(path_or_gray)
    if crop:
        w0, h0 = g.size
        g = g.crop((int(w0 * crop[0]), int(h0 * crop[1]), int(w0 * (1 - crop[2])), int(h0 * (1 - crop[3]))))
    w, h = g.size
    s = max(W / w, H / h)
    big = g.resize((int(math.ceil(w * s)), int(math.ceil(h * s))), Image.BILINEAR)
    l, t = (big.width - W) // 2, (big.height - H) // 2
    big = big.crop((l, t, l + W, t + H))
    a = cv2.GaussianBlur(np.asarray(big), (0, 0), blur * K)
    bgr = cv2.LUT(cv2.cvtColor(a, cv2.COLOR_GRAY2BGR), _duotone_lut(shadow=(8, 9, 10), high=(150, 172, 184)))
    return (bgr.astype(np.float32) * dark).astype(np.uint8)


# ---- film look -------------------------------------------------------------
class Film:
    """Grain, vignette, flicker, dust and scratches applied to every finished frame.

    Implemented with saturating uint8 OpenCV ops only (about 100 ms per 4K frame).
    """

    def __init__(self, seed=3):
        rng = np.random.default_rng(seed)
        gh, gw = max(H // 2, 8), max(W // 2, 8)
        self.gpos, self.gneg = [], []
        for _ in range(6):
            g = np.clip(rng.normal(0, 1, (gh, gw)) * 5.0, -22, 22)
            self.gpos.append(np.clip(g, 0, 255).astype(np.uint8))
            self.gneg.append(np.clip(-g, 0, 255).astype(np.uint8))
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * .62)) ** 2 + ((yy - H / 2) / (H * .60)) ** 2)
        vig = np.clip(1.08 - 0.62 * r ** 2.1, 0.30, 1.0)
        self.vig3 = cv2.cvtColor((vig * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        self._x = np.arange(256, dtype=np.float32)

    def _lut(self, flick):
        lut = np.zeros((256, 1, 3), np.uint8)
        for i, (lift, gain) in enumerate([(5, .94), (4, .985), (3, 1.0)]):   # B, G, R (warm grade)
            lut[:, 0, i] = np.clip((lift + self._x * gain) * flick, 0, 255)
        return lut

    def apply(self, cv, frame_idx, flash=0.0):
        rr = np.random.default_rng(frame_idx * 7919 + 13)
        flick = 1.0 + rr.uniform(-0.016, 0.016) + 0.025 * math.sin(frame_idx * 0.37)
        out = cv2.LUT(cv, self._lut(flick))
        out = cv2.multiply(out, self.vig3, scale=1 / 255.0)
        i = frame_idx % 6
        gp = np.roll(self.gpos[i], (frame_idx * 37 % self.gpos[i].shape[0], frame_idx * 91 % self.gpos[i].shape[1]), (0, 1))
        gn = np.roll(self.gneg[i], (frame_idx * 53 % self.gneg[i].shape[0], frame_idx * 17 % self.gneg[i].shape[1]), (0, 1))
        gp = cv2.cvtColor(cv2.resize(gp, (W, H), interpolation=cv2.INTER_LINEAR), cv2.COLOR_GRAY2BGR)
        gn = cv2.cvtColor(cv2.resize(gn, (W, H), interpolation=cv2.INTER_LINEAR), cv2.COLOR_GRAY2BGR)
        out = cv2.subtract(cv2.add(out, gp), gn)
        # dust / hair / scratches
        for _ in range(int(rr.integers(2, 7))):
            x, y = int(rr.integers(0, W)), int(rr.integers(0, H))
            ln = int(rr.integers(4, 26) * K) + 1
            ang = rr.uniform(0, math.pi)
            col = (235, 235, 235) if rr.random() < .6 else (10, 10, 10)
            cv2.line(out, (x, y), (int(x + ln * math.cos(ang)), int(y + ln * math.sin(ang))), col, 1, cv2.LINE_AA)
        if rr.random() < 0.05:
            x = int(rr.integers(0, W)); cv2.line(out, (x, 0), (x + int(rr.integers(-3, 3)), H), (150, 160, 165), 1, cv2.LINE_AA)
        if flash > 0:
            out = cv2.addWeighted(out, 1 - flash, np.full_like(out, 255), flash, 0)
        return out


# ---- map view --------------------------------------------------------------
class MapView:
    """Maps projected km coordinates to design px (screen centre (sx, sy) shows km (cx, cy))."""

    def __init__(self, cx, cy, ppk, sx=DW / 2, sy=DH / 2):
        self.cx, self.cy, self.ppk, self.sx, self.sy = cx, cy, ppk, sx, sy

    def pts(self, ring):
        """km ring (N,2) -> real-pixel array (N,2) float64"""
        x = (ring[:, 0] - self.cx) * self.ppk + self.sx
        y = self.sy - (ring[:, 1] - self.cy) * self.ppk
        return np.column_stack([x, y]) * K

    def pt(self, x_km, y_km):
        return ((x_km - self.cx) * self.ppk + self.sx, self.sy - (y_km - self.cy) * self.ppk)


def fill_rings(cv, rings, view, color, edge=None, edge_w=2.0, cull=True):
    for r in rings:
        p = view.pts(r)
        if cull and (p[:, 0].max() < -20 or p[:, 0].min() > W + 20 or p[:, 1].max() < -20 or p[:, 1].min() > H + 20):
            continue
        q = np.round(p * 16).astype(np.int32)
        if color is not None:
            cv2.fillPoly(cv, [q], color, cv2.LINE_AA, 4)
        if edge is not None:
            cv2.polylines(cv, [q], True, edge, max(int(round(edge_w * K)), 1), cv2.LINE_AA, 4)


def poly_km(cv, ring, view, color, alpha=1.0, edge=None, edge_w=2.0):
    ov = cv.copy() if alpha < .999 else cv
    fill_rings(ov, [np.asarray(ring, np.float32)], view, color, edge, edge_w, cull=False)
    if alpha < .999:
        cv2.addWeighted(ov, alpha, cv, 1 - alpha, 0, cv)


def polyline_km(cv, pts_km, view, color, width, alpha=1.0, dash=None):
    ring = np.asarray(pts_km, np.float32)
    p = np.round(view.pts(ring) * 16).astype(np.int32)
    ov = cv.copy() if alpha < .999 else cv
    cv2.polylines(ov, [p], False, color, max(int(round(width * K)), 1), cv2.LINE_AA, 4)
    if alpha < .999:
        cv2.addWeighted(ov, alpha, cv, 1 - alpha, 0, cv)


def circle(cv, cx, cy, r, color, width=-1, alpha=1.0):
    ov = cv.copy() if alpha < .999 else cv
    cv2.circle(ov, (int(round(cx * K * 16)), int(round(cy * K * 16))), int(round(r * K * 16)), color,
               -1 if width < 0 else max(int(round(width * K)), 1), cv2.LINE_AA, 4)
    if alpha < .999:
        cv2.addWeighted(ov, alpha, cv, 1 - alpha, 0, cv)

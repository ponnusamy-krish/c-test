"""Thumbnail (2160x3840 PNG + 1080x1920 JPG) built with the same engine as the film."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cv2
import numpy as np
from common import *
import scenes

ROOT = Path(__file__).resolve().parent.parent


def main():
    cv = new_canvas(INK)
    # archival crowd photograph (LoC, 1917) as a red-toned full-bleed layer
    fl = scenes.crowd_flash("soviet_deputies")
    cv[:] = cv2.addWeighted(cv, 1.0, fl, 0.78, 0)
    cv[:] = (cv.astype(np.float32) * 0.82).astype(np.uint8)
    # map of the empire with Petrograd marked, lower third
    view = MapView(FULL_CX, FULL_CY, FULL_PPK * 1.02, DW / 2, 2750)
    layer = new_canvas(INK)
    draw_base_map(layer, view, dim=0.9)
    m = np.zeros((H, W), np.uint8); cv2.rectangle(m, (0, int(1950 * K)), (W, H), 255, -1)
    blend_mask(cv, m, (0, 0, 0), 0.45)
    ov = cv.copy()
    draw_base_map(ov, view, dim=1.0)
    k = np.zeros((H, W), np.uint8); cv2.rectangle(k, (0, int(1900 * K)), (W, H), 255, -1)
    k = cv2.GaussianBlur(k, (0, 0), 60 * K)
    a = (k.astype(np.float32) / 255 * 0.95)[..., None]
    cv[:] = (cv * (1 - a) + ov * a).astype(np.uint8)
    marker(cv, view, PET, 0.0, r=24, pulse=False)
    circle(cv, *view.pt(*PET), 62, RED_HI, 7)
    # title
    for txt, col, y, size in (("HOW THE", RED_HI, 520, 215), ("BOLSHEVIKS", PAPER, 880, fit_size("BOLSHEVIKS", "black", 1960)),
                              ("TOOK POWER", PAPER, 1270, fit_size("TOOK POWER", "black", 1960))):
        tile = text_tile(txt, "black", size, col, shadow=34, stroke=9 if col == RED_HI else 0, track=12 if size == 215 else 0)
        blit(cv, tile, DW / 2, y, scale=1.0)
    label(cv, "1917 – 1922", DW / 2, 1560, "mono", 84, PAPER, 14, shadow=16)
    line(cv, (DW / 2 - 420, 1640), (DW / 2 + 420, 1640), RED_HI, 8)
    out = Film().apply(cv, 7)
    p = ROOT / "output"; p.mkdir(exist_ok=True)
    cv2.imwrite(str(p / "thumbnail_2160x3840.png"), out)
    small = cv2.resize(out, (1080, 1920), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(p / "thumbnail_1080x1920.jpg"), small, [cv2.IMWRITE_JPEG_QUALITY, 93])
    print("thumbnails written", out.shape)


if __name__ == "__main__":
    main()

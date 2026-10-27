"""Frame assembly: scene -> captions -> film look."""
import cv2
import numpy as np

import scenes
import timeline as T
from common import draw_caption
from engine import FPS, INK, Film, new_canvas, smooth

XFADE = 0.30

SCENES = {k: getattr(scenes, k) for k in ("hook", "crisis", "tsar", "lenin", "october", "civil_war", "consolidation", "end")
          if hasattr(scenes, k)}
_film = None


def build_frame(i):
    global _film
    if _film is None:
        _film = Film()
    t = i / FPS
    cv = new_canvas(INK)
    name = T.which_scene(t)
    SCENES[name](cv, t)
    idx = T.ORDER.index(name)
    dt = t - T.SCENE[name][0]
    if idx > 0 and dt < XFADE:                         # 0.3 s dissolve from the previous scene instead of a hard cut
        prev = new_canvas(INK)
        SCENES[T.ORDER[idx - 1]](prev, t)
        k = smooth(dt / XFADE)
        cv = cv2.addWeighted(prev, 1.0 - k, cv, k, 0)
    if name != "end":
        draw_caption(cv, t)
    flash = 0.0
    if t < 0.12:
        flash = 0.85 * (1 - t / 0.12)
    for tf, amp in ((0.92, 0.22), (1.62, 0.22)):
        if 0 <= t - tf < 0.09:
            flash = max(flash, amp * (1 - (t - tf) / 0.09))
    return _film.apply(cv, i, flash)

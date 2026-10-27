"""Approximate, simplified 'Soviet-held' territory for five phases, morphable over time.

SIMPLIFIED ILLUSTRATION. Boundaries are hand-drawn from general histories of the
Russian Civil War and are deliberately coarse (tens of km at best). The phases:

  A  Oct-Nov 1917   Petrograd and Moscow (+ the railway between them) only
  B  mid-1918       'Soviet Russia' heartland after Brest-Litovsk, Czech Legion revolt,
                    Don/Kuban Whites, Allied landings in the North
  C  Oct 1919       high-water mark of the White offensives (Denikin at Orel,
                    Yudenich at Petrograd's gates; Kolchak already driven back to Omsk line)
  D  Nov 1920       Whites reduced to Crimea; Far East, Georgia and Poland-held lands outside
  E  Oct 1922       the Red area as the USSR forms: most, NOT all, of the old empire
                    (Poland, Finland, the Baltic states, Bessarabia and the Polish-held
                    western borderlands stay outside)

Phases are rasterised on a coarse km grid, turned into signed-distance fields and
interpolated, so the front line flows smoothly between phases.
"""
import pickle
from pathlib import Path

import cv2
import numpy as np

import mapdata

ROOT = Path(__file__).resolve().parent.parent
GX0, GX1, GY0, GY1, RES = -3700.0, 4900.0, -2300.0, 4750.0, 6.0
GW, GH = int((GX1 - GX0) / RES), int((GY1 - GY0) / RES)
CACHE = ROOT / "build/territory.pkl"

CORE_B = [(29.6, 61.0), (28.0, 59.5), (28.4, 57.9), (30.4, 55.7), (30.7, 54.2), (31.4, 52.4), (34.9, 52.3),
          (36.9, 50.7), (40.3, 50.1), (41.9, 49.3), (44.1, 48.5), (45.5, 49.6), (46.3, 51.5), (47.7, 52.6),
          (48.6, 54.3), (49.5, 56.2), (50.4, 57.8), (53.0, 58.5), (56.5, 58.0), (59.0, 59.8), (58.5, 62.0),
          (52.0, 63.2), (46.0, 63.8), (41.5, 63.0), (39.0, 62.0), (35.5, 62.4), (33.0, 62.8), (31.5, 61.8)]
CORE_C = [(29.6, 61.0), (28.3, 59.9), (28.5, 58.0), (30.6, 55.8), (30.7, 54.2), (32.5, 52.4), (34.0, 52.2),
          (36.5, 52.6), (37.5, 51.4), (38.5, 50.8), (40.4, 50.6), (41.5, 50.0), (43.0, 50.2), (45.0, 50.6),
          (48.0, 50.8), (51.0, 51.0), (55.0, 51.0), (61.0, 52.0), (65.0, 53.5), (68.0, 54.6), (70.0, 56.5),
          (68.0, 60.0), (62.0, 62.0), (56.0, 63.5), (50.0, 64.5), (45.0, 65.0), (41.5, 64.8), (39.0, 62.3),
          (35.5, 62.5), (33.0, 62.8), (31.5, 61.8)]
CRIMEA = [(32.4, 45.0), (33.5, 46.2), (36.6, 45.9), (36.8, 45.0), (35.2, 44.4), (33.6, 44.3)]
KRESY = [(23.2, 56.0), (27.6, 55.2), (28.2, 53.9), (27.2, 52.6), (27.0, 51.7), (26.8, 50.7), (26.0, 49.6),
         (25.1, 48.7), (24.0, 48.4), (22.5, 49.0), (22.0, 51.0), (23.2, 54.5)]
FAR_EAST = [(110.0, 40.0), (110.0, 75.0), (200.0, 75.0), (200.0, 40.0)]
GEORGIA = [(40.0, 41.0), (40.0, 43.7), (47.0, 43.7), (47.0, 41.0)]
LOST_COUNTRIES = ["Poland", "Finland", "Estonia", "Latvia", "Lithuania", "Moldova"]


def _grid(ring_km):
    r = np.asarray(ring_km, np.float64)
    return np.round(np.column_stack([(r[:, 0] - GX0) / RES, (GY1 - r[:, 1]) / RES]) * 16).astype(np.int32)


def _poly_mask(poly_lonlat, mask=None, value=255):
    m = np.zeros((GH, GW), np.uint8) if mask is None else mask
    x, y = mapdata.project(*np.array(poly_lonlat).T)
    cv2.fillPoly(m, [_grid(np.column_stack([x, y]))], value, cv2.LINE_8, 4)
    return m


def _rings_mask(rings, mask=None, value=255):
    m = np.zeros((GH, GW), np.uint8) if mask is None else mask
    for r in rings:
        cv2.fillPoly(m, [_grid(r)], value, cv2.LINE_8, 4)
    return m


def _sdf(mask):
    m = (mask > 0).astype(np.uint8)
    din = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    dout = cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)
    s = din - dout
    return cv2.GaussianBlur(s, (0, 0), 1.6).astype(np.float32)


def build():
    md = mapdata.load()
    land = _rings_mask(md["empire_union"])
    # A: disks around Petrograd and Moscow plus the railway between them
    a = np.zeros((GH, GW), np.uint8)
    pts = {}
    for name, (lon, lat) in {"pet": (30.31, 59.93), "mos": (37.62, 55.75)}.items():
        x, y = mapdata.project(lon, lat); pts[name] = (float((x - GX0) / RES), float((GY1 - y) / RES))
        cv2.circle(a, (int(pts[name][0]), int(pts[name][1])), int(150 / RES), 255, -1)
    cv2.line(a, tuple(map(int, pts["pet"])), tuple(map(int, pts["mos"])), 255, int(60 / RES))
    states = {"A": a}
    for key, poly in (("B", CORE_B), ("C", CORE_C)):
        states[key] = cv2.bitwise_and(_poly_mask(poly), land)
    # D: empire minus lost western lands, Far East, Georgia, Crimea
    lost = np.zeros((GH, GW), np.uint8)
    for name in LOST_COUNTRIES:
        _rings_mask(md["empire"][name], lost)
    _poly_mask(KRESY, lost)
    states["E"] = cv2.bitwise_and(land, cv2.bitwise_not(lost))
    d = states["E"].copy()
    for poly in (FAR_EAST, GEORGIA, CRIMEA):
        _poly_mask(poly, d, 0)
    states["D"] = d
    # phase order for interpolation
    data = {"sdf": {k: _sdf(v) for k, v in states.items()}, "land": land,
            "pet": pts["pet"], "mos": pts["mos"]}
    pickle.dump(data, open(CACHE, "wb"))
    return data


_DATA = None


def data():
    global _DATA
    if _DATA is None:
        _DATA = pickle.load(open(CACHE, "rb")) if CACHE.exists() else build()
    return _DATA


ORDER = ["A", "B", "C", "D", "E"]


def contours_km(phase):
    """Contours (list of (N,2) km arrays) of the Red area at fractional phase index (0=A .. 4=E)."""
    d = data()["sdf"]
    phase = float(np.clip(phase, 0, len(ORDER) - 1))
    i = min(int(phase), len(ORDER) - 2); u = phase - i
    u = u * u * (3 - 2 * u)
    s = d[ORDER[i]] * (1 - u) + d[ORDER[i + 1]] * u
    m = (s > 0).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cs:
        if len(c) < 4:
            continue
        c = cv2.approxPolyDP(c, 0.7, True)[:, 0, :].astype(np.float32)
        out.append(np.column_stack([c[:, 0] * RES + GX0 + RES / 2, GY1 - c[:, 1] * RES - RES / 2]))
    return out


if __name__ == "__main__":
    build()
    import time
    t = time.time()
    n = sum(len(contours_km(p)) for p in (0, 0.5, 1.5, 2.5, 3.5))
    print("built; contour extraction 5 phases: %.0f ms, contours: %d" % ((time.time() - t) * 1000, n))

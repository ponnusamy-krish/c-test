"""Build projected vector geometry for the animated maps (cached to build/maps.pkl).

Source: Natural Earth 1:50m admin-0 countries (public domain).

The Russian Empire outline is APPROXIMATE, assembled from modern country shapes:
  + Russia, Finland, Estonia, Latvia, Lithuania, Belarus, Ukraine, Moldova,
    Georgia, Armenia, Azerbaijan, Kazakhstan, Uzbekistan, Turkmenistan,
    Tajikistan, Kyrgyzstan
  + Poland clipped to a hand-drawn polygon for Congress Poland (Vistula Land)
  - Kaliningrad oblast (German East Prussia in 1914)
  - Southern Sakhalin (Japanese Karafuto 1905-1945)
Not modelled: Kars/Batum (held 1878-1918), Tannu Uriankhai (protectorate 1914).
"""
import json
import pickle
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets/maps/ne_50m_admin_0_countries.geojson"
CACHE = ROOT / "build/maps.pkl"

EMPIRE = ["Russia", "Finland", "Estonia", "Latvia", "Lithuania", "Belarus", "Ukraine",
          "Moldova", "Georgia", "Armenia", "Azerbaijan", "Kazakhstan", "Uzbekistan",
          "Turkmenistan", "Tajikistan", "Kyrgyzstan"]

# Congress Poland (Vistula Land), approximate (lon, lat)
CONGRESS_POLAND = Polygon([(18.6, 50.8), (19.3, 50.3), (20.8, 50.2), (22.4, 50.5),
                           (24.2, 50.5), (24.2, 54.4), (22.8, 54.4), (20.3, 53.5),
                           (19.2, 52.8), (18.3, 52.4), (18.0, 51.7), (18.4, 51.1)])
KALININGRAD = box(19.5, 54.2, 23.0, 55.5)
S_SAKHALIN = box(141.0, 45.5, 145.0, 50.0)

# Lambert conformal conic centred on the Eurasian landmass
LON0, LAT0, LAT1, LAT2 = 75.0, 55.0, 45.0, 65.0
R = 6371.0  # km


def project(lon, lat):
    lon = np.asarray(lon, float); lat = np.asarray(lat, float)
    p1, p2, p0 = np.radians([LAT1, LAT2, LAT0])
    n = np.log(np.cos(p1) / np.cos(p2)) / np.log(np.tan(np.pi / 4 + p2 / 2) / np.tan(np.pi / 4 + p1 / 2))
    F = np.cos(p1) * np.tan(np.pi / 4 + p1 / 2) ** n / n
    rho = R * F / np.tan(np.pi / 4 + np.radians(lat) / 2) ** n
    rho0 = R * F / np.tan(np.pi / 4 + p0 / 2) ** n
    th = n * np.radians(lon - LON0)
    return rho * np.sin(th), rho0 - rho * np.cos(th)   # x east, y NORTH (km)


def _unwrap(geom_json, shift_antimeridian):
    g = shape(geom_json)
    polys = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    out = []
    for p in polys:
        if shift_antimeridian:   # Chukotka is split at +-180: move west-of-180 lon to 180+
            xs, ys = p.exterior.xy
            if min(xs) < -150:
                p = Polygon([(x + 360, y) for x, y in zip(xs, ys)])
        out.append(p)
    return out


def _rings(geom):
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    res = []
    for p in polys:
        if p.is_empty or p.geom_type != "Polygon":
            continue
        x, y = project(*map(np.array, p.exterior.xy))
        res.append(np.column_stack([x, y]).astype(np.float32))
    return res


def build():
    feats = json.loads(SRC.read_text())["features"]
    empire_parts, neighbours = {}, {}
    for f in feats:
        name = f["properties"]["NAME"]
        if name in EMPIRE:
            polys = _unwrap(f["geometry"], name == "Russia")
            g = unary_union(polys)
            if name == "Russia":
                g = g.difference(KALININGRAD).difference(S_SAKHALIN)
            empire_parts[name] = g
        elif name == "Poland":
            empire_parts[name] = shape(f["geometry"]).intersection(CONGRESS_POLAND)
        elif f["properties"].get("CONTINENT") in ("Europe", "Asia") or name in ("Turkey",):
            geom = shape(f["geometry"])
            if name == "Poland":
                continue
            neighbours[name] = geom
    # Poland outside Congress Poland + Kaliningrad / S.Sakhalin remain "other land"
    poland_full = next(shape(f["geometry"]) for f in feats if f["properties"]["NAME"] == "Poland")
    neighbours["Poland (non-Congress)"] = poland_full.difference(CONGRESS_POLAND)
    for k, g in list(neighbours.items()):
        neighbours[k] = g.intersection(box(-10, 20, 150, 82))
    empire_union = unary_union(list(empire_parts.values()))
    data = {
        "empire": {k: _rings(g) for k, g in empire_parts.items()},
        "empire_union": _rings(empire_union),
        "neighbours": {k: _rings(g) for k, g in neighbours.items() if not g.is_empty},
    }
    CACHE.parent.mkdir(exist_ok=True)
    pickle.dump(data, open(CACHE, "wb"))
    return data


def load():
    return pickle.load(open(CACHE, "rb")) if CACHE.exists() else build()


if __name__ == "__main__":
    d = build()
    allr = np.vstack([r for rs in d["empire"].values() for r in rs])
    print("empire parts:", len(d["empire"]), "rings:", sum(len(v) for v in d["empire"].values()),
          "vertices:", len(allr))
    print("extent km  x:[%.0f, %.0f]  y:[%.0f, %.0f]" % (allr[:, 0].min(), allr[:, 0].max(), allr[:, 1].min(), allr[:, 1].max()))
    px, py = project(30.3, 59.93)
    print("Petrograd (km):", float(px), float(py), "| Moscow:", [float(v) for v in project(37.62, 55.75)])

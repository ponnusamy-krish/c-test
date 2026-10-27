"""The eight scenes. Each takes (canvas, t) where t is absolute video time in seconds."""
import json
import math
import os

import cv2
import numpy as np

from common import *
import common
import mapdata

STANDIN = os.environ.get("PREVIEW_STANDIN") == "1"      # layout previews only; never used for the final render


USED = set()          # every archive file a rendered frame has touched (used to build the manifest)
CROPS = {"lenin_a_1920": (0.045, 0.075, 0.04, 0.065), "arc_denikin_cavalry": (0.045, 0.04, 0.045, 0.075), "arc_south_russia_war": (0.05, 0.05, 0.04, 0.07),
         "arc_bolshevik_prisoners_omsk": (0.045, 0.04, 0.03, 0.08), "burning_coats_of_arms": (0, 0, 0, 0.17),
         "wwi_soldiers_1917": (0.02, 0.03, 0.02, 0.03), "duma_troops": (0.0, 0.0, 0.0, 0.0)}


def have(name):
    try:
        asset(name); return True
    except FileNotFoundError:
        return False


PICKS = [("womens_day", "arsenal_barricades"), ("july_days", "wwi_soldiers_1917")]     # every pick() used by a scene
CHOICE_FILE = ROOT / "build" / "choices.json"
_choices = json.loads(CHOICE_FILE.read_text()) if CHOICE_FILE.exists() else {}


def freeze_choices():
    """Resolve every preference list once, so a file that appears mid-render cannot change a scene half-way."""
    ch = {}
    for names in PICKS:
        ch["|".join(names)] = next((n for n in names if have(n)), names[-1])
    CHOICE_FILE.write_text(json.dumps(ch, indent=1))
    return ch


def pick(*names):
    """First genuine archive file that exists (never a stand-in); frozen by freeze_choices() for the render."""
    key = "|".join(names)
    if key in _choices:
        return _choices[key]
    for n in names:
        if have(n):
            return n
    if STANDIN:
        return names[0]
    raise FileNotFoundError(f"none of {names} present in assets/raw")


def photo(name, width, **kw):
    """Cached photo card. In STANDIN preview mode a missing archive file is replaced by a layout placeholder."""
    crop = kw.pop("crop", CROPS.get(name))
    try:
        card = photo_card(name, asset(name), width, crop=crop, **kw)
        USED.add(name)
        return card
    except FileNotFoundError:
        if not STANDIN:
            raise
        return photo_card("standin_" + name, asset("duma_troops"), width, **kw)


@lru_cache(maxsize=None)
def plate(name, dark=0.32):
    try:
        USED.add(name)
        return cover_plate(asset(name), blur=48, dark=dark, crop=CROPS.get(name))
    except FileNotFoundError:
        if not STANDIN:
            raise
        return cover_plate(asset("duma_troops"), blur=48, dark=dark)


@lru_cache(maxsize=None)
def crowd_flash(name):
    """Full-bleed red-tinted crowd image used for the cold-open flashes."""
    g = load_gray(asset(name))
    w, h = g.size
    s = max(W / w, H / h)
    big = g.resize((int(math.ceil(w * s)), int(math.ceil(h * s))), Image.LANCZOS)
    l, t = (big.width - W) // 2, (big.height - H) // 2
    a = np.asarray(big.crop((l, t, l + W, t + H))).astype(np.float32) / 255
    a = np.clip((a - 0.12) * 1.5, 0, 1) ** 1.2
    out = np.zeros((H, W, 3), np.uint8)
    out[..., 2] = (a * 235).astype(np.uint8); out[..., 1] = (a * 60).astype(np.uint8); out[..., 0] = (a * 50).astype(np.uint8)
    return out


def red_discs(cv, view, rp, rm, line=0.0):
    """Phase-A footprint (Petrograd, Moscow, railway) clipped to land, radii in km."""
    m = np.zeros((H, W), np.uint8)
    if rp > 0:
        x, y = view.pt(*PET); circle(m, x, y, rp * view.ppk, 255)
    if rm > 0:
        x, y = view.pt(*MOS); circle(m, x, y, rm * view.ppk, 255)
    if line > 0:
        a, b = view.pt(*PET), view.pt(*MOS)
        cv2.line(m, (int(a[0] * K), int(a[1] * K)), (int(b[0] * K), int(b[1] * K)), int(255 * line), max(int(60 * view.ppk * K), 2), cv2.LINE_AA)
    blend_mask(cv, cv2.min(m, land_mask(view)), RED, 0.88)


def title_banner(cv, alpha):
    tile = text_tile("HOW THE BOLSHEVIKS TOOK POWER", "bold", 58, PAPER, track=9, shadow=10)
    blit(cv, tile, DW / 2, 300, alpha=alpha * 0.85)
    line(cv, (DW / 2 - 330, 372), (DW / 2 + 330, 372), RED_HI, 5, alpha=alpha)


# ============================================================ 0 HOOK
def hook(cv, t):
    p0 = (DW / 2 + (PET[0] - FULL_CX) * FULL_PPK, 1650 - (PET[1] - FULL_CY) * FULL_PPK)
    HI = 1.15
    if t < 3.0:
        zf = in_out_expo(t / 3.0); extra = 0.0
    elif t < 8.4:
        zf = 1.0; extra = 0.25 * smooth(seg(t, 3.0, 8.4))
    else:
        zo = in_out_cubic(seg(t, 8.4, 12.4)); zf = 1 - zo; extra = 0.25 * (1 - zo)
    ppk = FULL_PPK * (HI / FULL_PPK) ** zf * (1 + extra)
    sp = (lerp(p0[0], DW / 2, zf), lerp(p0[1], 1650, zf))
    view = view_lock(PET, ppk, sp, DW / 2, 1650)

    draw_base_map(cv, view)
    graticule(cv, view)
    # Petrograd reveal and Moscow
    rp = 150 * out_cubic(seg(t, 5.3, 8.0))
    rm = 150 * out_cubic(seg(t, 10.3, 11.4))
    red_discs(cv, view, rp, rm, line=seg(t, 10.8, 11.8))
    if t > 3.0:
        marker(cv, view, PET, t, r=16 + 4 * min(zf, 1))
    # empire outline pulse for "Russia itself"
    k = seg(t, 9.6, 11.0) * (1 - seg(t, 12.0, 12.7))
    if k > 0:
        fill_rings(cv, EMP, view, None, PAPER, 5.0 * k + 1.0)
    # labels
    a = out_cubic(seg(t, 3.4, 3.9)) * (1 - seg(t, 8.9, 9.4))
    if a > 0:
        x, y = view.pt(*PET)
        label(cv, "PETROGRAD", x + 70, y - 70, "mono", 66, PAPER, 6, anchor=(0, 0.5), alpha=a)
        label(cv, "CAPITAL OF THE EMPIRE", x + 70, y - 8, "mono", 40, PAPER_DIM, 4, anchor=(0, 0.5), alpha=a)
    if ppk < 1.0:
        x, y = view.pt(*MOS)
        label(cv, "MOSCOW", x + 40, y - 6, "mono", 46, PAPER, 5, anchor=(0, 0.5), alpha=smooth(seg(1.0 - ppk, 0.0, 0.5)) * 0.9)
    # "IN HOURS" slam
    th = T.word("hook", "hours")
    if th - 0.05 < t < th + 1.6:
        s = 1 + 0.5 * (1 - out_expo(u(t, th - 0.05, 0.25)))
        al = u(t, th - 0.05, 0.08) * (1 - u(t, th + 1.0, 0.6))
        label(cv, "IN HOURS", DW / 2, 930, "black", 230, RED_HI, 8, alpha=al, scale=s, shadow=22)
    if 10.2 < t < 12.76:
        a2 = smooth(seg(t, 10.2, 10.8)) * (1 - seg(t, 12.2, 12.7))
        label(cv, "THE REST OF RUSSIA", DW / 2, 2600, "mono", 62, PAPER, 8, alpha=a2)

    # cold open: crowd flashes and title slam (first ~3 s)
    for t0, name, dur in ((0.22, "duma_troops", 0.55), (0.88, "soviet_deputies", 0.5), (1.55, "liteiny_barricade", 0.55)):
        if t0 <= t < t0 + dur:
            ph = (t - t0) / dur
            al = 0.62 * math.sin(math.pi * clamp(ph)) ** 0.7
            fl = crowd_flash(name)
            z = 1.0 + 0.10 * ph
            M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, z)
            cv[:] = cv2.addWeighted(cv, 1.0, cv2.warpAffine(fl, M, (W, H)), al, 0)
    big = seg(t, 2.5, 3.1)
    if t < 3.1:
        for i, (txt, col, y, t0) in enumerate((("HOW THE", RED_HI, 560, 0.30), ("BOLSHEVIKS", PAPER, 840, 0.42), ("TOOK POWER", PAPER, 1130, 0.54))):
            size = 200 if i == 0 else fit_size(txt, "black", 1900, track=0)
            tile = text_tile(txt, "black", size, col, shadow=24, track=10 if i == 0 else 0, stroke=7 if i == 0 else 0)
            pp = u(t, t0, 0.30)
            s = (1 + 0.45 * (1 - out_expo(pp))) * (1 - 0.18 * smooth(big))
            sh = (math.sin(t * 90) * 7 * max(0.0, 1 - (t - t0) / 0.25)) if t0 < t < t0 + 0.25 else 0
            blit(cv, tile, DW / 2 + sh, y - 150 * smooth(big), scale=s, alpha=u(t, t0, 0.05) * (1 - smooth(big)))
    title_banner(cv, smooth(seg(t, 2.9, 3.5)) * (1 - seg(t, 12.4, 12.76)))


# ============================================================ 1 CRISIS
def crisis(cv, t):
    t0, t1 = T.SCENE["crisis"]
    r = t - t0
    view = MapView(FULL_CX, FULL_CY, FULL_PPK, DW / 2, 1650)
    draw_base_map(cv, view, dim=0.42)
    red_discs(cv, view, 150, 150, 1.0)
    cv[:] = (cv.astype(np.float32) * 0.55).astype(np.uint8)

    def enter(delay, dx, dur=0.6):
        p = out_cubic(u(r, delay, dur))
        return (1 - p) * dx
    c1 = photo("wwi_soldiers_1917", 1560)
    c2 = photo("bread_queue", 1620)
    tm = T.word("crisis", "millions") - t0 - 0.25
    drift = 1.0 + 0.025 * smooth(r / 4.8)
    blit(cv, c1, 880 - enter(0.05, 1500), 1230, scale=drift, rot=-3.2, alpha=1 - 0.28 * smooth(u(r, tm, 0.4)))
    blit(cv, c2, 1290 + enter(tm, 1500), 2130, scale=drift, rot=2.6)
    tag(cv, "1914 – 1918 · WORLD WAR I", 200, 560, p=u(r, 0.30, 0.45), anchor=(0, 0.5), size=54)
    credit(cv, "Russian soldiers, 1917 · Library of Congress, World Digital Library", 880, 1795, alpha=u(r, 0.6, 0.4), size=36, rot=-1)
    tag(cv, "SHORTAGES · PETROGRAD, 1917", 2010, 1560, p=u(r, tm + 0.3, 0.45), anchor=(1, 0.5), size=54, bg=RED)
    credit(cv, "Bread queue, Petrograd, early 1917 · Wikimedia Commons (public domain)", 1290, 2745, alpha=u(r, tm + 0.6, 0.4), size=36, rot=1.2)


# ============================================================ 2 THE TSAR FALLS
CREDITS = {
    "womens_day": "Women's Day march, Petrograd, 8 March 1917 (N.S.) · Museum of Political History of Russia, via Wikimedia Commons",
    "arsenal_barricades": "Barricades by the Arsenal, Petrograd, 1917 · Library of Congress",
}


def tsar(cv, t):
    t0, t1 = T.SCENE["tsar"]
    r = t - t0
    ts = T.word("tsar", "strikes") - t0 - 0.25
    tf = T.word("tsar", "forced") - t0 - 0.25
    tab = T.word("tsar", "abdicate") - t0
    tp = T.word("tsar", "provisional") - t0 - 0.2
    first = pick("womens_day", "arsenal_barricades")
    phases = [(0.0, ts, first), (ts, tf, "liteiny_barricade"), (tf, tp, "np_kennebec_column"), (tp, 99, "soviet_deputies")]
    cur = next(i for i, (a, b, _) in enumerate(phases) if a <= r < b)
    pa = plate(phases[cur][2])
    if cur > 0:
        k = smooth(u(r, phases[cur][0], 0.5))
        cv[:] = cv2.addWeighted(plate(phases[cur - 1][2]), 1 - k, pa, k, 0)
    else:
        cv[:] = pa

    def top_date(txt, sub, a):
        label(cv, txt, DW / 2, 520, "mono", 108, PAPER, 6, alpha=a, shadow=14)
        label(cv, sub, DW / 2, 640, "mono", 46, PAPER_DIM, 5, alpha=a)

    tsar_timeline(cv, r, ts, tf, tab, tp)

    def draw(i, r):
        if i == 0:
            a = u(r, 0.0, 0.4)
            top_date("FEBRUARY 1917", "23 FEB · RUSSIAN (O.S.) CALENDAR", a)
            c = photo(first, 1780)
            s = 1.0 + 0.035 * smooth(r / max(ts, 0.1))
            blit(cv, c, DW / 2, 1560 - 40 * (1 - out_cubic(u(r, 0, 0.6))), scale=s, rot=-1.2, alpha=u(r, 0.05, 0.3))
            credit(cv, CREDITS[first], DW / 2, 2200, alpha=a, size=34)
        elif i == 1:
            q = r - ts
            top_date("23 – 27 FEB 1917", "STRIKES · MUTINIES · BARRICADES (O.S.)", u(q, 0.12, 0.3))
            c1 = photo("liteiny_barricade", 1500); c2 = photo("duma_troops", 1500)
            blit(cv, c1, 800 - (1 - out_cubic(u(q, 0, 0.5))) * 1400, 1300, rot=-3.0, scale=1 + 0.03 * smooth(q / 2.4))
            blit(cv, c2, 1380 + (1 - out_cubic(u(q, 0.35, 0.5))) * 1400, 1990, rot=2.4, scale=1 + 0.03 * smooth(q / 2.4))
            credit(cv, "Barricades on Liteiny Prospect · Library of Congress", 800, 1800, alpha=u(q, 0.4, 0.3), size=34, rot=-2)
            credit(cv, "Troops at the State Duma · Library of Congress", 1380, 2490, alpha=u(q, 0.6, 0.3), size=34, rot=2)
        elif i == 2:
            q = r - tf
            top_date("2 MARCH 1917", "= 15 MARCH IN THE GREGORIAN CALENDAR", u(q, 0.12, 0.3))
            ban = photo("np_kennebec_banner", 1960, border=16)
            col = photo("np_kennebec_column", 1420, border=20)
            s = 1.0 + 0.05 * smooth(q / max(tp - tf, 0.1))
            blit(cv, ban, DW / 2, 905, rot=-0.4, alpha=u(q, 0.0, 0.3), scale=1 + 0.02 * smooth(q / 2.5))
            blit(cv, col, DW / 2, 1740, scale=s, rot=0.8, alpha=u(q, 0.12, 0.3))
            ps = u(r, tab - 0.05, 0.22)
            if ps > 0:
                tile = text_tile("ABDICATED", "black", 190, RED_HI, track=6, stroke=8, shadow=14)
                blit(cv, tile, DW / 2 + 160, 2150, scale=1 + 0.55 * (1 - out_expo(ps)), rot=-9, alpha=min(1.0, ps * 6))
            credit(cv, "Daily Kennebec Journal (Augusta, Maine), 16 March 1917 · Library of Congress, Chronicling America", DW / 2, 2470,
                   alpha=u(q, 0.2, 0.4), size=32)
        else:
            q = r - tp
            a = u(q, 0.0, 0.35)
            label(cv, "PROVISIONAL", DW / 2, 640, "black", fit_size("PROVISIONAL", "black", 1850), PAPER, 0, alpha=a, shadow=18,
                  scale=1 + 0.3 * (1 - out_expo(u(q, 0, 0.3))))
            label(cv, "GOVERNMENT", DW / 2, 900, "black", fit_size("GOVERNMENT", "black", 1850), RED_HI, 0, alpha=u(q, 0.12, 0.35), shadow=18,
                  scale=1 + 0.3 * (1 - out_expo(u(q, 0.12, 0.3))))
            label(cv, "MARCH 1917 · DUAL POWER WITH THE PETROGRAD SOVIET", DW / 2, 1090, "mono", 40, PAPER_DIM, 4, alpha=u(q, 0.4, 0.4))
            c = photo("soviet_deputies", 1700)
            blit(cv, c, DW / 2, 1800 + (1 - out_cubic(u(q, 0.1, 0.6))) * 500, rot=1.4, scale=1 + 0.03 * smooth(q / 2.0), alpha=u(q, 0.1, 0.3))
            credit(cv, "Petrograd, 1917: 'Long live the Council of Workers' and Soldiers' Deputies!' · Library of Congress", DW / 2, 2440,
                   alpha=u(q, 0.7, 0.4), size=33)

    if cur > 0:                                   # outgoing phase dissolves while the next one animates in
        k = u(r, phases[cur][0], 0.18)
        if k < 1.0:
            with alpha_scale(1.0 - k):
                draw(cur - 1, r)
    draw(cur, r)


def tsar_timeline(cv, r, ts, tf, tab, tp):
    """Animated date ribbon (Russian O.S. dates) shown under the photographs."""
    y = 2650
    nodes = [(260, "23 FEB", "STRIKES BEGIN", 0.0), (820, "27 FEB", "TROOPS MUTINY", ts + 0.1),
             (1380, "2 MAR", "TSAR ABDICATES", tab - 0.05), (1900, "2 MAR", "PROV. GOVERNMENT", tp + 0.15)]
    line(cv, (260, y), (1900, y), (110, 112, 114), 4)
    prog = [n[3] for n in nodes]
    last_x = 260
    for i, (x, d, txt, tt) in enumerate(nodes):
        if r >= tt:
            nxt = nodes[i + 1][3] if i + 1 < len(nodes) else tt + 0.6
            frac = clamp((r - tt) / max(min(nxt - tt, 1.0), 0.4))
            x2 = x + (nodes[i + 1][0] - x) * out_cubic(frac) if i + 1 < len(nodes) and r >= tt else x
            line(cv, (x, y), (x2, y), RED_HI, 9)
    for x, d, txt, tt in nodes:
        a = u(r, tt, 0.35)
        on = r >= tt
        circle(cv, x, y, 24 if on else 14, RED_HI if on else (110, 112, 114))
        if a > 0:
            label(cv, d, x, y - 80, "mono", 50, PAPER, 5, alpha=a)
            label(cv, txt, x, y + 78, "mono", 30, PAPER_DIM, 3, alpha=a)


# ============================================================ 3 LENIN'S OPPORTUNITY
def lenin(cv, t):
    t0, t1 = T.SCENE["lenin"]
    r = t - t0
    tl = T.word("lenin", "lenin's") - t0 - 0.2
    tw = T.word("lenin", "workers") - t0 - 0.25
    tp, tn, tb = (T.word("lenin", w) - t0 for w in ("peace", "land", "bread"))
    war = pick("july_days", "wwi_soldiers_1917")
    plates = ["wwi_plate", "may_day_square", "laborers_deputation"]
    names = [war, "may_day_square", "laborers_deputation"]
    cur = 0 if r < tl else 1 if r < tw else 2
    bounds = [0.0, tl, tw]
    pa = plate(names[cur], 0.34 if cur == 0 else 0.28)
    if cur > 0:
        k = smooth(u(r, bounds[cur], 0.5))
        cv[:] = cv2.addWeighted(plate(names[cur - 1], 0.34 if cur - 1 == 0 else 0.28), 1 - k, pa, k, 0)
    else:
        cv[:] = pa

    def draw(i, r):
        if i == 0:                                                   # "It kept fighting the war."
            c = photo(war, 1840)
            blit(cv, c, DW / 2, 1500 - 30 * (1 - out_cubic(u(r, 0, 0.6))), scale=1 + 0.04 * smooth(r / max(tl, .1)), rot=-0.8, alpha=u(r, 0, 0.3))
            tag(cv, "THE WAR GOES ON", DW / 2, 620, p=u(r, 0.15, 0.45), size=64)
            if war == "july_days":
                credit(cv, "Petrograd, 4 July 1917 (O.S.): government troops have just opened fire · Wikimedia Commons", DW / 2, 2210,
                       alpha=u(r, 0.5, 0.4), size=34)
            else:
                credit(cv, "Russian soldiers, 1917 · Library of Congress, World Digital Library", DW / 2, 2210, alpha=u(r, 0.5, 0.4), size=34)
        elif i == 1:
            q = r - tl
            label(cv, "LENIN'S BOLSHEVIKS PROMISE", DW / 2, 520, "mono", 54, PAPER_DIM, 6, alpha=u(q, 0.12, 0.4))
            # portrait while the narrator names Lenin; it dissolves as the three promises slam in
            lf = (1 - u(r, tp - 0.20, 0.18)) * u(q, 0.0, 0.3)
            if lf > 0:
                port = photo("lenin_a_1920", 1560, border=30)
                blit(cv, port, DW / 2, 1500 + (1 - out_cubic(u(q, 0.0, 0.55))) * 260, rot=-1.4, scale=1 + 0.035 * smooth(q / 1.8), alpha=lf)
                tag(cv, "V. I. LENIN", 330, 830, p=u(q, 0.15, 0.4) * (1 - u(r, tp - 0.20, 0.18)), anchor=(0, 0.5), size=56)
                credit(cv, "Lenin at his desk · Bain News Service, published 1920 · Library of Congress", DW / 2, 2150, alpha=lf, size=34)
            slots = [  # word, cue, image, caption, card side
                ("PEACE", tp, "np_seattle_column", "The Seattle Star, 8 Nov 1917 · Library of Congress", "L"),
                ("LAND", tn, "may_day_square", "Palace Square, Petrograd, 18 Apr 1917 (O.S.): banner 'Land and Freedom'", "R"),
                ("BREAD", tb, "bread_queue", "Bread queue, Petrograd, early 1917", "L"),
            ]
            ys = (1000, 1560, 2120)
            for (word, tt, img, cap, side), y in zip(slots, ys):
                pp = u(r, tt - 0.04, 0.26)
                if pp <= 0:
                    continue
                cx_card, cx_word = (610, 1560) if side == "L" else (1550, 610)
                card = photo(img, 800 if img != "np_seattle_column" else 700, border=24)
                slide = (1 - out_cubic(pp)) * (-700 if side == "L" else 700)
                blit(cv, card, cx_card + slide, y, rot=-2.5 if side == "L" else 2.5, alpha=min(1.0, pp * 4))
                tile = text_tile(word, "black", 230, PAPER, shadow=20)
                blit(cv, tile, cx_word, y - 20, scale=1 + 0.6 * (1 - out_expo(pp)), alpha=min(1.0, pp * 5))
                bw = tile.shape[1] / K * 0.92 * out_cubic(u(r, tt, 0.3))
                line(cv, (cx_word - bw / 2, y + 120), (cx_word + bw / 2, y + 120), RED_HI, 12)
                credit(cv, cap, cx_card, y + 330 if img != "np_seattle_column" else y + 410, alpha=u(r, tt + 0.2, 0.4), size=28)
        else:
            q = r - tw
            label(cv, "PEACE  ·  LAND  ·  BREAD", DW / 2, 600, "black", 108, RED_HI, 6, alpha=u(q, 0.12, 0.3), shadow=16)
            c = photo("laborers_deputation", 1780)
            blit(cv, c, DW / 2, 1560 + (1 - out_cubic(u(q, 0.05, 0.6))) * 500, rot=-1.2, scale=1 + 0.03 * smooth(q / 2.0), alpha=u(q, 0.05, 0.3))
            tag(cv, "WORKERS AND SOLDIERS · PETROGRAD 1917", DW / 2, 2200, p=u(q, 0.5, 0.5), size=48)
            credit(cv, "Labour demonstration, Palace Square, Petrograd, 1 May 1917 (O.S.) · Library of Congress", DW / 2, 2300, alpha=u(q, 0.8, 0.4), size=34)

    if cur > 0:
        k = u(r, bounds[cur], 0.18)
        if k < 1.0:
            with alpha_scale(1.0 - k):
                draw(cur - 1, r)
    draw(cur, r)


# ============================================================ geography helpers for the war scenes
def km(lon, lat):
    x, y = mapdata.project(lon, lat)
    return (float(x), float(y))


def path_km(pts):
    return [km(*p) for p in pts]


WAR_CX, WAR_CY, WAR_PPK, WAR_SY = -250.0, 1250.0, 0.38, 1760
ARROWS = {   # approximate axes of the main White offensives of 1919 (simplified)
    "DENIKIN": path_km([(39.7, 47.2), (38.2, 49.0), (36.6, 50.8), (36.1, 52.9)]),
    "KOLCHAK": path_km([(73.4, 55.0), (66.0, 55.4), (60.5, 55.2), (55.5, 55.0)]),
    "YUDENICH": path_km([(27.6, 58.8), (29.0, 59.3), (30.1, 59.56)]),
}
LABEL_AT = {"DENIKIN": (km(40.5, 46.0), (1, 0)), "KOLCHAK": (km(74.5, 57.2), (0.5, 0)), "YUDENICH": (km(24.0, 60.8), (0.5, 1))}


def war_view(zoom=1.0):
    ppk = FULL_PPK + (WAR_PPK - FULL_PPK) * zoom
    cx = FULL_CX + (WAR_CX - FULL_CX) * zoom
    cy = FULL_CY + (WAR_CY - FULL_CY) * zoom
    return MapView(cx, cy, ppk, DW / 2, lerp(1650, WAR_SY, zoom))


def map_with_phase(cv, view, phase, dim=1.0, discs=None):
    draw_base_map(cv, view, dim=dim)
    if discs is not None:
        red_discs(cv, view, *discs)
    else:
        draw_red(cv, view, phase)


# ============================================================ 5 CIVIL WAR
def civil_war(cv, t):
    t0, t1 = T.SCENE["civil_war"]
    r = t - t0
    zoom = in_out_cubic(seg(r, 0.0, 1.6))
    view = war_view(zoom)
    ph = in_out_cubic(seg(r, 2.9, 6.4))
    map_with_phase(cv, view, ph)
    marker(cv, view, PET, t, r=13, ring_color=RED_HI)
    marker(cv, view, MOS, t, r=13, pulse=False)
    label(cv, "PETROGRAD", *[v for v in view.pt(*PET)], "mono", 38, PAPER, 4, anchor=(1.15, 1.8), alpha=0.9)
    label(cv, "MOSCOW", view.pt(*MOS)[0] + 28, view.pt(*MOS)[1] + 4, "mono", 38, PAPER, 4, anchor=(0, 0.5), alpha=0.9)
    a = out_cubic(u(r, 0.9, 0.5)) * (1 - u(r, 3.1, 0.4))
    label(cv, "CAPTURING THE CAPITAL", DW / 2, 560, "black", 104, PAPER, 2, alpha=a, shadow=18)
    label(cv, "≠ CONTROLLING THE COUNTRY", DW / 2, 700, "black", 104, RED_HI, 2, alpha=u(r, 1.15, 0.5) * (1 - u(r, 3.1, 0.4)), shadow=18)
    tc = T.word("civil_war", "civil") - t0
    for i, (name, pts) in enumerate(ARROWS.items()):
        p = out_cubic(u(r, tc + 0.15 + 0.25 * i, 1.1))
        if p > 0:
            arrow_km(cv, pts, view, PAPER, 9, progress=p)
            if p > 0.5:
                (pos, anc) = LABEL_AT[name]
                x, y = view.pt(*pos)
                label(cv, name, x, y, "mono", 40, PAPER, 5, anchor=anc, alpha=smooth((p - 0.5) * 2))
    tr = T.word("civil_war", "reds") - t0
    tw = T.word("civil_war", "whites") - t0
    if r > tr - 0.1:
        s = 1 + 0.5 * (1 - out_expo(u(r, tr - 0.1, 0.25)))
        label(cv, "RED ARMY", DW / 2 - 430, 2480, "black", 104, RED_HI, 4, alpha=min(1, u(r, tr - 0.1, 0.1) * 5), scale=s, shadow=20)
    if r > tw - 0.1:
        s = 1 + 0.5 * (1 - out_expo(u(r, tw - 0.1, 0.25)))
        label(cv, "WHITE ARMIES", DW / 2 + 400, 2480, "black", 104, PAPER, 4, alpha=min(1, u(r, tw - 0.1, 0.1) * 5), scale=s, shadow=20)
    # archival photographs, one for each side (American Red Cross, 1919)
    c1 = photo("arc_bolshevik_prisoners_omsk", 880)
    blit(cv, c1, 640 - (1 - out_cubic(u(r, tr - 0.2, 0.6))) * 900, 830, rot=-4.0, alpha=u(r, tr - 0.2, 0.2), scale=1 + 0.02 * r / 6)
    credit(cv, "Bolshevik prisoners captured by Kolchak's troops, Omsk, 1919 · American Red Cross, Library of Congress", 640, 1215,
           alpha=u(r, tr + 0.2, 0.4), size=28, rot=-3)
    c2 = photo("arc_denikin_cavalry", 880)
    blit(cv, c2, 1540 + (1 - out_cubic(u(r, tw - 0.2, 0.6))) * 900, 830, rot=3.5, alpha=u(r, tw - 0.2, 0.2), scale=1 + 0.02 * r / 6)
    credit(cv, "Volunteer Army cavalry, Kharkov, 1919 · American Red Cross, Library of Congress", 1540, 1215,
           alpha=u(r, tw + 0.2, 0.4), size=28, rot=3)
    label(cv, "FRONT LINES: APPROXIMATE, SIMPLIFIED", DW / 2, 3120, "mono", 30, PAPER_DIM, 4, alpha=0.8)


# ============================================================ 6 CONSOLIDATION
CITIES = {"PETROGRAD": (30.31, 59.93), "KYIV": (30.52, 50.45), "KHARKIV": (36.23, 49.99), "TIFLIS": (44.8, 41.7), "BAKU": (49.87, 40.41),
          "TASHKENT": (69.24, 41.3), "OMSK": (73.37, 54.99), "IRKUTSK": (104.3, 52.3), "VLADIVOSTOK": (131.9, 43.12)}


def consolidation(cv, t):
    t0, t1 = T.SCENE["consolidation"]
    r = t - t0
    # camera eases back out toward the whole-empire view
    zoom = 1.0 - 0.55 * in_out_cubic(seg(r, 2.0, 5.5))
    view = war_view(zoom)
    keys = [(0.0, 1.0), (0.45, 1.0), (1.05, 2.0), (1.55, 3.0), (1.95, 3.0), (3.2, 4.0)]
    ph = 4.0
    for (ta, pa), (tb, pb) in zip(keys, keys[1:]):
        if ta <= r < tb:
            ph = lerp(pa, pb, smooth((r - ta) / (tb - ta))); break
    if r < keys[0][0]:
        ph = 1.0
    map_with_phase(cv, view, ph)
    # year ticker
    yr = [(0.0, "1918"), (0.45, "1919"), (1.05, "1920"), (1.55, "1921"), (1.95, "1922")]
    cur, idx = "1918", 0
    for i, (tt, y) in enumerate(yr):
        if r >= tt:
            cur, idx = y, i
    tt = yr[idx][0]
    pop = 1 + 0.25 * (1 - out_expo(u(r, tt, 0.18)))
    label(cv, cur, DW / 2, 640, "black", 320, PAPER if cur != "1922" else RED_HI, 4, scale=pop, shadow=26)
    label(cv, "CIVIL WAR · POLITICAL CENTRALISATION", DW / 2, 860, "mono", 40, PAPER_DIM, 5, alpha=u(r, 0.3, 0.5))
    # centralisation web from Moscow
    tcent = T.word("consolidation", "centralised") - t0 - 0.2
    mx, my = view.pt(*MOS)
    for i, (name, (lon, lat)) in enumerate(CITIES.items()):
        pp = out_cubic(u(r, tcent + 0.08 * i, 0.8))
        if pp <= 0:
            continue
        cx_, cy_ = view.pt(*km(lon, lat))
        ex, ey = lerp(mx, cx_, pp), lerp(my, cy_, pp)
        line(cv, (mx, my), (ex, ey), PAPER, 3.5, alpha=0.9)
        if pp >= 1.0:
            circle(cv, cx_, cy_, 11, PAPER)
    if r > tcent:
        a = u(r, tcent + 0.5, 0.5)
        circle(cv, mx, my, 26, PAPER); circle(cv, mx, my, 15, RED_HI)
        label(cv, "MOSCOW · CAPITAL SINCE MARCH 1918", DW / 2, 2480, "mono", 42, PAPER, 5, alpha=a)
    tw = T.word("consolidation", "won") - t0
    if r > tw - 0.15:
        s = 1 + 0.5 * (1 - out_expo(u(r, tw - 0.15, 0.25)))
        label(cv, "USSR FOUNDED · 30 DEC 1922", DW / 2, 2330, "black", 92, PAPER, 3, alpha=min(1, u(r, tw - 0.15, 0.1) * 5), scale=s, shadow=18)
    tw_ = T.word("consolidation", "war") - t0 - 0.1
    if tw_ < r < tcent + 1.6:
        pp = u(r, tw_, 0.5) * (1 - u(r, tcent + 1.1, 0.5))
        c = photo("arc_south_russia_war", 700)
        blit(cv, c, 470 - (1 - out_cubic(u(r, tw_, 0.5))) * 700, 1060, rot=-3.5, alpha=pp)
        credit(cv, "Volunteer Army skirmish line, South Russia, 1919 · American Red Cross, LoC", 470, 1390, alpha=pp, size=26, rot=-3)
    label(cv, "FRONT LINES: APPROXIMATE, SIMPLIFIED", DW / 2, 3120, "mono", 30, PAPER_DIM, 4, alpha=0.8)


# ============================================================ 7 ENDING
def end(cv, t):
    t0, t1 = T.SCENE["end"]
    r = t - t0
    dur = t1 - t0
    # same wide camera as the opening; closes with the opening zoom into Petrograd
    zin = in_expo(seg(r, dur - 1.0, dur))
    ppk = FULL_PPK * (1.0 + 0.05 * smooth(r / dur)) * (1.15 / FULL_PPK) ** zin
    p0 = (DW / 2 + (PET[0] - FULL_CX) * FULL_PPK, 1650 - (PET[1] - FULL_CY) * FULL_PPK)
    sp = (lerp(p0[0], DW / 2, zin), lerp(p0[1], 1650, zin))
    view = view_lock(PET, ppk, sp, DW / 2, 1650) if zin > 0 else MapView(FULL_CX, FULL_CY, ppk, DW / 2, 1650)
    draw_base_map(cv, view)
    graticule(cv, view)
    draw_red(cv, view, 4.0)
    marker(cv, view, PET, t, r=15, ring_color=RED_HI)
    a1 = T.word("end", "capital") - t0 - 0.05
    a2 = T.word("end", "consolidating") - t0 - 0.05
    for (txt, col, y, size, tt) in (("THE CAPITAL FELL", PAPER, 2380, 170, a1), ("IN HOURS.", PAPER, 2580, 170, a1 + 0.10),
                                    ("CONSOLIDATING POWER", RED_HI, 2900, 150, a2), ("TOOK YEARS.", RED_HI, 3070, 150, a2 + 0.10)):
        pp = u(r, tt, 0.30)
        if pp <= 0:
            continue
        size = min(size, fit_size(txt, "black", 1900))
        tile = text_tile(txt, "black", size, col, shadow=24)
        blit(cv, tile, DW / 2, y, scale=1 + 0.5 * (1 - out_expo(pp)), alpha=min(1.0, pp * 5))
    fade = 1 - in_cubic(seg(r, dur - 0.55, dur))
    cv[:] = (cv.astype(np.float32) * fade).astype(np.uint8)


# ============================================================ 4 THE OCTOBER REVOLUTION
PINS = json.loads((ROOT / "assets/petrograd_pins.json").read_text())["pins_native_px"]


@lru_cache(maxsize=1)
def baedeker_plate():
    """Baedeker's 1914 plan of St Petersburg, darkened and slightly desaturated for use as a stage."""
    USED.add("baedeker_plan_i_1914")
    key = CACHE / f"baedeker_plate_v2_{int(K*1000)}.npy"
    if key.exists():
        return np.load(key)
    im = cv2.imread(str(asset("baedeker_plan_i_1914")))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= 0.92
    hsv[..., 2] *= 0.92
    im = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    im = cv2.addWeighted(im, 1.25, cv2.GaussianBlur(im, (0, 0), 2.2), -0.25, 0)      # gentle sharpen
    s = max(K * 1.45, 0.05)                                                         # plate resolution reserve (design zoom up to ~1.45)
    im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    np.save(key, im)
    return im


PLATE_RES = None


@lru_cache(maxsize=1)
def october_shade():
    """Darkening gradient: heavy at top and bottom where text sits."""
    y = np.linspace(0, 1, H, dtype=np.float32)
    top = np.clip(1 - (y * DH - 0) / 900.0, 0, 1) ** 1.8
    bot = np.clip((y * DH - 2600) / 500.0, 0, 1) ** 1.2
    m = 1.0 - 0.86 * np.maximum(top, bot)
    return cv2.cvtColor(np.repeat((m * 255).astype(np.uint8)[:, None], W, axis=1), cv2.COLOR_GRAY2BGR)


PIN_SPEC = [  # key, label, side (label placement), dx, dy
    ("nikolaevsky_station", "NIKOLAEVSKY STATION", "R", 48, 8),
    ("palace_bridge", "PALACE BRIDGE", "R", 56, -200),
    ("post_telegraph", "POST & TELEGRAPH", "R", 40, 88),
    ("state_bank", "STATE BANK", "R", 56, -48),
    ("baltic_station", "BALTIC STATION", "R", 48, 8),
]


def october(cv, t):
    t0, t1 = T.SCENE["october"]
    r = t - t0
    plate = baedeker_plate()
    z = lerp(1.14, 1.38, in_out_cubic(seg(r, 0.0, 4.6))) + 0.06 * smooth(seg(r, 4.6, 11.4))
    cx, cy = lerp(1830, 1912, in_out_cubic(seg(r, 0.0, 4.6))), lerp(1620, 1607, in_out_cubic(seg(r, 0.0, 4.6)))
    sx, sy = DW / 2, 1700
    pk = z * K
    s = max(K * 1.45, 0.05)
    # warp: design map-px -> screen px; plate was resized by s
    Mw = np.float32([[pk / s, 0, sx * K - pk * cx], [0, pk / s, sy * K - pk * cy]])
    cv[:] = cv2.warpAffine(plate, Mw, (W, H), flags=cv2.INTER_AREA if pk / s < 0.8 else cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=INK)
    cv[:] = cv2.multiply(cv, october_shade(), scale=1 / 255.0)

    def to_screen(p):
        return (sx + (p[0] - cx) * z, sy + (p[1] - cy) * z)

    # ---- date block: 25 October first, then the Gregorian equivalent
    tn = T.word("october", "november") - t0
    big = 1 - u(r, 3.0, 0.5)
    if big > 0:
        label(cv, "25 OCTOBER 1917", DW / 2, 640, "black", 200, PAPER, 4, alpha=u(r, 0.0, 0.3) * big, scale=1 + 0.35 * (1 - out_expo(u(r, 0.0, 0.3))), shadow=24)
        label(cv, "OLD STYLE · THE RUSSIAN CALENDAR OF THE DAY", DW / 2, 820, "mono", 46, PAPER_DIM, 5, alpha=u(r, 0.5, 0.4) * big)
    small = u(r, 3.1, 0.5) * (1 - u(r, tn - 0.15, 0.25))
    if small > 0:
        label(cv, "25 OCTOBER 1917 (O.S.)", DW / 2, 520, "black", 104, PAPER, 3, alpha=small, shadow=16)
        label(cv, "PETROGRAD · THE SEIZURE BEGINS", DW / 2, 630, "mono", 44, PAPER_DIM, 5, alpha=small)
    if r > tn - 0.1:
        q = r - (tn - 0.1)
        s_ = 1 + 0.45 * (1 - out_expo(u(q, 0, 0.3)))
        label(cv, "= 7 NOVEMBER 1917", DW / 2, 540, "black", 128, RED_HI, 3, alpha=min(1, u(q, 0, 0.1) * 5), scale=s_, shadow=20)
        label(cv, "GREGORIAN CALENDAR · +13 DAYS", DW / 2, 672, "mono", 46, PAPER_DIM, 5, alpha=u(q, 0.35, 0.4))

    # ---- pins: the key points seized
    for i, (key, text, side, dx, dy) in enumerate(PIN_SPEC):
        tt = T.OCT_PINS[i] - t0
        p = u(r, tt, 0.3)
        if p <= 0:
            continue
        x, y = to_screen(PINS[key])
        for k in range(2):
            ph = clamp((r - tt) * 0.9 + k * 0.5, 0, 99) % 1.0
            circle(cv, x, y, 22 + ph * 70, RED_HI, 3, alpha=max(0.0, 0.7 * (1 - ph)) * min(1.0, (r - tt) * 3))
        circle(cv, x, y, 25, INK)
        circle(cv, x, y, 18 * (0.6 + 0.4 * out_back(p)), RED_HI)
        circle(cv, x, y, 18 * (0.6 + 0.4 * out_back(p)), PAPER, 3)
        line(cv, (x, y), (x + dx, y + dy), PAPER, 3.5, alpha=0.8 * u(r, tt, 0.25))
        tag(cv, text, x + dx, y + dy, p=u(r, tt + 0.05, 0.3), size=50, track=3,
            anchor=(0, 0.5) if side == "R" else (1, 0.5), bg=(24, 22, 20), fg=PAPER)
    # ---- the Winter Palace falls
    tp = T.OCT_PALACE - t0
    if r > tp - 0.05:
        q = r - (tp - 0.05)
        x, y = to_screen(PINS["winter_palace"])
        for k in range(3):
            ph = (q * 0.8 + k / 3.0) % 1.0
            circle(cv, x, y, 30 + ph * 150, RED_HI, 5, alpha=0.85 * (1 - ph) * min(1.0, q * 4))
        circle(cv, x, y, 40, INK); circle(cv, x, y, 29 * (0.7 + 0.3 * out_back(u(q, 0, 0.3))), RED_HI); circle(cv, x, y, 29, PAPER, 4)
        line(cv, (x, y), (x + 150, y - 112), PAPER, 4, alpha=0.9 * u(q, 0, 0.3))
        tag(cv, "WINTER PALACE", x + 150, y - 112, p=u(q, 0.1, 0.35), size=64, track=4, anchor=(0, 0.5), bg=RED)
        tag(cv, "MINISTERS ARRESTED", x + 150, y - 36, p=u(q, 0.45, 0.35), size=44, track=3, anchor=(0, 0.5), bg=(24, 22, 20))
        tag(cv, "NIGHT OF 25–26 OCTOBER", x + 150, y + 36, p=u(q, 0.55, 0.35), size=38, track=3, anchor=(0, 0.5), bg=(24, 22, 20), fg=PAPER_DIM)
        xs, ys = to_screen(PINS["smolny"])
        ps = u(q, 0.7, 0.4)
        if ps > 0:
            circle(cv, xs, ys, 16, RED_HI); circle(cv, xs, ys, 16, PAPER, 3)
            tag(cv, "SMOLNY · BOLSHEVIK HQ", xs - 40, ys + 6, p=ps, size=46, track=3, anchor=(1, 0.5), bg=(24, 22, 20))
    # ---- a US newspaper of 8 Nov 1917 (Gregorian) announces the news
    if r > tn:
        q = r - tn
        card = photo("np_seattle_banner", 1960, border=16)
        blit(cv, card, DW / 2, 2330 + (1 - out_cubic(u(q, 0.1, 0.6))) * 500, rot=-0.8, alpha=u(q, 0.1, 0.25), scale=1 + 0.015 * q)
        credit(cv, "The Seattle Star, Thursday 8 Nov 1917 · Library of Congress, Chronicling America", DW / 2, 2600, alpha=u(q, 0.7, 0.4), size=32)
    credit(cv, "Plan of St. Petersburg, 1914 · Baedeker, Russia · via Internet Archive", DW / 2, 3120, alpha=0.8, size=28)

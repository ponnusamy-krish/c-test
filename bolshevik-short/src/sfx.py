"""Procedural sound design + final audio mix -> audio/mix.wav (48 kHz stereo, 32-bit float).

All effects are synthesised here from noise and sine components, so they carry
no third-party licence. No music. The narration stays on top: ambience and
footsteps are ducked by the voice, and one-shot hits are kept well below it.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import timeline as T

ROOT = Path(__file__).resolve().parent.parent
SR = 48000
rng = np.random.default_rng(20171107)


# ---- primitives ------------------------------------------------------------
def n_(sec):
    return int(round(sec * SR))


def noise(sec):
    return rng.standard_normal(n_(sec))


def _sos(kind, f, order=4):
    return butter(order, f, kind, fs=SR, output="sos")


def bp(x, lo, hi, order=3):
    return sosfilt(_sos("band", [lo, min(hi, SR / 2 - 100)], order), x)


def lp(x, fc, order=4):
    return sosfilt(_sos("low", fc, order), x)


def hp(x, fc, order=4):
    return sosfilt(_sos("high", fc, order), x)


def decay(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def reverb(x, rt60=1.3, wet=0.25, damp=5000):
    L = n_(rt60 * 1.1)
    ir = lp(rng.standard_normal(L), damp, 2) * np.exp(-np.arange(L) / SR * 6.9 / rt60)
    ir[: n_(0.012)] *= np.linspace(0, 1, n_(0.012))
    y = fftconvolve(x, ir)[: len(x) + L // 2]
    y /= np.abs(y).max() + 1e-9
    xx = np.pad(x, (0, len(y) - len(x)))
    return (1 - wet) * xx + wet * y * np.abs(x).max()


def norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-9) * peak


def db(g):
    return 10 ** (g / 20)


# ---- sound designs ---------------------------------------------------------
def impact(sec=2.2, heavy=1.0):
    n = n_(sec)
    t = np.arange(n) / SR
    f = 62 * np.exp(-t * 2.2) + 34
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * decay(n, 0.42)
    body = lp(noise(sec), 500) * decay(n, 0.18)
    click = hp(noise(sec), 2500) * decay(n, 0.010)
    crack = bp(noise(sec), 700, 6000) * decay(n, 0.045)
    x = heavy * 1.0 * sub + 0.9 * norm(body) + 0.55 * norm(click) + 0.6 * norm(crack)
    x = reverb(x, rt60=1.6, wet=0.30)
    return norm(x, 0.95)


def whoosh(sec=1.0, rising=True, lo=180, hi=7000):
    n = n_(sec)
    t = np.linspace(0, 1, n)
    centres = np.geomspace(lo, hi, 16)
    out = np.zeros(n)
    base = rng.standard_normal(n)
    for i, fc in enumerate(centres):
        band = bp(base, fc / 1.35, fc * 1.35, 2)
        pos = (i / (len(centres) - 1)) if rising else 1 - i / (len(centres) - 1)
        out += band * np.exp(-((t - (0.15 + 0.7 * pos)) ** 2) / (2 * 0.12 ** 2))
    env = np.sin(np.pi * t) ** 1.5
    return norm(out * env, 0.8)


def crowd(sec, voices=46):
    n = n_(sec)
    L = np.zeros(n); R = np.zeros(n)
    for _ in range(voices):
        f0 = rng.uniform(180, 420)
        v = bp(rng.standard_normal(n), f0, f0 * rng.uniform(3.0, 5.5), 2)
        rate = rng.uniform(2.5, 5.5)
        m = lp(np.abs(rng.standard_normal(n)), rate, 2)
        m = np.clip((m - m.mean()) / (m.std() + 1e-9) + 0.2, 0, None) ** 1.2
        v *= m
        pan = rng.uniform(0, 1)
        L += v * np.cos(pan * np.pi / 2); R += v * np.sin(pan * np.pi / 2)
    rum = lp(rng.standard_normal(n), 140, 2) * 0.6
    L += rum; R += rum
    st = np.vstack([L, R])
    st = np.vstack([reverb(st[0], 0.9, 0.35), reverb(st[1], 0.9, 0.35)])
    return norm(st, 0.9)


def sounder_click(pitch=1.0):
    """One telegraph-sounder 'clack': sharp metallic tick with a woody body."""
    n = n_(0.09)
    t = np.arange(n) / SR
    tick = bp(rng.standard_normal(n), 1800, 6500, 2) * decay(n, 0.004)
    ring = np.sin(2 * np.pi * 2400 * pitch * t) * decay(n, 0.010)
    body = np.sin(2 * np.pi * 820 * pitch * t) * decay(n, 0.022)
    return norm(0.8 * norm(tick) + 0.45 * ring + 0.7 * body, 0.9)


def morse(pattern, unit=0.075, pitch=1.0):
    """pattern like '.-.. ' ; returns click track (down-click at start, up-click at end of each element)."""
    total = sum((unit if c == '.' else unit * 3 if c == '-' else unit * 2) + unit for c in pattern) + 0.2
    out = np.zeros(n_(total) + n_(0.1))
    t = 0.0
    for c in pattern:
        if c in ".-":
            dur = unit if c == '.' else unit * 3
            for tt, p in ((t, 1.0 * pitch), (t + dur, 0.82 * pitch)):
                s = sounder_click(p) * (1.0 if tt == t else 0.8)
                i = n_(tt); out[i:i + len(s)] += s[: len(out) - i]
            t += dur + unit
        else:
            t += unit * 2
    return out


def boots(sec, bpm=114, ranks=7, seed=5):
    r = np.random.default_rng(seed)
    n = n_(sec)
    L = np.zeros(n + n_(0.3)); R = np.zeros_like(L)
    beat = 60.0 / bpm
    steps = int(sec / beat)
    for k in range(steps):
        for s in range(ranks):
            t = k * beat + r.normal(0, 0.016)
            if t < 0:
                continue
            m = n_(0.16)
            tt = np.arange(m) / SR
            thump = np.sin(2 * np.pi * (95 + 25 * r.random()) * tt) * decay(m, 0.035)
            gravel = bp(r.standard_normal(m), 400, 3200, 2) * decay(m, 0.045)
            heel = hp(r.standard_normal(m), 2200) * decay(m, 0.006)
            st = (0.9 * thump + 0.55 * gravel + 0.35 * heel) * r.uniform(0.35, 1.0) * (1.0 if k % 2 == 0 else 0.82)
            pan = r.uniform(0, 1)
            i = n_(t)
            L[i:i + m] += st * np.cos(pan * np.pi / 2); R[i:i + m] += st * np.sin(pan * np.pi / 2)
    st = np.vstack([L[:n + n_(0.3)], R[:n + n_(0.3)]])
    st = np.vstack([reverb(st[0], 1.1, 0.30), reverb(st[1], 1.1, 0.30)])
    return norm(st, 0.9)


def paper(sec=0.7):
    n = n_(sec)
    x = np.zeros(n)
    for _ in range(int(sec * 70)):
        i = int(rng.uniform(0, n * 0.9)); m = n_(rng.uniform(0.002, 0.01))
        x[i:i + m] += rng.standard_normal(min(m, n - i)) * rng.uniform(0.2, 1) * decay(min(m, n - i), m / SR / 3)
    soft = bp(rng.standard_normal(n), 2500, 9000, 2) * (lp(np.abs(rng.standard_normal(n)), 18, 2) * 0.8)
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.6
    return norm((hp(x, 1800, 2) * 0.9 + soft * 0.9) * env, 0.8)


def stamp():
    n = n_(0.7)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 7) + 48) / SR) * decay(n, 0.11)
    slap = bp(rng.standard_normal(n), 900, 5200, 2) * decay(n, 0.016)
    return norm(reverb(norm(thud) + 0.55 * norm(slap), 0.7, 0.18), 0.9)


def heartbeat():
    n = n_(0.5)
    t = np.arange(n) / SR
    b = np.sin(2 * np.pi * 52 * t) * decay(n, 0.09)
    return norm(b, 0.9)


# ---- mixing helpers --------------------------------------------------------
class Bus:
    def __init__(self, sec):
        self.buf = np.zeros((2, n_(sec)))

    def add(self, x, t, gain_db=0.0, pan=0.5, fade=0.0):
        x = np.asarray(x, float)
        if x.ndim == 1:
            x = np.vstack([x * np.cos(pan * np.pi / 2), x * np.sin(pan * np.pi / 2)])
        x = x * db(gain_db)
        if fade:
            f = min(n_(fade), x.shape[1] // 2)
            x[:, :f] *= np.linspace(0, 1, f); x[:, -f:] *= np.linspace(1, 0, f)
        i = n_(t)
        if i >= self.buf.shape[1]:
            return
        j = min(i + x.shape[1], self.buf.shape[1])
        self.buf[:, i:j] += x[:, : j - i]


def speech_envelope(nar, win=0.06, smooth=0.25):
    e = np.sqrt(lp(nar ** 2, 1 / win, 1) + 1e-12)
    e = lp(e, 1 / smooth, 1)
    return np.clip(e / (np.percentile(e, 95) + 1e-9), 0, 1)


def main():
    total = T.TOTAL
    nar24, sr = sf.read(ROOT / "audio/narration.wav")
    nar = np.zeros(n_(total))
    from scipy.signal import resample_poly
    n48 = resample_poly(nar24, 2, 1)
    nar[: len(n48)] = n48[: len(nar)]
    duck = 1 - 0.62 * speech_envelope(nar)            # bed gain while speaking

    bed = Bus(total)    # ambience, footsteps, telegraph chatter  (ducked)
    hits = Bus(total)   # impacts, whooshes, stamps, paper         (lightly ducked)

    S = T.SCENE
    # ---------- hook: cold-open impact + zoom whoosh + crowd flashes
    hits.add(impact(2.4), 0.0, -9)
    hits.add(whoosh(2.9, True, 160, 6500), 0.05, -17)
    hits.add(impact(1.2, 0.5), 0.92, -19)
    hits.add(impact(1.2, 0.5), 1.62, -19)
    hits.add(whoosh(1.0, False, 200, 5000), 2.45, -24)
    bed.add(crowd(T.SCENE["hook"][1] + 1.0), 0.0, -33, fade=1.2)
    for tt in (4.1, 5.9, 7.7):                          # Petrograd pulses
        hits.add(heartbeat(), tt, -22)
    # ---------- scene transitions: soft air + thud
    for k in ("crisis", "tsar", "lenin", "october", "civil_war", "consolidation"):
        t0 = S[k][0] - 0.12
        hits.add(whoosh(0.7, True, 250, 4500), t0, -27)
        hits.add(heartbeat(), S[k][0], -23)
    # ---------- crisis: murmur of queues
    bed.add(crowd(5.2, 30), S["crisis"][0] - 0.3, -35, fade=0.8)
    # ---------- tsar: paper handling + stamp on the manifesto + crowd
    ts = S["tsar"][0]
    for dt in (0.15, 2.0, 4.0, 6.4):
        hits.add(paper(0.7), ts + dt, -26, pan=rng.uniform(0.3, 0.7))
    bed.add(crowd(7.0, 40), ts + 0.2, -34, fade=1.0)
    t_ab = T.word("tsar", "abdicate")
    hits.add(stamp(), t_ab + 0.15, -17)
    # ---------- lenin: slams on peace / land / bread
    for w in ("peace", "land", "bread"):
        tw = T.word("lenin", w)
        hits.add(impact(1.0, 0.55), tw - 0.03, -20)
    bed.add(crowd(6.5, 36), S["lenin"][0], -35, fade=0.8)
    # ---------- october: telegraph chatter + a click per seized location
    to = S["october"][0]
    patterns = [".-.. ..-", "-... .-", ".--. -.", "..- -..", ".-. ---", "-.- .-.."]
    t = to + 0.6
    k = 0
    while t < S["october"][1] - 3.2:
        m = morse(patterns[k % len(patterns)], unit=0.062 + 0.01 * (k % 3), pitch=1.0 + 0.05 * (k % 2))
        bed.add(m, t, -29, pan=0.32 + 0.12 * (k % 3))
        t += len(m) / SR + rng.uniform(0.5, 1.1); k += 1
    for i, tt in enumerate(T.OCT_PINS):                       # a sounder click as each point is marked on the plan
        bed.add(morse(".-" if i % 2 else "-.", unit=0.06, pitch=1.0 + 0.04 * i), tt - 0.02, -24, pan=0.35 + 0.08 * i)
    hits.add(impact(1.4, 0.7), T.word("october", "seized") - 0.02, -17)
    hits.add(impact(1.8, 0.85), T.OCT_PALACE - 0.02, -15)
    hits.add(stamp(), T.word("october", "november") - 0.05, -18)
    # ---------- civil war: marching column
    tc = S["civil_war"][0]
    bed.add(boots(S["consolidation"][0] + 2.2 - tc, 114), tc + 0.2, -31, fade=0.6)
    hits.add(impact(1.6, 0.8), T.word("civil_war", "civil") - 0.02, -16)
    hits.add(paper(0.5), T.word("civil_war", "reds") - 0.1, -30)
    # ---------- consolidation
    hits.add(stamp(), T.word("consolidation", "1922") + 0.2, -18)
    # ---------- ending
    hits.add(impact(2.4, 1.0), T.word("end", "capital") - 0.03, -12)
    hits.add(impact(3.0, 1.0), T.word("end", "consolidating") - 0.03, -10)
    hits.add(whoosh(1.6, False, 150, 3500), total - 1.7, -24)

    mix_bed = bed.buf * duck[None, :] * 1.0
    hduck = 1 - 0.30 * speech_envelope(nar)
    mix_hits = hits.buf * hduck[None, :]
    narr = np.vstack([nar, nar])
    mix = narr * db(0.0) + mix_bed + mix_hits
    # gentle bus limiter (soft clip above -3 dBFS) then export
    ceil = db(-3)
    mix = np.where(np.abs(mix) > ceil, np.sign(mix) * (ceil + (1 - ceil) * np.tanh((np.abs(mix) - ceil) / (1 - ceil))), mix)
    sf.write(ROOT / "audio/mix_raw.wav", mix.T.astype(np.float32), SR, subtype="FLOAT")
    sf.write(ROOT / "audio/sfx_only.wav", ((mix_bed + mix_hits).T).astype(np.float32), SR, subtype="FLOAT")
    print("mix_raw peak %.3f dBFS  | sfx peak %.3f dBFS" % (
        20 * np.log10(np.abs(mix).max()), 20 * np.log10(np.abs(mix_bed + mix_hits).max())))
    # loudness-normalise to -14 LUFS integrated, true peak <= -1.5 dBTP (two-pass, linear)
    import json, re
    out = ROOT / "audio/mix.wav"
    src = str(ROOT / "audio/mix_raw.wav")
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af",
                         "loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1.stderr, re.S).group(0))
    af = ("loudnorm=I=-14:TP=-1.5:LRA=7:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
          % (m["input_i"], m["input_tp"], m["input_lra"], m["input_thresh"], m["target_offset"]))
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-af", af,
                    "-ar", "48000", "-c:a", "pcm_s24le", str(out)], check=True)
    print("pass-1 measurement: I=%s LUFS  TP=%s dBTP  LRA=%s" % (m["input_i"], m["input_tp"], m["input_lra"]))


if __name__ == "__main__":
    main()

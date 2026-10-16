"""v4 sound design. Rules (sources in ../ENGAGEMENT.md, v4 section):

- One family of soft mallet tones in the music's key (A minor / C major), so effects belong to the music.
  Sine plus a little 2nd harmonic, base pitches 300-1,500 Hz, attacks of 6-30 ms (no clicks), never a noise burst.
- Every effect goes through the same gentle tone shaping: about -6 dB above 4 kHz (the band where hearing is most
  sensitive and where unpleasant sounds concentrate, Kumar et al. 2012) and nothing above 9 kHz.
- Each effect is placed relative to the music at that moment: +3 to +5 dB for ordinary events, +6/+7 for the two
  reveals, a little under the music for cuts and clicks. One effect per visual event; nothing within 150 ms.
- Progress is heard: the four "what we do differently" steps rise C-D-E-G; the brief's checklist climbs a scale.
- Silence before a reveal: each riser stops 0.45 s before it lands; the music is ducked for that gap.
- Music: instrumental, 96 bpm, warm (no hi-hats, claps or noise), rolled off above about 4 kHz.
- Master (run4.sh): -16 LUFS integrated, true peak -1.5 dBTP, small loudness range.

    python audio4.py   -> audio4.wav
"""
import json, os, wave
import numpy as np
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
TL = json.load(open(os.path.join(HERE, "timeline4_out.json")))
FPS, FR, EV = TL["fps"], TL["frames"], TL["events"]
TOTAL = FR / FPS
n = int(TOTAL * SR) + SR
rng = np.random.default_rng(4)
tt = lambda N: np.arange(N) / SR
midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
db = lambda x: 10 ** (x / 20)


def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR); return lfilter([1 - a], [1, -a], x).astype(np.float32)
def lp2(x, cut): return lowpass(lowpass(x, cut), cut)
def highpass(x, cut): return (x - lowpass(x, cut)).astype(np.float32)
def shelf(x, f=4000, g=-6.0):
    """High shelf: everything above f lowered by g dB (a gentle, fixed tone shaping)."""
    return (x - (1 - db(g)) * highpass(x, f)).astype(np.float32)
def env(N, a, r, s=1.0):
    e = np.ones(N, np.float32) * s; A = max(1, int(a * SR)); R = max(1, int(r * SR))
    e[:A] = np.linspace(0, s, A); e[-R:] *= np.linspace(1, 0, R); return e
def add(buf, t, sig, pan=0.0, gain=1.0):
    i = int(t * SR)
    if i < 0: sig = sig[-i:]; i = 0
    j = min(len(buf), i + len(sig))
    if j <= i or i < 0: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[:j - i] * l * gain; buf[i:j, 1] += sig[:j - i] * r * gain

# ------------------------------------------------------------------ music: same chords as before, warmer and steadier
BPM = 96; beat = 60 / BPM; bar = 4 * beat
CH = [(57, [57, 60, 64, 67]), (53, [53, 57, 60, 64]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67])]   # Am F C G
L = {k: np.zeros((n, 2), np.float32) for k in ("pad", "bass", "pluck", "kick", "lift")}
end_ev = [e for e in EV if e.get("mus") == "resolve"]
music_end = end_ev[0]["f"] / FPS if end_ev else TOTAL

def pluck(m, d=1.0, a=0.012, decay=4.0):
    N = int(d * SR); x = tt(N); f = midi(m)
    s = (np.sin(2 * np.pi * f * x) + 0.28 * np.sin(4 * np.pi * f * x) + 0.06 * np.sin(6 * np.pi * f * x)) * np.exp(-x * decay)
    A = int(a * SR); s[:A] *= np.linspace(0, 1, A); return s.astype(np.float32)

# v4.1: the bar grid is placed so the twist (the peak) lands on a downbeat; every level change snaps to a beat
_pk = [e["f"] / FPS for e in EV if e.get("sfx") == "impact_big"]
GRID0 = ((_pk[0] % bar) - bar) if _pk else 0.0
snap = lambda t: GRID0 + round((t - GRID0) / beat) * beat
t, k = GRID0, 0
while t < music_end:
    root, voice = CH[k % 4]; d = 2 * bar; N = int((d + 1.5) * SR); x = tt(N)
    pad = sum(np.sin(2 * np.pi * midi(m) * (1 + det / 1000) * x) for m in voice for det in (-0.6, 0.6)).astype(np.float32)
    add(L["pad"], t, pad * env(N, 1.2, 1.6) / 12)
    add(L["bass"], t, (np.sin(2 * np.pi * midi(root - 12) * x) + 0.45 * np.sin(4 * np.pi * midi(root - 12) * x) + 0.15 * np.sin(6 * np.pi * midi(root - 12) * x)).astype(np.float32) * env(N, 0.05, 1.2) / 9)
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    for b8 in range(16):
        add(L["pluck"], t + b8 * beat / 2, pluck(voice[pat[b8 % 8]] + 12, 1.1, 0.015, 4.5), 0.22 if b8 % 2 else -0.22, 0.075)
    for bt in range(8):
        if bt % 2 == 0:
            Nk = int(0.3 * SR); xk = tt(Nk); fk = 52 + 40 * np.exp(-xk * 28)
            kk = np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-xk * 10) + 0.3 * np.sin(2 * np.pi * 120 * xk) * np.exp(-xk * 25)
            kk[:120] *= np.linspace(0, 1, 120)
            add(L["kick"], t + bt * beat, kk.astype(np.float32), 0, 0.11)
    for b8 in range(0, 16, 2):                                         # lift: the line an octave up, on the off-beats
        add(L["lift"], t + b8 * beat / 2 + beat / 2, pluck(voice[pat[(b8 + 3) % 8]] + 24, 0.7, 0.02, 6.0), 0.35, 0.022)
    t += d; k += 1
for kk in L:
    for c in (0, 1): L[kk][:, c] = lp2(shelf(L[kk][:, c], 3500, -6), 7000)

if end_ev:                                                            # the resolve: C major, root low, long and soft
    N = int(9 * SR); x = tt(N)
    chord = sum(np.sin(2 * np.pi * midi(m) * x) * (0.6 if m < 50 else 1) for m in (36, 48, 55, 60, 64, 67, 72)).astype(np.float32)
    add(L["pad"], music_end, chord * env(N, 0.12, 6.5) / 13)

LEVELS = {0: dict(pad=0, bass=0, pluck=0, kick=0, lift=0), 0.4: dict(pad=.55, bass=.3, pluck=0, kick=0, lift=0),
          1: dict(pad=.9, bass=.8, pluck=.6, kick=0, lift=0), 2: dict(pad=.9, bass=.9, pluck=1, kick=.8, lift=0),
          3: dict(pad=1, bass=1, pluck=1, kick=1, lift=1)}
# Layer changes (v4.1): a layer coming in rises over one bar while its low-pass opens (dark -> bright); a layer going out
# falls over two beats; raised-cosine curves, never a jump. The "drop" keeps a soft pad, so the music never goes silent.
LEVELS["drop"] = dict(pad=.55, bass=.35, pluck=.2, kick=0, lift=0)
LEVELS["resolve"] = dict(pad=1, bass=0, pluck=0, kick=0, lift=0)
cuts = sorted([(max(0.0, snap(e["f"] / FPS)), e["mus"]) for e in EV if "mus" in e], key=lambda x: x[0])
gain = {}
for kk in L:
    gk = np.zeros(n, np.float32); cur = 0.0; pos = 0
    for t0, m in cuts:
        i0 = min(n, int(t0 * SR)); gk[pos:i0] = cur
        tgt = LEVELS[m][kk]
        R = int((bar if tgt > cur else 2 * beat) * SR); r = min(R, n - i0)
        u = np.arange(r) / max(1, R); shape = 0.5 - 0.5 * np.cos(np.pi * u)
        gk[i0:i0 + r] = cur + (tgt - cur) * shape; cur = tgt; pos = i0 + r
    gk[pos:] = cur; gain[kk] = gk
TOP = {kk: max(LEVELS[l][kk] for l in LEVELS) or 1.0 for kk in L}
mus = np.zeros((n, 2), np.float32)
for kk in L:
    o = np.clip(gain[kk] / TOP[kk], 0, 1) ** 0.6                    # openness follows the layer's level
    dark = np.stack([lp2(L[kk][:, 0], 700), lp2(L[kk][:, 1], 700)], 1)
    mus += (L[kk] * o[:, None] + dark * (1 - o[:, None])) * gain[kk][:, None]

# before each landing the music dips 3 dB over one beat and comes back over one bar (no hole, no jump)
duck = np.ones(n, np.float32)
for e in EV:
    if "rise" in e:
        land = (e["f"] + e["rise"]) / FPS
        a, b_, c_ = int((land - beat) * SR), int(land * SR), int((land + bar) * SR)
        if a > 0 and c_ < n:
            u = np.linspace(0, 1, b_ - a); duck[a:b_] = np.minimum(duck[a:b_], 1 - (1 - db(-3)) * (0.5 - 0.5 * np.cos(np.pi * u)))
            u = np.linspace(0, 1, c_ - b_); duck[b_:c_] = np.minimum(duck[b_:c_], db(-3) + (1 - db(-3)) * (0.5 - 0.5 * np.cos(np.pi * u)))
mus *= duck[:, None]

# the music's own level, moment by moment (RMS in 400 ms windows), for placing each effect relative to it
def level_db(x, t, w=0.4):
    i = int(t * SR); a, b_ = max(0, i - int(w * SR / 2)), min(len(x), i + int(w * SR / 2))
    v = np.sqrt((x[a:b_] ** 2).mean() + 1e-12); return 20 * np.log10(v)
BED_REF = 20 * np.log10(np.sqrt((mus[int(5 * SR):int(min(TOTAL, 60) * SR)] ** 2).mean()) + 1e-12)   # typical bed level

# ------------------------------------------------------------------ the effect family
def mallet(ms, d=0.6, a=0.008, decay=6.0, h2=0.22):
    N = int(d * SR); x = tt(N); s = np.zeros(N, np.float32)
    for m in ms:
        f = midi(m); s += (np.sin(2 * np.pi * f * x) + (h2 if f < 700 else h2 * 0.5) * np.sin(4 * np.pi * f * x)) * np.exp(-x * decay)
    A = max(1, int(a * SR)); s[:A] *= np.linspace(0, 1, A); return (s / len(ms)).astype(np.float32)
def thump(f0=72, d=0.7):
    N = int(d * SR); x = tt(N); f = f0 * (0.7 + 0.3 * np.exp(-x * 9))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 5) + 0.25 * np.sin(2 * np.pi * 2 * np.cumsum(f) / SR) * np.exp(-x * 9)
    A = int(0.015 * SR); s[:A] *= np.linspace(0, 1, A); return s.astype(np.float32)
def swell(d=0.45):
    """A soft air movement for a cut: low-passed noise, slow attack, no hiss."""
    N = int(d * SR); x = tt(N); w = lp2(rng.standard_normal(N).astype(np.float32), 900)
    e = np.sin(np.pi * x / d) ** 2; s = w * e; return (s / (np.abs(s).max() + 1e-9)).astype(np.float32)
def glide(m0, m1, d=0.7, a=0.03):
    N = int(d * SR); x = tt(N); f = midi(m0) * (midi(m1) / midi(m0)) ** (x / d)
    ph = 2 * np.pi * np.cumsum(f) / SR; s = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * env(N, a, d * 0.5)
    return s.astype(np.float32)
def riser(d):
    """A tone that rises and swells into the landing; its last 150 ms fade into a reverb tail (added below)."""
    d = max(0.6, d); N = int(d * SR); x = tt(N); p = x / d
    f = midi(57) * 2 ** (p * 1.0)                                       # A3 up an octave
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) + 0.3 * np.sin(2 * ph + 0.3) + 0.15 * np.sin(3 * ph)) * p ** 2.2
    s[-int(0.15 * SR):] *= np.cos(np.linspace(0, np.pi / 2, int(0.15 * SR))); return s.astype(np.float32)
def buildup(d):
    """A musical build into a landing (v4.2), counted back from the downbeat so everything converges on it:
    a rising arpeggio of the A minor chord (eighth notes, then sixteenths in the last beat), a soft kick on the
    beats (eighths in the last beat), and the chord swelling while its tone opens from dark to bright."""
    d = max(1.0, d); N = int(d * SR); out = np.zeros(N, np.float32)
    seq = [57, 60, 64, 69, 72, 76, 81]                                   # A3 C4 E4 A4 C5 E5 A5
    t = d; ts = []
    while True:
        dist = d - t; step = beat / 4 if dist < beat else beat / 2
        t -= step
        if t < 0.05: break
        ts.append(t)
    for t in ts:
        p = t / d; m = seq[min(len(seq) - 1, int(p * len(seq)))]
        note = mallet([m], 0.35, 0.004, 10.0, 0.15) * (0.18 + 0.6 * p ** 1.3)
        i = int(t * SR); out[i:i + len(note)] += note[:N - i]
    k = d
    while k > 0.05:                                                     # kick: beats, then eighths in the last beat
        dist = d - k; step = beat / 2 if dist < beat else beat
        k -= step
        if k < 0.05: break
        p = k / d; kk = thump(60, 0.25) * (0.15 + 0.45 * p ** 1.5)
        i = int(k * SR); out[i:i + len(kk)] += kk[:N - i]
    x = tt(N); p = x / d
    chord = sum(np.sin(2 * np.pi * midi(m) * x) + 0.3 * np.sin(4 * np.pi * midi(m) * x) for m in (57, 60, 64, 69)) / 4
    bright, dark = chord.astype(np.float32), lp2(chord.astype(np.float32), 500)
    o = p ** 1.5; out += (bright * o + dark * (1 - o)) * (p ** 1.8) * 0.55
    out[-int(0.12 * SR):] *= np.cos(np.linspace(0, np.pi / 2, int(0.12 * SR)))
    return out.astype(np.float32)

SCALE_DOWN = [76, 74, 72, 69, 67, 64, 62, 60, 57]                       # E5 down to A3, A minor pentatonic
def slider_notes(t0, d, level=-5.0):
    """Soft notes on the music's own sixteenth-note grid while a slider moves; the pitch follows the slider
    (stepping down as slippage rises and profit melts, or as the replay rewinds to the crash)."""
    g16 = beat / 4; t = GRID0 + np.ceil((t0 - GRID0) / g16) * g16; last = None; lt = -9
    while t < t0 + d:
        u = 0.5 - 0.5 * np.cos(np.pi * min(1.0, (t - t0) / d)); idx = int(round(u * (len(SCALE_DOWN) - 1)))
        if idx != last or t - lt >= beat / 2 - 1e-6:
            put(t, mallet([SCALE_DOWN[idx]], 0.3, 0.005, 9.0, 0.15), level, 0.15 * np.sin(idx), True); last, lt = idx, t
        t += g16

def pop():
    """Pari's bubble appears: a small soft 'boop'."""
    N = int(0.11 * SR); x = tt(N); f = 520 * (1 + 0.35 * (1 - np.exp(-x * 40)))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 26); s[:int(0.006 * SR)] *= np.linspace(0, 1, int(0.006 * SR))
    return s.astype(np.float32)
def bloom(ms, d=1.6):
    s = mallet(ms, d, 0.01, 2.2); N = len(s); x = tt(N)
    pad = sum(np.sin(2 * np.pi * midi(m) * x) for m in ms) / len(ms) * env(N, 0.18, d * 0.7) * 0.5
    return (s + pad).astype(np.float32)

STEP = {1: [72], 2: [74], 3: [76], 4: [79]}                            # C5 D5 E5 G5: the four differences rise
TICK = {0: [72], 1: [74], 2: [76], 3: [79], 4: [81], 5: [72, 76, 79], 6: [57], 7: [79]}   # brief checklist; 6 = "still open"

def make(ev):
    """(signal, level above the music in dB, pan) for one event, or None."""
    s = ev.get("sfx")
    if s == "impact":      return thump(72, 0.8) * 0.8 + np.pad(mallet([60, 64, 67], 0.8, 0.012, 4.0), (0, int(0.0 * SR)))[:int(0.8 * SR)], 5.0, 0
    if s == "impact_big":  return np.concatenate([thump(55, 1.2)]) * 0.8 + bloom([45, 57, 60, 64], 1.2)[:int(1.2 * SR)], 5.0, 0
    if s == "reveal":      return bloom([57, 60, 64], 1.6), 6.0, 0
    if s == "alert":       # the crash: the motif descending, darker
        out = np.zeros(int(0.9 * SR), np.float32)
        for i, m in enumerate((67, 64, 60)):
            b_ = mallet([m - 12, m], 0.6, 0.01, 5.0); j = int(i * 0.16 * SR); out[j:j + len(b_)] += b_[:len(out) - j]
        return lowpass(out, 2200), 3.5, 0.1
    if s == "cost":        # profit melting: two clean falling notes (the slider's own notes carry it while it moves)
        if "d" in ev: return None
        a_, b2 = mallet([69], 0.5, 0.008, 6.0), mallet([65], 0.7, 0.008, 5.0); j = int(0.16 * SR)
        o_ = np.zeros(j + len(b2), np.float32); o_[:len(a_)] += a_; o_[j:] += b2; return o_, 1.5, -0.05
    if s == "land":        return mallet([76], 0.45, 0.01, 7.0), 3.0, 0.05
    if s == "click":       return mallet([69], 0.12, 0.004, 30.0, 0.0), -3.0, 0.1
    if s in ("whoosh", "whoosh_soft"): return swell(0.6), -4.0, 0
    if s == "step":        return mallet(STEP[ev.get("step", 1)], 0.6, 0.01, 5.0), 4.0, 0
    if s == "tick_up":     i = ev.get("step", 0); return mallet(TICK[i], 0.7 if i == 5 else 0.45, 0.01, 4.0 if i == 5 else 6.0), (4.5 if i == 5 else 2.0 if i == 6 else 3.0), 0
    if s == "theme_dark":  return mallet([57, 64, 69], 0.9, 0.012, 3.5), 2.0, 0.2     # the site turns dark: a low, open chord
    if s == "theme_light": return mallet([64, 69, 76], 0.8, 0.012, 4.0), 1.5, 0.2     # and back to light: the same, brighter
    if s == "end_chime":   return bloom([60, 64, 67, 72], 2.4), 4.0, 0
    return None

fx = np.zeros((n, 2), np.float32)
placed = []
QUEUE = []                                    # (time, signal, dB above the music, pan, primary?)
def put(t, sig, above, pan=0.0, primary=False): QUEUE.append((t, sig, above, pan, primary))
def place(t, sig, above, pan=0.0):
    """Place a shaped effect so its loudest 100 ms sits `above` dB over the music at that moment."""
    sig = lp2(shelf(sig, 4000, -6), 9000)
    ref = level_db(mus[:, 0], t + 0.05)
    ref = max(ref, BED_REF - 4)                                       # when the music is near-silent, use the usual bed
    w = int(0.1 * SR); r = max(np.sqrt((sig[i:i + w] ** 2).mean()) for i in range(0, max(1, len(sig) - w), w // 2))
    g = db(ref + above) / (r + 1e-9)
    add(fx, t, sig, pan, g); placed.append((round(t, 3), above))

SECONDARY = ("whoosh", "whoosh_soft", "click")
_sf = sorted([(e["f"] / FPS, e.get("sfx")) for e in EV if e.get("sfx")])
SCRUBS = [(t0, t1 - t0) for (t0, a_), (t1, b_) in zip(_sf, _sf[1:]) if a_ == "click" and b_ == "alert" and 0.5 < t1 - t0 < 3.0]
for e in EV:
    t = e["f"] / FPS
    m = make(e)
    if m: put(t - (0.3 if e.get("sfx") in ("whoosh", "whoosh_soft") else 0.0), *m, primary=e.get("sfx") not in SECONDARY)
    if e.get("bubble"):
        bl = mallet([76], 0.25, 0.006, 14.0); b2 = mallet([79], 0.3, 0.006, 12.0); j = int(0.07 * SR)
        blip = np.zeros(j + len(b2), np.float32); blip[:len(bl)] += bl; blip[j:] += b2
        put(t, blip, -4.0, -0.3, True)
    if "tick" in e: slider_notes(t, e["tick"] / FPS)                 # the slippage slider: notes on the beat grid
    if "rise" in e:
        land = t + e["rise"] / FPS; d_ = e["rise"] / FPS
        put(land - d_, buildup(d_), 1.0, 0)
    if "predict" in e:                                                # one soft note as each "your guess" dot fills
        d = e["predict"] / FPS
        for i in range(1, 4): put(t + i * d / 3.2, mallet([67], 0.35, 0.01, 9.0), 0.0, 0, True)
for t0, d_ in SCRUBS: slider_notes(t0 + 0.1, d_ - 0.15)                # the replay slider rewinding to the crash
# never two sounds within 150 ms: a background sound that collides with a meaningful one is dropped; two meaningful
# ones are spaced 150 ms apart; the riser is long and starts quietly, so it is exempt
QUEUE.sort(key=lambda q: (q[0], not q[4]))
last = -9.0; dropped = 0
for t, sig, above, pan, primary in QUEUE:
    long_ = len(sig) > 1.5 * SR and above <= 2.0
    if not long_ and t - last < 0.15:
        if not primary: dropped += 1; continue
        t = last + 0.15
    place(t, sig, above, pan)
    if not long_: last = t
print("background sounds dropped for spacing:", dropped)
from scipy.signal import fftconvolve
_ir_t = tt(int(2.2 * SR)); IR = lp2(rng.standard_normal(len(_ir_t)).astype(np.float32), 3000) * np.exp(-_ir_t / 0.45).astype(np.float32)
IR /= np.sqrt((IR ** 2).sum())
wet = np.stack([fftconvolve(fx[:, c], IR)[:n] for c in (0, 1)], 1).astype(np.float32)
fx += wet * 0.22                                                      # every effect gets a little room; risers end in it
room = lp2(rng.standard_normal(n).astype(np.float32), 400) * db(-52)
fx += room[:, None]

ts = sorted(p[0] for p in placed)
close = [(a, b_) for a, b_ in zip(ts, ts[1:]) if b_ - a < 0.15]
print("effects", len(ts), " pairs closer than 150 ms:", len(close), close[:6])

mix = mus + fx
mix = mix[: int(TOTAL * SR)]
mix[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))[:, None]   # the last moment fades to true silence
peak = np.abs(mix).max(); mix = mix / peak * 0.85
with wave.open(os.path.join(HERE, "audio4.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
rms = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
print("seconds %.1f  music %.1f dB  effects %.1f dB (before mastering)" % (TOTAL, rms(mus), rms(fx)))

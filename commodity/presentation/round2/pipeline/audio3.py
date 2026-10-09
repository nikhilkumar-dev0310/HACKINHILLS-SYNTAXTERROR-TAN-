"""v3 sound design: a music bed whose intensity follows the story, and sound effects only on meaningful moments.

Principles (see ../ENGAGEMENT.md): a sound that lands exactly on a visual change makes that change stand out
(Van der Burg et al. 2008), so effects are tied to on-screen events and never to every cursor move; silence
before a reveal; one loudest moment (the twist); the music thins while the viewer guesses and resolves on the
address of the live site. Levels are relative to the music bed; the final mix is loudness-normalised by run3.sh.
If pipeline/voice.wav exists (a recorded voice-over), it is mixed in and the music ducks under it.

    python audio3.py   -> audio3.wav
"""
import json, os, wave
import numpy as np
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
TL = json.load(open(os.path.join(HERE, "timeline3_out.json")))
FPS, FR, EV = TL["fps"], TL["frames"], TL["events"]
TOTAL = FR / FPS
n = int(TOTAL * SR) + SR
rng = np.random.default_rng(11)
tt = lambda N: np.arange(N) / SR
midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)
db = lambda x: 10 ** (x / 20)


def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR); return lfilter([1 - a], [1, -a], x).astype(np.float32)
def highpass(x, cut): return (x - lowpass(x, cut)).astype(np.float32)
def env(N, a, r, s=1.0):
    e = np.ones(N, np.float32) * s; A = max(1, int(a * SR)); R = max(1, int(r * SR))
    e[:A] = np.linspace(0, s, A); e[-R:] *= np.linspace(1, 0, R); return e
def add(buf, t, sig, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(len(buf), i + len(sig))
    if j <= i or i < 0: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[:j - i] * l * gain; buf[i:j, 1] += sig[:j - i] * r * gain

# ------------------------------------------------------------------ music: four layers, same chords, 92 bpm
BPM = 92; beat = 60 / BPM; bar = 4 * beat
CH = [(57, [57, 60, 64, 67]), (53, [53, 57, 60, 64]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67])]   # Am F C G
L = {k: np.zeros((n, 2), np.float32) for k in ("pad", "bass", "arp", "drums", "lift")}
end_ev = [e for e in EV if e.get("mus") == "resolve"]
music_end = end_ev[0]["f"] / FPS if end_ev else TOTAL
t, k = 0.0, 0
while t < music_end:
    root, voice = CH[k % 4]; d = 2 * bar; N = int((d + 1.5) * SR); x = tt(N)
    pad = sum(np.sin(2 * np.pi * midi(m + 12) * (1 + det / 100) * x) for m in voice for det in (-0.08, 0.08)).astype(np.float32)
    add(L["pad"], t, pad * env(N, 1.0, 1.5) / 16)
    add(L["bass"], t, (np.sin(2 * np.pi * midi(root - 12) * x) * env(N, 0.04, 1.2)).astype(np.float32) / 5)
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    for b8 in range(16):
        m = voice[pat[b8 % 8]] + 12; N2 = int(1.1 * SR); x2 = tt(N2)       # v3.2: an octave lower, pure tone, soft attack
        pl = (np.sin(2 * np.pi * midi(m) * x2) * np.exp(-x2 * 4)).astype(np.float32); A2 = int(0.018 * SR); pl[:A2] *= np.linspace(0, 1, A2)
        add(L["arp"], t + b8 * beat / 2, pl, 0.25 if b8 % 2 else -0.25, 0.045)
    for bt in range(8):
        if bt % 2 == 0:
            Nk = int(0.35 * SR); xk = tt(Nk); fk = 50 + 55 * np.exp(-xk * 30)
            add(L["drums"], t + bt * beat, (np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-xk * 9)).astype(np.float32), 0, 0.2)
        # v3.2: no hi-hats or claps (the noise bursts were the harsh part); a soft low shaker instead
        Ns = int(0.09 * SR); ns = lowpass(highpass(rng.standard_normal(Ns).astype(np.float32), 900), 2400)
        add(L["drums"], t + bt * beat + beat / 2, ns * env(Ns, 0.02, 0.06), 0.15, 0.012)
    hi = (np.sin(2 * np.pi * midi(voice[3] + 12) * x) * env(N, 0.8, 1.5)).astype(np.float32) / 30
    add(L["lift"], t, hi, 0.25)
    t += d; k += 1
for kk in L:                                                       # warm: roll off everything above about 3 kHz
    for c in (0, 1): L[kk][:, c] = lowpass(lowpass(L[kk][:, c], 3200), 3200)

# the resolve: a long C major chord with the root low, on the ending
if end_ev:
    tr = music_end; N = int(9 * SR); x = tt(N)
    chord = sum(np.sin(2 * np.pi * midi(m) * x) * (0.5 if m < 50 else 1) for m in (36, 48, 55, 60, 64, 67, 72)).astype(np.float32)
    add(L["pad"], tr, chord * env(N, 0.08, 6.5) / 14)

# intensity per layer over time, from the `mus` events (0, 0.4, 1, 2, 3, "drop", "resolve")
LEVELS = {0: dict(pad=0, bass=0, arp=0, drums=0, lift=0), 0.4: dict(pad=.45, bass=0, arp=0, drums=0, lift=0),
          1: dict(pad=1, bass=.8, arp=0, drums=0, lift=0), 2: dict(pad=1, bass=1, arp=1, drums=.8, lift=0),
          3: dict(pad=1, bass=1, arp=1, drums=1, lift=1)}
gain = {kk: np.zeros(n, np.float32) for kk in L}
cuts = sorted([(e["f"] / FPS, e["mus"]) for e in EV if "mus" in e], key=lambda x: x[0]) + [(TOTAL + 1, None)]
lvl = LEVELS[0]
for (t0, m), (t1, _) in zip(cuts, cuts[1:]):
    i0, i1 = int(t0 * SR), min(n, int(t1 * SR))
    if m == "drop":
        tgt, ramp = LEVELS[0], 0.08
    elif m == "resolve":
        tgt, ramp = dict(pad=1, bass=0, arp=0, drums=0, lift=0), 0.3
    else:
        tgt, ramp = LEVELS[m], (0.35 if m == 0.4 else 0.6)
    R = max(1, int(ramp * SR))
    for kk in L:
        a, b = lvl[kk], tgt[kk]
        seg = np.full(i1 - i0, b, np.float32); r = min(R, i1 - i0); seg[:r] = np.linspace(a, b, r)
        gain[kk][i0:i1] = seg
    lvl = tgt
mus = sum(L[kk] * gain[kk][:, None] for kk in L)

# ------------------------------------------------------------------ sound effects
fx = np.zeros((n, 2), np.float32)
def sub_hit(f0=55, d=0.9, punch=1.0):
    N = int(d * SR); x = tt(N); f = f0 * (0.65 + 0.35 * np.exp(-x * 7))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 3.2)
    th = lowpass(rng.standard_normal(N).astype(np.float32), 400) * np.exp(-x * 30) * 1.4 * punch
    return ((s + th) / 1.6).astype(np.float32)
def land():
    N = int(0.25 * SR); x = tt(N)
    s = np.sin(2 * np.pi * 180 * x) * np.exp(-x * 26) + 0.15 * np.sin(2 * np.pi * 720 * x) * np.exp(-x * 60)
    return (s * 0.7).astype(np.float32)
def click():
    N = int(0.05 * SR); x = tt(N)
    return (np.sin(2 * np.pi * 950 * x) * np.exp(-x * 110) * 0.5).astype(np.float32)
def tick():
    N = int(0.02 * SR); x = tt(N)
    return (np.sin(2 * np.pi * 1300 * x) * np.exp(-x * 260) * 0.5).astype(np.float32)
def whoosh(d=0.55, bright=0.35):
    N = int(d * SR); x = tt(N); w = rng.standard_normal(N).astype(np.float32); e = np.sin(np.pi * x / d) ** 2
    s = (lowpass(w, 700) * (1 - x / d) + lowpass(highpass(w, 1200), 2600) * (x / d) * bright) * e
    return (s / (np.abs(s).max() + 1e-6) * 0.5).astype(np.float32)
def bell(ms, d=2.2, decay=2.2):
    N = int(d * SR); x = tt(N)
    s = sum(sum(a * np.sin(2 * np.pi * midi(m) * r * x) * np.exp(-x * decay * dk) for a, r, dk in ((1, 1, 1), (.25, 2.01, 2.0))) for m in ms)
    s[:240] *= np.linspace(0, 1, 240); return (s / len(ms) * 0.4).astype(np.float32)
def alert():
    out = np.zeros(int(0.9 * SR), np.float32)
    for i, m in enumerate((67, 71, 74)):
        b = bell([m], 0.5, 6); j = int(i * 0.11 * SR); out[j:j + len(b)] += b[:len(out) - j]
    return out
def cost(d=1.6):
    N = int(d * SR); x = tt(N); f = 220 * (1 - 0.5 * x / d)
    s = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(N, 0.08, 0.5)
    return lowpass(s.astype(np.float32), 1600) * 0.5
def shimmer():
    N = int(1.1 * SR); x = tt(N)
    s = sum(np.sin(2 * np.pi * f * x + p) * np.exp(-x * (3 + i)) for i, (f, p) in enumerate(zip(rng.uniform(1500, 2800, 6), rng.uniform(0, 6, 6))))
    s[:400] *= np.linspace(0, 1, 400); return (s / 6 * 0.5).astype(np.float32)
def riser(d):
    N = int(d * SR); x = tt(N); p = x / d
    nz = highpass(rng.standard_normal(N).astype(np.float32), 600) * (p ** 2.2)
    sw = np.sin(2 * np.pi * np.cumsum(180 + 900 * p ** 2) / SR) * p ** 2.5 * 0.35
    s = (lowpass(lowpass(nz, 3000), 3000) * 0.7 + sw).astype(np.float32); s[-60:] *= np.linspace(1, 0, 60)   # cut dead at the landing
    return s * 0.6
def room():
    N = n; w = lowpass(rng.standard_normal(N).astype(np.float32), 500); return w * db(-46)

# Effects sit under the music: the meaningful ones a few dB below the bed's level at that moment, the
# background ones well below; the twist's impact is still the loudest single sound (v3.1: about 8-10 dB quieter)
G = {"impact": -13, "impact_big": -9, "land": -15, "click": -17, "tick": -27, "whoosh": -15, "whoosh_soft": -18,
     "reveal": -12, "alert": -15, "cost": -18, "shimmer": -20, "end_chime": -13}
for e in EV:
    t = e["f"] / FPS; s = e.get("sfx")
    if s == "impact": add(fx, t, sub_hit(55, 1.0), 0, db(G[s]))
    elif s == "impact_big": add(fx, t, sub_hit(48, 1.6, 1.4), 0, db(G[s])); add(fx, t, bell([57, 64, 69], 2.5, 1.4), 0, db(-16))
    elif s == "land": add(fx, t, land(), 0.05, db(G[s]))
    elif s == "click": add(fx, t, click(), 0.1, db(G[s]))
    elif s in ("whoosh", "whoosh_soft"): add(fx, t - 0.2, whoosh(0.55 if s == "whoosh" else 0.45), 0, db(G[s]))
    elif s == "reveal": add(fx, t, bell([72, 76, 79], 2.4), 0, db(G[s]))
    elif s == "alert": add(fx, t, alert(), 0.15, db(G[s]))
    elif s == "cost": add(fx, t, cost(e.get("d", 1.2)), -0.05, db(G[s]))
    elif s == "shimmer": add(fx, t, shimmer(), 0.3, db(G[s]))
    elif s == "end_chime": add(fx, t, bell([72, 79, 84], 3.5, 1.2), 0, db(G[s]))
    if "tick" in e:                                     # counter ticks while a number rolls, slowing as it lands
        d = e["tick"] / FPS; k = 0
        while True:
            p = k / 14.0; at = d * (1 - (1 - min(1, p)) ** 1.6)
            if p > 1: break
            add(fx, t + at, tick(), 0.2 * np.sin(k), db(G["tick"])); k += 1
    if "rise" in e: d = e["rise"] / FPS; add(fx, t, riser(d), 0, db(-21))
    if "predict" in e:                                  # one soft tick as each "your guess" dot fills
        d = e["predict"] / FPS
        for i in range(1, 4): add(fx, t + i * d / 3.2, bell([76], 0.4, 9), 0, db(-23))
for c in (0, 1): fx[:, c] = lowpass(fx[:, c], 4500)                 # nothing sharp: effects rolled off above 4.5 kHz
fx += room()[:, None] * np.array([1, 1], np.float32)

# ------------------------------------------------------------------ optional voice-over, with the music ducked under it
mix_music = mus * db(-6)                  # the bed sits under the meaningful sounds
vpath = os.path.join(HERE, "voice.wav")
voice = np.zeros((n, 2), np.float32)
if os.path.exists(vpath):
    import subprocess
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", vpath, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    v = np.frombuffer(raw, np.float32)[:n]
    voice[:len(v), 0] = voice[:len(v), 1] = v
    envv = lowpass(np.abs(v), 6.0); duck = 1 - 0.68 * np.clip(envv / (envv.max() * 0.25 + 1e-9), 0, 1)
    mix_music[:len(v)] *= duck[:, None]
    print("voice-over mixed in, music ducked under it")

mix = mix_music + fx + voice
for c in (0, 1): mix[:, c] = mix[:, c] - 0.35 * highpass(mix[:, c], 5000)   # gentle top-end shelf on the whole mix
mix = mix[: int(TOTAL * SR)]
mix[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))[:, None]       # hard cut, no click
peak = np.abs(mix).max(); mix = mix / peak * 0.9
with wave.open(os.path.join(HERE, "audio3.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
rms = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
print("seconds %.1f  music %.1f dBFS  fx %.1f dBFS" % (TOTAL, rms(mix_music), rms(fx)))

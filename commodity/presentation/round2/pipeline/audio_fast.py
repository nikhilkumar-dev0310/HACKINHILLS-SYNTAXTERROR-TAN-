"""Soundtrack: a calm synthesized music bed plus soft interface sounds, timed from the timeline.

    python audio.py   -> audio.wav
"""
import json, os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR, FPS = 44100, 30
L = json.load(open(os.path.join(HERE, "layout_fast.json")))
TL = json.load(open(os.path.join(HERE, "timeline_fast.json")))
TOTAL = (L["intro"] + L["main"] + L["outro"]) / FPS
n = int(TOTAL * SR) + SR
rng = np.random.default_rng(7)
mus = np.zeros((n, 2), np.float32); fx = np.zeros((n, 2), np.float32)

midi = lambda m: 440.0 * 2 ** ((m - 69) / 12)


from scipy.signal import lfilter
def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR)
    return lfilter([1 - a], [1, -a], x).astype(np.float32)


def env(N, a, r, sustain=1.0):
    e = np.ones(N, np.float32) * sustain
    A = max(1, int(a * SR)); R = max(1, int(r * SR))
    e[:A] = np.linspace(0, sustain, A); e[-R:] *= np.linspace(1, 0, R)
    return e


def add(buf, t, sig, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(len(buf), i + len(sig))
    if j <= i: return
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:j, 0] += sig[:j - i] * l * gain; buf[i:j, 1] += sig[:j - i] * r * gain


# ------------------------------------------------------------------ music: Am - F - C - G, 84 bpm, two bars per chord
BPM = 96; beat = 60 / BPM; bar = 4 * beat
chords = [(57, [57, 60, 64, 67]), (53, [53, 57, 60, 64]), (48, [55, 60, 64, 67]), (55, [55, 59, 62, 67])]   # root, voicing
t = 0.0; k = 0
tt = lambda N: np.arange(N) / SR
while t < TOTAL:
    root, voice = chords[k % 4]; dur = 2 * bar; N = int((dur + 1.2) * SR); x = tt(N)
    pad = np.zeros(N, np.float32)
    for m in voice:
        for det in (-0.07, 0.07):
            f = midi(m + 12) * (1 + det / 100)
            pad += (np.sin(2 * np.pi * f * x) + 0.25 * np.sin(4 * np.pi * f * x)).astype(np.float32)
    pad *= env(N, 0.9, 1.4, 1.0) / 18
    add(mus, t, pad, 0.0, 0.55)
    bass = (np.sin(2 * np.pi * midi(root - 12) * x) * env(N, 0.05, 1.0)).astype(np.float32) / 6
    add(mus, t, bass, 0.0, 0.5)
    # soft plucked arpeggio, eighth notes
    pat = [0, 2, 1, 3, 2, 1, 3, 2]
    for b8 in range(16):
        m = voice[pat[b8 % 8]] + 24; N2 = int(0.9 * SR); x2 = tt(N2)
        pl = (np.sin(2 * np.pi * midi(m) * x2) + 0.3 * np.sin(4 * np.pi * midi(m) * x2)) * np.exp(-x2 * 6.0)
        pl[:60] *= np.linspace(0, 1, 60)
        add(mus, t + b8 * beat / 2, pl.astype(np.float32), 0.3 if b8 % 2 else -0.3, 0.038)
    for bt in range(8):                       # soft pulse: a round low kick on 1 and 3, a faint shaker on the off-beats
        if bt % 2 == 0:
            Nk = int(0.35 * SR); xk = tt(Nk); fk = 48 + 50 * np.exp(-xk * 30)
            kk = np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-xk * 9)
            add(mus, t + bt * beat, kk.astype(np.float32), 0.0, 0.16)
        Ns = int(0.06 * SR); ns = rng.standard_normal(Ns).astype(np.float32); ns = ns - lowpass(ns, 6000)
        add(mus, t + bt * beat + beat / 2, ns * np.exp(-tt(Ns) * 70).astype(np.float32), 0.15, 0.022)
    t += dur; k += 1
mus[:, 0] = lowpass(mus[:, 0], 5200); mus[:, 1] = lowpass(mus[:, 1], 5200)
# fade in over the first 2 s, out over the last 4 s
fade = np.ones(n, np.float32); fi = int(2 * SR); fo = int(4 * SR); end = int(TOTAL * SR)
fade[:fi] = np.linspace(0, 1, fi); fo = int(3 * SR); fade[end - fo:end] = np.linspace(1, 0, fo); fade[end:] = 0
mus *= fade[:, None]


# ------------------------------------------------------------------ interface sounds
def click():
    N = int(0.05 * SR); x = tt(N)
    s = 0.6 * np.sin(2 * np.pi * 1900 * x) * np.exp(-x * 120) + 0.4 * rng.standard_normal(N) * np.exp(-x * 300)
    return s.astype(np.float32) * 0.5
def key():
    N = int(0.03 * SR); x = tt(N)
    return (rng.standard_normal(N) * np.exp(-x * 400) * 0.18 + np.sin(2 * np.pi * 3100 * x) * np.exp(-x * 250) * 0.1).astype(np.float32)
def pop():
    N = int(0.12 * SR); x = tt(N); f = 420 + 900 * x / x[-1]
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 26) * 0.5).astype(np.float32)
def whoosh(d=0.7):
    N = int(d * SR); x = tt(N); w = rng.standard_normal(N).astype(np.float32)
    e = np.sin(np.pi * x / d) ** 2
    lo = lowpass(w, 900) * 1.0; hi = w - lowpass(w, 2500)
    s = (lo * (1 - x / d) + hi * (x / d) * 0.35) * e
    return (s / (np.abs(s).max() + 1e-6) * 0.32).astype(np.float32)
def chime(m=76):
    N = int(2.2 * SR); x = tt(N)
    s = sum(a * np.sin(2 * np.pi * midi(m) * r * x) * np.exp(-x * dcy) for a, r, dcy in ((1, 1, 2.2), (.45, 2.01, 3.4), (.25, 3.0, 5), (.12, 4.2, 7)))
    s[:200] *= np.linspace(0, 1, 200)
    return (s * 0.16).astype(np.float32)

off = L["intro"] / FPS
SFX = {"click": click(), "pop": pop()}          # typing ticks dropped: too busy
for e in TL["events"]:
    t = off + e["f"] / FPS
    if e.get("sfx") in SFX: add(fx, t, SFX[e["sfx"]], 0.1, 0.32)
    if "card" in e:
        add(fx, t - 0.05, whoosh(0.6), 0.0, 0.32)
        add(fx, t + 0.25, chime(76 if e["card"] % 2 else 79), 0.0, 0.22)
    if e.get("cap"):
        pass
# intro: chimes as the four tiles land and when the logo appears; outro: checklist ticks and a final chord
K = 1.6                                     # intro / outro play 1.6x faster
for i in range(4): add(fx, (1.8 + i * .22 + .25) / K, chime(72 + [0, 4, 7, 12][i]), [-.4, -.15, .15, .4][i], 0.22)
add(fx, 6.55 / K, whoosh(0.7), 0, 0.3)
add(fx, 12.05 / K, chime(84), 0, 0.38); add(fx, 12.1 / K, chime(79), 0, 0.25)
o0 = (L["intro"] + L["main"]) / FPS
for i in range(6): add(fx, o0 + (.4 + i * .55 + .1) / K, pop(), 0, 0.2)
add(fx, o0 + 7.05 / K, whoosh(0.6), 0, 0.28); add(fx, o0 + 11.05 / K, whoosh(0.6), 0, 0.28)
add(fx, o0 + 11.4 / K, chime(72), -.3, .3); add(fx, o0 + 11.45 / K, chime(76), 0, .25); add(fx, o0 + 11.5 / K, chime(79), .3, .25)

mix = (mus * 1.15 + fx * 1.0) * 1.5
peak = np.abs(mix).max(); mix = mix / peak * 0.89 if peak > 0.89 else mix
mix = mix[: int(TOTAL * SR)]
with wave.open(os.path.join(HERE, "audio_fast.wav"), "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
rms = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
print("seconds %.1f  music rms %.1f dBFS  mix rms %.1f dBFS  peak %.2f" % (TOTAL, rms(mus * 1.15), rms(mix), np.abs(mix).max()))

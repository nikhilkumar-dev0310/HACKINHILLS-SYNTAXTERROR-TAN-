"""v4 compositor. Rules (sources in ../ENGAGEMENT.md, v4 section):

- The site footage plays at real speed (v3.3-3.6 dropped every 5th frame, which read as "sped up").
- Camera moves inside a scene take at least 0.8 s, eased in and out, then hold.
- No outlines, brackets, rings or pointers. The cue is the camera's framing plus a soft darkening of the surround
  (to about 55% brightness, faded in over 0.4 s once the camera settles, lifted before the next move).
- A brightness pulse lands on the same frame as each key sound: 2-frame onset, 0.4 s decay ("pip and pop").
- Pari, the mascot (unchanged design), is a guide: speech bubbles for the questions and asides (pop in over 1/3 s),
  reactions only at real moments, smooth cross-fades between poses, blinks every 3-5 s, a small hop only on
  reactions, a lean when pointing. No mouth movement on captions.
- "What we do differently" counter, top left, during that run.

    python compose4.py               -> video4_noaudio.mp4, timeline4_out.json (events in output frames)
    python compose4.py 300 600       -> preview4.mp4 of output frames 300-600
"""
import hashlib, json, math, os, subprocess, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OW, OH, FPS = 1920, 1080, 30
TL = json.load(open(os.path.join(HERE, "timeline4.json")))
VW, VH, DSF, NS = TL["vw"], TL["vh"], TL["dsf"], TL["frames"]
EV = TL["events"]
OV = os.path.join(HERE, "ov4")

clamp = lambda p: max(0.0, min(1.0, p))
ease = lambda p: 0.5 - 0.5 * math.cos(math.pi * clamp(p))
ezo = lambda p: 1 - (1 - clamp(p)) ** 3
def back(p):
    p = clamp(p); c1 = 1.70158; c3 = c1 + 1; return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
key = lambda t: hashlib.md5(t.encode()).hexdigest()[:12]

# ------------------------------------------------------------------ which source frames are kept (setup frames only)
skip = np.zeros(NS, bool)
for e in EV:
    if "skip" in e: skip[e["f"]:e["f"] + e["skip"]] = True
KEEP = [f for f in range(NS) if not skip[f]]
N = len(KEEP)
out_of = np.cumsum(~skip) - 1
def to_out(f):
    f = min(max(0, f), NS - 1)
    while f < NS - 1 and skip[f]: f += 1
    return int(out_of[f])

# ------------------------------------------------------------------ camera (source frames), with eased, unhurried moves
def crop_for(rect, zmax):
    if rect is None: return (0.0, 0.0, float(VW))
    x, y, w, h = rect
    z = max(1.0, min(zmax, VW / max(w, 1), VH * 0.78 / max(h, 1)))
    W, H = VW / z, VH / z
    cx, cy = x + w / 2, y + h / 2
    return (min(max(cx - W / 2, 0), VW - W), min(max(cy - 0.45 * H, 0), VH - H), W)

cam_src = [None] * NS
tgt_src = [None] * NS           # (target rect, source frame the move started, source frame it settles)
cur, start, target, t0, dur = (0.0, 0.0, float(VW)), None, None, 0, 1
cam_ev = {e["f"]: e for e in EV if "cam" in e}
_tgt = None
for f in range(NS):
    if f in cam_ev:
        e = cam_ev[f]; d = max(1, e["dur"])
        if d > 3: d = max(d, 24)                                     # in-scene moves: at least 0.8 s
        start, target, t0, dur = cur, crop_for(e["cam"], e.get("zmax", 1.45)), f, d
        _tgt = (e["cam"], f, f + d) if e["cam"] is not None else None
    if target is not None:
        p = ease((f - t0 + 1) / dur)
        cur = tuple(a + (b - a) * p for a, b in zip(start, target))
        if p >= 1: target = None
    cam_src[f] = cur; tgt_src[f] = _tgt

# ------------------------------------------------------------------ events in output frames
OUT_EV = []
for e in EV:
    if "skip" in e: continue
    e2 = dict(e); e2["f"] = to_out(e["f"])
    for k in ("tick", "rise", "predict"):
        if k in e: e2[k] = max(1, to_out(e["f"] + e[k]) - e2["f"]); e2[k + "_src"] = e[k]
    OUT_EV.append(e2)
TOTAL = max([e["f"] + e.get("dur", 0) for e in OUT_EV if "beat" in e] + [N])

beat = [None] * (TOTAL + 1)
for e in OUT_EV:
    if "beat" in e:
        for i in range(e["dur"]):
            if e["f"] + i <= TOTAL: beat[e["f"] + i] = (e["beat"], i, e["dur"])
cap_segs, cur_cap = [], None
for e in sorted([e for e in OUT_EV if "cap" in e], key=lambda e: e["f"]):
    if cur_cap: cur_cap[2] = e["f"] - 1; cap_segs.append(cur_cap); cur_cap = None
    if e["cap"]: cur_cap = [key(e["cap"]), e["f"], TOTAL]
if cur_cap: cap_segs.append(cur_cap)
pred = [(e["f"], e["predict"], e["predict_src"]) for e in OUT_EV if "predict" in e]

# brightness pulse on the key sounds: (frame, amount)
PULSE_ON = {"impact": .06, "impact_big": .07, "reveal": .06, "alert": .045, "step": .035, "end_chime": .04}
PULSE = [(e["f"], PULSE_ON[e["sfx"]]) for e in OUT_EV if e.get("sfx") in PULSE_ON]
PULSE += [(e["f"], .03) for e in OUT_EV if e.get("sfx") == "tick_up" and e.get("step") == 5]

# "what we do differently" counter
CHIP = [0] * (TOTAL + 1); _c = 0; _ce = sorted([(e["f"], e["chip"]) for e in OUT_EV if "chip" in e])
for g in range(TOTAL + 1):
    while _ce and _ce[0][0] <= g: _c = _ce.pop(0)[1]
    CHIP[g] = _c

# ------------------------------------------------------------------ Pari: poses over time, bubbles, hops
PARI_IMG = {k: cv2.imread(os.path.join(HERE, "ov3", "pari", k + ".png"), cv2.IMREAD_UNCHANGED) for k in
            ("idle", "blink", "talk", "wow", "think", "no", "sad", "point_r", "cheer", "wave0", "wave1", "proud")}
POSE = ["idle"] * (TOTAL + 1); BUB = [None] * (TOTAL + 1); HOPS = []
for e in sorted([e for e in OUT_EV if "pari" in e], key=lambda e: e["f"]):
    s0, d = e["f"], e["dur"]
    for g in range(s0, min(TOTAL + 1, s0 + d)):
        POSE[g] = e["pari"]
        if e.get("bubble"): BUB[g] = (key(e["bubble"]), s0, s0 + d)
    if e["pari"] in ("wow", "cheer", "point_r", "proud", "wave"): HOPS.append(s0)
PARI_IN = next(g for g in range(TOTAL) if not (beat[g] and beat[g][0] == "black"))

# v4.1: Pari talks more. Extra lines react to a caption once it has been read (start no earlier than 60% of its
# reading time), end before the next caption starts, and never start within 4 s of another bubble.
BANTER = json.load(open(os.path.join(HERE, "banter4.json")))
CAPTXT = {key(e["cap"]): e["cap"].replace("**", "") for e in OUT_EV if e.get("cap")}
starts = sorted(e["f"] for e in OUT_EV if e.get("bubble"))
BANTER_EV = []
def _free(a, b): return all(g > TOTAL or BUB[g] is None for g in range(a, b))
for pre, text, pose in BANTER["after_caption"]:
    seg = next(((k, s0, e0) for k, s0, e0 in cap_segs if CAPTXT[k].startswith(pre)), None)
    if not seg: continue
    k, s0, e0 = seg; read = round((len(CAPTXT[k]) / 15 + 0.6) * FPS)
    dur = round(max(1.8, 1.0 + 0.3 * len(text.split())) * FPS)
    nxt = min([c[1] for c in cap_segs if c[1] > s0] + [TOTAL])
    st = max(s0 + round(0.6 * read), min(s0 + read, nxt - dur))
    dur = min(dur, nxt + 9 - st)
    if dur < round(1.4 * FPS) or any(abs(st - x) < 4 * FPS for x in starts) or not _free(st, st + dur):
        print("banter skipped:", text); continue
    starts.append(st); BANTER_EV.append({"f": st, "pari": pose, "bubble": text, "dur": dur})
for name, off, text, pose in BANTER["on_card"]:
    b0 = next((e for e in OUT_EV if e.get("beat") == name), None)
    if not b0: continue
    st = b0["f"] + round(off * FPS); dur = min(round((1.2 + 0.3 * len(text.split())) * FPS), b0["dur"] - round(off * FPS))
    starts.append(st); BANTER_EV.append({"f": st, "pari": pose, "bubble": text, "dur": dur, "card": name})
for e in BANTER_EV:
    for g in range(e["f"], min(TOTAL + 1, e["f"] + e["dur"])):
        POSE[g] = e["pari"]; BUB[g] = (key(e["bubble"]), e["f"], e["f"] + e["dur"])
    if e["pari"] in ("wow", "cheer", "point_r", "proud", "wave"): HOPS.append(e["f"])
OUT_EV += BANTER_EV
print("Pari lines:", len([e for e in OUT_EV if e.get("bubble")]))
_r = np.random.default_rng(9); BLINKS = set(); _g = PARI_IN + 40
while _g < TOTAL: BLINKS.update(range(_g, _g + 4)); _g += int(_r.integers(90, 150))   # every 3-5 s

def pose_img(g):
    p = POSE[min(g, TOTAL)]
    if p == "wave": p = ("wave0", "wave1")[(g // 8) % 2]
    if p == "idle" and g in BLINKS: p = "blink"
    return p

# ------------------------------------------------------------------ drawing helpers
def blend(dst, src, x, y, a=1.0):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0 or a <= 0: return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    al = (s[:, :, 3:4].astype(np.float32) / 255.0) * a if s.shape[2] == 4 else np.float32(a)
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (s[:, :, :3].astype(np.float32) * al + d * (1 - al)).astype(np.uint8)

_cache = {}
def img(path, flags=cv2.IMREAD_UNCHANGED):
    if path not in _cache:
        if len(_cache) > 400: _cache.clear()
        _cache[path] = cv2.imread(path, flags)
    return _cache[path]

_yy, _xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
_rr = np.sqrt(((_xx - OW / 2) / (OW / 2)) ** 2 + ((_yy - OH / 2) / (OH / 2)) ** 2)
VIG = (1 - 0.12 * np.clip((_rr - 0.55) / 0.9, 0, 1) ** 1.6)[:, :, None].astype(np.float32)
DARK = np.full((OH, OW, 3), (13, 11, 10), np.uint8)
_sy, _sx = np.mgrid[0:OH // 4, 0:OW // 4].astype(np.float32) * 4

def surround(out, box, a):
    """Darken everything outside the framed target (soft 150 px edge) to about 55% brightness."""
    x, y, w, h = box; pad = 22
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    dx = np.maximum(np.maximum(x0 - _sx, _sx - x1), 0); dy = np.maximum(np.maximum(y0 - _sy, _sy - y1), 0)
    wm = a * np.clip(np.sqrt(dx * dx + dy * dy) / 150.0, 0, 1) ** 0.9
    wm = cv2.resize(wm, (OW, OH), interpolation=cv2.INTER_LINEAR)[:, :, None]
    small = cv2.resize(out, (OW // 4, OH // 4), interpolation=cv2.INTER_AREA)
    blur = cv2.resize(cv2.GaussianBlur(small, (0, 0), 2.0), (OW, OH), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    o = out.astype(np.float32)
    out[:] = ((o * (1 - 0.85 * wm) + blur * 0.85 * wm) * (1 - 0.42 * wm)).astype(np.uint8)

def page(g):
    f = KEEP[min(g, N - 1)]
    im = cv2.imread(os.path.join(HERE, "frames4", f"{f:05d}.jpg"))
    def cam_at(ff, gg):
        x0, y0, W = cam_src[ff]
        z = 1 + 0.02 * (0.5 - 0.5 * math.cos(2 * math.pi * gg / (FPS * 9.0)))      # breathing: ~2% over 9 s
        W2 = W / z; x0 = x0 + (W - W2) / 2 + 8 * math.sin(2 * math.pi * gg / (FPS * 13.0)); W = W2
        y0 = y0 + (W * z - W) * VH / VW / 2 + 5 * math.sin(2 * math.pi * gg / (FPS * 11.0) + 1)
        x0 = min(max(x0, 0), VW - W); H = W * VH / VW; y0 = min(max(y0, 0), VH - H)
        return x0, y0, W
    def view(x0, y0, W, interp=cv2.INTER_CUBIC):
        H = W * VH / VW; sx, sy, sw, sh = x0 * DSF, y0 * DSF, W * DSF, H * DSF
        M = np.float32([[OW / sw, 0, -sx * OW / sw], [0, OH / sh, -sy * OH / sh]])
        return cv2.warpAffine(im, M, (OW, OH), flags=interp)
    x0, y0, W = cam_at(f, g)
    f2 = KEEP[min(g + 1, N - 1)]
    nx0, ny0, nW = cam_at(f2, g + 1)
    k_ = OW / W; motion = max(abs(nx0 - x0) * k_, abs(ny0 - y0) * k_, abs(nW - W) * k_ * 0.5)
    if motion > 3:                                                   # motion blur: 4 samples over half a frame (180-degree shutter)
        acc = np.zeros((OH, OW, 3), np.float32)
        for u in (0.0, 0.125, 0.25, 0.375):
            acc += view(x0 + (nx0 - x0) * u, y0 + (ny0 - y0) * u, W + (nW - W) * u, cv2.INTER_LINEAR)
        out = (acc / 4).astype(np.uint8)
    else:
        out = view(x0, y0, W)
    out = (out.astype(np.float32) * VIG).astype(np.uint8)
    tg = tgt_src[f]
    if tg is not None:
        (rx, ry, rw, rh), fs, fe = tg
        k = OW / W; box = ((rx - x0) * k, (ry - y0) * k, rw * k, rh * k)
        settle = g - to_out(fe)                                      # frames since the camera settled
        nxt = next((to_out(ff) for ff in range(f + 1, min(NS, f + 8)) if ff in cam_ev), None)
        a = ease(settle / 12.0) if settle >= 0 else 0.0
        if nxt is not None: a *= clamp((nxt - g) / 6.0)              # lift before the next move
        if a > 0 and 40 < box[2] < OW * 0.85 and box[3] > 20 and box[2] * box[3] < 0.55 * OW * OH:
            surround(out, box, a)
    return out

# framed screen (v4.1): the site sits at 95% on a dark warm gradient, rounded 18 px, with a soft shadow
IW, IH = int(OW * 0.95) // 2 * 2, int(OH * 0.95) // 2 * 2
IX, IY = (OW - IW) // 2, (OH - IH) // 2 - 6
_rad = np.sqrt(((_xx - OW / 2) / (OW * 0.62)) ** 2 + ((_yy - OH * 0.45) / (OH * 0.7)) ** 2)
BG = (np.array([16, 20, 27], np.float32) * (1 - np.clip(_rad, 0, 1))[:, :, None] + np.array([13, 11, 10], np.float32) * np.clip(_rad, 0, 1)[:, :, None])
_m = np.zeros((IH, IW), np.float32); cv2.rectangle(_m, (18, 0), (IW - 19, IH - 1), 1, -1); cv2.rectangle(_m, (0, 18), (IW - 1, IH - 19), 1, -1)
for cx_, cy_ in ((18, 18), (IW - 19, 18), (18, IH - 19), (IW - 19, IH - 19)): cv2.circle(_m, (cx_, cy_), 18, 1, -1, cv2.LINE_AA)
_m = cv2.GaussianBlur(_m, (3, 3), 0.7)
_sh = np.zeros((OH, OW), np.float32); _sh[IY + 14:IY + 14 + IH, IX:IX + IW] = _m
_sh = cv2.GaussianBlur(_sh, (0, 0), 22) * 0.55
BASE = (BG * (1 - _sh[:, :, None])).astype(np.float32)
MASK = _m[:, :, None]
def framed(page_img):
    out = BASE.copy()
    small = cv2.resize(page_img, (IW, IH), interpolation=cv2.INTER_AREA).astype(np.float32)
    out[IY:IY + IH, IX:IX + IW] = small * MASK + out[IY:IY + IH, IX:IX + IW] * (1 - MASK)
    return out.astype(np.uint8)

GOLD = np.array([61, 184, 245], np.float32)
_dr = np.random.default_rng(5); DUST = _dr.uniform(0, 1, (110, 5))
def _sprite(r):
    k = np.arange(-2 * r, 2 * r + 1, dtype=np.float32); g_ = np.exp(-(k[None, :] ** 2 + k[:, None] ** 2) / (2 * (r * 0.75) ** 2)); return g_[:, :, None]
SPR = {r: _sprite(r) for r in (1, 2, 3)}
def dust(im, g, amax=0.24):
    """Slow, soft gold dust on the dark statement cards."""
    for x, y, sz, sp, ph in DUST:
        px = int((x * OW + 22 * math.sin(g / 45 + ph * 6)) % OW); py = int((y * OH - g * (0.3 + sp * 0.8)) % OH)
        a = amax * (0.25 + 0.75 * (0.5 + 0.5 * math.sin(g / 27 + ph * 9))) * (0.55 + 0.45 * sz)
        r_ = 1 + int(sz * 2.99); m = SPR[r_] * a; R = 2 * r_
        y0, y1, x0, x1 = py - R, py + R + 1, px - R, px + R + 1
        if y0 < 0 or x0 < 0 or y1 > OH or x1 > OW: continue
        im[y0:y1, x0:x1] = (im[y0:y1, x0:x1].astype(np.float32) * (1 - m) + GOLD * m).astype(np.uint8)

def sheen(im, c, s, g, x, y):
    """One soft warm light sweep across a caption as it appears."""
    p = (g - s - 4) / 20.0
    if not 0 <= p <= 1: return
    p = ezo(p); h, w = c.shape[:2]; cx = int(-120 + (w + 240) * p)
    xs = np.arange(w)[None, :]
    band = np.exp(-((xs - cx - (np.arange(h)[:, None] - h / 2) * 0.35) ** 2) / (2 * 52.0 ** 2)) * (c[:, :, 3] / 255.0) * 0.4
    reg = im[max(0, y):max(0, y) + h, max(0, x):max(0, x) + w].astype(np.float32)
    band = band[:reg.shape[0], :reg.shape[1], None]
    im[max(0, y):max(0, y) + h, max(0, x):max(0, x) + w] = np.clip(reg + band * np.array([200, 235, 255], np.float32), 0, 255).astype(np.uint8)

PX, PBASE, PS = 34, OH - 40, 0.9                                     # Pari: left edge, feet line, scale
def sprite(name, sc):
    im = PARI_IMG[name]; w, h = int(im.shape[1] * sc), int(im.shape[0] * sc)
    return cv2.resize(im, (max(4, w), max(4, h)), interpolation=cv2.INTER_AREA)

def pari(out, g):
    if g < PARI_IN: return
    t_in = (g - PARI_IN) / 10.0
    sc = PS * (1 if t_in >= 1 else max(0.05, back(t_in)))
    hy, sq = 0.0, 1.0
    for h0 in HOPS:
        u = (g - h0) / 10.0
        if 0 <= u < 1: hy = -18 * math.sin(math.pi * u)
        elif 1 <= u < 1.4: sq = 1 - 0.07 * math.sin(math.pi * (u - 1) / 0.4)
    bob = 2.5 * math.sin(2 * math.pi * g / (FPS * 2.6))
    cur, prev = pose_img(g), pose_img(g - 5) if g >= 5 else pose_img(g)
    # cross-fade over 5 frames when the pose changes (blinks swap instantly)
    ch = next((i for i in range(1, 6) if g - i >= 0 and pose_img(g - i) != cur), None)
    layers = [(cur, 1.0)]
    if ch is not None and "blink" not in (cur, pose_img(g - ch)):
        a = ch / 6.0; layers = [(pose_img(g - ch), 1 - a), (cur, a)]
    for name, a in layers:
        spr = sprite(name, sc)
        h, w = int(spr.shape[0] * sq), int(spr.shape[1] / sq ** 0.5)
        spr = cv2.resize(spr, (w, h), interpolation=cv2.INTER_AREA)
        if name == "point_r":
            R = cv2.getRotationMatrix2D((w / 2, h * 0.9), -6.0, 1.0)
            spr = cv2.warpAffine(spr, R, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        blend(out, spr, PX + (int(264 * PS) - w) // 2, int(PBASE - h + hy + bob), a)
    b = BUB[min(g, TOTAL)]
    if b:
        k, s0, s1 = b; bm = img(os.path.join(OV, "bubbles", k + ".png"))
        u = (g - s0) / 10.0; sc2 = 1.0 if u >= 1 else max(0.05, back(u))
        fa = clamp((s1 - g) / 6.0) * clamp((g - s0 + 1) / 3.0)
        bw, bh = int(bm.shape[1] * sc2), int(bm.shape[0] * sc2)
        if bw > 6 and bh > 6:
            top = PBASE - int(232 * PS) - 6
            if beat[min(g, TOTAL)] and beat[min(g, TOTAL)][0] == "end":
                blend(out, cv2.resize(bm, (bw, bh), interpolation=cv2.INTER_AREA), PX + int(264 * PS) - 30, int(PBASE - 150 - bh + 60), fa)
            else:
                blend(out, cv2.resize(bm, (bw, bh), interpolation=cv2.INTER_AREA), PX + int(264 * PS * 0.55) - 64, int(top - bh + 60 + hy), fa)

def frame(g):
    b = beat[g]
    if b and b[0] == "black":
        out = DARK.copy()
    elif b and b[0] != "cut":
        name, i, d = b
        out = img(os.path.join(OV, "beats", name, f"{i:04d}.jpg"), cv2.IMREAD_COLOR).copy()
        dust(out, g)
        fin = 1.0 if name == "end" or i >= 8 else ease((i + 1) / 9)            # cross-fade in over 0.3 s
        fout = 1.0 if name == "end" or i < d - 8 else ease((d - i) / 9)
        a = min(fin, fout)
        if i < 9 and name != "end":                                             # cards settle in: 96% -> 100% over 0.3 s
            sc_ = 0.96 + 0.04 * ezo((i + 1) / 9); M_ = cv2.getRotationMatrix2D((OW / 2, OH / 2), 0, sc_)
            out = cv2.warpAffine(out, M_, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if a < 1: out = cv2.addWeighted(out, a, framed(page(g)), 1 - a, 0)
    else:
        out = framed(page(g))
        if b:                                                                    # a short dip through dark between scenes
            name, i, d = b
            a = ease(min(1.0, (i + 1) / 4, (d - i) / 5))
            out = cv2.addWeighted(DARK, a, out, 1 - a, 0)
    if not (b and b[0] not in ("cut",)):
        for k, s, e in cap_segs:
            if s <= g <= e + 8:
                c = img(os.path.join(OV, "caps", k + ".png"))
                pin = ezo((g - s) / 9); pout = 1 - clamp((g - e) / 8) if g > e else 1.0
                h, w = c.shape[:2]; cx_, cy_ = (OW - w) // 2, OH - 58 - h + int(20 * (1 - pin))
                blend(out, c, cx_, cy_, pin * pout); sheen(out, c, s, g, cx_, cy_)
        for s, d, ds in pred:
            if s <= g < s + d:
                blend(out, img(os.path.join(OV, "predict", f"{min(ds - 1, int((g - s) * ds / d)):04d}.png")), 0, 0, 1.0)
        tu = g - PARI_IN                                                         # title chip, first ~4 s
        if 0 <= tu < 135:
            ta = ezo(tu / 12.0) * (1 - clamp((tu - 123) / 12.0))
            blend(out, img(os.path.join(OV, "chips", "title.png")), 0, int(-14 * (1 - ezo(tu / 12.0))), ta)
        n = CHIP[g]
        if n:
            s_on = max([e["f"] for e in OUT_EV if e.get("chip") == 1 and e["f"] <= g] or [g])
            a = ezo((g - s_on) / 12.0)
            blend(out, img(os.path.join(OV, "chips", f"{n}.png")), 0, int(-16 * (1 - a)), a)
        else:
            off = [e["f"] for e in OUT_EV if e.get("chip") == 0 and e["f"] <= g]
            if off and g - off[-1] < 6 and CHIP[off[-1] - 1]:
                blend(out, img(os.path.join(OV, "chips", f"{CHIP[off[-1] - 1]}.png")), 0, 0, 1 - (g - off[-1]) / 6)
    pari(out, g)
    for f0, amt in PULSE:                                                        # fast onset, 0.4 s eased decay
        u = g - f0
        if 0 <= u < 14:
            a = amt * (min(1.0, (u + 1) / 2) if u < 2 else (1 - ease((u - 2) / 12)))
            out = np.clip(out.astype(np.float32) * (1 + a) + 255 * a * 0.22, 0, 255).astype(np.uint8)
    return out

def writer(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

if __name__ == "__main__":
    json.dump({"fps": FPS, "frames": TOTAL, "events": OUT_EV}, open(os.path.join(HERE, "timeline4_out.json"), "w"))
    a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (0, TOTAL)
    w = writer(os.path.join(HERE, "preview4.mp4" if len(sys.argv) == 3 else "video4_noaudio.mp4"))
    for g in range(a, min(b, TOTAL)):
        w.stdin.write(frame(g).tobytes())
        if g % 300 == 0: print("frame", g, "/", TOTAL, flush=True)
    w.stdin.close(); w.wait()
    print("done", TOTAL, "frames", round(TOTAL / FPS, 1), "s")

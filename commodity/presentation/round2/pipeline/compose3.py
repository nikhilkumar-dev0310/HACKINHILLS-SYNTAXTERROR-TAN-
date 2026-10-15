"""v3 compositor: camera, captions, statement cards, the "your guess" countdown, quick dark cuts.
Frames the director marked as setup (`skip`) are left out, so every cut is fast.

    python compose3.py               -> video3_noaudio.mp4, timeline3_out.json (events in output frames)
    python compose3.py 300 600       -> preview3.mp4 of output frames 300-600
"""
import hashlib, json, math, os, subprocess, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OW, OH, FPS = 1920, 1080, 30
TL = json.load(open(os.path.join(HERE, "timeline3.json")))
VW, VH, DSF, NS = TL["vw"], TL["vh"], TL["dsf"], TL["frames"]
EV = TL["events"]
OV = os.path.join(HERE, "ov3")
CAPMETA = json.load(open(os.path.join(OV, "caps", "meta.json")))

ease = lambda p: 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, p)))
ezo = lambda p: 1 - (1 - max(0.0, min(1.0, p))) ** 3

# ------------------------------------------------------------------ which source frames are kept
skip = np.zeros(NS, bool)
for e in EV:
    if "skip" in e: skip[e["f"]:e["f"] + e["skip"]] = True
# v3.3 pace: the site footage plays 25% faster (4 of every 5 frames kept), so the cut is under 1:30 with every
# scene and caption still in it. Events that fall on a dropped frame land on the next kept one.
_k = 0
for f in range(NS):
    if not skip[f]:
        if _k % 5 == 4: skip[f] = True
        _k += 1
KEEP = [f for f in range(NS) if not skip[f]]
N = len(KEEP)
out_of = np.cumsum(~skip) - 1                         # output index of each kept source frame
def to_out(f):
    f = min(max(0, f), NS - 1)
    while f < NS - 1 and skip[f]: f += 1              # an event inside dropped frames lands on the next kept one
    return int(out_of[f])

# ------------------------------------------------------------------ camera (in source frames, then sampled)
def crop_for(rect, zmax):
    if rect is None: return (0.0, 0.0, float(VW))
    x, y, w, h = rect
    z = max(1.0, min(zmax, VW / max(w, 1), VH * 0.78 / max(h, 1)))
    W, H = VW / z, VH / z
    cx, cy = x + w / 2, y + h / 2
    return (min(max(cx - W / 2, 0), VW - W), min(max(cy - 0.45 * H, 0), VH - H), W)

cam_src = [None] * NS
spot_src = [None] * NS                                 # (target rect in page px, source frame the camera arrived)
_tgt, _arr = None, None
cur, start, target, t0, dur = (0.0, 0.0, float(VW)), None, None, 0, 1
cam_ev = {e["f"]: e for e in EV if "cam" in e}
for f in range(NS):
    if f in cam_ev:
        e = cam_ev[f]; start, target, t0, dur = cur, crop_for(e["cam"], e.get("zmax", 1.45)), f, max(1, e["dur"])
        _tgt, _arr = e["cam"], f + max(1, e["dur"])
    if target is not None:
        p = ease((f - t0 + 1) / dur)
        cur = tuple(a + (b - a) * p for a, b in zip(start, target))
        if p >= 1: target = None
    cam_src[f] = cur
    spot_src[f] = (_tgt, _arr) if _tgt is not None else None

# ------------------------------------------------------------------ spotlight targets: where the page is changing
# (motion3.py). Runs of at least 8 frames; each held 15 frames after the motion stops; age counts from its start.
MOT = json.load(open(os.path.join(HERE, "motion3.json")))
MSPOT = [None] * NS
_runs, _cur = [], None
for f in range(NS):
    b_ = MOT[f] if f < len(MOT) else None
    if b_ is not None and _cur is not None and _cur[1] == f - 1: _cur[1] = f; _cur[2] = b_
    elif b_ is not None: _cur = [f, f, b_]; _runs.append(_cur)
for f0, f1, b_ in _runs:
    if f1 - f0 < 8: continue
    for f in range(f0, min(NS, f1 + 16)):
        MSPOT[f] = (MOT[f] if f <= f1 and MOT[f] else b_, f0, max(0.0, 1 - (f - f1) / 15) if f > f1 else 1.0)

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
    if e["cap"]: cur_cap = [hashlib.md5(e["cap"].encode()).hexdigest()[:12], e["f"], TOTAL]
if cur_cap: cap_segs.append(cur_cap)
pred = [(e["f"], e["predict"], e["predict_src"]) for e in OUT_EV if "predict" in e]
# v3.1 attention layer: tied to meaning, low amplitude
BLOOM = {e["f"]: (0.07 if e["sfx"] in ("impact", "impact_big") else 0.04) for e in OUT_EV if e.get("sfx") in ("impact", "impact_big", "reveal", "alert")}
_g = np.random.default_rng(5)
DUST = _g.uniform(0, 1, (130, 5))                                                                # x, y, size, speed, phase (cards)
PDUST = _g.uniform(0, 1, (45, 5))                                                                # a sparser, fainter layer over the site
def _sprite(r):
    k = np.arange(-2 * r, 2 * r + 1, dtype=np.float32); g_ = np.exp(-(k[None, :] ** 2 + k[:, None] ** 2) / (2 * (r * 0.75) ** 2)); return g_[:, :, None]
SPR = {r: _sprite(r) for r in (1, 2, 3)}

# ------------------------------------------------------------------ Pari, the mascot: reacts to what happens on screen
# Layers, lowest priority first: talks as each caption lands, points (with a hop) when the spotlight lands, then the
# story beats, then the key sounds (the number, "No.", the crash, the twist). Idle Pari bobs and blinks.
PZ = [None] * (TOTAL + 1); HOP = []
def _put(s0, d, pose, hop=False):
    for g in range(max(0, s0), min(TOTAL + 1, s0 + d)):
        PZ[g] = pose(g - s0) if callable(pose) else pose
    if hop: HOP.append(s0)
for k_, s0, e0 in cap_segs:
    _put(s0, 34, lambda i: "talk" if (i // 4) % 2 == 0 else "idle")
_last = -99
for f0, f1, b_ in _runs:
    if f1 - f0 >= 8 and to_out(f0) - _last > 45:            # point at a new spotlight (not more than every 1.5 s)
        _last = to_out(f0); _put(_last, 30, "point_r", hop=True)
for e in OUT_EV:
    if "beat" in e and e["beat"] == "toogood": _put(e["f"], e["dur"], "think")
    if "beat" in e and e["beat"] == "tomorrow": _put(e["f"], e["dur"], "point_r", hop=True)
    if "beat" in e and e["beat"] == "end": _put(e["f"], e["dur"], lambda i: ("wave0", "wave1")[(i // 7) % 2] if i < 60 else "cheer", hop=True)
for s0, d, ds in pred: _put(s0, d, "think")
REACT = {"impact": ("wow", 30, True), "impact_big": ("wow", 40, True), "reveal": ("no", 45, False), "alert": ("sad", 45, True),
         "cost": ("sad", 40, False), "land": ("proud", 24, False), "shimmer": ("proud", 30, False)}
for e in OUT_EV:
    if e.get("sfx") in REACT:
        pose, d, hop = REACT[e["sfx"]]; _put(e["f"], d, pose, hop)
PARI = {k: cv2.imread(os.path.join(HERE, "ov3", "pari", k + ".png"), cv2.IMREAD_UNCHANGED) for k in
        ("idle", "blink", "talk", "wow", "think", "no", "sad", "point_r", "cheer", "wave0", "wave1", "proud")}

# v3.4: Pari speaks. Short speech bubbles on the moments that matter (the words are reactions, never new claims).
from PIL import Image, ImageDraw, ImageFont
_BF = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 34)
def _bubble(text):
    l, t, r, b_ = _BF.getbbox(text); w, h = r - l + 44, b_ - t + 30
    im = Image.new("RGBA", (w + 8, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([4, 4, w + 4, h + 4], 22, fill=(255, 246, 222, 245), outline=(201, 141, 12, 255), width=4)
    d.polygon([(30, h + 2), (58, h + 2), (24, h + 28)], fill=(255, 246, 222, 245))
    d.line([(30, h + 4), (24, h + 28), (58, h + 4)], fill=(201, 141, 12, 255), width=4)
    d.text((26 - l, 17 - t), text, font=_BF, fill=(26, 19, 0, 255))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGRA)
SAY = [None] * (TOTAL + 1)
def _say(s0, d, text):
    for g in range(max(0, s0), min(TOTAL + 1, s0 + d)): SAY[g] = (text, s0, s0 + d)
SAYS = {"impact": "Whoa!", "impact_big": "Wait... what?", "reveal": "Nope.", "alert": "Ouch!", "cost": "Costs eat it.", "shimmer": "Nice!"}
_seen = set()
for e in OUT_EV:
    sx_ = e.get("sfx")
    if sx_ in SAYS and (sx_, e["f"] // 300) not in _seen:
        _seen.add((sx_, e["f"] // 300)); _say(e["f"], 40, SAYS[sx_])
    if e.get("beat") == "toogood": _say(e["f"] + 10, e["dur"] - 10, "Hmm... too good?")
    if e.get("beat") == "tomorrow": _say(e["f"] + 8, e["dur"] - 8, "Come see today's!")
    if e.get("beat") == "end": _say(e["f"] + 6, 70, "See you there!")
for s0, d, ds in pred: _say(s0, d, "Your guess?")
BUB = {}
POINT_AT = [None] * (TOTAL + 1)          # filled by page(): where the spotlight is, so Pari's pointer can reach it
PARI_HAND = (34 + 0.8 * 264 * 0.86, OH - 46 - 0.8 * 232 * 0.62)
PARI_IN = next(g for g in range(TOTAL) if not (beat[g] and beat[g][0] == "black"))   # pops in after the black open

def pari(out, g):
    if g < PARI_IN: return
    pose = PZ[g] or ("blink" if g % 97 in (0, 1, 2, 3) else "idle")
    im = PARI[pose]
    t_in = (g - PARI_IN) / 10.0
    sc = 0.8 * (1 if t_in >= 1 else max(0.05, 1 + 2.7 * (t_in - 1) ** 3 + 1.7 * (t_in - 1) ** 2))   # ease-out-back pop
    hy, sq = 0.0, 1.0
    for h0 in HOP:
        u = (g - h0) / 11.0
        if 0 <= u < 1: hy = -26 * math.sin(math.pi * u)
        elif 1 <= u < 1.35: sq = 1 - 0.10 * math.sin(math.pi * (u - 1) / 0.35)      # squash on landing
    bob = 3.5 * math.sin(2 * math.pi * g / (FPS * 2.3))
    w, h = int(im.shape[1] * sc / sq ** 0.5), int(im.shape[0] * sc * sq)
    if w < 4 or h < 4: return
    spr = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
    base = OH - 46                                                     # feet on this line
    px_, py_ = 34 + (int(im.shape[1] * 0.8) - w) // 2, int(base - h + hy + bob)
    # a dotted gold "laser" from Pari's hand to whatever the spotlight is on, while Pari points
    tgt = POINT_AT[g]
    if pose == "point_r" and tgt is not None:
        hx, hy_ = PARI_HAND[0], PARI_HAND[1] + hy + bob
        tx, ty = tgt; L = math.hypot(tx - hx, ty - hy_)
        if L > 80:
            n = int(L / 22); lay = out.copy()
            for i in range(1, n):
                u = i / n; ph = (u * 6 - g * 0.35) % 1.0
                xx = hx + (tx - hx) * u; yy = hy_ + (ty - hy_) * u - 60 * math.sin(math.pi * u)
                cv2.circle(lay, (int(xx), int(yy)), 3 + int(2 * (ph < 0.3)), (61, 184, 245), -1, cv2.LINE_AA)
            cv2.circle(lay, (int(tx), int(ty)), 9 + int(3 * math.sin(g / 3)), (61, 184, 245), 3, cv2.LINE_AA)
            cv2.addWeighted(lay, 0.8, out, 0.2, 0, out)
    blend(out, spr, px_, py_, 1.0)
    sy_ = SAY[g]
    if sy_:
        text, s0, s1 = sy_
        if text not in BUB: BUB[text] = _bubble(text)
        bm = BUB[text]; u = (g - s0) / 7.0
        sc2 = 1.0 if u >= 1 else max(0.05, 1 + 2.7 * (u - 1) ** 3 + 1.7 * (u - 1) ** 2)
        fa = min(1.0, (s1 - g) / 6.0)
        bw, bh = int(bm.shape[1] * sc2), int(bm.shape[0] * sc2)
        if bw > 6 and bh > 6:
            blend(out, cv2.resize(bm, (bw, bh), interpolation=cv2.INTER_AREA), px_ + int(w * 0.62), py_ - bh + 18, fa)

# ------------------------------------------------------------------ drawing
def blend(dst, src, x, y, a=1.0):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0 or a <= 0: return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    al = (s[:, :, 3:4].astype(np.float32) / 255.0) * a if s.shape[2] == 4 else np.float32(a)
    rgb = s[:, :, :3].astype(np.float32)
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (rgb * al + d * (1 - al)).astype(np.uint8)

_cache = {}
def img(path, flags=cv2.IMREAD_UNCHANGED):
    if path not in _cache:
        if len(_cache) > 400: _cache.clear()
        _cache[path] = cv2.imread(path, flags)
    return _cache[path]

_yy, _xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
_r = np.sqrt(((_xx - OW / 2) / (OW / 2)) ** 2 + ((_yy - OH / 2) / (OH / 2)) ** 2)
VIG = (1 - 0.14 * np.clip((_r - 0.55) / 0.9, 0, 1) ** 1.6)[:, :, None].astype(np.float32)
DARK = np.full((OH, OW, 3), (13, 11, 10), np.uint8)

def page(g):
    f = KEEP[min(g, N - 1)]
    im = cv2.imread(os.path.join(HERE, "frames3", f"{f:05d}.jpg"))
    x0, y0, W = cam_src[f]
    # breathing camera: never perfectly still (v3.2: about 3% zoom and 10 px of drift, on slow 8-13 s periods)
    z = 1 + 0.03 * (0.5 - 0.5 * math.cos(2 * math.pi * g / (FPS * 8.0)))
    W2 = W / z; x0 = x0 + (W - W2) / 2 + 10 * math.sin(2 * math.pi * g / (FPS * 13.0)); W = W2
    y0 = y0 + (W * z - W) * VH / VW / 2 + 6 * math.sin(2 * math.pi * g / (FPS * 11.0) + 1)
    x0 = min(max(x0, 0), VW - W); H = W * VH / VW; y0 = min(max(y0, 0), VH - H)
    sx, sy, sw, sh = x0 * DSF, y0 * DSF, W * DSF, H * DSF
    if sw > OW * 1.02:
        out = cv2.resize(im[int(sy):int(sy + sh), int(sx):int(sx + sw)], (OW, OH), interpolation=cv2.INTER_AREA)
    else:
        M = np.float32([[OW / sw, 0, -sx * OW / sw], [0, OH / sh, -sy * OH / sh]])
        out = cv2.warpAffine(im, M, (OW, OH), flags=cv2.INTER_CUBIC)
    out = (out.astype(np.float32) * VIG).astype(np.uint8)
    sp = MSPOT[f]
    if sp is not None:
        (rx, ry, rw, rh), start, fade = sp
        k = OW / W                                      # page px -> output px
        box = ((rx - x0) * k, (ry - y0) * k, rw * k, rh * k)
        age = g - to_out(start)
        if 0 <= age and box[2] * box[3] < 0.45 * OW * OH and box[2] > 20 and box[3] > 12:
            spotlight(out, box, min(1.0, age / 10.0) * fade, age)
            if g <= TOTAL: POINT_AT[g] = (box[0], box[1] + box[3] / 2)
    ss = spot_src[f]
    if ss is not None and ss[0] is not None:                # v3.4: gold focus brackets lock onto where the camera went
        rx, ry, rw, rh = ss[0]; k = OW / W
        age = g - to_out(ss[1])
        if -6 <= age < 60:
            brackets(out, ((rx - x0) * k, (ry - y0) * k, rw * k, rh * k), age)
            if g <= TOTAL and POINT_AT[g] is None and age >= 0: POINT_AT[g] = ((rx - x0) * k, (ry - y0 + rh / 2) * k)
    return out

def brackets(out, box, age):
    """Four gold corner brackets that close in on the target, pulse twice, then fade."""
    x, y, w, h = box
    if w < 30 or h < 16 or w > OW * 0.95: return
    t = ezo((age + 6) / 12.0); pad = 14 + 60 * (1 - t)
    a = min(1.0, (age + 6) / 6.0) * (1.0 if age < 44 else max(0.0, (60 - age) / 16.0))
    x0, y0, x1, y1 = int(x - pad), int(y - pad), int(x + w + pad), int(y + h + pad)
    L = int(min(46, 0.3 * min(x1 - x0, y1 - y0))); th = 5 if age % 30 < 15 else 4
    lay = out.copy(); c = (61, 184, 245)
    for (cx, cy, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.line(lay, (cx, cy), (cx + dx * L, cy), c, th, cv2.LINE_AA); cv2.line(lay, (cx, cy), (cx, cy + dy * L), c, th, cv2.LINE_AA)
    if 0 <= age < 24:                                    # one soft glow ring expanding from the target
        r = int(0.5 * math.hypot(w, h) + age * 5)
        cv2.ellipse(lay, (int(x + w / 2), int(y + h / 2)), (r, int(r * min(1.0, h / max(w, 1)) + age * 2)), 0, 0, 360, c, 2, cv2.LINE_AA)
    cv2.addWeighted(lay, 0.9 * a, out, 1 - 0.9 * a, 0, out)

_sy, _sx = np.mgrid[0:OH // 4, 0:OW // 4].astype(np.float32) * 4
def spotlight(out, box, a, age):
    """Dim everything outside the target (soft edge), and trace a gold outline round it once as the camera lands."""
    x, y, w, h = box; pad = 26
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    dx = np.maximum(np.maximum(x0 - _sx, _sx - x1), 0); dy = np.maximum(np.maximum(y0 - _sy, _sy - y1), 0)
    d = np.sqrt(dx * dx + dy * dy)
    m = 1 - 0.42 * a * np.clip(d / 90.0, 0, 1) ** 0.8
    m = cv2.resize(m, (OW, OH), interpolation=cv2.INTER_LINEAR)[:, :, None]
    out[:] = (out.astype(np.float32) * m).astype(np.uint8)
    if age < 34:                                        # the outline draws itself, then fades
        t = min(1.0, age / 14.0); fade = 1.0 if age < 20 else (34 - age) / 14.0
        per = 2 * (x1 - x0 + y1 - y0); L = per * (1 - (1 - t) ** 3)
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        lay = out.copy(); run = 0.0
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            seg = abs(bx - ax) + abs(by - ay)
            if run >= L: break
            u = min(1.0, (L - run) / seg)
            cv2.line(lay, (int(ax), int(ay)), (int(ax + (bx - ax) * u), int(ay + (by - ay) * u)), (61, 184, 245), 4, cv2.LINE_AA)
            run += seg
        cv2.addWeighted(lay, 0.85 * fade, out, 1 - 0.85 * fade, 0, out)

GOLD = np.array([61, 184, 245], np.float32)
def dust(img, g, pts=None, amax=0.30):
    """Slow, soft gold dust: many faint specks on the statement cards, a sparser layer over the site."""
    for x, y, sz, sp, ph in (DUST if pts is None else pts):
        px = int((x * OW + 22 * math.sin(g / 45 + ph * 6)) % OW)
        py = int((y * OH - g * (0.3 + sp * 0.8)) % OH)
        a = amax * (0.25 + 0.75 * (0.5 + 0.5 * math.sin(g / 27 + ph * 9))) * (0.55 + 0.45 * sz)
        r_ = 1 + int(sz * 2.99); m = SPR[r_] * a; R = 2 * r_
        y0, y1, x0, x1 = py - R, py + R + 1, px - R, px + R + 1
        if y0 < 0 or x0 < 0 or y1 > OH or x1 > OW: continue
        patch = img[y0:y1, x0:x1].astype(np.float32)
        img[y0:y1, x0:x1] = (patch * (1 - m) + GOLD * m).astype(np.uint8)

def sheen(img, k, s, g, x, y):
    """A soft light sweep across a caption once, as it appears."""
    p = ezo((g - s - 4) / 20.0) if 0 <= (g - s - 4) / 20.0 <= 1 else -1
    if p < 0: return
    c = img_cap(k); h, w = c.shape[:2]
    cx = int(-120 + (w + 240) * p)
    xs = np.arange(w)[None, :]
    band = np.exp(-((xs - cx - (np.arange(h)[:, None] - h / 2) * 0.35) ** 2) / (2 * 52.0 ** 2)) * (c[:, :, 3] / 255.0) * 0.55
    y0, x0 = max(0, y), max(0, x)
    reg = img[y0:y0 + h, x0:x0 + w].astype(np.float32)
    band = band[:reg.shape[0], :reg.shape[1], None]
    img[y0:y0 + h, x0:x0 + w] = np.clip(reg + band * np.array([200, 235, 255], np.float32), 0, 255).astype(np.uint8)   # warm white

def img_cap(k): return img(os.path.join(OV, "caps", k + ".png"))

def frame(g):
    b = beat[g]
    if b and b[0] in ("black",):
        out = DARK.copy()
    elif b and b[0] != "cut":
        name, i, d = b
        out = img(os.path.join(OV, "beats", name, f"{i:04d}.jpg"), cv2.IMREAD_COLOR).copy()
        if name not in ("black",): dust(out, g)
        fin = 1.0 if name in ("end",) or i >= 6 else (i + 1) / 7            # cross-fade in over 6 frames
        fout = 1.0 if name in ("end",) or i < d - 6 else (d - i) / 7        # and out over 6, except the last card: hard cut
        a = min(fin, fout)
        if a < 1: out = cv2.addWeighted(out, a, page(g), 1 - a, 0)
    else:
        out = page(g)
        dust(out, g, PDUST, 0.12)
        if b:                                                                 # quick dip through dark
            name, i, d = b
            a = min(1.0, (i + 1) / 3, (d - i) / 4)
            out = cv2.addWeighted(DARK, a, out, 1 - a, 0)
    if not (b and b[0] not in ("cut",)):
        for k, s, e in cap_segs:
            if s <= g <= e + 8:
                c = img(os.path.join(OV, "caps", k + ".png"))
                pin = ezo((g - s) / 8); pout = 1 - max(0.0, (g - e) / 8) if g > e else 1.0
                h, w = c.shape[:2]
                cx_, cy_ = (OW - w) // 2, OH - 58 - h + int(22 * (1 - pin))
                blend(out, c, cx_, cy_, pin * pout)
                sheen(out, k, s, g, cx_, cy_)
        for s, d, ds in pred:
            if s <= g < s + d:
                blend(out, img(os.path.join(OV, "predict", f"{min(ds - 1, int((g - s) * ds / d)):04d}.png")), 0, 0, 1.0)
    pari(out, g)
    # a soft bloom exactly on the four key sounds (the number, the reveal, the crash, the twist)
    for f0, amt in BLOOM.items():
        if f0 <= g < f0 + 9:
            a = amt * (1 - (g - f0) / 9) ** 2
            out = np.clip(out.astype(np.float32) * (1 + a) + 255 * a * 0.25, 0, 255).astype(np.uint8)
    return out

def writer(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

SPEED = float(os.environ.get("PARITY_SPEED", "1.0"))    # >1 plays the cut faster (sound and captions follow); v3.4 runs 87 s at 1.0

if __name__ == "__main__":
    def sc(v): return int(round(v / SPEED))
    EVS = []
    for e in OUT_EV:
        e2 = dict(e); e2["f"] = sc(e["f"])
        for k in ("dur", "tick", "rise", "predict", "d"):
            if k in e2 and k != "d": e2[k] = max(1, sc(e2[k]))
        EVS.append(e2)
    json.dump({"fps": FPS, "frames": sc(TOTAL), "events": EVS}, open(os.path.join(HERE, "timeline3_out.json"), "w"))
    OUTN = sc(TOTAL)
    a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (0, OUTN)
    w = writer(os.path.join(HERE, "preview3.mp4" if len(sys.argv) == 3 else "video3_noaudio.mp4"))
    for j in range(a, min(b, OUTN)):
        w.stdin.write(frame(min(TOTAL, int(round(j * SPEED)))).tobytes())
        if j % 300 == 0: print("frame", j, "/", OUTN, flush=True)
    w.stdin.close(); w.wait()
    print("done", OUTN, "frames", round(OUTN / FPS, 1), "s")

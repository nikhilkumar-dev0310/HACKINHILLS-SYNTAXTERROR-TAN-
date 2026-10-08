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
cur, start, target, t0, dur = (0.0, 0.0, float(VW)), None, None, 0, 1
cam_ev = {e["f"]: e for e in EV if "cam" in e}
for f in range(NS):
    if f in cam_ev:
        e = cam_ev[f]; start, target, t0, dur = cur, crop_for(e["cam"], e.get("zmax", 1.45)), f, max(1, e["dur"])
    if target is not None:
        p = ease((f - t0 + 1) / dur)
        cur = tuple(a + (b - a) * p for a, b in zip(start, target))
        if p >= 1: target = None
    cam_src[f] = cur

# ------------------------------------------------------------------ events in output frames
OUT_EV = []
for e in EV:
    if "skip" in e: continue
    e2 = dict(e); e2["f"] = to_out(e["f"]); OUT_EV.append(e2)
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
pred = [(e["f"], e["predict"]) for e in OUT_EV if "predict" in e]

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
    x0, y0, W = cam_src[f]; H = W * VH / VW
    sx, sy, sw, sh = x0 * DSF, y0 * DSF, W * DSF, H * DSF
    if sw > OW * 1.02:
        out = cv2.resize(im[int(sy):int(sy + sh), int(sx):int(sx + sw)], (OW, OH), interpolation=cv2.INTER_AREA)
    else:
        M = np.float32([[OW / sw, 0, -sx * OW / sw], [0, OH / sh, -sy * OH / sh]])
        out = cv2.warpAffine(im, M, (OW, OH), flags=cv2.INTER_CUBIC)
    return (out.astype(np.float32) * VIG).astype(np.uint8)

def frame(g):
    b = beat[g]
    if b and b[0] in ("black",):
        out = DARK.copy()
    elif b and b[0] != "cut":
        name, i, d = b
        out = img(os.path.join(OV, "beats", name, f"{i:04d}.jpg"), cv2.IMREAD_COLOR).copy()
        fin = 1.0 if name in ("end",) or i >= 6 else (i + 1) / 7            # cross-fade in over 6 frames
        fout = 1.0 if name in ("end",) or i < d - 6 else (d - i) / 7        # and out over 6, except the last card: hard cut
        a = min(fin, fout)
        if a < 1: out = cv2.addWeighted(out, a, page(g), 1 - a, 0)
    else:
        out = page(g)
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
                blend(out, c, (OW - w) // 2, OH - 58 - h + int(22 * (1 - pin)), pin * pout)
        for s, d in pred:
            if s <= g < s + d:
                blend(out, img(os.path.join(OV, "predict", f"{g - s:04d}.png")), 0, 0, 1.0)
    return out

def writer(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)

if __name__ == "__main__":
    json.dump({"fps": FPS, "frames": TOTAL, "events": OUT_EV}, open(os.path.join(HERE, "timeline3_out.json"), "w"))
    a, b = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) == 3 else (0, TOTAL)
    w = writer(os.path.join(HERE, "preview3.mp4" if len(sys.argv) == 3 else "video3_noaudio.mp4"))
    for g in range(a, min(b, TOTAL)):
        w.stdin.write(frame(g).tobytes())
        if g % 300 == 0: print("frame", g, "/", TOTAL, flush=True)
    w.stdin.close(); w.wait()
    print("done", TOTAL, "frames", round(TOTAL / FPS, 1), "s")

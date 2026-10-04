"""Compositor: camera moves, captions with Pari, chapter cards, intro and outro -> video.mp4 (no audio yet).

    python compose.py [start_frame end_frame]     (a range renders a preview of the main section only)
"""
import hashlib, json, math, os, subprocess, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OW, OH, FPS = 1920, 1080, 30
SRC = json.load(open(os.path.join(HERE, "timeline.json")))
TL = json.load(open(os.path.join(HERE, "timeline_fast.json")))
VW, VH, DSF, N = TL["vw"], TL["vh"], TL["dsf"], TL["frames"]
NS, WARP = SRC["frames"], TL["warp"]
CARD_SRC = 66
LABELS = ["The front page", "The brief", "Relative value", "Term structure", "Backtest", "Signals", "Contracts", "Data quality"]
CAPMETA = json.load(open(os.path.join(HERE, "ov/caps/meta.json")))
INTRO = sorted(os.listdir(os.path.join(HERE, "ov/intro_fast")))
OUTRO = sorted(os.listdir(os.path.join(HERE, "ov/outro_fast")))
XFADE = 10

ease = lambda p: 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, p)))
ezo = lambda p: 1 - (1 - max(0.0, min(1.0, p))) ** 3


def crop_for(rect, zmax):
    if rect is None: return (0.0, 0.0, float(VW))
    x, y, w, h = rect
    z = max(1.0, min(zmax, VW / max(w, 1), VH * 0.78 / max(h, 1)))
    W, H = VW / z, VH / z
    cx, cy = x + w / 2, y + h / 2
    x0 = min(max(cx - W / 2, 0), VW - W)
    y0 = min(max(cy - 0.45 * H, 0), VH - H)
    return (x0, y0, W)


# ------------------------------------------------------------------ per-frame state from the timeline
cam_src = [None] * NS
cur, start, target, t0, dur = (0.0, 0.0, float(VW)), None, None, 0, 1
src_cam_ev = {e["f"]: e for e in SRC["events"] if "cam" in e}
for f in range(NS):
    if f in src_cam_ev:
        e = src_cam_ev[f]; start, target, t0, dur = cur, crop_for(e["cam"], e.get("zmax", 1.45)), f, max(1, e["dur"])
    if target is not None:
        p = ease((f - t0 + 1) / dur)
        cur = tuple(a + (b - a) * p for a, b in zip(start, target))
        if p >= 1: target = None
    cam_src[f] = cur
cam = [cam_src[WARP[g]] for g in range(N)]
cap = [None] * N; card = [None] * N
cam_ev = {}; cap_ev = {}; card_ev = {}
chapter = 0
for e in TL["events"]:
    if "cam" in e: cam_ev[e["f"]] = e
    if "cap" in e: cap_ev.setdefault(e["f"], []).append(e)
    if "card" in e: card_ev[e["f"]] = e
ch_at = []
cur_cap = None
for f in range(N):
    if f in card_ev: chapter = card_ev[f]["card"]; ch_at.append(f)
    for e in cap_ev.get(f, []):
        if e["cap"] is None: cur_cap = None
        else:
            label = f"{chapter:02d} · {LABELS[chapter - 1]}"
            cur_cap = (hashlib.md5((label + "|" + e["cap"]).encode()).hexdigest()[:12], f)
    cap[f] = cur_cap
for f, e in card_ev.items():
    for i in range(e["dur"]):
        if f + i < N: card[f + i] = (e["card"], i, e["dur"])

# caption segments for cross-fades: list of (key, start, end)
segs = []
for f in range(N):
    c = cap[f]
    if c and (not segs or segs[-1][0] != c[0] or segs[-1][1] != c[1]): segs.append([c[0], c[1], f])
    if c and segs: segs[-1][2] = f
seg_at = {}
for k, s, e in segs:
    for f in range(s, min(N, e + 9)): seg_at.setdefault(f, []).append((k, s, e))

# ------------------------------------------------------------------ sprites
def load_rgba(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    return im
CAPS = {}
def cap_img(k):
    if k not in CAPS: CAPS[k] = load_rgba(os.path.join(HERE, "ov/caps", k + ".png"))
    return CAPS[k]
PARI = {(m, b): cv2.resize(load_rgba(os.path.join(HERE, f"ov/pari_{m}_{b}.png")), (126, 130), interpolation=cv2.INTER_AREA) for m in ("happy", "talk", "wow") for b in (0, 1)}


def blend(dst, src, x, y, a=1.0):
    """Alpha-blend RGBA (or BGR with alpha a) src onto BGR dst at (x, y)."""
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0 or a <= 0: return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    if s.shape[2] == 4:
        al = (s[:, :, 3:4].astype(np.float32) / 255.0) * a; rgb = s[:, :, :3].astype(np.float32)
    else:
        al = np.float32(a); rgb = s.astype(np.float32)
    d = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (rgb * al + d * (1 - al)).astype(np.uint8)


def caption_layer(img, f):
    for k, s, e in seg_at.get(f, []):
        c = cap_img(k)
        h, w = c.shape[:2]
        pin = ezo((f - s) / 9)
        pout = 1 - max(0.0, (f - e) / 8) if f > e else 1.0
        a = pin * pout
        x = (OW - w) // 2; y = OH - 46 - h + int(26 * (1 - pin))
        blend(img, c, x, y, a)
        # Pari: hop when a caption starts, talk for a moment, blink now and then
        age = f - s
        hop = 14 * math.sin(math.pi * min(1, age / 10)) if age < 10 else 0
        bob = 0
        mood = ("talk" if (age // 4) % 2 == 0 else "happy") if age < 20 else "happy"
        blink = 1 if (f % 97) in (0, 1, 2) else 0
        p = PARI[(mood, blink)]
        blend(img, p, x + 14, int(y + h / 2 - 78 - hop + bob), a)


def progress_layer(img, f, total_main):
    p = f / max(1, total_main - 1)
    img[OH - 6:OH, :, :] = (img[OH - 6:OH, :, :].astype(np.float32) * 0.82).astype(np.uint8)
    img[OH - 6:OH, :int(OW * p), :] = (39, 162, 226)   # gold, BGR
    for s in ch_at:
        x = int(OW * s / max(1, total_main - 1))
        img[OH - 10:OH, max(0, x - 1):x + 2, :] = (255, 255, 255)


def main_frame(f):
    im = cv2.imread(os.path.join(HERE, "frames", f"{WARP[f]:05d}.jpg"))
    x0, y0, W = cam[f]; H = W * VH / VW
    sx, sy, sw, sh = x0 * DSF, y0 * DSF, W * DSF, H * DSF
    M = np.float32([[OW / sw, 0, -sx * OW / sw], [0, OH / sh, -sy * OH / sh]])
    interp = cv2.INTER_AREA if sw > OW * 1.02 else cv2.INTER_CUBIC
    out = cv2.warpAffine(im, M, (OW, OH), flags=interp if interp != cv2.INTER_AREA else cv2.INTER_LINEAR)
    if sw > OW * 1.02:   # downscale cleanly when the crop is wider than the output
        crop = im[int(sy):int(sy + sh), int(sx):int(sx + sw)]
        out = cv2.resize(crop, (OW, OH), interpolation=cv2.INTER_AREA)
    out = (out.astype(np.float32) * VIG).astype(np.uint8)
    if card[f]:
        c, i, d = card[f]
        cim = cv2.imread(os.path.join(HERE, "ov/cards", f"{c}_{min(CARD_SRC - 1, round(i * CARD_SRC / d)):03d}.jpg"))
        a = min(1.0, i / 7, (d - 1 - i) / 7) if i > 0 else 0.0
        a = max(0.0, min(1.0, a))
        if i < 7 and f < 7: a = 1.0                    # the very first card follows the dark intro: no fade-in
        out = cv2.addWeighted(cim, a, out, 1 - a, 0) if a < 1 else cim.copy()
    caption_layer(out, f)
    if not card[f] or 0 < card[f][1] < 3 or card[f][1] > card[f][2] - 4: progress_layer(out, f, N)
    return out


_yy, _xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
_r = np.sqrt(((_xx - OW / 2) / (OW / 2)) ** 2 + ((_yy - OH / 2) / (OH / 2)) ** 2)
VIG = (1 - 0.16 * np.clip((_r - 0.55) / 0.9, 0, 1) ** 1.6)[:, :, None].astype(np.float32)


def writer(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path], stdin=subprocess.PIPE)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        a, b = int(sys.argv[1]), int(sys.argv[2])
        w = writer(os.path.join(HERE, "preview_fast.mp4"))
        for f in range(a, min(b, N)): w.stdin.write(main_frame(f).tobytes())
        w.stdin.close(); w.wait(); print("preview", a, b); sys.exit()
    w = writer(os.path.join(HERE, "video_fast_noaudio.mp4"))
    for n in INTRO: w.stdin.write(cv2.imread(os.path.join(HERE, "ov/intro_fast", n)).tobytes())
    last = None; cut_from, cut_i = None, 99
    for f in range(N):
        fr = main_frame(f)
        if f and WARP[f] - WARP[f - 1] > 20: cut_from, cut_i = last, 0      # a removed section: soften the jump
        if cut_i < 6: fr = cv2.addWeighted(fr, (cut_i + 1) / 7, cut_from, 1 - (cut_i + 1) / 7, 0); cut_i += 1
        last = fr; w.stdin.write(fr.tobytes())
        if f % 300 == 0: print("main", f, "/", N, flush=True)
    for i, n in enumerate(OUTRO):
        o = cv2.imread(os.path.join(HERE, "ov/outro_fast", n))
        if i < XFADE: o = cv2.addWeighted(o, i / XFADE, last, 1 - i / XFADE, 0)
        w.stdin.write(o.tobytes())
    w.stdin.close(); w.wait()
    json.dump({"intro": len(INTRO), "main": N, "outro": len(OUTRO)}, open(os.path.join(HERE, "layout_fast.json"), "w"))
    print("done")

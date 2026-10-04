"""Re-time the captured tour: still frames are squeezed, motion keeps near real speed, captions keep reading time.
    python warp.py  -> timeline_fast.json  (warp[g] = source frame for output frame g; events in output frames)"""
import json, math, re
import numpy as np
FPS = 30
TL = json.load(open("timeline.json")); N = TL["frames"]; EV = TL["events"]
mot = np.array(json.load(open("motion.json")))
CARD_OUT = 40                     # chapter card: 1.5 s instead of 2.2 s
MOT_SPEED, MIN_STILL = 1.4, 0.10 # motion plays at 1.25x; a still frame costs at least 0.12 of a frame
READ_CPS, READ_PAD, READ_MIN = 18.0, 0.55, 2.1
from captions_fast import NEW, DROP

# camera movement per source frame (moving camera counts as motion)
camf = np.zeros(N, bool)
for e in EV:
    if "cam" in e: camf[e["f"]:min(N, e["f"] + e["dur"] + 1)] = True
moving = (mot > 0.002) | camf
# dilate by 2 frames so motion edges stay smooth
mv = moving.copy()
for s in (1, 2): mv[s:] |= moving[:-s]; mv[:-s] |= moving[s:]

# segment boundaries = every caption / card start
bounds = sorted({0, N} | {e["f"] for e in EV if "cap" in e or "card" in e})
cap_at = {e["f"]: NEW.get(e["f"], e["cap"]) for e in EV if "cap" in e}
card_at = {e["f"]: e for e in EV if "card" in e}
dur = np.zeros(N)                 # output length (in frames) each source frame occupies
report = []
for a, b in zip(bounds[:-1], bounds[1:]):
    src = b - a
    if a in card_at:
        cd = card_at[a]["dur"]; dur[a:a + cd] = CARD_OUT / cd
        a2 = a + cd
        if a2 >= b: continue
        a, src = a2, b - a2
    if a in DROP: dur[a:b] = 0; report.append((a, src / FPS, 0.0, "CUT")); continue
    txt = cap_at.get(a)
    need = (len(re.sub(r"\*\*", "", txt)) / READ_CPS + READ_PAD) * FPS if txt else 0
    need = max(need, READ_MIN * FPS) if txt else 0
    M = int(mv[a:b].sum()); S = src - M
    tgt = min(src / 1.1, max(need, M / MOT_SPEED + S * MIN_STILL))
    av, bv = 1 / MOT_SPEED, (tgt - M / MOT_SPEED) / S if S else 0
    if S and bv < MIN_STILL: bv = MIN_STILL; av = (tgt - S * bv) / M if M else 0
    if bv > av: av = bv = tgt / src
    seg = np.where(mv[a:b], av, bv); dur[a:b] = seg
    report.append((a, src / FPS, seg.sum() / FPS, txt[:40] if txt else ""))

cum = np.concatenate([[0], np.cumsum(dur)])     # output position where each source frame starts
NOUT = int(round(cum[-1]))
warp = [int(min(N - 1, np.searchsorted(cum, g + 0.5, side="right") - 1)) for g in range(NOUT)]
o = lambda f: int(round(cum[f]))
events = []
for e in EV:
    if any(a <= e["f"] < b for a, b in zip(bounds[:-1], bounds[1:]) if a in DROP): continue
    e2 = dict(e); e2["f"] = o(e["f"])
    if e.get("cap"): e2["cap"] = NEW.get(e["f"], e["cap"])
    if "card" in e: e2["dur"] = CARD_OUT
    if "cam" in e: e2["dur"] = max(1, o(min(N, e["f"] + e["dur"])) - e2["f"])
    events.append(e2)
json.dump({**{k: v for k, v in TL.items() if k != "events"}, "frames": NOUT, "src_frames": N, "warp": warp, "events": events}, open("timeline_fast.json", "w"))
for r in report: print("%5d %5.1fs -> %4.1fs  %s" % r)
print("main %.1fs -> %.1fs" % (N / FPS, NOUT / FPS))

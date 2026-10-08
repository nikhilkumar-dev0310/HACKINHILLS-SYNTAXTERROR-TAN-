"""Subtitles for the v3 cut from timeline3_out.json (captions, in output frames)."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "timeline3_out.json"))); FPS = TL["fps"]
caps = sorted([e for e in TL["events"] if "cap" in e], key=lambda e: e["f"])
ts = lambda f: "%02d:%02d:%02d,%03d" % (f // FPS // 3600, f // FPS // 60 % 60, f // FPS % 60, round(f % FPS * 1000 / FPS))
out, k = [], 1
for a, b in zip(caps, caps[1:] + [{"f": TL["frames"]}]):
    if not a["cap"]: continue
    out.append(f"{k}\n{ts(a['f'])} --> {ts(b['f'] - 1)}\n{re.sub(r'[*]{2}', '', a['cap'])}\n"); k += 1
open(os.path.join(HERE, "..", "Parity_demo.srt"), "w").write("\n".join(out))
print("subtitles", k - 1)

"""Subtitles for the v4 cut from timeline4_out.json: captions, Pari's lines and the words on the statement cards,
so the subtitle file carries every number shown on screen (tests/test_video.py checks them against the data)."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "timeline4_out.json"))); FPS = TL["fps"]
D = json.load(open(os.path.join(HERE, "..", "..", "..", "dashboard", "data.json")))
ALL = D["meta"]["all"]; YEARS = int(ALL["last"][:4]) - int(ALL["first"][:4]); LAST = D["meta"]["last"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CARD = {"same": "Same gold. Four contracts. Four prices. %d years of official MCX data. %d contracts." % (YEARS, ALL["contracts"]),
        "toogood": "Too good to be true?",
        "brief": "How close are we? The brief's five directions: 5 of 5 done. Final challenge: 5 of 5 lines answered. "
                 "Still open: order-book depth. Checked by %s automated tests." % f"{D['tests']['tests']:,}",
        "tomorrow": "Tomorrow's answer isn't in this video. This video stops at %d %s %s. The site doesn't." % (int(LAST[8:]), MON[int(LAST[5:7]) - 1], LAST[:4]),
        "end": "Parity. See today's answer: parity-gold-site.vercel.app."}
items = []                                  # (start, end, text)
caps = sorted([e for e in TL["events"] if "cap" in e], key=lambda e: e["f"])
for a, b in zip(caps, caps[1:] + [{"f": TL["frames"]}]):
    if a["cap"]: items.append([a["f"], b["f"] - 1, re.sub(r"[*]{2}", "", a["cap"])])
for e in TL["events"]:
    if e.get("bubble"): items.append([e["f"], e["f"] + e["dur"] - 1, "Pari: " + e["bubble"]])
    if e.get("beat") in CARD:                                    # card text in short timed lines (80 characters at most)
        parts = [x.strip() + ("" if x.strip().endswith(("?", ".")) else ".") for x in re.split(r"(?<=[.?]) ", CARD[e["beat"]]) if x.strip()]
        lines, cur = [], ""
        for x in parts:
            if cur and len(cur) + 1 + len(x) > 80: lines.append(cur); cur = x
            else: cur = (cur + " " + x).strip()
        lines.append(cur)
        step = e["dur"] / len(lines)
        for j, x in enumerate(lines): items.append([e["f"] + round(j * step), e["f"] + round((j + 1) * step) - 1, x])
items.sort()
for i in range(len(items) - 1):                                   # no overlaps: each line ends before the next starts
    items[i][1] = min(items[i][1], items[i + 1][0] - 1)
ts = lambda f: "%02d:%02d:%02d,%03d" % (f // FPS // 3600, f // FPS // 60 % 60, f // FPS % 60, round(f % FPS * 1000 / FPS))
out = [f"{k}\n{ts(a)} --> {ts(b)}\n{t}\n" for k, (a, b, t) in enumerate(items, 1)]
open(os.path.join(HERE, "..", "Parity_demo_v4.srt"), "w").write("\n".join(out))
print("subtitles", len(out))

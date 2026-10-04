import json
L = json.load(open("layout_fast.json")); T = json.load(open("timeline_fast.json")); FPS = 30; K = 1.6
caps = [(e["f"], e["cap"]) for e in T["events"] if "cap" in e]
fmt = lambda s: "%02d:%02d:%02d,%03d" % (int(s) // 3600, int(s) // 60 % 60, int(s) % 60, round((s - int(s)) * 1000) % 1000)
off = L["intro"] / FPS; lines, k = [], 1
for a, b, t in [(0.3, 4.8, "Four ways to buy gold on MCX."), (5.4, 8.5, "Same gold. Which price is fair?"), (8.9, 11.8, "Per gram of pure gold, they almost match."), (12.1, 15.0, "Meet Parity: MCX gold futures intelligence. A guided tour in 8 short stops.")]:
    lines.append(f"{k}\n{fmt(a / K)} --> {fmt(min(b / K, off - 0.05))}\n{t}\n"); k += 1
for i, (f, c) in enumerate(caps):
    if c is None: continue
    end = next((g for g, _ in caps[i + 1:]), T["frames"])
    lines.append(f"{k}\n{fmt(off + f / FPS)} --> {fmt(off + end / FPS - 0.05)}\n{c.replace('**', '')}\n"); k += 1
o = (L["intro"] + L["main"]) / FPS; ow = lambda s: s / K if s < 11.1 else 11.1 / K + (s - 11.1)
for a, b, t in [(0.3, 7.0, "What you just saw: a fair comparison, the curve explained, honest backtests, 8 sealed years, quiet alerts, and the contract calendar."),
                (7.1, 11.0, "The honest answer: a small, real edge. Tested honestly, doubts included."),
                (11.1, 15.0, "Parity by SYNTAX TERROR (TAN): Nikhil Kumar, Sai Ganesh, Ishaan Chhabra.")]:
    lines.append(f"{k}\n{fmt(o + ow(a))} --> {fmt(o + ow(b))}\n{t}\n"); k += 1
open("Parity_demo_fast.srt", "w").write("\n".join(lines)); print(k - 1, "subtitles, ends", fmt(o + ow(15.0)))

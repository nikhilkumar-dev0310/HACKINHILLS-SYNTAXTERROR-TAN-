import json
L = json.load(open("layout.json")); T = json.load(open("timeline.json")); FPS = 30
caps = [(e["f"], e["cap"]) for e in T["events"] if "cap" in e]
ts = lambda s: "%02d:%02d:%02d,%03d" % (s // 3600, s // 60 % 60, s % 60, round((s - int(s)) * 1000))
fmt = lambda s: ts(s) if False else "%02d:%02d:%02d,%03d" % (int(s) // 3600, int(s) // 60 % 60, int(s) % 60, round((s - int(s)) * 1000) % 1000)
off = L["intro"] / FPS
lines, k = [], 1
intro = [(0.3, 4.8, "Four ways to buy gold on MCX."), (5.4, 8.5, "Same gold. Which price is fair?"), (8.9, 11.8, "Per gram of pure gold, they almost match."), (12.1, 14.9, "Meet Parity: MCX gold futures intelligence. A guided tour in 8 short stops.")]
for a, b, t in intro: lines.append(f"{k}\n{fmt(a)} --> {fmt(b)}\n{t}\n"); k += 1
for i, (f, c) in enumerate(caps):
    if c is None: continue
    end = next((g for g, _ in caps[i + 1:]), T["frames"])
    lines.append(f"{k}\n{fmt(off + f / FPS)} --> {fmt(off + end / FPS - 0.05)}\n{c.replace('**', '')}\n"); k += 1
o = (L["intro"] + L["main"]) / FPS
for a, b, t in [(0.3, 7.0, "What you just saw: a fair comparison, the curve explained, honest backtests, 8 sealed years, quiet alerts, and the contract calendar."),
                (7.1, 11.0, "The honest answer: a small, real edge. Tested honestly, doubts included."),
                (11.1, 15.0, "Parity by SYNTAX TERROR (TAN): Nikhil Kumar, Sai Ganesh, Ishaan Chhabra.")]:
    lines.append(f"{k}\n{fmt(o + a)} --> {fmt(o + b)}\n{t}\n"); k += 1
open("Parity_demo.srt", "w").write("\n".join(lines))
print(k - 1, "subtitles")

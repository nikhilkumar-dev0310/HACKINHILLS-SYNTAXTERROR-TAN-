"""Build the Parity intro prototype. Every figure is read from the site's own data.json; nothing typed by hand."""
import json, datetime, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]   # commodity/dashboard
HERE = pathlib.Path(__file__).parent
d = json.loads((ROOT / "data.json").read_text())

def fdate(s):
    t = datetime.date.fromisoformat(s)
    return f"{t.day} {t.strftime('%b')} {t.year}"

def inr(x):  # Indian grouping, no decimals
    s = f"{abs(round(x)):d}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("−" if x < 0 else "") + "₹" + s

q = {r["symbol"]: r for r in d["quotes"]}
SPEC = {"GOLDM": ("100 g bar", "995"), "GOLDTEN": ("10 g bar", "999"), "GOLDGUINEA": ("8 g coin", "999"), "GOLDPETAL": ("1 g", "999")}
pieces = [{"sym": s, "kind": SPEC[s][0], "purity": SPEC[s][1], "rs_per_g": q[s]["rs_per_g"], "per_g": inr(q[s]["rs_per_g"])} for s in ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]]
pg = [p["rs_per_g"] for p in pieces]
spread_bp = (max(pg) - min(pg)) / q["GOLDM"]["rs_per_g"] * 1e4
quote_day = fdate(q["GOLDM"]["date"])

h = d["hurdle"]
rt = [b for b in d["alerts"]["baseline"] if b["alert_day"]][0]["round_trip_cost_bp_at_5bp"]
cost_line = round(2 * rt, 1)
sig = {r["symbol"]: r for r in d["signals"]["rows"]}
gaps = [{"sym": s, "gap": h[s]["gap"][-1], "z": h[s]["z"][-1], "sd": sig[s]["sd_bp"]} for s in ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]]
thr = d["signals"]["threshold"]
over = [g for g in gaps if g["gap"] >= cost_line]
signal_today = [g for g in gaps if g["gap"] >= cost_line and abs(g["z"]) >= thr]
A = d["meta"]["all"]
years = int(A["last"][:4]) - int(A["first"][:4])
boot = d["sealed"]["boot5"]["B"]

DATA = {
    "pieces": pieces, "quoteDay": quote_day, "spreadBp": round(spread_bp),
    "gaps": gaps, "costLine": cost_line, "roundTrip": rt, "thr": thr,
    "over": [g["sym"] for g in over], "signalToday": [g["sym"] for g in signal_today],
    "rows": f"{A['rows']:,}", "contracts": A["contracts"], "first": fdate(A["first"]), "years": years,
    "tests": f"{d['tests']['tests']:,}", "sealed": 3,
    "bootNet": inr(boot["net"]), "bootLo": inr(boot["lo"]), "bootHi": inr(boot["hi"]), "zeroInside": boot["lo"] < 0 < boot["hi"],
}
assert DATA["zeroInside"], "copy says the range includes zero"

# recast beat: what each quote stands for, and the pure gold inside it
GRAMS = {"GOLDM": 10, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}     # MCX quotes GOLDM and GOLDTEN per 10 g
for p in pieces:
    s = p["sym"]; pure = GRAMS[s] * int(p["purity"]) / 1000
    p.update(close=inr(q[s]["close"]), per=f"{GRAMS[s]} g", pure=f"{pure:g} g", chg=q[s]["chg_pct"])
    assert abs(q[s]["close"] / pure - q[s]["rs_per_g"]) < 0.2, (s, q[s]["close"] / pure, q[s]["rs_per_g"])

# ribbon beat: each small contract's distance from its usual premium, every trading day (thinned, keeping peaks)
H = d["hurdle"]; n = len(H["dates"]); STEP = 3
series = {"dates": [H["dates"][min(i + STEP - 1, n - 1)] for i in range(0, n, STEP)]}
for s in ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]:
    v = H[s]["gap"]
    series[s] = [max([x for x in v[i:i + STEP] if x is not None], default=None) for i in range(0, n, STEP)]
peak = {s: max(x for x in H[s]["gap"] if x is not None) for s in ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]}
DATA["series"] = series
DATA["seriesFrom"] = fdate(H["dates"][0])
DATA["petalPeak"] = round(peak["GOLDPETAL"])
DATA["petalMedian"] = round(sorted(x for x in H["GOLDPETAL"]["gap"] if x is not None)[sum(1 for x in H["GOLDPETAL"]["gap"] if x is not None) // 2])

# quiet beat: every alert episode, and how alert days compared with ordinary ones
AH = d["alerts"]["history"]
DATA["alerts"] = [{"sym": a["symbol"], "start": a["start"], "days": a["alert_days"], "bp": a["premium_bp"]} for a in AH]
summ = {r["symbol"]: r for r in d["alerts"]["summary"]}
assert summ["All"]["alerts"] == len(AH)
base = {b["alert_day"]: b for b in d["alerts"]["baseline"]}
DATA["alertCount"] = len(AH)
DATA["alertDays"] = f"{base[True]['days']:,}"
DATA["allDays"] = f"{base[True]['days'] + base[False]['days']:,}"
DATA["alertShare"] = round(100 * base[True]["days"] / (base[True]["days"] + base[False]["days"]))
DATA["closedAlert"] = round(base[True]["closed_half_10d"])
DATA["closedNormal"] = round(base[False]["closed_half_10d"])
months = (datetime.date.fromisoformat(H["dates"][-1]) - datetime.date.fromisoformat(H["dates"][0])).days / 30.44
DATA["alertsPerMonth"] = f"{len(AH) / months:.1f}"
DATA["seriesYears"] = round(months / 12)

petal = [g for g in gaps if g["sym"] == "GOLDPETAL"][0]
DATA["petal"] = {"gap": petal["gap"], "z": petal["z"], "band": round(thr * petal["sd"], 1)}

tpl = (HERE / "intro.tpl.html").read_text()
out = tpl.replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
for k, v in DATA.items():
    if not isinstance(v, (dict, list)):
        out = out.replace("{{" + k + "}}", str(v))
out = out.replace("{{petalGap}}", f"{petal['gap']:.1f}").replace("{{petalZ}}", f"{petal['z']:+.2f}").replace("{{petalBand}}", f"{DATA['petal']['band']:.0f}")
out = out.replace("{{costLine}}", f"{cost_line:.1f}")
assert "{{" not in out, out[out.index("{{"):out.index("{{") + 40]
(HERE / "intro.html").write_text(out)   # fragment, for previewing as a Claude artifact
# the page the site serves at /intro (tools/vercel_build.sh copies it; the daily job regenerates it)
head, body = out.split("</style>", 1)
NUM = dict(enumerate("zero one two three four five six seven eight nine ten eleven twelve".split()))
steps = NUM[tpl.count('<section class="beat')]   # the description names how many beats the intro has
(HERE / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    f'<meta name="description" content="Parity in {steps} steps: why MCX\u2019s four gold futures should cost the same per gram, and when a gap is worth a look.">\n'
    '<meta name="theme-color" content="#060606" media="(prefers-color-scheme: dark)">\n'
    '<meta name="theme-color" content="#ebe5da" media="(prefers-color-scheme: light)">\n'
    + head + "</style>\n</head>\n<body style=\"margin:0\">\n" + body + "\n</body>\n</html>\n")
print(json.dumps(DATA, ensure_ascii=False, indent=1)[:1600])

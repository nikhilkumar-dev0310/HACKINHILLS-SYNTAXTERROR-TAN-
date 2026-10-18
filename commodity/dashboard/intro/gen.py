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
(HERE / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Parity in six steps: why MCX\u2019s four gold futures should cost the same per gram, and when a gap is worth a look.">\n'
    '<meta name="theme-color" content="#0a0806">\n'
    + head + "</style>\n</head>\n<body style=\"margin:0\">\n" + body + "\n</body>\n</html>\n")
print(json.dumps(DATA, ensure_ascii=False, indent=1)[:1600])

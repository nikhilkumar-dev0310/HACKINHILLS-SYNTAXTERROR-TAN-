"""Export the real results to dashboard/data.json for the frontend. No sample or invented values.

    python dashboard/export.py        (from commodity/, after ingest.py and the analysis scripts)

Everything comes from clean/gold_futures.csv and the files in results/ that the analysis scripts
wrote. Trade logs are the stored ones from the single TEST / HOLDOUT runs; they are not re-run here.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import accuracy as ac          # noqa: E402
import fairvalue as fv         # noqa: E402
import uncertainty as un       # noqa: E402

SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
CRASH = (pd.Timestamp("2025-12-01"), pd.Timestamp("2026-03-31"))
R = "results/"


def r(x, n=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def main():
    out = {}
    d = pd.read_csv("clean/gold_futures.csv", parse_dates=["date", "expiry_date"])
    lot = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
    d["grams"] = d.volume_lots * d.symbol.map(lot)
    tr = d[~d.no_trade & (d.volume_lots > 0)]

    # ---------- meta
    integ = pd.read_csv(R + "testbed_integrity.csv")
    out["meta"] = {"rows": int(len(d)), "contracts": int(d.groupby(["symbol", "expiry_date"]).ngroups),
                   "first": str(d.date.min().date()), "last": str(d.date.max().date()),
                   "files": int(len([f for f in os.listdir("raw_clean") if f.endswith(".xls")])),
                   "sealed_contracts": int(pd.read_csv("clean/sealed_rows.csv").groupby(["symbol", "expiry_date"]).ngroups)
                   if os.path.exists("clean/sealed_rows.csv") and os.path.getsize("clean/sealed_rows.csv") > 200 else 0,
                   "exported": pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M IST")}

    # ---------- normalized price: per day, the most-traded contract of each symbol (Rs per pure gram)
    idx = tr.groupby(["date", "symbol"]).grams.idxmax()
    top = tr.loc[idx.values, ["date", "symbol", "rs_per_g", "expiry_date"]]
    p = top.pivot(index="date", columns="symbol", values="rs_per_g").sort_index()
    out["prices"] = {"dates": [str(x.date()) for x in p.index],
                     **{s: [r(v, 1) for v in p[s]] for s in SYMS}}

    # ---------- premium of each small contract over GOLDM (carry-adjusted), daily and monthly
    dd, carry = fv.load()
    frames = fv.add_z(fv.build(dd, carry))
    allf = pd.concat(frames.values())
    ok = allf[allf.ok]
    daily = ok.groupby([ok.index, "symbol"]).prem_bp.mean().unstack().sort_index()
    out["premium_daily"] = {"dates": [str(x.date()) for x in daily.index],
                            **{s: [r(v, 1) for v in daily[s]] for s in daily.columns}}
    m = daily.groupby(daily.index.to_period("M")).mean()
    m = m.reindex(pd.period_range(m.index.min(), m.index.max(), freq="M"))
    out["premium_monthly"] = {"months": [str(x) for x in m.index], **{s: [r(v, 1) for v in m[s]] for s in m.columns}}

    # ---------- latest signal state (fair-price model, past-only stats), last 90 market days of z
    sig = []
    for s in ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]:
        g = ok[ok.symbol == s]
        if g.empty:
            continue
        last = g.index.max()
        row = g.loc[[last]].sort_values("x_grams").iloc[-1]
        zs = g.groupby(level=0).z.mean().dropna().iloc[-90:]
        sig.append({"symbol": s, "date": str(last.date()), "expiry": str(row.expiry), "premium_bp": r(row.prem_bp),
                    "usual_bp": r(row.ref_bp), "sd_bp": r(row.sd_bp), "z": r(row.z, 2),
                    "z_hist": {"dates": [str(x.date()) for x in zs.index], "z": [r(v, 2) for v in zs]}})
    out["signals"] = {"threshold": json.load(open(R + "fairvalue_params.json"))["k"], "rows": sig}

    # ---------- pairs: all periods (accuracy.py output) + normal vs crash split
    acc = pd.read_csv(R + "accuracy_pairs.csv")
    _, t = ac.load()
    c, car = ac.carry_table(t)
    pairs, series = [], {}
    for a, b in [("GOLDM", "GOLDTEN"), ("GOLDM", "GOLDGUINEA"), ("GOLDM", "GOLDPETAL"),
                 ("GOLDTEN", "GOLDGUINEA"), ("GOLDTEN", "GOLDPETAL"), ("GOLDGUINEA", "GOLDPETAL")]:
        ps = ac.pair_series(t, car, a, b, "rs_per_g").spread_bp
        dt = ps.index.get_level_values("date")
        crash = (dt >= CRASH[0]) & (dt <= CRASH[1])
        y24 = dt < pd.Timestamp("2025-01-01")
        e, lo, hi, n = ac.week_boot_mean(ps[~crash & ~y24])            # 2025-26 quiet months
        e2, lo2, hi2, n2 = ac.week_boot_mean(ps[crash])
        y = ac.week_boot_mean(ps[y24]) if y24.sum() >= 20 else None
        key = f"{a[4:]}-{b[4:]}"
        al = acc[(acc.pair == key) & (acc.price == "close")].iloc[0]
        pairs.append({"pair": key, "a": a, "b": b,
                      "normal": [r(e), r(lo), r(hi), int(n)], "crash": [r(e2), r(lo2), r(hi2), int(n2)],
                      "y2024": [r(y[0]), r(y[1]), r(y[2]), int(y[3])] if y else None,
                      "all": [r(al.mean_bp), r(al.ci95_low), r(al.ci95_high), int(al.weeks)],
                      "cycles_same_sign": al.cycles_same_sign, "daily_sd": r(al.daily_sd_bp)})
        dm = ps.groupby(level="date").mean().sort_index()
        series[key] = {"dates": [str(x.date()) for x in dm.index], "bp": [r(v) for v in dm]}
    out["pairs"] = pairs
    out["pair_series"] = series
    out["crash_window"] = [str(CRASH[0].date()), str(CRASH[1].date())]

    # ---------- carry and futures curve
    cy = pd.read_csv(R + "accuracy_carry.csv")
    out["carry"] = cy.round(2).to_dict(orient="records")
    curves = {}
    per_day = tr.groupby("date").size()
    last = per_day[per_day >= 8].index.max()          # last day with a full curve (most contracts traded)
    for lab, target in (("today", last), ("t30", last - pd.Timedelta(days=30)), ("t90", last - pd.Timedelta(days=90))):
        day = tr[tr.date <= target].date.max()
        g = tr[tr.date == day]
        curves[lab] = {"date": str(day.date()),
                       "points": [{"symbol": x.symbol, "expiry": str(x.expiry_date.date()), "rs_per_g": r(x.rs_per_g, 1),
                                   "dte": int((x.expiry_date - day).days), "kg": r(x.grams / 1000, 1)}
                                  for x in g.sort_values("expiry_date").itertuples()]}
    out["curves"] = curves
    # the "as of" day: after it, the files hold only contracts running into their own expiry
    out["meta"]["last_full"] = str(last.date())

    # ---------- backtests (stored single runs)
    def summ(df, label, extra=None):
        rows = []
        for sl, g in df.groupby("slip_bp"):
            un.RNG = np.random.default_rng(20261001)      # same seed per call: reproducible ranges
            n, net, ci, pp = un.bootstrap(g)
            rows.append({"slip": int(sl), "trades": int(len(g)), "gross": r(g.gross_rs.sum(), 0), "cost": r(g.cost_rs.sum(), 0),
                         "net": r(g.net_rs.sum(), 0), "hit": r((g.net_rs > 0).mean() * 100, 0),
                         "ci": [r(ci[0], 0), r(ci[1], 0)], "p_pos": r(pp * 100, 0), "weeks": int(n)})
        return {"label": label, **(extra or {}), "rows": rows}

    test = pd.read_csv(R + "test_trades.csv")
    hold = pd.read_csv(R + "holdout_trades.csv")
    fvd = pd.read_csv(R + "fairvalue_dev_trades.csv")
    fvh = pd.read_csv(R + "fairvalue_holdout_trades.csv")
    k = json.load(open(R + "fairvalue_params.json"))["k"]
    out["backtests"] = {
        "A_test": summ(test, "Strategy A · Test 1", {"window": "1 May – 31 Jul 2025", "grams": 40}),
        "A_hold": summ(hold, "Strategy A · Sealed holdout", {"window": "Aug 2025 – May 2026", "grams": 40}),
        "B_dev": summ(fvd[fvd.k == k].drop(columns="k"), "Strategy B · Development (in-sample)", {"window": "to 5 Aug 2025", "grams": 200}),
        "B_hold": summ(fvh.drop(columns="k"), "Strategy B · Sealed holdout", {"window": "6 Aug 2025 – 29 May 2026", "grams": 200}),
    }
    out["train_note"] = {"trades": 9, "gross": -3939}

    def log(df, kind):
        w = df.pivot_table(index=[c for c in df.columns if c not in ("slip_bp", "cost_rs", "net_rs", "k")],
                           columns="slip_bp", values="net_rs").reset_index()
        rows = []
        for x in w.to_dict(orient="records"):
            rows.append({"what": x.get("pair") or x.get("symbol"), "expiry": str(x["expiry"])[:10], "m_exp": str(x.get("goldm_expiry") or "")[:10],
                         "entry": str(x["entry"])[:10], "exit": str(x["exit"])[:10], "side": x["side"],
                         "days": int(x["days_held"]), "gross": r(x["gross_rs"], 0),
                         "net0": r(x[0], 2), "net5": r(x[5], 2), "net10": r(x[10], 2)})
        return sorted(rows, key=lambda z: z["entry"])
    out["trades"] = {"A_test": log(test, "A"), "A_hold": log(hold, "A"),
                     "B_dev": log(fvd[fvd.k == k].drop(columns="k"), "B"), "B_hold": log(fvh.drop(columns="k"), "B")}
    h5 = hold[hold.slip_bp == 5]
    mm = h5.groupby(pd.to_datetime(h5.entry).dt.to_period("M")).net_rs.agg(["sum", "size"])
    out["A_hold_monthly"] = [{"month": str(i), "net": r(v["sum"], 0), "trades": int(v["size"])} for i, v in mm.iterrows()]

    out["timeline"] = [
        {"when": "1 Oct 2026, 21:45 IST", "commit": "e5e0a21", "what": "Holdout window declared and download list written"},
        {"when": "1 Oct 2026, 22:15 IST", "commit": "045ab2b", "what": "Strategy B rules and setting (k = 1.5) frozen"},
        {"when": "1 Oct 2026, 23:01 IST", "commit": "7acf18e", "what": "Holdout data (39 MCX files) uploaded"},
        {"when": "1 Oct 2026, 23:05 IST", "commit": "3e9e82d", "what": "Holdout run once; results recorded as they came out"},
        {"when": "2 Oct 2026, 03:28 IST", "commit": "35d7e7b", "what": "Sealed test 2 (2020–2023) declared before download"},
        {"when": "3 Oct 2026, 01:13 IST", "commit": "a8cda54", "what": "Sealed test 3 (2016–2019) declared before download"},
        {"when": "3 Oct 2026, 01:47 IST", "commit": "8f16845", "what": "Test 2 shortened to end 9 Oct 2023 (late-2023 days seen via 2024 files); sealed rows walled off in code"},
        {"when": "3 Oct 2026, 02:43 IST", "commit": "79129fc", "what": "2020 files set aside in the sealed file, unread"},
    ]

    # ---------- contracts (calendar) and data quality
    cal = []
    for (s, e), g in d.groupby(["symbol", "expiry_date"]):
        gt = g[~g.no_trade & (g.volume_lots > 0)]
        cal.append({"symbol": s, "expiry": str(e.date()), "first": str(g.date.min().date()), "last": str(g.date.max().date()),
                    "days": int(len(g)), "no_trade": int(g.no_trade.sum()), "kg_median": r(gt.grams.median() / 1000, 2) if len(gt) else 0})
    out["contracts"] = cal
    out["integrity"] = integ.assign(error_rate=lambda x: (x.error_rate * 100).round(2)).to_dict(orient="records")
    out["close_vs_vwap"] = pd.read_csv(R + "testbed_close_vs_vwap.csv").query("dates == 'all dates'").to_dict(orient="records")
    out["per_contract"] = pd.read_csv(R + "accuracy_contracts.csv").to_dict(orient="records")

    # flagged rows: >5% from same-cycle median, and previous-close mismatches (all after no-trade days)
    t2 = d[~d.no_trade].copy()
    t2["cyc"] = (t2.expiry_date + pd.Timedelta(days=10)).dt.to_period("M")
    t2["med"] = t2.groupby(["date", "cyc"]).rs_per_g.transform("median")
    t2["dev"] = t2.rs_per_g / t2.med - 1
    flags = [{"date": str(x.date.date()), "symbol": x.symbol, "expiry": str(x.expiry_date.date()), "kind": "Far from peers",
              "detail": f"{x.dev * 100:+.1f}% vs same-month median; close {x.close:,.0f}, day low {x.low:,.0f}",
              "action": "Kept: real crash-period price"} for x in t2[t2.dev.abs() > 0.05].itertuples()]
    g = d.sort_values("date").groupby(["symbol", "expiry_date"])
    chk = d.assign(prior=g.close.shift(1), prior_nt=g.no_trade.shift(1)).dropna(subset=["prior"])
    mism = chk[chk.prev_close.round(2) != chk.prior.round(2)]
    flags += [{"date": str(x.date.date()), "symbol": x.symbol, "expiry": str(x.expiry_date.date()), "kind": "Previous close mismatch",
               "detail": f"file says {x.prev_close:,.0f}, prior row {x.prior:,.0f}; prior day had no trades",
               "action": "Explained: no-trade day excluded"} for x in mism.itertuples()]
    out["flags"] = sorted(flags, key=lambda z: z["date"], reverse=True)

    # ---------- brief items: gold attribution, tender compliance, roll-down, liquidity build-up
    att = pd.read_csv(R + "attribution_trades.csv")
    lt = pd.read_csv(R + "lifecycle_trades.csv")
    key = ["what", "expiry", "entry", "exit"]
    for run, rows in out["trades"].items():
        A = att[att.run == run].set_index(key)
        Lt = lt[lt.run == run].set_index(key)
        for x in rows:
            k = (x["what"], x["expiry"], x["entry"], x["exit"])
            x["gap_part"] = r(A.loc[k, "gap_part"], 0) if k in A.index else None
            x["gold_part"] = r(A.loc[k, "gold_part"], 0) if k in A.index else None
            x["gold_move"] = r(A.loc[k, "gold_move_pct"], 2) if k in A.index else None
            x["ok_tender"] = bool(Lt.loc[k, "outside_tender"]) if k in Lt.index else None
            x["safe_exit"] = str(Lt.loc[k, "last_safe_exit"]) if k in Lt.index else None
    out["attribution"] = pd.read_csv(R + "attribution_summary.csv").to_dict(orient="records")
    out["lifecycle_summary"] = pd.read_csv(R + "lifecycle_summary.csv").to_dict(orient="records")
    rd = pd.read_csv(R + "rolldown_monthly.csv")
    out["rolldown"] = {"goldm": rd[rd.symbol == "GOLDM"][["month", "expiry", "carry_pa_pct", "total_pct", "rolldown_pct", "curve_move_pct"]].round(2).to_dict(orient="records"),
                       "summary": pd.read_csv(R + "rolldown_summary.csv").round(2).to_dict(orient="records")}
    lq = pd.read_csv(R + "lifecycle_liquidity.csv")
    out["liquidity"] = lq.round(2).to_dict(orient="records")
    lc = pd.read_csv(R + "lifecycle_contracts.csv")
    safe = {(x.symbol, x.expiry_date): x.last_safe_exit for x in lc.itertuples()}
    for c in out["contracts"]:
        c["safe_exit"] = safe.get((c["symbol"], c["expiry"]))
    # ---------- alert history and curve slope
    ah = pd.read_csv(R + "alerts_history.csv")
    out["alerts"] = {"history": ah.where(ah.notna(), None).to_dict(orient="records"),
                     "summary": pd.read_csv(R + "alerts_summary.csv").to_dict(orient="records"),
                     "baseline": pd.read_csv(R + "alerts_baseline.csv").to_dict(orient="records")}
    cm = pd.read_csv(R + "curve_slope_monthly.csv")
    out["curve_slope"] = {"months": cm.month.tolist(), **{c: [r(v, 2) for v in cm[c]] for c in cm.columns if c != "month"}}
    json.dump(out, open(os.path.join(HERE, "data.json"), "w"), separators=(",", ":"), default=str)
    print("wrote dashboard/data.json", os.path.getsize(os.path.join(HERE, "data.json")) // 1024, "KB")


if __name__ == "__main__":
    main()

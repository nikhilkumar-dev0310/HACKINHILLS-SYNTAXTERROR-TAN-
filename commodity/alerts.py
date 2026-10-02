"""Alert history: every past fair-price alert and what the gap did next.

    python alerts.py

Uses the same fair-price model as fairvalue.py (GOLDM moved to the same expiry + the contract's usual
premium; usual premium and its spread from PREVIOUS days only). An alert fires when a contract's distance
from usual |z| reaches the frozen threshold k. Consecutive alert days for the same contract and direction
form one episode. For each episode, from its first day:
  - premium then, usual premium then
  - premium 5, 10 and 20 trading days later
  - closed_half_10d: did the gap to usual shrink by at least half within 10 trading days?
  - days_to_half: trading days until it first did (within 20)
This is descriptive: it shows how often an alert was followed by the gap closing, before costs, and compares
it with the same test on every day (alerts_baseline.csv), because small gaps also close by chance.
Whether that paid after costs is the backtest's job. Writes results/alerts_history.csv, alerts_summary.csv.
"""
import json
import os

import numpy as np
import pandas as pd

import backtest as bt
import fairvalue as fv


def main():
    k = json.load(open(os.path.join(bt.RES, "fairvalue_params.json")))["k"]
    d, carry = fv.load()
    frames = fv.add_z(fv.build(d, carry))
    allf = pd.concat(frames.values())
    ok = allf[allf.ok & allf.z.notna()]
    rows = []
    for sym, g in ok.groupby("symbol"):
        # one value per day: the most-traded cycle of this contract type
        day = g.sort_values("x_grams").groupby(level=0).tail(1).sort_index()
        dates = list(day.index)
        side = np.where(day.z >= k, 1, np.where(day.z <= -k, -1, 0))
        i = 0
        while i < len(day):
            if side[i] == 0:
                i += 1
                continue
            j = i
            while j + 1 < len(day) and side[j + 1] == side[i]:
                j += 1
            r0 = day.iloc[i]
            gap0 = r0.prem_bp - r0.ref_bp
            fut = day.iloc[i + 1:i + 21]
            later = {h: (fut.prem_bp.iloc[h - 1] if len(fut) >= h else np.nan) for h in (5, 10, 20)}
            half = None
            for n, (_, rr) in enumerate(fut.iterrows(), 1):
                if abs(rr.prem_bp - r0.ref_bp) <= abs(gap0) / 2:
                    half = n
                    break
            rows.append({"symbol": sym, "start": dates[i].date(), "end": dates[j].date(), "alert_days": j - i + 1,
                         "direction": "rich vs GOLDM" if side[i] > 0 else "cheap vs GOLDM", "expiry": r0.expiry,
                         "z": round(r0.z, 2), "premium_bp": round(r0.prem_bp, 1), "usual_bp": round(r0.ref_bp, 1),
                         "prem_5d": round(later[5], 1), "prem_10d": round(later[10], 1), "prem_20d": round(later[20], 1),
                         "closed_half_10d": bool(half is not None and half <= 10) if len(fut) >= 10 else None,
                         "days_to_half": half})
            i = j + 1
    # baseline: the same "closed half within 10 trading days" test on every day, alert or not
    base = []
    for sym, g in ok.groupby("symbol"):
        day = g.sort_values("x_grams").groupby(level=0).tail(1).sort_index()
        p, ref, z = day.prem_bp.values, day.ref_bp.values, day.z.values
        for i in range(len(day) - 10):
            gap0 = p[i] - ref[i]
            if abs(gap0) < 1e-9:
                continue
            hit = any(abs(p[i + n] - ref[i]) <= abs(gap0) / 2 for n in range(1, 11))
            closed_bp = np.sign(gap0) * (p[i] - p[i + 10])          # bp the gap moved toward usual in 10 days
            base.append({"symbol": sym, "alert_day": abs(z[i]) >= k, "closed_half_10d": hit, "abs_gap_bp": abs(gap0),
                         "closed_bp_10d": closed_bp})
    base = pd.DataFrame(base)
    bs = base.groupby("alert_day").agg(days=("closed_half_10d", "size"), closed_half_10d=("closed_half_10d", "mean"),
                                       median_gap_bp=("abs_gap_bp", "median"), median_closed_bp_10d=("closed_bp_10d", "median"),
                                       mean_closed_bp_10d=("closed_bp_10d", "mean"))
    bs.closed_half_10d *= 100
    px = 15000.0                                                        # Rs per gram, typical 2026 level
    rt = (fv.leg_cost(px, "buy", 5) + fv.leg_cost(px, "sell", 5)) * 2 / (px * fv.GRAMS) * 1e4
    bs["round_trip_cost_bp_at_5bp"] = rt
    bs.round(1).to_csv(os.path.join(bt.RES, "alerts_baseline.csv"))
    print("Every day, alert or not: share where the gap to usual halved within 10 trading days")
    print(bs.round(1).to_string(), "\n")
    h = pd.DataFrame(rows).sort_values("start")
    h.to_csv(os.path.join(bt.RES, "alerts_history.csv"), index=False)
    done = h[h.closed_half_10d.notna()]
    s = done.groupby("symbol").agg(alerts=("start", "size"), closed_half_10d_pct=("closed_half_10d", lambda x: 100 * x.astype(bool).mean()),
                                   median_days_to_half=("days_to_half", "median"))
    s.loc["All"] = [len(done), 100 * done.closed_half_10d.astype(bool).mean(), done.days_to_half.median()]
    s.round(1).to_csv(os.path.join(bt.RES, "alerts_summary.csv"))
    pd.set_option("display.width", 200)
    print(f"Alert episodes (|z| >= {k}), {h.start.min()} to {h.start.max()}:")
    print(s.round(1).to_string())
    print(h.groupby([pd.to_datetime(h.start).dt.year, "symbol"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()

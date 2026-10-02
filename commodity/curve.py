"""Shape of the futures curve over time: its slope, from every listed expiry each day.

    python curve.py

For each contract type and day, take every contract that traded and is outside its tender period
(more than 5 business days to expiry), and fit ln(price per pure gram) = a + slope * (days to expiry / 365).
The slope is the curve's annualised carry across the whole curve, not just the two nearest contracts.
Days with fewer than 3 such contracts are skipped. A rising slope means later expiries got dearer
relative to near ones (steepening); a falling slope means flattening.
Writes results/curve_slope_daily.csv and results/curve_slope_monthly.csv.
"""
import os

import numpy as np
import pandas as pd

import backtest as bt

MIN_CONTRACTS = 3


def main():
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    d = d[~d.no_trade & (d.volume_lots > 0)].copy()
    d["bdays"] = np.busday_count(d.date.values.astype("datetime64[D]"), d.expiry_date.values.astype("datetime64[D]"))
    d = d[d.bdays > 5]
    d["t"] = (d.expiry_date - d.date).dt.days / 365
    rows = []
    for (dt, sym), g in d.groupby(["date", "symbol"]):
        if len(g) < MIN_CONTRACTS:
            continue
        slope, a = np.polyfit(g.t, np.log(g.rs_per_g), 1)
        fit = a + slope * g.t
        rows.append({"date": dt.date(), "symbol": sym, "contracts": len(g), "slope_pa_pct": 100 * slope,
                     "max_days": int((g.t * 365).max()), "fit_error_bp": 1e4 * float(np.sqrt(np.mean((np.log(g.rs_per_g) - fit) ** 2)))})
    r = pd.DataFrame(rows)
    r.round(3).to_csv(os.path.join(bt.RES, "curve_slope_daily.csv"), index=False)
    m = r.assign(month=pd.to_datetime(r.date).dt.to_period("M").astype(str)).groupby(["month", "symbol"]).slope_pa_pct.median().unstack()
    m.round(2).to_csv(os.path.join(bt.RES, "curve_slope_monthly.csv"))
    pd.set_option("display.width", 200)
    print("Median curve slope, % a year (annualised carry across the whole curve):")
    print(r.groupby([pd.to_datetime(r.date).dt.year, "symbol"]).slope_pa_pct.median().unstack().round(2).to_string())
    print("\nDays fitted:", r.groupby("symbol").size().to_dict(), " median fit error (bp):", r.groupby("symbol").fit_error_bp.median().round(1).to_dict())


if __name__ == "__main__":
    main()

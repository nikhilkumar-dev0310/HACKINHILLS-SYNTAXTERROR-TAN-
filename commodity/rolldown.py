"""Separate mechanical roll-down toward expiry from genuine changes in the futures curve.

    python rolldown.py

A futures price sits above spot by the cost of carry. As days pass the contract 'rolls down' toward
spot even if nothing in the market changes. For each contract type and each calendar month we take the
most-traded contract on the month's first trading day (t0) that is still alive on the next month's first
trading day (t1), and split its price change:
    total      = F1 / F0 - 1
    roll-down  = exp(-c0 * days / 365) - 1        what time alone would do on an unchanged curve
    curve move = F1 / (F0 * exp(-c0 * days / 365)) - 1   everything else: gold's move and curve reshaping
c0 is that day's carry of the same contract type, measured from its neighbouring expiries (accuracy.carry_table;
the all-contract median is the fallback),
past and same-day data only. Prices: settlement close per pure gram.
Writes results/rolldown_monthly.csv and results/rolldown_summary.csv.
"""
import os

import numpy as np
import pandas as pd

import accuracy as ac
import backtest as bt


def main():
    d, t = ac.load()
    c, carry = ac.carry_table(t)
    own = c.groupby(["date", "symbol"]).carry_pa.median()          # each contract type's own carry
    t = t.copy()
    rows = []
    months = sorted(t.date.dt.to_period("M").unique())
    for m0, m1 in zip(months[:-1], months[1:]):
        d0 = t[t.date.dt.to_period("M") == m0].date.min()
        d1 = t[t.date.dt.to_period("M") == m1].date.min()
        for sym, g in t[t.date == d0].groupby("symbol"):
            c0 = own.get((d0, sym), carry.get(d0, np.nan))
            if np.isnan(c0):
                continue
            g = g[g.expiry_date > d1 + pd.Timedelta(days=7)]          # still alive and outside tender
            if g.empty:
                continue
            row = g.loc[g.grams.idxmax()]
            e = row.expiry_date
            f1 = t[(t.symbol == sym) & (t.expiry_date == e) & (t.date == d1)]
            if f1.empty:
                continue
            F0, F1, days = row.rs_per_g, f1.rs_per_g.iloc[0], (d1 - d0).days
            roll = np.exp(-c0 * days / 365) - 1
            rows.append({"month": str(m0), "symbol": sym, "expiry": e.date(), "from": d0.date(), "to": d1.date(),
                         "days": days, "carry_pa_pct": 100 * c0, "total_pct": 100 * (F1 / F0 - 1),
                         "rolldown_pct": 100 * roll, "curve_move_pct": 100 * (F1 / (F0 * (1 + roll)) - 1),
                         "rolldown_rs_per_g": F0 * roll, "total_rs_per_g": F1 - F0})
    r = pd.DataFrame(rows)
    r.round(3).to_csv(os.path.join(bt.RES, "rolldown_monthly.csv"), index=False)
    s = r.groupby("symbol").agg(months=("month", "size"), avg_rolldown_pct=("rolldown_pct", "mean"),
                                avg_abs_curve_move_pct=("curve_move_pct", lambda x: x.abs().mean()),
                                avg_total_pct=("total_pct", "mean"),
                                rolldown_share_of_abs_change_pct=("rolldown_pct", lambda x: 100 * x.abs().sum()
                                                                  / (x.abs().sum() + r.loc[x.index, "curve_move_pct"].abs().sum())))
    s.round(3).to_csv(os.path.join(bt.RES, "rolldown_summary.csv"))
    pd.set_option("display.width", 200)
    print("Monthly price change of the most-traded contract, split into roll-down and curve move (% per month)")
    print(s.round(2).to_string())
    print("\nGOLDM, last 6 months:")
    print(r[r.symbol == "GOLDM"].tail(6)[["month", "expiry", "carry_pa_pct", "total_pct", "rolldown_pct", "curve_move_pct"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()

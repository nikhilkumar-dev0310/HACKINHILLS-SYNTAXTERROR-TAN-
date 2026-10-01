"""Precision of every contract and every pair, including GOLDM.

    python accuracy.py          (run ingest.py first)

1. Cost of carry, measured from the data: for each symbol and day, the annualized log price
   difference between adjacent expiries (20-40 days apart). Used to move a price to another
   expiry date: F(T2) = F(T1) * exp(carry * (T2 - T1) / 365).
2. GOLDM pairs: GOLDM expires on the 3rd-5th, the others at month-end, so they never share an
   expiry. GOLDM is matched to the nearest partner expiry and moved to that date with the same-day
   carry (median of all symbols that day; trailing 20-day median if none).
3. Two price measures per pair: settlement close, and the day's average traded price (VWAP from
   turnover / grams traded). Spread levels and 95% margins (week-block bootstrap) for all six pairs.
4. Precision per contract: no-trade share, close-vs-VWAP gap, liquidity.
Writes results/accuracy_*.csv.
"""
import itertools
import os

import numpy as np
import pandas as pd

import backtest as bt
from ingest import PURITY

LOT_GRAMS = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
RNG = np.random.default_rng(11)
B = 5000


def load():
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    t = d[~d.no_trade & (d.volume_lots > 0)].copy()
    t["vwap_rs_per_g"] = t.value_lakhs * 1e5 / (t.volume_lots * t.symbol.map(LOT_GRAMS)) / t.symbol.map(PURITY)
    t["grams"] = t.volume_lots * t.symbol.map(LOT_GRAMS)
    return d, t


def carry_table(t):
    rows = []
    for (dt, sym), g in t.groupby(["date", "symbol"]):
        g = g.sort_values("expiry_date")
        for i in range(len(g) - 1):
            a, b = g.iloc[i], g.iloc[i + 1]
            days = (b.expiry_date - a.expiry_date).days
            if 20 <= days <= 40:
                rows.append({"date": dt, "symbol": sym, "days": days,
                             "carry_pa": np.log(b.close / a.close) * 365 / days})
    c = pd.DataFrame(rows)
    daily = c.groupby("date").carry_pa.median()
    full = daily.reindex(pd.DatetimeIndex(sorted(t.date.unique())))
    fallback = full.shift(1).rolling(20, min_periods=1).median()        # past days only
    return c, full.fillna(fallback)


def pair_series(t, carry, a, b, price):
    """Daily spread a-b in bp. GOLDM is moved to the partner's expiry using same-day carry."""
    A = t[t.symbol == a].set_index(["date", "expiry_date"])[price]
    Bs = t[t.symbol == b].set_index(["date", "expiry_date"])[price]
    if "GOLDM" not in (a, b):
        both = pd.concat([A.rename("a"), Bs.rename("b")], axis=1).dropna()
        both["adj_bp"] = 0.0
    else:
        m_sym, o_sym = (a, b) if a == "GOLDM" else (b, a)
        M = t[t.symbol == m_sym][["date", "expiry_date", price]]
        O = t[t.symbol == o_sym][["date", "expiry_date", price]]
        rows = []
        for (dt, oe), orow in O.set_index(["date", "expiry_date"]).iterrows():
            cands = M[(M.date == dt) & ((M.expiry_date - oe).dt.days.abs() <= 10)]
            if len(cands) != 1:
                continue
            me = cands.expiry_date.iloc[0]
            gap = (oe - me).days
            k = carry.get(dt, np.nan)
            if np.isnan(k):
                continue
            m_adj = cands[price].iloc[0] * np.exp(k * gap / 365)       # GOLDM moved to partner's expiry
            rows.append({"date": dt, "expiry_date": oe, "m": m_adj, "o": orow[price],
                         "adj_bp": 1e4 * k * gap / 365})
        x = pd.DataFrame(rows).set_index(["date", "expiry_date"])
        both = pd.DataFrame({"a": x.m if a == "GOLDM" else x.o, "b": x.o if a == "GOLDM" else x.m,
                             "adj_bp": x.adj_bp})
    both["spread_bp"] = 1e4 * np.log(both.a / both.b)
    return both


def week_boot_mean(s):
    weeks = s.index.get_level_values("date").to_period("W")
    groups = [g.values for _, g in s.groupby(weeks)]
    n = len(groups)
    draws = np.array([np.concatenate([groups[j] for j in RNG.integers(0, n, n)]).mean() for _ in range(B)])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return s.mean(), lo, hi, n


def main():
    d, t = load()
    c, carry = carry_table(t)
    cs = c.groupby([c.date.dt.year, "symbol"]).carry_pa.median().unstack() * 100
    cs.round(2).to_csv(os.path.join(bt.RES, "accuracy_carry.csv"))
    print("1. COST OF CARRY (% per year, median of adjacent-expiry pairs)")
    print(cs.round(2).to_string(), "\n")

    rows, cycles = [], []
    for a, b in itertools.combinations(SYMS, 2):
        for price, label in (("rs_per_g", "close"), ("vwap_rs_per_g", "VWAP")):
            p = pair_series(t, carry, a, b, price)
            if len(p) < 10:
                continue
            est, lo, hi, nw = week_boot_mean(p.spread_bp)
            per_cycle = p.spread_bp.groupby(level="expiry_date").mean()
            rows.append({"pair": f"{a[4:]}-{b[4:]}", "price": label, "days": len(p), "weeks": nw, "cycles": len(per_cycle),
                         "mean_bp": round(est, 1), "ci95_low": round(lo, 1), "ci95_high": round(hi, 1),
                         "half_width_bp": round((hi - lo) / 2, 1), "daily_sd_bp": round(p.spread_bp.std(), 1),
                         "cycles_same_sign": f"{int((np.sign(per_cycle) == np.sign(est)).sum())}/{len(per_cycle)}",
                         "carry_adj_bp_median": round(p.adj_bp.abs().median(), 2)})
            if label == "close":
                for e, v in per_cycle.items():
                    cycles.append({"pair": f"{a[4:]}-{b[4:]}", "expiry": e.date(), "mean_bp": round(v, 1),
                                   "days": int((p.index.get_level_values("expiry_date") == e).sum())})
    lv = pd.DataFrame(rows)
    lv.to_csv(os.path.join(bt.RES, "accuracy_pairs.csv"), index=False)
    pd.DataFrame(cycles).to_csv(os.path.join(bt.RES, "accuracy_pair_cycles.csv"), index=False)
    pd.set_option("display.width", 220)
    print("2-3. ALL SIX PAIRS: level per gram of pure gold (a minus b), 95% margin, close vs VWAP")
    print(lv.to_string(index=False), "\n")

    prec = []
    for s in SYMS:
        g = d[d.symbol == s]
        tr = t[t.symbol == s]
        gap = (1e4 * np.log(tr.rs_per_g / tr.vwap_rs_per_g)).abs()
        prec.append({"symbol": s, "rows": len(g), "contracts": g.expiry_date.nunique(),
                     "no_trade_pct": round(100 * g.no_trade.mean(), 2),
                     "median_kg_traded_per_day": round(tr.grams.median() / 1000, 1),
                     "close_vs_vwap_median_bp": round(gap.median(), 1),
                     "close_vs_vwap_p90_bp": round(gap.quantile(0.9), 1)})
    pr = pd.DataFrame(prec)
    pr.to_csv(os.path.join(bt.RES, "accuracy_contracts.csv"), index=False)
    print("4. PRECISION PER CONTRACT")
    print(pr.to_string(index=False))


if __name__ == "__main__":
    main()

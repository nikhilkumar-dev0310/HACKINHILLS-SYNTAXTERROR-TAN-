"""Accuracy testbed: how much error is in the data, and how much in the conclusions.

    python testbed.py          (run ingest.py first)

Part A  Data integrity: share of rows failing each check.
Part B  Price measurement error: settlement close vs the day's average traded price
        (VWAP = turnover / grams traded). The gap is what using the close as a fill can cost.
Part C  Statistical margins (95%) on the main numbers, resampling by week because daily
        spreads are autocorrelated (Politis & Romano 1994, doi:10.1080/01621459.1994.10476870).
Writes results/testbed_*.csv.
"""
import os

import numpy as np
import pandas as pd

import backtest as bt
from ingest import PURITY

LOT_GRAMS = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
RNG = np.random.default_rng(7)
B = 5000


def pct(x):
    return f"{100 * x:.2f}%"


def part_a(d):
    rows = []
    traded = d[~d.no_trade]
    rows.append(("Duplicate (date, symbol, expiry)", d.duplicated(["date", "symbol", "expiry_date"]).mean(), len(d)))
    rows.append(("Row dated after its expiry", (d.date > d.expiry_date).mean(), len(d)))
    ohlc_bad = (traded[["open", "close"]].min(axis=1) < traded.low) | (traded[["open", "close"]].max(axis=1) > traded.high)
    rows.append(("Open/close outside [low, high]", ohlc_bad.mean(), len(traded)))
    rows.append(("Non-positive price", (traded[["open", "high", "low", "close"]] <= 0).any(axis=1).mean(), len(traded)))

    # previous close in the file must equal the close of the previous row of the same contract
    g = d.sort_values("date").groupby(["symbol", "expiry_date"])
    prior = g["close"].shift(1)
    chk = d.assign(prior=prior).dropna(subset=["prior"])
    mism = chk.prev_close.round(2) != chk.prior.round(2)
    after_nt = g["no_trade"].shift(1).reindex(chk.index).fillna(False).astype(bool)
    rows.append(("Previous Close != prior row's Close", mism.mean(), len(chk)))
    rows.append(("  ...of which NOT right after a no-trade day", (mism & ~after_nt).mean(), len(chk)))

    # trading calendar = every date that appears in any file; count gaps inside each contract's life
    cal = np.sort(d.date.unique())
    gaps, expected = 0, 0
    for _, c in g:
        span = cal[(cal >= c.date.min()) & (cal <= c.date.max())]
        expected += len(span)
        gaps += len(span) - c.date.nunique()
    rows.append(("Missing trading day inside a contract's life", gaps / expected, expected))

    # cross-contract: a wrong quote unit or lot size would put a contract 10-90% away from the others in
    # the same expiry cycle (comparing across cycles mixes in cost of carry, 2-3% at 4-6 months).
    cycle = (traded.expiry_date + pd.Timedelta(days=10)).dt.to_period("M")
    med = traded.groupby([traded.date, cycle]).rs_per_g.transform("median")
    dev = (traded.rs_per_g / med - 1).abs()
    rows.append(("Normalized price >5% from same-cycle median", (dev > 0.05).mean(), len(traded)))
    print(f"Same-cycle deviation (all traded rows): median {100*dev.median():.2f}%, "
          f"99th pct {100*dev.quantile(.99):.2f}%, max {100*dev.max():.2f}%\n")
    out = pd.DataFrame(rows, columns=["check", "error_rate", "rows_checked"])
    out["errors"] = (out.error_rate * out.rows_checked).round().astype(int)
    return out


def part_b(d):
    t = d[(~d.no_trade) & (d.volume_lots > 0) & (d.value_lakhs > 0)].copy()
    grams = t.volume_lots * t.symbol.map(LOT_GRAMS)
    t["vwap_rs_per_g"] = t.value_lakhs * 1e5 / grams / t.symbol.map(PURITY)
    t["gap_bp"] = 1e4 * np.log(t.rs_per_g / t.vwap_rs_per_g)
    rows = []
    for label, sub in (("TRAIN dates", t[t.date <= bt.TRAIN_END]), ("all dates", t)):
        for sym, g in sub.groupby("symbol"):
            a = g.gap_bp.abs()
            rows.append({"symbol": sym, "dates": label, "days": len(g), "median_abs_gap_bp": round(a.median(), 1),
                         "p90_abs_gap_bp": round(a.quantile(0.9), 1), "mean_signed_gap_bp": round(g.gap_bp.mean(), 1)})
    # The same gap measured on spreads: gold's own intraday move cancels between the two legs,
    # leaving how far the settlement spread is from the spread at which trading actually happened.
    w_close = t.pivot_table(index=["expiry_date", "date"], columns="symbol", values="rs_per_g")
    w_vwap = t.pivot_table(index=["expiry_date", "date"], columns="symbol", values="vwap_rs_per_g")
    for a, b in [("GOLDPETAL", "GOLDTEN"), ("GOLDGUINEA", "GOLDTEN"), ("GOLDGUINEA", "GOLDPETAL")]:
        gap = (1e4 * (np.log(w_close[a] / w_close[b]) - np.log(w_vwap[a] / w_vwap[b]))).dropna()
        rows.append({"symbol": f"spread {a[4:]}-{b[4:]}", "dates": "all dates", "days": len(gap),
                     "median_abs_gap_bp": round(gap.abs().median(), 1), "p90_abs_gap_bp": round(gap.abs().quantile(0.9), 1),
                     "mean_signed_gap_bp": round(gap.mean(), 1)})
    return pd.DataFrame(rows), t


def week_boot(values, weeks):
    df = pd.DataFrame({"v": values, "w": weeks})
    groups = [g.v.values for _, g in df.groupby("w")]
    n = len(groups)
    est = np.mean(values)
    draws = np.empty(B)
    for i in range(B):
        pick = RNG.integers(0, n, n)
        draws[i] = np.concatenate([groups[j] for j in pick]).mean()
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return est, lo, hi


def part_c(d, vw):
    rows = []
    traded = d[~d.no_trade]
    wide = traded.pivot_table(index=["expiry_date", "date"], columns="symbol", values="rs_per_g")
    for a, b in [("GOLDPETAL", "GOLDTEN"), ("GOLDGUINEA", "GOLDTEN"), ("GOLDGUINEA", "GOLDPETAL")]:
        s = (1e4 * np.log(wide[a] / wide[b])).dropna()
        dates = s.index.get_level_values("date")
        est, lo, hi = week_boot(s.values, dates.to_period("W"))
        rows.append({"quantity": f"Mean spread {a[4:]}-{b[4:]} (bp)", "estimate": est, "ci95_low": lo, "ci95_high": hi,
                     "n": len(s)})
    import uncertainty                                  # same week-block bootstrap as uncertainty.py
    t = pd.read_csv(os.path.join(bt.RES, "test_trades.csv"))
    for sl, g in t.groupby("slip_bp"):
        _, net, ci, _ = uncertainty.bootstrap(g)
        rows.append({"quantity": f"TEST net P&L at {sl} bp (Rs, total)", "estimate": net, "ci95_low": ci[0],
                     "ci95_high": ci[1], "n": len(g)})
    out = pd.DataFrame(rows)
    out["margin_pct_of_estimate"] = ((out.ci95_high - out.ci95_low) / 2 / out.estimate.abs() * 100).round(0)
    return out.round(1)


def main():
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    a = part_a(d)
    b, vw = part_b(d)
    c = part_c(d, vw)
    for name, df in (("integrity", a), ("close_vs_vwap", b), ("margins", c)):
        df.to_csv(os.path.join(bt.RES, f"testbed_{name}.csv"), index=False)
    pd.set_option("display.width", 200)
    print(f"Rows: {len(d)}  Contracts: {d.groupby(['symbol', 'expiry_date']).ngroups}\n")
    print("A. DATA INTEGRITY")
    print(a.assign(error_rate=a.error_rate.map(pct)).to_string(index=False))
    print("\nB. SETTLEMENT CLOSE vs AVERAGE TRADED PRICE (bp, per gram of pure gold)")
    print(b.to_string(index=False))
    print("\nC. 95% MARGINS ON THE MAIN NUMBERS")
    print(c.to_string(index=False))


if __name__ == "__main__":
    main()

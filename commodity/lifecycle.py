"""Contract lifecycle: liquidity build-up, the tender period, and whether every trade fits inside it.

    python lifecycle.py

MCX gold contracts are compulsory/staggered delivery: the tender period starts 5 business days before
expiry, and brokers square off open positions before it (e.g. 5 Feb 2026 expiry: close by 29 Jan 2026;
28 Nov 2025 expiry: close by 21 Nov 2025). Here the last safe exit day is 5 business days before expiry
(numpy business-day offset, Mon-Fri; exchange holidays ignored, which only makes the check stricter
by at most a day).
Checks, for every stored trade of both strategies:
  - entry on or after the contract's first trading day in our files
  - exit on or before the last safe exit day (outside the tender period)
Also measures how liquidity builds over a contract's life (median kg traded per day by business days
to expiry) and records each contract's first and last trading day.
Writes results/lifecycle_liquidity.csv, results/lifecycle_trades.csv, results/lifecycle_contracts.csv.
"""
import os

import numpy as np
import pandas as pd

import backtest as bt

LOT = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
TENDER_BDAYS = 5
BUCKETS = [0, 5, 10, 20, 40, 60, 80, 100, 130]


def main():
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    d["kg"] = d.volume_lots * d.symbol.map(LOT) / 1000
    d["bdays_left"] = np.busday_count(d.date.values.astype("datetime64[D]"), d.expiry_date.values.astype("datetime64[D]"))

    # liquidity build-up
    d["bucket"] = pd.cut(d.bdays_left, BUCKETS, right=True, include_lowest=True)
    liq = d.groupby(["symbol", "bucket"], observed=True).agg(kg_median=("kg", "median"), oi_lots_median=("open_interest_lots", "median"),
                                                              no_trade_pct=("no_trade", lambda x: 100 * x.mean()), days=("kg", "size"))
    liq.round(2).to_csv(os.path.join(bt.RES, "lifecycle_liquidity.csv"))

    # contracts
    con = d.groupby(["symbol", "expiry_date"]).agg(first=("date", "min"), last=("date", "max"), days=("date", "size")).reset_index()
    con["last_safe_exit"] = pd.to_datetime(np.busday_offset(con.expiry_date.values.astype("datetime64[D]"), -TENDER_BDAYS, roll="backward"))
    con.to_csv(os.path.join(bt.RES, "lifecycle_contracts.csv"), index=False, date_format="%Y-%m-%d")
    C = con.set_index(["symbol", "expiry_date"])

    # trades
    rows = []
    runs = {"A_test": "test_trades.csv", "A_hold": "holdout_trades.csv", "B_dev": "fairvalue_dev_trades.csv", "B_hold": "fairvalue_holdout_trades.csv"}
    k = pd.read_json(os.path.join(bt.RES, "fairvalue_params.json"), typ="series")["k"]
    for run, f in runs.items():
        log = pd.read_csv(os.path.join(bt.RES, f))
        if "k" in log:
            log = log[log.k == k]
        log = log[log.slip_bp == 5]
        for t in log.itertuples():
            e = pd.Timestamp(t.expiry)
            legs = ([(s, e) for s in t.pair.split("-")] if run.startswith("A")
                    else [(t.symbol, e), ("GOLDM", pd.Timestamp(t.goldm_expiry))])
            entry, exit_ = pd.Timestamp(t.entry), pd.Timestamp(t.exit)
            first = max(C.at[l, "first"] for l in legs)
            safe = min(C.at[l, "last_safe_exit"] for l in legs)
            rows.append({"run": run, "what": getattr(t, "pair", None) or t.symbol, "expiry": t.expiry, "entry": t.entry, "exit": t.exit,
                         "last_safe_exit": safe.date(), "bdays_before_safe": int(np.busday_count(exit_.date(), safe.date())),
                         "inside_life": entry >= first, "outside_tender": exit_ <= safe, "net_5bp": t.net_rs})
    tr = pd.DataFrame(rows)
    tr.to_csv(os.path.join(bt.RES, "lifecycle_trades.csv"), index=False)
    s = tr.groupby("run").agg(trades=("net_5bp", "size"), inside_life=("inside_life", "sum"), outside_tender=("outside_tender", "sum"),
                              net_all=("net_5bp", "sum"))
    s["net_outside_tender_only"] = tr[tr.outside_tender].groupby("run").net_5bp.sum()
    s["net_of_tender_trades"] = tr[~tr.outside_tender].groupby("run").net_5bp.sum()
    s = s.fillna(0).round(0)
    s.to_csv(os.path.join(bt.RES, "lifecycle_summary.csv"))
    pd.set_option("display.width", 200)
    print("Liquidity build-up: median kg traded per day, by business days left to expiry")
    print(liq.kg_median.unstack(0).round(1).to_string())
    print("\nTrades vs contract calendar (net at 5 bp, Rs)")
    print(s.to_string())


if __name__ == "__main__":
    main()

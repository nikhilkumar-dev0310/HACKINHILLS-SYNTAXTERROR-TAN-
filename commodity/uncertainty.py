"""How sure can we be? Two descriptive checks (no parameter is chosen here).

    python uncertainty.py

1. Bootstrap the already-run TEST result of the frozen strategy. Trades entered in the same
   week are resampled together, because one price move can trigger several pairs at once.
   Method: block resampling in the spirit of Politis & Romano (1994), JASA 89(428),
   doi:10.1080/01621459.1994.10476870.
2. Structural level of each spread: mean and sd per contract cycle. If a gap sits at a stable
   non-zero level cycle after cycle, it is a persistent premium, not a temporary mispricing.
"""
import os

import numpy as np
import pandas as pd

import backtest as bt

RNG = np.random.default_rng(20261001)
B = 10000


def bootstrap(trades):
    weeks = trades.assign(wk=pd.to_datetime(trades.entry).dt.to_period("W")).groupby("wk")["net_rs"].sum().values
    draws = np.array([RNG.choice(weeks, len(weeks), replace=True).sum() for _ in range(B)])
    return len(weeks), weeks.sum(), np.percentile(draws, [2.5, 97.5]), (draws > 0).mean()


def main():
    t = pd.read_csv(os.path.join(bt.RES, "test_trades.csv"))
    rows = []
    for sl, g in t.groupby("slip_bp"):
        n, net, ci, p_pos = bootstrap(g)
        rows.append({"slip_bp": sl, "trades": len(g), "entry_weeks": n, "net_rs": round(net),
                     "ci95_low": round(ci[0]), "ci95_high": round(ci[1]), "share_of_draws_positive": round(p_pos, 2)})
    boot = pd.DataFrame(rows)
    boot.to_csv(os.path.join(bt.RES, "test_bootstrap.csv"), index=False)
    print("TEST (frozen strategy, already run once): 95% interval for total net P&L, Rs")
    print(boot.to_string(index=False))

    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    d = d[(d.symbol != "GOLDM") & ~d.no_trade]
    wide = d.pivot_table(index=["expiry_date", "date"], columns="symbol", values="rs_per_g")
    out = []
    for a, b in [("GOLDGUINEA", "GOLDPETAL"), ("GOLDGUINEA", "GOLDTEN"), ("GOLDPETAL", "GOLDTEN")]:
        s = (1e4 * np.log(wide[a] / wide[b])).dropna()
        for exp, g in s.groupby(level=0):
            if len(g) >= 10:
                out.append({"pair": f"{a[4:]}-{b[4:]}", "expiry": exp.date(), "days": len(g),
                            "mean_bp": round(g.mean()), "sd_bp": round(g.std()),
                            "share_days_positive": round((g > 0).mean(), 2)})
    lv = pd.DataFrame(out)
    lv.to_csv(os.path.join(bt.RES, "spread_levels.csv"), index=False)
    print("\nSpread level per contract cycle (bp, price per gram of pure gold, a minus b):")
    print(lv.to_string(index=False))


if __name__ == "__main__":
    main()

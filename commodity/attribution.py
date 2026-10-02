"""Split every trade's profit into the part from the gap and the part from gold's own move.

    python attribution.py          (after the strategy runs; reads the stored trade logs)

For a trade long A / short B in equal grams g (pos = +1, or -1 for the reverse):
    gross = pos * g * [(A1 - A0) - (B1 - B0)]
This splits EXACTLY into
    gap part  = pos * g * B0 * (A1/B1 - A0/B0)      gap change, valued at the entry gold price
    gold part = pos * g * (B1 - B0) * (A1/B1 - 1)   gold's move times the gap still open at exit
The gold part is what the gold price itself did to the trade: it is non-zero only because the two
legs are not identical (a premium, or GOLDM's 99.5% purity against 99.9%). B is the hedge leg
(the second contract for Strategy A, GOLDM for Strategy B). Prices are the ones each trade was
filled at: settlement close per pure gram (A) and the day's average traded price per gram (B).
Writes results/attribution_trades.csv and results/attribution_summary.csv.
"""
import os

import numpy as np
import pandas as pd

import backtest as bt

LOT = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}


def prices():
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    grams = d.volume_lots * d.symbol.map(LOT)
    d["vwap_g"] = np.where(grams > 0, d.value_lakhs * 1e5 / grams.where(grams > 0), np.nan)
    return d.set_index(["symbol", "expiry_date", "date"])


def split(pos, g, a0, a1, b0, b1):
    gross = pos * g * ((a1 - a0) - (b1 - b0))
    gap = pos * g * b0 * (a1 / b1 - a0 / b0)
    return gross, gap, gross - gap, (b1 / b0 - 1) * 100


def strategy_a(px, log):
    rows = []
    for t in log[log.slip_bp == 5].itertuples():
        a, b = t.pair.split("-")
        e, d0, d1 = pd.Timestamp(t.expiry), pd.Timestamp(t.entry), pd.Timestamp(t.exit)
        pos = 1 if t.side.startswith("long") else -1
        A0, A1 = px.at[(a, e, d0), "rs_per_g"], px.at[(a, e, d1), "rs_per_g"]
        B0, B1 = px.at[(b, e, d0), "rs_per_g"], px.at[(b, e, d1), "rs_per_g"]
        gross, gap, gold, mv = split(pos, 40, A0, A1, B0, B1)
        rows.append({"strategy": "A", "what": t.pair, "expiry": t.expiry, "entry": t.entry, "exit": t.exit,
                     "gross_stored": t.gross_rs, "gross": gross, "gap_part": gap, "gold_part": gold,
                     "gold_move_pct": mv, "net_5bp": t.net_rs})
    return rows


def strategy_b(px, log):
    rows = []
    for t in log[log.slip_bp == 5].itertuples():
        x, e, me = t.symbol, pd.Timestamp(t.expiry), pd.Timestamp(t.goldm_expiry)
        d0, d1 = pd.Timestamp(t.entry), pd.Timestamp(t.exit)
        pos = 1 if t.side.startswith("buy X") else -1
        A0, A1 = px.at[(x, e, d0), "vwap_g"], px.at[(x, e, d1), "vwap_g"]
        B0, B1 = px.at[("GOLDM", me, d0), "vwap_g"], px.at[("GOLDM", me, d1), "vwap_g"]
        gross, gap, gold, mv = split(pos, 200, A0, A1, B0, B1)
        rows.append({"strategy": "B", "what": x, "expiry": t.expiry, "entry": t.entry, "exit": t.exit,
                     "gross_stored": t.gross_rs, "gross": gross, "gap_part": gap, "gold_part": gold,
                     "gold_move_pct": mv, "net_5bp": t.net_rs})
    return rows


def main():
    px = prices()
    runs = {"A_test": ("A", "test_trades.csv"), "A_hold": ("A", "holdout_trades.csv"),
            "B_dev": ("B", "fairvalue_dev_trades.csv"), "B_hold": ("B", "fairvalue_holdout_trades.csv")}
    out, summ = [], []
    for key, (kind, f) in runs.items():
        log = pd.read_csv(os.path.join(bt.RES, f))
        if kind == "B" and "k" in log:
            k = pd.read_json(os.path.join(bt.RES, "fairvalue_params.json"), typ="series")["k"]
            log = log[log.k == k]
        rows = strategy_a(px, log) if kind == "A" else strategy_b(px, log)
        df = pd.DataFrame(rows).assign(run=key)
        err = (df.gross - df.gross_stored).abs().max()
        assert err < 1, f"{key}: decomposition does not reproduce stored gross (max error Rs {err:.2f})"
        out.append(df)
        corr = np.corrcoef(df.net_5bp, df.gold_move_pct)[0, 1] if len(df) > 2 else np.nan
        summ.append({"run": key, "trades": len(df), "gross": df.gross.sum(), "gap_part": df.gap_part.sum(),
                     "gold_part": df.gold_part.sum(), "gold_share_of_gross_pct": 100 * df.gold_part.sum() / df.gross.sum(),
                     "abs_gold_share_pct": 100 * df.gold_part.abs().sum() / (df.gap_part.abs().sum() + df.gold_part.abs().sum()),
                     "corr_net_vs_gold_move": corr,
                     "corr_net_vs_abs_gold_move": np.corrcoef(df.net_5bp, df.gold_move_pct.abs())[0, 1] if len(df) > 2 else np.nan,
                     "max_reproduction_error_rs": err})
    pd.concat(out).round(2).to_csv(os.path.join(bt.RES, "attribution_trades.csv"), index=False)
    s = pd.DataFrame(summ).round(2)
    s.to_csv(os.path.join(bt.RES, "attribution_summary.csv"), index=False)
    pd.set_option("display.width", 200)
    print("Profit split per run (Rs, before costs). gold_part = what gold's own move did to the trade.")
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()

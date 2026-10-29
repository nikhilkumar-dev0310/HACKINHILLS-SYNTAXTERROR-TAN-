"""One verdict per pair: is the gap tradable after costs on data the rules never saw?

    python pair_verdict.py      (writes results/pair_verdicts.json; run before dashboard/export.py)

Uses only trades already made by the two frozen rules on windows opened after they were frozen; nothing is
chosen or re-run here. Each of the six pairs is traded by exactly one rule, so rupees are never mixed
across position sizes:
    GOLDM vs a small contract   Strategy B (fair price, 200 g a leg): holdout Aug 2025 - May 2026, sealed 2016-2023
    two small contracts         Strategy A (pairs, 40 g a leg): test 1 May - Jul 2025, holdout, sealed 2016-2023
Retrained Strategy C is left out: it was fitted after the earlier windows had been seen.

The verdict rule, written before the numbers were read (net after all costs at 5 bp slippage per leg, 95% range
from resampling whole entry weeks, as in uncertainty.py):
    UNTESTABLE   fewer than MIN_TRADES out-of-sample trades: too little to say either way
    EDGE         the 95% range is above zero, and the result is still positive without the Dec 2025 - Mar 2026 crash
    CRASH ONLY   the 95% range is above zero, but outside the crash it does not make money
    NO EDGE      the 95% range includes zero or sits below it
"""
import json
import os

import numpy as np
import pandas as pd

import backtest as bt

OUT = os.path.join(bt.RES, "pair_verdicts.json")
SLIP = 5
MIN_TRADES = 20
B_RUNS = 10000
CRASH = ("2025-12-01", "2026-03-31")
PAIRS = [("M-TEN", "GOLDM", "GOLDTEN"), ("M-GUINEA", "GOLDM", "GOLDGUINEA"), ("M-PETAL", "GOLDM", "GOLDPETAL"),
         ("TEN-GUINEA", "GOLDTEN", "GOLDGUINEA"), ("TEN-PETAL", "GOLDTEN", "GOLDPETAL"), ("GUINEA-PETAL", "GOLDGUINEA", "GOLDPETAL")]
WINDOWS = {"test": "May – Jul 2025", "holdout": "Aug 2025 – May 2026", "test3": "2016 – 2019", "test2": "2020 – 2023"}


def out_of_sample():
    """Every out-of-sample trade of the frozen rules at SLIP bp: pair key, window, entry date, net rupees."""
    R = bt.RES
    key = lambda a, b: "-".join(sorted([a, b], key=lambda s: ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"].index(s)))
    rows = []
    for f, win in (("test_trades.csv", "test"), ("holdout_trades.csv", "holdout")):          # Strategy A
        t = pd.read_csv(os.path.join(R, f))
        for x in t[t.slip_bp == SLIP].itertuples():
            rows.append((key(*x.pair.split("-")), "A", win, x.entry, x.net_rs))
    t = pd.read_csv(os.path.join(R, "fairvalue_holdout_trades.csv"))                          # Strategy B holdout, frozen k
    k = json.load(open(os.path.join(R, "fairvalue_params.json"))).get("k", 1.5) if os.path.exists(os.path.join(R, "fairvalue_params.json")) else 1.5
    t = t[(t.slip_bp == SLIP) & (t.k == k)]
    for x in t.itertuples():
        rows.append((key("GOLDM", x.symbol), "B", "holdout", x.entry, x.net_rs))
    s = pd.read_csv(os.path.join(R, "sealed_trades.csv"))                                     # sealed 2016-2023, frozen A and B only
    s = s[(s.slip_bp == SLIP) & s.strategy.str.contains("as frozen")]
    for x in s.itertuples():
        st = x.strategy[0]
        pair = key(*x.symbol.split("-")) if st == "A" else key("GOLDM", x.symbol)
        rows.append((pair, st, x.test, x.entry, x.net_rs))
    return pd.DataFrame(rows, columns=["pair", "strategy", "window", "entry", "net"])


def week_boot(t, rng):
    w = t.assign(wk=pd.to_datetime(t.entry).dt.to_period("W")).groupby("wk").net.sum().values
    if len(w) < 2:
        return None
    d = np.array([rng.choice(w, len(w), replace=True).sum() for _ in range(B_RUNS)])
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), float((d > 0).mean()), int(len(w))


def verdict(n, lo, net_ex_crash):
    if n < MIN_TRADES:
        return "UNTESTABLE"
    if lo is not None and lo > 0:
        return "EDGE" if net_ex_crash > 0 else "CRASH ONLY"
    return "NO EDGE"


def main():
    rng = np.random.default_rng(20261029)
    T = out_of_sample()
    names = {"GOLDM-GOLDTEN": "M-TEN", "GOLDM-GOLDGUINEA": "M-GUINEA", "GOLDM-GOLDPETAL": "M-PETAL",
             "GOLDTEN-GOLDGUINEA": "TEN-GUINEA", "GOLDTEN-GOLDPETAL": "TEN-PETAL", "GOLDGUINEA-GOLDPETAL": "GUINEA-PETAL"}
    T["pair"] = T.pair.map(names)
    out = []
    for p, a, b in PAIRS:
        t = T[T.pair == p]
        crash = t.entry.between(*CRASH)
        bs = week_boot(t, rng) if len(t) else None
        n, net = int(len(t)), float(t.net.sum())
        ex = float(t[~crash].net.sum())
        v = verdict(n, bs[0] if bs else None, ex)
        out.append({"pair": p, "a": a, "b": b, "strategy": t.strategy.iloc[0] if n else ("B" if a == "GOLDM" else "A"),
                    "trades": n, "net": round(net), "lo": round(bs[0]) if bs else None, "hi": round(bs[1]) if bs else None,
                    "p_pos": round(100 * bs[2]) if bs else None, "weeks": bs[3] if bs else 0,
                    "net_crash": round(float(t[crash].net.sum())), "net_ex_crash": round(ex), "trades_crash": int(crash.sum()),
                    "windows": {w: {"trades": int((t.window == w).sum()), "net": round(float(t[t.window == w].net.sum()))} for w in WINDOWS if (t.window == w).any()},
                    "verdict": v})
    res = {"slip_bp": SLIP, "min_trades": MIN_TRADES, "crash": list(CRASH), "windows": WINDOWS, "rows": out,
           "source": "results/test_trades.csv, holdout_trades.csv, fairvalue_holdout_trades.csv, sealed_trades.csv (frozen A and B only)"}
    json.dump(res, open(OUT, "w"), indent=1)
    for r in out:
        print(f"{r['pair']:13s} {r['verdict']:11s} trades {r['trades']:4d}  net {r['net']:>9,}  95% {r['lo']} to {r['hi']}  ex-crash {r['net_ex_crash']:>9,}  {r['windows']}")


if __name__ == "__main__":
    main()

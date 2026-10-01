"""Walk-forward relative-value backtest for same-expiry MCX gold futures pairs.

    python backtest.py train      # parameter sweep on TRAIN dates only, applies the pre-declared rule
    python backtest.py test       # runs the FROZEN parameters once on TEST dates (only after you approve)
    python backtest.py holdout    # second sealed test: same frozen parameters, run once on HOLDOUT dates

Reads clean/gold_futures.csv produced by ingest.py. Writes results/*.csv and results/frozen_params.json.
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "clean", "gold_futures.csv")
RES = os.path.join(HERE, "results")

# ---- Split by calendar date (not by contract), so no market day is seen in both sets ----
TRAIN_END = pd.Timestamp("2025-04-30")
TEST_START = pd.Timestamp("2025-05-01")
TEST_END = pd.Timestamp("2025-07-31")      # last expiry with all three symbols downloaded
# Second sealed test, declared on 2026-10-01 before any of its data was downloaded.
HOLDOUT_START = pd.Timestamp("2025-08-01")
HOLDOUT_END = pd.Timestamp("2026-09-30")

# ---- Position: equal grams of gold per leg, in whole lots ----
LOT_GRAMS = {"GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}   # confirmed from Volume(In 000's) / Volume(Lots)
POSITION_GRAMS = 40                                            # LCM of 1, 8, 10: 40 PETAL / 5 GUINEA / 4 TEN lots

# ---- Trading rules (fixed, not tuned) ----
EXIT_Z = 0.0                 # close when the spread returns to its trailing mean
NO_ENTRY_DAYS = 7            # no new entries within 7 calendar days of expiry
FORCE_EXIT_DAYS = 3          # close any open trade 3 calendar days before expiry (avoid tender/delivery period)
MIN_GRAMS_TRADED = 1000      # skip a day if either leg traded under 1 kg of gold that day

# ---- Costs, per leg per side, as a fraction of turnover ----
EXCHANGE_FEE = 2.10 / 1e5    # MCX: Rs 2.10 per lakh of futures turnover (exchange filing, effective 1 Oct 2024)
CTT_SELL = 0.0001            # Commodity transaction tax 0.01%, sell side only (non-agri futures)
STAMP_BUY = 0.00002          # Stamp duty 0.002%, buy side (assumption from broker charge sheets)
SEBI_FEE = 10 / 1e7          # Rs 10 per crore (assumption from broker charge sheets)
BROKERAGE_FLAT = 20.0        # Rs 20 per executed order, capped at 0.03% (ASSUMPTION: typical discount broker)
BROKERAGE_CAP = 0.0003
GST = 0.18                   # on brokerage + exchange fee + SEBI fee
SLIPPAGE_BP = [0, 5, 10]     # per leg per side: settlement close is not a fill, so test a range

# ---- Sweep grid and the selection rule, declared before any result was seen ----
LOOKBACKS = [5, 10, 15]
ENTRY_ZS = [1.5, 2.0, 2.5]
SELECT_SLIPPAGE_BP = 5
MIN_TRADES, MIN_PAIRS = 8, 2
DEFAULT = {"lookback": 10, "entry_z": 2.0}   # used if no combination qualifies


def load_pairs():
    d = pd.read_csv(DATA, parse_dates=["date", "expiry_date"])
    last = d["date"].max()
    d = d[(d["symbol"] != "GOLDM") & (d["expiry_date"] <= last)]   # GOLDM never shares an expiry; drop live contracts
    d["grams_traded"] = d["volume_lots"] * d["symbol"].map(LOT_GRAMS)
    pairs = {}
    for exp, g in d.groupby("expiry_date"):
        for a, b in itertools.combinations(sorted(g["symbol"].unique()), 2):
            A = g[(g.symbol == a) & ~g.no_trade].set_index("date")
            B = g[(g.symbol == b) & ~g.no_trade].set_index("date")
            idx = A.index.intersection(B.index).sort_values()
            if len(idx) < 10:
                continue
            p = pd.DataFrame({
                "a": A.loc[idx, "rs_per_g"], "b": B.loc[idx, "rs_per_g"],
                "liq_ok": (A.loc[idx, "grams_traded"] >= MIN_GRAMS_TRADED) & (B.loc[idx, "grams_traded"] >= MIN_GRAMS_TRADED),
                "dte": (exp - idx).days,
            }, index=idx)
            p["spread_bp"] = 1e4 * np.log(p["a"] / p["b"])
            pairs[(a, b, exp.date())] = p
    return pairs


def leg_cost(price_per_g, side, slip_bp):
    """Cost in rupees for one leg, one side (buy or sell), POSITION_GRAMS of gold."""
    turnover = price_per_g * POSITION_GRAMS
    brokerage = min(BROKERAGE_FLAT, BROKERAGE_CAP * turnover)
    fees = turnover * (EXCHANGE_FEE + SEBI_FEE)
    tax = turnover * (CTT_SELL if side == "sell" else STAMP_BUY)
    return brokerage + fees + GST * (brokerage + fees) + tax + turnover * slip_bp / 1e4


def run_pair(p, lookback, entry_z, start, end, slip_bp):
    """Signal at close t, execute at the next both-traded close (t+1). History before `start` may be used for z."""
    s = p["spread_bp"]
    # Compare today's spread with the PREVIOUS `lookback` days. Including today in the window caps |z| at
    # (N-1)/sqrt(N) (1.79 for N=5), which made high thresholds unreachable in the first run.
    prev = s.shift(1)
    mu = prev.rolling(lookback, min_periods=lookback).mean()
    sd = prev.rolling(lookback, min_periods=lookback).std()
    z = (s - mu) / sd
    days = p.index[(p.index >= start) & (p.index <= end)]
    trades, pos, pending = [], 0, None
    entry = None
    for i, t in enumerate(days):
        # 1) execute yesterday's decision at today's close
        if pending is not None:
            px = p.loc[t]
            if pending == "close" and pos != 0:
                trades.append(close_trade(entry, t, px, pos, slip_bp))
                pos, entry = 0, None
            elif pending in (1, -1) and pos == 0 and px["liq_ok"]:
                pos, entry = pending, (t, px)
            pending = None
        last_day = i == len(days) - 1
        # 2) forced exits act today (no waiting) to stay out of the expiry window and the split boundary
        if pos != 0 and (p.loc[t, "dte"] <= FORCE_EXIT_DAYS or last_day):
            trades.append(close_trade(entry, t, p.loc[t], pos, slip_bp))
            pos, entry = 0, None
            continue
        if last_day or np.isnan(z.loc[t]):
            continue
        # 3) decide at today's close
        if pos == 0 and p.loc[t, "liq_ok"] and p.loc[t, "dte"] > NO_ENTRY_DAYS:
            if z.loc[t] >= entry_z:
                pending = -1          # spread rich: short a, long b
            elif z.loc[t] <= -entry_z:
                pending = 1           # spread cheap: long a, short b
        elif pos != 0 and ((pos == 1 and z.loc[t] >= EXIT_Z) or (pos == -1 and z.loc[t] <= EXIT_Z)):
            pending = "close"
    return trades


def close_trade(entry, t_exit, px_exit, pos, slip_bp):
    t_in, px_in = entry
    g = POSITION_GRAMS
    gross = pos * ((px_exit["a"] - px_in["a"]) - (px_exit["b"] - px_in["b"])) * g
    buy_a = "buy" if pos == 1 else "sell"
    sell_a = "sell" if pos == 1 else "buy"
    cost = (leg_cost(px_in["a"], buy_a, slip_bp) + leg_cost(px_in["b"], sell_a, slip_bp)
            + leg_cost(px_exit["a"], sell_a, slip_bp) + leg_cost(px_exit["b"], buy_a, slip_bp))
    gold_move = ((px_exit["a"] + px_exit["b"]) - (px_in["a"] + px_in["b"])) / 2 * g   # unhedged 40 g, for comparison
    return {"entry": t_in.date(), "exit": t_exit.date(), "side": "long a/short b" if pos == 1 else "short a/long b",
            "entry_spread_bp": round(1e4 * np.log(px_in["a"] / px_in["b"]), 1),
            "exit_spread_bp": round(1e4 * np.log(px_exit["a"] / px_exit["b"]), 1),
            "days_held": (t_exit - t_in).days, "gross_rs": gross, "cost_rs": cost, "net_rs": gross - cost,
            "gold_move_40g_rs": gold_move}


def sweep(pairs, start, end):
    rows, logs = [], []
    for lb, ez, sl in itertools.product(LOOKBACKS, ENTRY_ZS, SLIPPAGE_BP):
        per_pair = {}
        for key, p in pairs.items():
            tr = run_pair(p, lb, ez, start, end, sl)
            per_pair[f"{key[0][4:]}-{key[1][4:]} {key[2]:%d%b}"] = len(tr)
            for t in tr:
                logs.append({"lookback": lb, "entry_z": ez, "slip_bp": sl, "pair": f"{key[0]}-{key[1]}", "expiry": key[2], **t})
        sub = [l for l in logs if (l["lookback"], l["entry_z"], l["slip_bp"]) == (lb, ez, sl)]
        rows.append({"lookback": lb, "entry_z": ez, "slip_bp": sl, "trades": len(sub),
                     "pairs_traded": sum(v > 0 for v in per_pair.values()),
                     "gross_rs": sum(l["gross_rs"] for l in sub), "cost_rs": sum(l["cost_rs"] for l in sub),
                     "net_rs": sum(l["net_rs"] for l in sub),
                     "hit_rate": np.mean([l["net_rs"] > 0 for l in sub]) if sub else np.nan, **per_pair})
    return pd.DataFrame(rows), pd.DataFrame(logs)


def main(mode):
    os.makedirs(RES, exist_ok=True)
    pairs = load_pairs()
    print("Pairs (both legs traded):")
    for (a, b, e), p in pairs.items():
        tr = p[p.index <= TRAIN_END]
        te = p[(p.index >= TEST_START) & (p.index <= TEST_END)]
        print(f"  {a}-{b} exp {e}: train {len(tr)} days, test {len(te)} days, "
              f"spread mean {p.spread_bp.mean():.0f} bp, sd {p.spread_bp.std():.0f} bp")

    if mode == "train":
        table, log = sweep(pairs, pd.Timestamp("2000-01-01"), TRAIN_END)
        table.to_csv(os.path.join(RES, "train_sweep.csv"), index=False)
        log.to_csv(os.path.join(RES, "train_trades.csv"), index=False)
        pd.set_option("display.width", 200)
        show = table[table.slip_bp == SELECT_SLIPPAGE_BP].round(1)
        print(f"\nTRAIN sweep at {SELECT_SLIPPAGE_BP} bp slippage per leg per side (Rs, 40 g per leg):")
        print(show.to_string(index=False))
        ok = show[(show.trades >= MIN_TRADES) & (show.pairs_traded >= MIN_PAIRS)]
        if len(ok):
            best = ok.sort_values(["net_rs", "lookback"], ascending=[False, False]).iloc[0]
            chosen = {"lookback": int(best.lookback), "entry_z": float(best.entry_z), "how": "pre-declared rule"}
        else:
            chosen = {**DEFAULT, "how": f"default: no combination had >= {MIN_TRADES} trades across >= {MIN_PAIRS} pairs"}
        chosen.update({"exit_z": EXIT_Z, "position_grams": POSITION_GRAMS, "min_grams_traded": MIN_GRAMS_TRADED,
                       "train_end": str(TRAIN_END.date()), "test": [str(TEST_START.date()), str(TEST_END.date())]})
        json.dump(chosen, open(os.path.join(RES, "frozen_params.json"), "w"), indent=2)
        print("\nSelected:", chosen)
        print("TEST has not been run.")
    elif mode in ("test", "holdout"):
        f = os.path.join(RES, "frozen_params.json")
        if not os.path.exists(f):
            sys.exit("Run `python backtest.py train` first.")
        fp = json.load(open(f))
        window = (TEST_START, TEST_END) if mode == "test" else (HOLDOUT_START, HOLDOUT_END)
        out = []
        for sl in SLIPPAGE_BP:
            for (a, b, e), p in pairs.items():
                for t in run_pair(p, fp["lookback"], fp["entry_z"], *window, sl):
                    out.append({"slip_bp": sl, "pair": f"{a}-{b}", "expiry": e, **t})
        log = pd.DataFrame(out)
        log.to_csv(os.path.join(RES, f"{mode}_trades.csv"), index=False)
        print(f"\n{mode.upper()} {window[0].date()} to {window[1].date()} with frozen params {fp['lookback']=} {fp['entry_z']=}")
        print(log.groupby("slip_bp")[["gross_rs", "cost_rs", "net_rs"]].agg(["count", "sum"]).round(1) if len(log) else "No trades.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")

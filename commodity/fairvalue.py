"""GOLDM-anchored fair-price strategy. Pre-registered 2026-10-01, before the holdout data exists.

    python fairvalue.py dev        # learn and choose k on market days up to 2025-08-05
    python fairvalue.py holdout    # run the frozen rule ONCE on 2025-08-06 to 2026-05-29

Idea (from accuracy.py): per gram of pure gold, GOLDM and GOLDTEN agree, while GOLDGUINEA and
GOLDPETAL carry a stable premium. GOLDM trades 20-60x more gold than the others, so it is the
most reliable price. For each smaller contract X:
    fair price of X today = GOLDM moved to X's expiry with today's carry  +  X's usual premium
    premium today         = 10,000 x ln(X / GOLDM moved to X's expiry), in bp
    usual premium         = mean of X's premium on all PREVIOUS days (all cycles, past only)
    z                     = (premium today - usual premium) / sd of previous premiums
Trade: z >= k -> X rich: sell X, buy GOLDM.  z <= -k -> X cheap: buy X, sell GOLDM.
One open position per contract type at a time: when several expiries of X signal on the same day,
only the most liquid one (most grams traded that day) is taken, so one event is not counted as
several trades. Exit when z returns to 0, 5 business days before X's expiry (delivery is staggered over the last
3 trading days), or at the end of the window. No entries in the last 10 business days.
Signals use the close of day t; trades fill at the NEXT day's average traded price (VWAP =
turnover / grams traded), plus slippage. 200 g per leg: 2 GOLDM lots vs 20 TEN / 25 GUINEA /
200 PETAL lots. Costs as in backtest.py.

Windows (calendar dates, declared before any holdout data was downloaded):
  DEV      market days up to 2025-08-05: every day already seen in any file before 2026-06.
  HOLDOUT  2025-08-06 to 2026-05-29: market days that appear in none of the files analyzed so far.
  Days from 2026-06-01 were seen (through contracts expiring Nov 2026 - Feb 2027) and are not
  used for evaluation.
Rule for k, declared before running: grid {1.0, 1.5, 2.0}; pick the highest DEV net at 5 bp among
settings with >= 8 trades over >= 2 contracts; if none qualifies, k = 2.0. The chosen rule goes to
HOLDOUT whatever its DEV result, because DEV has only a few months of GOLDTEN.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

import backtest as bt
from accuracy import carry_table
from ingest import PURITY, QUOTE_GRAMS

LOT_GRAMS = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
GRAMS = 200
DEV_END = pd.Timestamp("2025-08-05")
HOLD_START, HOLD_END = pd.Timestamp("2025-08-06"), pd.Timestamp("2026-05-29")
K_GRID, SELECT_SLIP, MIN_TRADES, MIN_CONTRACTS, DEFAULT_K = (1.0, 1.5, 2.0), 5, 8, 2, 2.0
MIN_HISTORY = 20
EXIT_BDAYS, NO_ENTRY_BDAYS = 5, 10
PARAMS = os.path.join(bt.RES, "fairvalue_params.json")


def load():
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    d["raw_per_g"] = d.close / d.symbol.map(QUOTE_GRAMS)
    d["grams"] = d.volume_lots * d.symbol.map(LOT_GRAMS)
    d["vwap_per_g"] = np.where(d.grams > 0, d.value_lakhs * 1e5 / d.grams.where(d.grams > 0), np.nan)
    d["ok"] = ~d.no_trade & (d.grams >= 1000) & d.vwap_per_g.notna()
    t = d[~d.no_trade & (d.volume_lots > 0)]
    _, carry = carry_table(t.assign(vwap_rs_per_g=t.vwap_per_g / t.symbol.map(PURITY)))
    return d, carry


def build(d, carry):
    """One frame per contract cycle of X, with the matched GOLDM contract."""
    M = d[d.symbol == "GOLDM"]
    frames = {}
    for (sym, exp), x in d[(d.symbol != "GOLDM")].groupby(["symbol", "expiry_date"]):
        m_exp = M.expiry_date[(M.expiry_date - exp).dt.days.between(0, 10)].unique()
        if len(m_exp) != 1:
            continue
        m = M[M.expiry_date == m_exp[0]].set_index("date")
        x = x.set_index("date")
        idx = x.index.intersection(m.index)
        f = pd.DataFrame(index=idx.sort_values())
        gap = (exp - m_exp[0]).days
        k = carry.reindex(f.index)
        f["prem_bp"] = 1e4 * (np.log(x.loc[f.index, "rs_per_g"] / m.loc[f.index, "rs_per_g"]) - k * gap / 365)
        f["x_fill"], f["m_fill"] = x.loc[f.index, "vwap_per_g"], m.loc[f.index, "vwap_per_g"]
        f["x_close"], f["m_close"] = x.loc[f.index, "raw_per_g"], m.loc[f.index, "raw_per_g"]
        f["x_grams"] = x.loc[f.index, "grams"]
        f["ok"] = x.loc[f.index, "ok"] & m.loc[f.index, "ok"] & k.notna()
        f["bleft"] = np.busday_count(f.index.values.astype("datetime64[D]"), np.datetime64(exp.date()))
        f["symbol"], f["expiry"], f["m_expiry"] = sym, exp.date(), m_exp[0].date()
        frames[(sym, exp)] = f
    return frames


def add_z(frames):
    """Usual premium and sd from previous days only, pooled over all cycles of the same symbol."""
    allp = pd.concat(frames.values())
    for sym, g in allp[allp.ok].groupby("symbol"):
        daily = g.groupby(level=0).prem_bp.mean().sort_index()          # one value per market day
        ref = daily.expanding(MIN_HISTORY).mean().shift(1)
        sd = daily.expanding(MIN_HISTORY).std().shift(1)
        for key, f in frames.items():
            if key[0] == sym:
                f["ref_bp"], f["sd_bp"] = ref.reindex(f.index), sd.reindex(f.index)
                f["z"] = (f.prem_bp - f.ref_bp) / f.sd_bp
    return frames


def leg_cost(price, side, slip):
    turnover = price * GRAMS
    brokerage = min(bt.BROKERAGE_FLAT, bt.BROKERAGE_CAP * turnover)
    fees = turnover * (bt.EXCHANGE_FEE + bt.SEBI_FEE)
    tax = turnover * (bt.CTT_SELL if side == "sell" else bt.STAMP_BUY)
    return brokerage + fees + bt.GST * (brokerage + fees) + tax + turnover * slip / 1e4


FILL = ("x_fill", "m_fill")      # next-day VWAP; ("x_close", "m_close") for the robustness check


def trade(entry, t_out, f, pos, slip):
    t_in = entry
    xc, mc = FILL
    xi, mi, xo, mo = f.at[t_in, xc], f.at[t_in, mc], f.at[t_out, xc], f.at[t_out, mc]
    gross = pos * ((xo - xi) - (mo - mi)) * GRAMS
    buy_x, sell_x = ("buy", "sell") if pos == 1 else ("sell", "buy")
    cost = (leg_cost(xi, buy_x, slip) + leg_cost(mi, sell_x, slip) + leg_cost(xo, sell_x, slip) + leg_cost(mo, buy_x, slip))
    return {"symbol": f.symbol.iloc[0], "expiry": f.expiry.iloc[0], "goldm_expiry": f.m_expiry.iloc[0],
            "entry": t_in.date(), "exit": t_out.date(), "side": "buy X / sell GOLDM" if pos == 1 else "sell X / buy GOLDM",
            "entry_prem_bp": round(f.at[t_in, "prem_bp"], 1), "exit_prem_bp": round(f.at[t_out, "prem_bp"], 1),
            "days_held": (t_out - t_in).days, "gross_rs": gross, "cost_rs": cost, "net_rs": gross - cost}


def simulate(fs, k, start, end, slip):
    """All cycles of one contract type; at most one open position at a time."""
    days = sorted(set().union(*[f.index[(f.index >= start) & (f.index <= end)] for f in fs]))
    last_day = {id(f): (f.index[(f.index >= start) & (f.index <= end) & f.ok].max()) for f in fs}
    out, pos, pending, entry, cur = [], 0, None, None, None
    for t in days:
        if pending is not None:
            f, act = pending
            if t in f.index and f.at[t, "ok"]:
                if act == "close":
                    out.append(trade(entry, t, f, pos, slip)); pos, entry, cur = 0, None, None
                else:
                    pos, entry, cur = act, t, f
                pending = None
            elif t > last_day[id(f)] or (act != "close"):
                if act != "close":
                    pending = None                       # entry not fillable next day: drop it
        if cur is not None and t in cur.index and cur.at[t, "ok"] and pending is None:
            if cur.at[t, "bleft"] <= EXIT_BDAYS or t == last_day[id(cur)]:
                out.append(trade(entry, t, cur, pos, slip)); pos, entry, cur = 0, None, None
                continue
            z = cur.at[t, "z"]
            if not np.isnan(z) and ((pos == 1 and z >= 0) or (pos == -1 and z <= 0)):
                pending = (cur, "close")
            continue
        if cur is None and pending is None:
            cands = [f for f in fs if t in f.index and f.at[t, "ok"] and t < last_day[id(f)]
                     and f.at[t, "bleft"] > NO_ENTRY_BDAYS and not np.isnan(f.at[t, "z"]) and abs(f.at[t, "z"]) >= k]
            if cands:
                f = max(cands, key=lambda c: c.at[t, "x_grams"])
                pending = (f, -1 if f.at[t, "z"] > 0 else 1)
    assert cur is None, "a position was left open"
    return out


def run(frames, k, start, end):
    rows = []
    for slip in bt.SLIPPAGE_BP:
        for sym in sorted({key[0] for key in frames}):
            fs = [f for key, f in frames.items() if key[0] == sym]
            rows += [{"k": k, "slip_bp": slip, **t} for t in simulate(fs, k, start, end, slip)]
    return pd.DataFrame(rows)


def summary(log):
    if log.empty:
        return pd.DataFrame()
    g = log.groupby(["k", "slip_bp"])
    s = g.agg(trades=("net_rs", "size"), contracts=("expiry", lambda e: log.loc[e.index, ["symbol", "expiry"]].drop_duplicates().shape[0]),
              gross_rs=("gross_rs", "sum"), cost_rs=("cost_rs", "sum"), net_rs=("net_rs", "sum"),
              hit_rate=("net_rs", lambda v: (v > 0).mean()))
    return s.reset_index().round(2)


def main(mode):
    d, carry = load()
    frames = add_z(build(d, carry))
    os.makedirs(bt.RES, exist_ok=True)
    if mode == "dev":
        logs = pd.concat([run(frames, k, pd.Timestamp("2000-01-01"), DEV_END) for k in K_GRID], ignore_index=True)
        logs.to_csv(os.path.join(bt.RES, "fairvalue_dev_trades.csv"), index=False)
        s = summary(logs)
        s.to_csv(os.path.join(bt.RES, "fairvalue_dev.csv"), index=False)
        print(f"DEV (market days up to {DEV_END.date()}), Rs for {GRAMS} g per leg, fills at next-day VWAP:")
        print(s.to_string(index=False))
        by = logs[logs.slip_bp == SELECT_SLIP].groupby(["k", "symbol"]).net_rs.agg(["size", "sum"]).round(0)
        print("\nBy contract at 5 bp (trades, net Rs):"); print(by.to_string())
        pool = s[(s.slip_bp == SELECT_SLIP) & (s.trades >= MIN_TRADES) & (s.contracts >= MIN_CONTRACTS)]
        k = float(pool.sort_values("net_rs", ascending=False).k.iloc[0]) if len(pool) else DEFAULT_K
        how = "pre-declared rule" if len(pool) else "default: no k had enough trades"
        params = {"k": k, "how": how, "grams_per_leg": GRAMS, "dev_end": str(DEV_END.date()),
                  "holdout": [str(HOLD_START.date()), str(HOLD_END.date())], "fills": "next-day VWAP",
                  "exit_bdays": EXIT_BDAYS, "no_entry_bdays": NO_ENTRY_BDAYS, "min_history_days": MIN_HISTORY}
        json.dump(params, open(PARAMS, "w"), indent=2)
        print("\nFrozen:", params, "\nHOLDOUT has not been run.")
    elif mode == "holdout":
        prm = json.load(open(PARAMS))
        log = run(frames, prm["k"], HOLD_START, HOLD_END)
        log.to_csv(os.path.join(bt.RES, "fairvalue_holdout_trades.csv"), index=False)
        print(f"HOLDOUT {HOLD_START.date()} to {HOLD_END.date()}, frozen k={prm['k']}")
        print(summary(log).to_string(index=False) if len(log) else "No trades (holdout data not downloaded yet?)")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")

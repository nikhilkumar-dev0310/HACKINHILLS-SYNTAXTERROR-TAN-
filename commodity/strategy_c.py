"""Strategy C: the GOLDM-anchored fair-price model (Strategy B), retrained on all development data.

    python strategy_c.py dev       # choose the rules on DEV only (walk-forward by calendar year)
    python strategy_c.py sealed    # run the FROZEN rules once on both sealed windows (A, B and C)

Declared in DOWNLOADS_ROUND2.md (round 3) and committed before this script first ran on the new data.

DEV  = market days before 2016-01-01 and from 2024-01-01 (clean/gold_futures.csv only; this mode
       never opens clean/sealed_rows.csv).
SEALED windows, run once each, after the rules are frozen:
       TEST 3  2016-01-01 to 2019-12-31
       TEST 2  2020-01-01 to 2023-10-09
       Signals use past days only, so earlier sealed days may serve as history for later ones.

What can be learned (grid declared here, before any DEV result was seen):
  ref     usual premium from all previous days ("all") or the previous 365 calendar days ("1y")
  k       entry when |z| >= k: 1.5, 2.0, 2.5
  stress  enter only when GOLDM's 5-day realised volatility is at or above this percentile of its
          previous 365 days: none, 0.80, 0.90   (the project's finding: gaps pay in sharp moves)
  exit    close when z comes back to within this distance of zero: 0.0, 0.5
  hold    close after this many business days at most: none, 10
Everything else is Strategy B unchanged: 200 g per leg, next-day VWAP fills, exit 5 business days
before expiry, no entries in the last 10, one open position per contract type, full costs.

Selection rule (declared): score every setting on DEV at 5 bp slippage. Eligible settings have
>= 10 trades over >= 2 contract types and a positive net in at least half of the DEV years in which
they traded. Pick the highest total net; ties go to fewer trades. If none is eligible, keep
Strategy B as frozen (ref all, k 1.5, no stress filter, exit 0, no hold limit).
Walk-forward check of the selection itself: for each DEV year from the third onward, choose with
the same rule using only earlier DEV years, then record that choice's net in the year.
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

import backtest as bt
import fairvalue as fv
from accuracy import carry_table
from ingest import PURITY, QUOTE_GRAMS

HERE = os.path.dirname(os.path.abspath(__file__))
SEALED_FILE = os.path.join(HERE, "clean", "sealed_rows.csv")
PARAMS = os.path.join(bt.RES, "strategy_c_params.json")
TESTS = {"test3": ("2016-01-01", "2019-12-31"), "test2": ("2020-01-01", "2023-10-09")}

GRID = {"ref": ["all", "1y"], "k": [1.5, 2.0, 2.5], "stress": [None, 0.80, 0.90], "exit": [0.0, 0.5], "hold": [None, 10]}
B_RULES = {"ref": "all", "k": 1.5, "stress": None, "exit": 0.0, "hold": None}
SELECT_SLIP, MIN_TRADES, MIN_TYPES = 5, 10, 2


# ---------------------------------------------------------------- data
def load(include_sealed):
    d = pd.read_csv(bt.DATA, parse_dates=["date", "expiry_date"])
    hist = os.path.join(HERE, "clean", "gold_futures_history.csv")      # pre-2016 DEV rows (ingest.py)
    if os.path.exists(hist):
        d = pd.concat([pd.read_csv(hist, parse_dates=["date", "expiry_date"]), d], ignore_index=True)
    if include_sealed:
        d = pd.concat([d, pd.read_csv(SEALED_FILE, parse_dates=["date", "expiry_date"])], ignore_index=True)
    d = d.sort_values(["symbol", "expiry_date", "date"]).reset_index(drop=True)
    d["raw_per_g"] = d.close / d.symbol.map(QUOTE_GRAMS)
    d["grams"] = d.volume_lots * d.symbol.map(fv.LOT_GRAMS)
    d["vwap_per_g"] = np.where(d.grams > 0, d.value_lakhs * 1e5 / d.grams.where(d.grams > 0), np.nan)
    d["ok"] = ~d.no_trade & (d.grams >= 1000) & d.vwap_per_g.notna()
    t = d[~d.no_trade & (d.volume_lots > 0)]
    _, carry = carry_table(t.assign(vwap_rs_per_g=t.vwap_per_g / t.symbol.map(PURITY)))
    return d, carry


def stress_pct(d):
    """Percentile of GOLDM's 5-day realised volatility within its previous 365 calendar days (incl. today)."""
    m = d[(d.symbol == "GOLDM") & ~d.no_trade & (d.prev_close > 0)]
    m = m.loc[m.groupby("date").grams.idxmax()].set_index("date").sort_index()
    r = np.log(m.close / m.prev_close)
    vol5 = np.sqrt((r ** 2).rolling(5, min_periods=5).sum())
    pct = vol5.rolling("365D", min_periods=60).apply(lambda w: (w <= w[-1]).mean(), raw=True)
    return pct


def add_ref(frames, ref):
    allp = pd.concat(frames.values())
    for sym, g in allp[allp.ok].groupby("symbol"):
        daily = g.groupby(level=0).prem_bp.mean().sort_index()
        if ref == "all":
            mu, sd = daily.expanding(fv.MIN_HISTORY).mean(), daily.expanding(fv.MIN_HISTORY).std()
        else:
            mu, sd = daily.rolling("365D", min_periods=fv.MIN_HISTORY).mean(), daily.rolling("365D", min_periods=fv.MIN_HISTORY).std()
        mu, sd = mu.shift(1), sd.shift(1)
        for key, f in frames.items():
            if key[0] == sym:
                f[f"z_{ref}"] = (f.prem_bp - mu.reindex(f.index)) / sd.reindex(f.index)
    return frames


# ---------------------------------------------------------------- simulation (Strategy B's loop plus the learned gates)
def simulate(fs, rules, start, end, slip, pct):
    zc, k, ex, hold, st = f"z_{rules['ref']}", rules["k"], rules["exit"], rules["hold"], rules["stress"]
    days = sorted(set().union(*[f.index[(f.index >= start) & (f.index <= end)] for f in fs]))
    last_day = {id(f): f.index[(f.index >= start) & (f.index <= end) & f.ok].max() for f in fs}
    out, pos, pending, entry, cur = [], 0, None, None, None
    for t in days:
        if pending is not None:
            f, act = pending
            if t in f.index and f.at[t, "ok"]:
                if act == "close":
                    out.append(fv.trade(entry, t, f, pos, slip)); pos, entry, cur = 0, None, None
                else:
                    pos, entry, cur = act, t, f
                pending = None
            elif act != "close":
                pending = None
        if cur is not None and t in cur.index and cur.at[t, "ok"] and pending is None:
            held = np.busday_count(entry.date(), t.date())
            if cur.at[t, "bleft"] <= fv.EXIT_BDAYS or t == last_day[id(cur)]:
                out.append(fv.trade(entry, t, cur, pos, slip)); pos, entry, cur = 0, None, None
                continue
            z = cur.at[t, zc]
            if (hold is not None and held >= hold) or (not np.isnan(z) and ((pos == 1 and z >= -ex) or (pos == -1 and z <= ex))):
                pending = (cur, "close")
            continue
        if cur is None and pending is None:
            if st is not None and not (pct.get(t, np.nan) >= st):
                continue
            cands = [f for f in fs if t in f.index and f.at[t, "ok"] and t < last_day[id(f)]
                     and f.at[t, "bleft"] > fv.NO_ENTRY_BDAYS and not np.isnan(f.at[t, zc]) and abs(f.at[t, zc]) >= k]
            if cands:
                f = max(cands, key=lambda c: c.at[t, "x_grams"])
                pending = (f, -1 if f.at[t, zc] > 0 else 1)
    return out


def run(frames, rules, start, end, slips, pct):
    rows = []
    for slip in slips:
        for sym in sorted({key[0] for key in frames}):
            fs = [f for key, f in frames.items() if key[0] == sym]
            rows += [{"slip_bp": slip, **t} for t in simulate(fs, rules, pd.Timestamp(start), pd.Timestamp(end), slip, pct)]
    return pd.DataFrame(rows)


def prepare(include_sealed):
    d, carry = load(include_sealed)
    frames = fv.build(d, carry)
    for ref in GRID["ref"]:
        frames = add_ref(frames, ref)
    return d, frames, stress_pct(d)


# ---------------------------------------------------------------- selection
def name(r):
    return f"ref={r['ref']} k={r['k']} stress={r['stress']} exit={r['exit']} hold={r['hold']}"


def choose(table, years):
    """table: one row per (setting, year) with trades, types, net. Returns the chosen setting name or None."""
    sub = table[table.year.isin(years)]
    if sub.empty:
        return None
    agg = sub.groupby("setting").agg(trades=("trades", "sum"), net=("net", "sum"))
    types = sub.groupby("setting").types.apply(lambda s: len(set().union(*s)))
    active = sub[sub.trades > 0].groupby("setting").net.apply(lambda v: (v > 0).mean())
    agg = agg.join(types).join(active.rename("pos_share"))
    ok = agg[(agg.trades >= MIN_TRADES) & (agg.types >= MIN_TYPES) & (agg.pos_share >= 0.5)]
    if ok.empty:
        return None
    return ok.sort_values(["net", "trades"], ascending=[False, True]).index[0]


def dev():
    d, frames, pct = prepare(include_sealed=False)
    assert not d.date.between(pd.Timestamp(TESTS["test3"][0]), pd.Timestamp(TESTS["test2"][1])).any(), "sealed rows leaked into DEV"
    settings = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    logs, rows = [], []
    for r in settings:
        log = run(frames, r, "2000-01-01", "2100-01-01", [SELECT_SLIP], pct)
        if len(log):
            log["year"] = pd.to_datetime(log.entry).dt.year
            log["setting"] = name(r)
            logs.append(log)
    L = pd.concat(logs, ignore_index=True)
    years = sorted(L.year.unique())
    for r in settings:
        n = name(r)
        for y in years:
            g = L[(L.setting == n) & (L.year == y)]
            rows.append({"setting": n, "year": y, "trades": len(g), "types": set(g.symbol), "net": g.net_rs.sum()})
    T = pd.DataFrame(rows)
    out = T.assign(types=T.types.apply(lambda s: ",".join(sorted(s))))
    out.pivot_table(index="setting", columns="year", values="net", aggfunc="sum").round(0).to_csv(os.path.join(bt.RES, "strategy_c_dev_grid.csv"))

    wf = []
    for i, y in enumerate(years):
        if i < 2:
            continue
        pick = choose(T, years[:i]) or name(B_RULES)
        g = T[(T.setting == pick) & (T.year == y)]
        wf.append({"year": y, "chosen_with_years_before": pick, "trades": int(g.trades.sum()), "net_rs": round(float(g.net.sum()), 0)})
    WF = pd.DataFrame(wf)
    WF.to_csv(os.path.join(bt.RES, "strategy_c_walkforward.csv"), index=False)

    final = choose(T, years)
    how = "declared rule on all DEV years" if final else "no setting eligible: Strategy B kept"
    final = final or name(B_RULES)
    rules = next(r for r in settings if name(r) == final)
    full = run(frames, rules, "2000-01-01", "2100-01-01", bt.SLIPPAGE_BP, pct)
    full.to_csv(os.path.join(bt.RES, "strategy_c_dev_trades.csv"), index=False)
    base = run(frames, B_RULES, "2000-01-01", "2100-01-01", bt.SLIPPAGE_BP, pct)
    base.to_csv(os.path.join(bt.RES, "strategy_b_dev_alldata_trades.csv"), index=False)
    params = {**rules, "how": how, "dev_years": [int(y) for y in years], "grams_per_leg": fv.GRAMS,
              "fills": "next-day VWAP", "selection_slip_bp": SELECT_SLIP, "sealed_windows": TESTS}
    json.dump(params, open(PARAMS, "w"), indent=2, default=str)

    pd.set_option("display.width", 220)
    top = T.groupby("setting").agg(trades=("trades", "sum"), net=("net", "sum")).sort_values("net", ascending=False)
    print(f"DEV years: {years}\nTop settings at {SELECT_SLIP} bp (Rs, {fv.GRAMS} g per leg):\n{top.head(12).round(0).to_string()}")
    print(f"\nStrategy B rules on all DEV data at 5 bp: {base[base.slip_bp == 5].net_rs.sum():,.0f} from {int((base.slip_bp == 5).sum())} trades")
    print("\nWalk-forward check of the selection (chosen with earlier years only):\n" + WF.to_string(index=False))
    print(f"  walk-forward total: {WF.net_rs.sum():,.0f}")
    print("\nFROZEN:", params)
    s = full.groupby("slip_bp").agg(trades=("net_rs", "size"), gross=("gross_rs", "sum"), cost=("cost_rs", "sum"), net=("net_rs", "sum")).round(0)
    print(s.to_string())
    print("Sealed windows have not been run.")


# ---------------------------------------------------------------- the one sealed run
def sealed():
    if not os.path.exists(PARAMS):
        sys.exit("Freeze the rules first: python strategy_c.py dev")
    marker = os.path.join(bt.RES, "sealed_run_done.json")
    if os.path.exists(marker):
        sys.exit("The sealed windows have already been run once; results are in results/sealed_*.csv.")
    rules = {k: v for k, v in json.load(open(PARAMS)).items() if k in GRID}
    d, frames, pct = prepare(include_sealed=True)
    out = []
    for test, (a, b) in TESTS.items():
        for label, r in (("C (retrained)", rules), ("B (as frozen)", B_RULES)):
            log = run(frames, r, a, b, bt.SLIPPAGE_BP, pct)
            if len(log):
                out.append(log.assign(test=test, strategy=label))
        # Strategy A: pairs of same-expiry small contracts, frozen lookback 10 / entry z 2.0
        fa = json.load(open(os.path.join(bt.RES, "frozen_params.json")))
        for (pa, pb, e), p in sealed_pairs(d).items():
            for sl in bt.SLIPPAGE_BP:
                for t in bt.run_pair(p, fa["lookback"], fa["entry_z"], pd.Timestamp(a), pd.Timestamp(b), sl):
                    out.append(pd.DataFrame([{"slip_bp": sl, "symbol": f"{pa}-{pb}", "expiry": e, **t, "test": test, "strategy": "A (as frozen)"}]))
    S = pd.concat(out, ignore_index=True)
    S.to_csv(os.path.join(bt.RES, "sealed_trades.csv"), index=False)
    summ = S.groupby(["test", "strategy", "slip_bp"]).agg(trades=("net_rs", "size"), gross=("gross_rs", "sum"),
                                                          cost=("cost_rs", "sum"), net=("net_rs", "sum"),
                                                          hit=("net_rs", lambda v: (v > 0).mean())).round(2).reset_index()
    summ.to_csv(os.path.join(bt.RES, "sealed_summary.csv"), index=False)
    json.dump({"run_at": pd.Timestamp.now(tz="Asia/Kolkata").isoformat(), "rules_c": rules}, open(marker, "w"), indent=2)
    print(summ.to_string(index=False))


def sealed_pairs(d):
    """Strategy A's pairs (backtest.load_pairs) built from the given rows, sealed windows included."""
    d = d[(d.symbol != "GOLDM") & (d.expiry_date <= d.date.max())].copy()
    d["grams_traded"] = d.volume_lots * d.symbol.map(bt.LOT_GRAMS)
    pairs = {}
    for exp, g in d.groupby("expiry_date"):
        for a, b in itertools.combinations(sorted(g.symbol.unique()), 2):
            A = g[(g.symbol == a) & ~g.no_trade].set_index("date")
            B = g[(g.symbol == b) & ~g.no_trade].set_index("date")
            idx = A.index.intersection(B.index).sort_values()
            if len(idx) < 10:
                continue
            p = pd.DataFrame({"a": A.loc[idx, "rs_per_g"], "b": B.loc[idx, "rs_per_g"],
                              "liq_ok": (A.loc[idx, "grams_traded"] >= bt.MIN_GRAMS_TRADED) & (B.loc[idx, "grams_traded"] >= bt.MIN_GRAMS_TRADED),
                              "dte": (exp - idx).days}, index=idx)
            p["spread_bp"] = 1e4 * np.log(p.a / p.b)
            pairs[(a, b, exp.date())] = p
    return pairs


if __name__ == "__main__":
    {"dev": dev, "sealed": sealed}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()

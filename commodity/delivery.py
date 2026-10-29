"""What the small contracts' premium costs a trader: selling before the delivery window, or taking delivery.

    python delivery.py          (writes results/delivery.json; run before dashboard/export.py)

GOLDGUINEA and GOLDPETAL trade at a standing premium per pure gram over GOLDM with the same expiry
(carry-adjusted, the series on the site; fairvalue.build). For every contract cycle of each small contract,
three readings of that premium:
    entry       about a month before expiry: the first liquid day 20 business days or fewer before it
    last exit   the last liquid day outside the delivery window: 5 business days before expiry, the
                project's safe-exit rule (MCX's tender period is the last 3 trading days)
    delivery    the contract's final settlement: its last day in our files, at most 2 business days from expiry
A trader who buys the small contract instead of GOLDM and sells before the delivery window carries only the
change in the premium while holding it (entry minus last exit). One who holds on and takes delivery of the
coins pays the premium in full: relative to taking GOLDM's bar, the gold costs what the premium was at entry
(the premium's change to settlement is P&L; the premium left at settlement is the price of the smaller piece).
Rupees per gram use the small contract's own price per pure gram on each day.

The headline uses cycles expiring from April 2025, when GOLDTEN started trading: from then on GOLDM (995) and
GOLDTEN (999) agree per pure gram, which checks the purity normalization. Older cycles are kept in the output
but not interpreted: they show the small contracts at a discount about as often as at a premium, and the
small contracts' specifications over those years have not been checked here.
A retail comparison (a 1 g coin at a jeweller) needs retail prices we do not hold, so none is made.
Size: at the last safe exit, the open interest still held (lots x grams per lot x purity) times the premium per
pure gram is the premium a holder carries into the delivery window, in rupees. Summed over the verified cycles,
it says how much money the premium question is about.
Reads every MCX row held (2003 on). Descriptive only: no strategy is chosen or re-run on these rows.
"""
import json
import os

import numpy as np
import pandas as pd

import backtest as bt
import fairvalue as fv
import strategy_c as sc

OUT = os.path.join(bt.RES, "delivery.json")
ENTRY_BDAYS = 20             # "about a month before expiry"
SETTLE_MAX_BDAYS = 2         # the last row must be this close to expiry to count as the settlement
VERIFIED_FROM = "2025-04-01"  # GOLDTEN's first day: the per-gram normalization is cross-checked from here


PURITY = 0.999                 # the three small contracts are 999 fine


def readings(f, price, oi=None, lot_g=None):
    """Entry, last-exit and settlement readings of one cycle's premium frame, or None if a reading is missing.
    f: fairvalue.build frame (index date; prem_bp, ok, bleft). price: the small contract's Rs per pure gram by date.
    oi, lot_g: the contract's open interest in lots by date and grams per lot, for the rupees held into delivery."""
    liq = f[f.ok]
    ent, pre = liq[liq.bleft <= ENTRY_BDAYS], liq[liq.bleft >= fv.EXIT_BDAYS]
    if ent.empty or pre.empty or f.bleft.iat[-1] > SETTLE_MAX_BDAYS:
        return None
    e, p, s = ent.index[0], pre.index[-1], f.index[-1]
    if e > p:                                   # liquid only inside the last few weeks: no room to enter and exit
        return None
    rs = lambda day, bp: float(price[day] * bp / 1e4)
    return {"entry": str(e.date()), "entry_bp": float(f.prem_bp[e]), "entry_rs_g": rs(e, f.prem_bp[e]),
            "exit": str(p.date()), "exit_bp": float(f.prem_bp[p]),
            "settle": str(s.date()), "settle_bp": float(f.prem_bp[s]), "settle_rs_g": rs(s, f.prem_bp[s]),
            "early_exit_bp": float(f.prem_bp[e] - f.prem_bp[p]), "early_exit_rs_g": rs(e, f.prem_bp[e] - f.prem_bp[p]),
            "window_change_bp": float(f.prem_bp[s] - f.prem_bp[p]),
            **({"exit_oi_lots": int(oi[p]), "exit_kg": float(oi[p] * lot_g * PURITY / 1e3),
                "exit_premium_rs_cr": float(oi[p] * lot_g * PURITY * price[p] * f.prem_bp[p] / 1e4 / 1e7)} if oi is not None and p in oi.index else {})}


def summary(rows):
    x = pd.DataFrame(rows)
    q = lambda c, p: round(float(x[c].quantile(p)), 1)
    return {"cycles": int(len(x)), "first": x.expiry.min(), "last": x.expiry.max(),
            "entry_bp": q("entry_bp", 0.5), "exit_bp": q("exit_bp", 0.5), "settle_bp": q("settle_bp", 0.5),
            "entry_rs_g": q("entry_rs_g", 0.5), "settle_rs_g": q("settle_rs_g", 0.5),
            "early_exit_bp": q("early_exit_bp", 0.5), "early_exit_bp_iqr": [q("early_exit_bp", 0.25), q("early_exit_bp", 0.75)],
            "early_exit_abs_bp": round(float(x.early_exit_bp.abs().median()), 1), "early_exit_rs_g": q("early_exit_rs_g", 0.5),
            "window_change_bp": q("window_change_bp", 0.5),
            "settle_positive": round(float((x.settle_bp > 0).mean()), 3), "entry_positive": round(float((x.entry_bp > 0).mean()), 3),
            **({"exit_premium_rs_cr_total": round(float(x.exit_premium_rs_cr.sum()), 2), "exit_premium_rs_cr_median": round(float(x.exit_premium_rs_cr.median()), 2),
                "exit_kg_median": round(float(x.exit_kg.median()), 1), "exit_oi_cycles": int(x.exit_premium_rs_cr.notna().sum())} if "exit_premium_rs_cr" in x else {})}


def main():
    d, carry = sc.load(include_sealed=True)
    frames = fv.build(d, carry)
    price = d.set_index(["symbol", "expiry_date", "date"]).rs_per_g
    oi = d.set_index(["symbol", "expiry_date", "date"]).open_interest_lots
    cyc = []
    for (sym, exp), f in sorted(frames.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        r = readings(f, price.loc[(sym, exp)], oi.loc[(sym, exp)], bt.LOT_GRAMS.get(sym))
        if r:
            cyc.append({"symbol": sym, "expiry": str(exp.date()), **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}})
    out = {"rows": [], "cycles": cyc, "rules": {"entry_bdays": ENTRY_BDAYS, "exit_bdays": fv.EXIT_BDAYS, "settle_max_bdays": SETTLE_MAX_BDAYS, "verified_from": VERIFIED_FROM},
           "retail": None, "source": "clean/gold_futures_history.csv, clean/sealed_rows.csv, clean/gold_futures.csv; fairvalue.build premium over GOLDM"}
    for sym in ("GOLDTEN", "GOLDGUINEA", "GOLDPETAL"):
        rows = [c for c in cyc if c["symbol"] == sym]
        if rows:
            ver = [c for c in rows if c["expiry"] >= VERIFIED_FROM]
            out["rows"].append({"symbol": sym, "verified": summary(ver) if ver else None, "all": summary(rows)})
    json.dump(out, open(OUT, "w"), indent=1)
    print(json.dumps(out["rows"], indent=1))


if __name__ == "__main__":
    main()

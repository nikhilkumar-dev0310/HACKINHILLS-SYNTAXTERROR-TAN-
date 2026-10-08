"""Is the result skill, tuning or luck? Three checks, on DEVELOPMENT data only (the sealed years are never opened).

    python overfit.py          (after strategy_c.py dev; writes results/overfit.json)

1. Probability of Backtest Overfitting (PBO), by combinatorially symmetric cross-validation
   (Bailey, Borwein, Lopez de Prado & Zhu, 2017, "The probability of backtest overfitting",
   Journal of Computational Finance 20(4)). Input: Strategy C's 72-setting grid, net profit per DEV year
   at 5 bp (results/strategy_c_dev_grid.csv). Blocks: the 10 complete DEV years (2008-2015, 2024, 2025);
   2026 is a part year and is left out. For each of the C(10,5) = 252 ways to split the years in two
   halves: pick the setting with the best total in one half, then see where that setting ranks in the
   other half. PBO = share of splits where it lands at or below the median. 0 means picking the best
   setting reliably picks a good one; 0.5 means the pick is a coin toss; above 0.5 means the in-sample
   winner tends to be an out-of-sample loser.
2. Placebo: Strategy B's own DEV trades (results/strategy_b_dev_alldata_trades.csv, 5 bp) against
   2,000 random strategies on the same contracts: the same number of trades per contract type, each
   opened on a random eligible day of a random cycle, held for the same number of market days, random
   direction, the same fills (next-day VWAP) and the same costs. Reports where B's net sits in that
   distribution.
3. No-carry baseline: Strategy B's rules with the carry adjustment switched off (GOLDM is not moved to
   the other contract's expiry). Shows what the carry adjustment contributes.
"""
import itertools
import json
import os

import numpy as np
import pandas as pd

import backtest as bt
import fairvalue as fv
import strategy_c as sc

OUT = os.path.join(bt.RES, "overfit.json")
N_PLACEBO = 2000
SLIP = 5


def pbo(grid, years):
    """grid: settings x years array of net profit. Returns PBO, the logits and the out-of-sample
    relative rank (0 worst .. 1 best) of the in-sample winner for every split."""
    M = np.asarray(grid, float)
    S = M.shape[1]
    if S % 2 or S < 2:
        raise ValueError("CSCV needs an even number of blocks")
    if M.shape[0] < 2:
        raise ValueError("CSCV needs at least two settings")
    ranks = []
    for half in itertools.combinations(range(S), S // 2):
        rest = [j for j in range(S) if j not in half]
        ins, oos = M[:, list(half)].sum(1), M[:, rest].sum(1)
        best = int(np.argmax(ins))
        # relative rank of the in-sample winner out of sample, ties counted half
        below = (oos < oos[best]).sum() + 0.5 * ((oos == oos[best]).sum() - 1)
        ranks.append(below / (len(oos) - 1))
    w = np.clip(np.asarray(ranks), 1e-6, 1 - 1e-6)
    logits = np.log(w / (1 - w))
    return float((logits <= 0).mean()), logits, w


def frames_dev(carry_on=True):
    d, carry = sc.load(include_sealed=False)
    assert not d.date.between(pd.Timestamp(sc.TESTS["test3"][0]), pd.Timestamp(sc.TESTS["test2"][1])).any(), "sealed rows leaked"
    if not carry_on:
        carry = carry * 0.0
    frames = fv.build(d, carry)
    for ref in sc.GRID["ref"]:
        frames = sc.add_ref(frames, ref)
    return d, frames


def in_dev(t):
    return any(pd.Timestamp(a) <= t <= pd.Timestamp(b) for a, b in sc.DEV_WINDOWS)


def placebo(frames, actual, rng):
    """Random-entry strategies matched to the actual trades (count per type, holding length)."""
    by_sym = {}
    for (sym, _), f in frames.items():
        ok = f.ok.values & np.array([in_dev(t) for t in f.index])
        by_sym.setdefault(sym, []).append((f, ok))
    plan = []
    for t in actual.itertuples():
        f = frames[(t.symbol, pd.Timestamp(t.expiry))]
        i0, i1 = f.index.get_loc(pd.Timestamp(t.entry)), f.index.get_loc(pd.Timestamp(t.exit))
        plan.append((t.symbol, max(1, i1 - i0)))
    nets = np.empty(N_PLACEBO)
    for n in range(N_PLACEBO):
        total = 0.0
        for sym, h in plan:
            cycles = by_sym[sym]
            for _ in range(200):                        # draw until an eligible start is found
                f, ok = cycles[rng.integers(len(cycles))]
                if len(f) <= h:
                    continue
                i = int(rng.integers(len(f) - h))
                if ok[i] and ok[i + h] and f.bleft.iat[i] > fv.NO_ENTRY_BDAYS and f.bleft.iat[i + h] >= fv.EXIT_BDAYS:
                    total += fv.trade(f.index[i], f.index[i + h], f, int(rng.choice([-1, 1])), SLIP)["net_rs"]
                    break
        nets[n] = total
    return nets


def main():
    g = pd.read_csv(os.path.join(bt.RES, "strategy_c_dev_grid.csv")).set_index("setting")
    years = [c for c in g.columns if c != "2026"]
    p, logits, w = pbo(g[years].fillna(0).values, years)
    out = {"pbo": {"value": round(p, 3), "splits": len(w), "settings": int(len(g)), "blocks": years,
                   "median_oos_rank": round(float(np.median(w)), 3),
                   "share_oos_loss": round(float(np.mean([g[[y for y in years if y not in h]].sum(1).iloc[
                       int(np.argmax(g[list(h)].sum(1).values))] < 0 for h in itertools.combinations(years, len(years) // 2)])), 3),
                   "source": "results/strategy_c_dev_grid.csv", "slip_bp": SLIP}}

    actual = pd.read_csv(os.path.join(bt.RES, "strategy_b_dev_alldata_trades.csv"))
    actual = actual[actual.slip_bp == SLIP]
    _, frames = frames_dev(carry_on=True)
    nets = placebo(frames, actual, np.random.default_rng(20261008))
    b_net = float(actual.net_rs.sum())
    out["placebo"] = {"strategy_b_net": round(b_net), "trades": int(len(actual)), "runs": N_PLACEBO,
                      "placebo_median": round(float(np.median(nets))), "placebo_p5": round(float(np.percentile(nets, 5))),
                      "placebo_p95": round(float(np.percentile(nets, 95))),
                      "share_placebo_at_or_above_b": round(float((nets >= b_net).mean()), 4),
                      "source": "results/strategy_b_dev_alldata_trades.csv", "slip_bp": SLIP}

    _, nf = frames_dev(carry_on=False)
    pct = sc.stress_pct(sc.load(include_sealed=False)[0])
    nc = sc.run_dev(nf, sc.B_RULES, [SLIP], pct)
    out["no_carry"] = {"net": round(float(nc.net_rs.sum())) if len(nc) else 0, "trades": int(len(nc)),
                       "with_carry_net": round(b_net), "with_carry_trades": int(len(actual)), "slip_bp": SLIP}
    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

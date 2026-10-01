"""Compare research-backed spread methods on TRAIN dates only (to 2025-04-30).

    python methods.py

TEST (May-Jul 2025) has already been used once and is NOT touched here.
HOLDOUT (2025-08-01 to 2026-09-30) stays sealed; the method chosen here is declared in
results/method_choice.json and run on HOLDOUT once, together with the frozen baseline.

Methods (all decide at close t and trade at the next both-traded close, same costs as backtest.py):
  zscore      Rolling mean/sd of the previous N days (the frozen baseline rule).
              Gatev, Goetzmann & Rouwenhorst (2006), Rev. Financial Studies 19(3), doi:10.1093/rfs/hhj020
  ou_sscore   AR(1)/Ornstein-Uhlenbeck fit on the previous W days; trade the s-score only when the
              fitted half-life is short; published thresholds 1.25 / 0.75 / 0.50.
              Avellaneda & Lee (2010), Quantitative Finance 10(7), doi:10.1080/14697680903124632
  ou_cost     ou_sscore, but enter only if the expected reversion (in rupees) is at least 2x the
              round-trip cost: costs decide whether a signal is worth taking.
              Motivated by Bertram (2010), Physica A 389(11), doi:10.1016/j.physa.2010.01.045 and
              Leung & Li (2015), Int. J. Theor. Appl. Finance 18(3), doi:10.1142/S021902491550020X
  kalman      Mean-reverting hidden spread observed with noise (settlement prices of thin contracts are
              noisy); parameters by maximum likelihood on the previous W days; trade the filtered spread.
              Elliott, van der Hoek & Malcolm (2005), Quantitative Finance 5(3), doi:10.1080/14697680500149370
"""
import itertools
import json
import os

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import backtest as bt

# MCX: delivery is compulsory and staggered over the last 3 trading days (contract spec), so exit
# 5 business days before expiry and take no new entries in the last 10 business days.
EXIT_BDAYS, NO_ENTRY_BDAYS = 5, 10
COST_FILTER_MULT, COST_FILTER_SLIP_BP = 2.0, 5

# Declared before running: pick the highest TRAIN net at 5 bp among candidates with >= 8 trades
# across >= 2 pairs. Promote it to HOLDOUT only if that net is > 0; otherwise promote nothing.
SELECT_SLIP, MIN_TRADES, MIN_PAIRS = 5, 8, 2

CANDIDATES = (
    [("zscore", {"N": 10, "entry": 2.0})]
    + [("ou_sscore", {"W": w}) for w in (20, 30)]
    + [("ou_cost", {"W": w}) for w in (20, 30)]
    + [("kalman", {"W": w, "c": c}) for w in (20, 30) for c in (1.0, 1.5)]
)


# ---------------------------------------------------------------- signals (past data only)
def sig_zscore(s, N, entry):
    prev = s.shift(1)
    z = (s - prev.rolling(N, min_periods=N).mean()) / prev.rolling(N, min_periods=N).std()
    return pd.DataFrame({"enter": np.where(z <= -entry, 1, np.where(z >= entry, -1, 0)),
                         "exit_long": z >= 0, "exit_short": z <= 0}, index=s.index)


def ar1(x):
    """OLS fit x[t+1] = a + b x[t] + e. Returns mean, equilibrium sd, half-life (days), or None."""
    b, a = np.polyfit(x[:-1], x[1:], 1)
    if not 0 < b < 1:
        return None
    resid = x[1:] - (a + b * x[:-1])
    return a / (1 - b), np.sqrt(resid.var(ddof=2) / (1 - b * b)), np.log(2) / -np.log(b)


def ou_scores(s, W):
    out = pd.Series(np.nan, index=s.index)
    mean = pd.Series(np.nan, index=s.index)
    vals = s.values
    for i in range(W, len(s)):
        fit = ar1(vals[i - W:i])                      # previous W days only
        if fit and fit[2] <= W / 2 and fit[1] > 0:    # trade only if it reverts within half the window
            mean.iloc[i] = fit[0]
            out.iloc[i] = (vals[i] - fit[0]) / fit[1]
    return out, mean


def sig_ou(s, W):
    sc, _ = ou_scores(s, W)
    enter = np.where(sc < -1.25, 1, np.where(sc > 1.25, -1, 0))
    return pd.DataFrame({"enter": enter, "exit_long": sc > -0.50, "exit_short": sc < 0.75}, index=s.index)


def sig_ou_cost(s, W, p):
    sig = sig_ou(s, W)
    _, mean = ou_scores(s, W)
    price = (p["a"] + p["b"]) / 2
    expected_rs = (s - mean).abs() / 1e4 * price * bt.POSITION_GRAMS
    round_trip = 4 * price.apply(lambda x: bt.leg_cost(x, "sell", COST_FILTER_SLIP_BP))
    sig.loc[~(expected_rs >= COST_FILTER_MULT * round_trip), "enter"] = 0
    return sig


def kalman_nll(theta, y):
    A, B, C, D = theta[0], 1 / (1 + np.exp(-theta[1])), np.exp(theta[2]), np.exp(theta[3])
    x, P = y[0], D * D
    nll = 0.0
    for obs in y[1:]:
        x, P = A + B * x, B * B * P + C * C
        S = P + D * D
        v = obs - x
        nll += 0.5 * (np.log(2 * np.pi * S) + v * v / S)
        K = P / S
        x, P = x + K * v, (1 - K) * P
    return nll


def kalman_fit(y):
    b0 = np.clip(np.polyfit(y[:-1], y[1:], 1)[0], 0.05, 0.95)
    sd = max(np.std(np.diff(y)), 1e-3)
    x0 = [y.mean() * (1 - b0), np.log(b0 / (1 - b0)), np.log(sd / 2), np.log(sd / 2)]
    r = minimize(kalman_nll, x0, args=(y,), method="Nelder-Mead", options={"maxiter": 2000, "xatol": 1e-4})
    A, B, C, D = r.x[0], 1 / (1 + np.exp(-r.x[1])), np.exp(r.x[2]), np.exp(r.x[3])
    return A, B, C, D


_KALMAN_CACHE = {}


def sig_kalman(s, W, c):
    key = (W, s.index[0], s.index[-1], round(float(s.sum()), 6))
    if key not in _KALMAN_CACHE:
        _KALMAN_CACHE[key] = kalman_scores(s, W)
    score = _KALMAN_CACHE[key]
    enter = np.where(score <= -c, 1, np.where(score >= c, -1, 0))
    return pd.DataFrame({"enter": enter, "exit_long": score >= 0, "exit_short": score <= 0}, index=s.index)


def kalman_scores(s, W):
    vals = s.values
    score = pd.Series(np.nan, index=s.index)
    for i in range(W, len(s)):
        y = vals[i - W:i + 1]                         # fit on previous W days, filter through today
        A, B, C, D = kalman_fit(y[:-1])
        if B >= 0.99:                                 # no mean reversion within the window: no signal
            continue
        mu, sig = A / (1 - B), C / np.sqrt(1 - B * B)
        x, P = y[0], D * D
        for obs in y[1:]:
            x, P = A + B * x, B * B * P + C * C
            K = P / (P + D * D)
            x, P = x + K * (obs - x), (1 - K) * P
        score.iloc[i] = (x - mu) / sig
    return score


def signals(method, p, prm):
    s = p["spread_bp"]
    if len(s) < 3:
        return pd.DataFrame({"enter": 0, "exit_long": False, "exit_short": False}, index=s.index)
    if method == "zscore":
        return sig_zscore(s, **prm)
    if method == "ou_sscore":
        return sig_ou(s, **prm)
    if method == "ou_cost":
        return sig_ou_cost(s, prm["W"], p)
    return sig_kalman(s, **prm)


# ---------------------------------------------------------------- engine
def simulate(p, sig, expiry, start, end, slip):
    days = p.index[(p.index >= start) & (p.index <= end)]
    bleft = pd.Series(np.busday_count(days.values.astype("datetime64[D]"), np.datetime64(expiry, "D")), index=days)
    trades, pos, pending, entry = [], 0, None, None
    for i, t in enumerate(days):
        px = p.loc[t]
        if pending is not None:
            if pending == "close" and pos:
                trades.append(bt.close_trade(entry, t, px, pos, slip)); pos, entry = 0, None
            elif pending in (1, -1) and not pos and px["liq_ok"]:
                pos, entry = pending, (t, px)
            pending = None
        last = i == len(days) - 1
        if pos and (bleft[t] <= EXIT_BDAYS or last):
            trades.append(bt.close_trade(entry, t, px, pos, slip)); pos, entry = 0, None
            continue
        if last:
            continue
        g = sig.loc[t]
        if not pos and px["liq_ok"] and bleft[t] > NO_ENTRY_BDAYS and g["enter"] != 0:
            pending = int(g["enter"])
        elif (pos == 1 and g["exit_long"]) or (pos == -1 and g["exit_short"]):
            pending = "close"
    return trades


def run(start, end, label):
    pairs = bt.load_pairs()
    rows, logs = [], []
    for method, prm in CANDIDATES:
        name = method + "(" + ", ".join(f"{k}={v}" for k, v in prm.items()) + ")"
        # signals use only data up to each day, so computing them on data up to `end` is exact
        sigs = {k: signals(method, p[p.index <= end], prm) for k, p in pairs.items()}
        for slip in bt.SLIPPAGE_BP:
            tr = []
            for (a, b_, e), p in pairs.items():
                for t in simulate(p, sigs[(a, b_, e)], e, start, end, slip):
                    tr.append({"method": name, "slip_bp": slip, "pair": f"{a}-{b_}", "expiry": e, **t})
            logs += tr
            rows.append({"method": name, "slip_bp": slip, "trades": len(tr),
                         "pairs_traded": len({(x["pair"], x["expiry"]) for x in tr}),
                         "gross_rs": sum(x["gross_rs"] for x in tr), "cost_rs": sum(x["cost_rs"] for x in tr),
                         "net_rs": sum(x["net_rs"] for x in tr),
                         "hit_rate": np.mean([x["net_rs"] > 0 for x in tr]) if tr else np.nan})
    table = pd.DataFrame(rows)
    table.to_csv(os.path.join(bt.RES, f"methods_{label}.csv"), index=False)
    pd.DataFrame(logs).to_csv(os.path.join(bt.RES, f"methods_{label}_trades.csv"), index=False)
    return table


def main():
    os.makedirs(bt.RES, exist_ok=True)
    table = run(pd.Timestamp("2000-01-01"), bt.TRAIN_END, "train")
    show = table.pivot_table(index="method", columns="slip_bp", values="net_rs", sort=False).round(0)
    cnt = table[table.slip_bp == SELECT_SLIP].set_index("method")[["trades", "pairs_traded", "gross_rs", "hit_rate"]]
    print("TRAIN (to 2025-04-30), Rs for 40 g per leg. Net P&L by slippage per leg per side:")
    print(cnt.join(show).round(2).to_string())
    pool = table[(table.slip_bp == SELECT_SLIP) & (table.trades >= MIN_TRADES) & (table.pairs_traded >= MIN_PAIRS)]
    best = pool.sort_values("net_rs", ascending=False).head(1)
    if len(best) and best.net_rs.iloc[0] > 0:
        choice = {"promoted": best.method.iloc[0], "train_net_rs_5bp": round(float(best.net_rs.iloc[0]), 1)}
    else:
        choice = {"promoted": None,
                  "reason": "no candidate had positive TRAIN net at 5 bp with enough trades",
                  "best_candidate": best.method.iloc[0] if len(best) else None,
                  "best_train_net_rs_5bp": round(float(best.net_rs.iloc[0]), 1) if len(best) else None}
    choice["holdout"] = [str(bt.HOLDOUT_START.date()), str(bt.HOLDOUT_END.date())]
    json.dump(choice, open(os.path.join(bt.RES, "method_choice.json"), "w"), indent=2)
    print("\nDecision:", choice)


if __name__ == "__main__":
    main()

"""How robust is each result? Five checks on STORED results and development data; nothing sealed is re-run.

    python robustness.py          (after overfit.py; writes results/robustness.json)

1. Break-even slippage. Costs rise linearly with slippage while gross profit does not change, so each
   sealed or holdout result has one slippage at which its net profit is exactly zero. Read from the
   stored results at 0 and 10 bp (sealed_summary.csv; data.json backtests for the holdouts).
2. Probabilistic Sharpe ratio (Bailey & Lopez de Prado, 2012, "The Sharpe ratio efficient frontier",
   Journal of Risk 15(2)): the probability that the true per-trade Sharpe ratio is above zero, given the
   trades' number, skew and fat tails. Deflated Sharpe ratio (Bailey & Lopez de Prado, 2014, Journal of
   Portfolio Management 40(5)) for Strategy C: the same test against the best Sharpe expected by luck
   from its 72 tried settings. Trade logs from results/sealed_trades.csv and the holdout logs, at 5 bp.
3. Does the premium mean-revert, and how fast? For each small contract's premium over GOLDM (same expiry,
   the series on the site): an augmented Dickey-Fuller test (lags chosen by AIC, constant, MacKinnon
   critical values) and the AR(1) half-life in market days.
4. Parameter neighbourhood: of Strategy C's settings that differ from the chosen one in a single
   parameter, how many also made money on the development years (strategy_c_dev_grid.csv)?
5. Premium regimes: monthly average premium per contract type split into regimes by binary segmentation
   (BIC), each break dated and set next to the dated MCX event closest to it. Coincidence, not proof of cause.
"""
import itertools
import json
import math
import os
from statistics import NormalDist

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")
OUT = os.path.join(RES, "robustness.json")
N = NormalDist()
SLIP = 5
EULER = 0.5772156649015329
# MacKinnon (2010) asymptotic critical values, constant and no trend
ADF_CRIT = {"1%": -3.43, "5%": -2.86, "10%": -2.57}
# Dated exchange and policy events (each sourced on the site's event notes)
EVENTS = [("2024-07-23", "Customs duty on gold cut to 6% (Union Budget)"),
          ("2025-04-01", "GOLDTEN (10 g, 999) starts trading"),
          ("2025-09-22", "MCX lists six expiries instead of three (circular MCX/TRD/456/2025)"),
          ("2026-01-30", "Gold crash: GOLDM's most-traded contract settles 15% lower"),
          ("2026-05-13", "Import duty on gold raised from 6% to 15%"),
          ("2026-07-13", "MCX widens Good Delivery to more refiners")]


# ---------------------------------------------------------------- 1. break-even slippage
def breakeven(net0, net10):
    """Slippage (bp per leg per side) at which net profit is zero, from the nets at 0 and 10 bp."""
    slope = (net10 - net0) / 10.0
    if slope >= 0:
        raise ValueError("net must fall as slippage rises")
    return -net0 / slope


# ---------------------------------------------------------------- 2. Sharpe statistics
def moments(x):
    x = np.asarray(x, float)
    m, s = x.mean(), x.std(ddof=1)
    z = (x - m) / x.std(ddof=0)
    return m, s, float((z ** 3).mean()), float((z ** 4).mean())


def psr(x, sr0=0.0):
    """Probability that the true Sharpe ratio exceeds sr0 (per observation)."""
    m, s, g3, g4 = moments(x)
    sr, n = m / s, len(x)
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return N.cdf((sr - sr0) * math.sqrt(n - 1) / den), sr


def expected_max_sr(var_sr, trials):
    """Expected best Sharpe ratio among `trials` independent tries with no skill."""
    return math.sqrt(var_sr) * ((1 - EULER) * N.inv_cdf(1 - 1 / trials) + EULER * N.inv_cdf(1 - 1 / (trials * math.e)))


# ---------------------------------------------------------------- 3. stationarity and half-life
def adf(y, max_lag=10):
    """ADF t-statistic with a constant; lag length by AIC. Returns (stat, lags, n)."""
    y = np.asarray(y, float)
    dy = np.diff(y)
    best = None
    for p in range(max_lag + 1):
        Y = dy[p:]
        cols = [np.ones(len(Y)), y[p:-1]] + [dy[p - i:-i] for i in range(1, p + 1)]
        X = np.column_stack(cols)
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        resid = Y - X @ beta
        n, k = len(Y), X.shape[1]
        sigma2 = resid @ resid / (n - k)
        aic = n * math.log(resid @ resid / n) + 2 * k
        se = math.sqrt(sigma2 * np.linalg.inv(X.T @ X)[1, 1])
        if best is None or aic < best[0]:
            best = (aic, beta[1] / se, p, n)
    return best[1], best[2], best[3]


def half_life(y):
    """AR(1) half-life in observations: x_t = a + phi x_{t-1}; hl = ln 2 / -ln phi."""
    y = np.asarray(y, float)
    X = np.column_stack([np.ones(len(y) - 1), y[:-1]])
    (a, phi), *_ = np.linalg.lstsq(X, y[1:], rcond=None)
    return (math.log(2) / -math.log(phi)) if 0 < phi < 1 else None, float(phi)


# ---------------------------------------------------------------- 5. regimes
def segment(x, min_len=3, max_breaks=4):
    """Binary segmentation of a series into constant-mean regimes, kept only while BIC improves.
    Returns sorted break indices (a break at i means a new regime starts at x[i])."""
    x = np.asarray(x, float)
    n = len(x)

    def sse(a, b):
        s = x[a:b]
        return float(((s - s.mean()) ** 2).sum()) if len(s) else 0.0

    def bic(bks):
        edges = [0] + sorted(bks) + [n]
        rss = sum(sse(a, b) for a, b in zip(edges, edges[1:]))
        # each break adds a location and a mean; the extra weight (3 per break, not 2) keeps false breaks in
        # pure noise to about 3% of series (tests/test_robustness.py measures it), where plain BIC gives about 13%
        k = 3 * len(bks) + 1
        return n * math.log(max(rss, 1e-9) / n) + k * math.log(n)

    bks = []
    while len(bks) < max_breaks:
        edges = [0] + sorted(bks) + [n]
        cand = None
        for a, b in zip(edges, edges[1:]):
            for i in range(a + min_len, b - min_len + 1):
                gain = sse(a, b) - sse(a, i) - sse(i, b)
                if cand is None or gain > cand[0]:
                    cand = (gain, i)
        if cand is None or bic(bks + [cand[1]]) >= bic(bks):
            break
        bks.append(cand[1])
    return sorted(bks)


def nearest_event(month):
    m = pd.Period(month, "M")
    best = min(EVENTS, key=lambda e: abs((pd.Period(e[0][:7], "M") - m).n))
    gap = abs((pd.Period(best[0][:7], "M") - m).n)
    return {"date": best[0], "event": best[1], "months_apart": gap} if gap <= 1 else None   # only within a month


# ---------------------------------------------------------------- main
def main():
    out = {}
    D = json.load(open(os.path.join(HERE, "dashboard", "data.json")))

    # 1. break-even slippage
    s = pd.read_csv(os.path.join(RES, "sealed_summary.csv"))
    rows = []
    for (test, strat), g in s.groupby(["test", "strategy"]):
        g = g.set_index("slip_bp").net
        rows.append({"test": test, "strategy": strat[0], "net0": round(float(g[0])), "net5": round(float(g[5])),
                     "net10": round(float(g[10])), "breakeven_bp": round(breakeven(g[0], g[10]), 2) if g[0] > 0 else None})
    for key, strat in (("A_hold", "A"), ("B_hold", "B")):
        r = {x["slip"]: x["net"] for x in D["backtests"][key]["rows"]}
        rows.append({"test": "holdout", "strategy": strat, "net0": round(r[0]), "net5": round(r[5]), "net10": round(r[10]),
                     "breakeven_bp": round(breakeven(r[0], r[10]), 2) if r[0] > 0 else None})
    out["breakeven"] = {"rows": rows, "realistic_bp": 5, "source": "results/sealed_summary.csv; dashboard/data.json backtests"}

    # 2. probabilistic and deflated Sharpe, per trade at 5 bp
    t = pd.read_csv(os.path.join(RES, "sealed_trades.csv"))
    t = t[t.slip_bp == SLIP]
    logs = {("holdout", "A"): pd.read_csv(os.path.join(RES, "holdout_trades.csv")),
            ("holdout", "B"): pd.read_csv(os.path.join(RES, "fairvalue_holdout_trades.csv"))}
    sharpe = []
    for (test, strat), g in t.groupby(["test", "strategy"]):
        p, sr = psr(g.net_rs)
        sharpe.append({"test": test, "strategy": strat[0], "trades": int(len(g)), "sr_per_trade": round(sr, 3), "psr": round(p, 3)})
    for (test, strat), g in logs.items():
        g = g[g.slip_bp == SLIP]
        p, sr = psr(g.net_rs)
        sharpe.append({"test": test, "strategy": strat, "trades": int(len(g)), "sr_per_trade": round(sr, 3), "psr": round(p, 3)})
    # Deflated: Strategy C was chosen from 72 settings; the spread of per-trade Sharpe across settings is
    # estimated from the development grid's yearly profits (Sharpe of yearly profit per setting).
    grid = pd.read_csv(os.path.join(RES, "strategy_c_dev_grid.csv")).set_index("setting")
    yrs = [c for c in grid.columns if c != "2026"]
    gsr = (grid[yrs].mean(axis=1) / grid[yrs].std(axis=1, ddof=1)).replace([np.inf, -np.inf], np.nan).dropna()
    c_all = t[t.strategy.str.startswith("C")].net_rs
    m, sd, g3, g4 = moments(c_all)
    sr_c, n_c = m / sd, len(c_all)
    # scale the cross-setting variance from yearly to per-trade units by the trades-per-year of the chosen rule
    per_year = n_c / 8.0                                   # 8 sealed years, 2016-2023
    var_trade = float(gsr.var(ddof=1)) / per_year
    sr0 = expected_max_sr(var_trade, len(grid))
    dsr = N.cdf((sr_c - sr0) * math.sqrt(n_c - 1) / math.sqrt(max(1e-12, 1 - g3 * sr_c + (g4 - 1) / 4 * sr_c ** 2)))
    out["sharpe"] = {"rows": sharpe, "slip_bp": SLIP,
                     "deflated_c": {"trials": int(len(grid)), "trades": int(n_c), "sr_per_trade": round(sr_c, 3),
                                    "sr_expected_by_luck": round(sr0, 3), "dsr": round(dsr, 3)},
                     "source": "results/sealed_trades.csv, holdout_trades.csv, fairvalue_holdout_trades.csv, strategy_c_dev_grid.csv"}

    # 3. stationarity and half-life of each premium
    pdly = D["premium_daily"]
    st = []
    for sym in ("GOLDTEN", "GOLDGUINEA", "GOLDPETAL"):
        y = pd.Series(pdly[sym], index=pd.to_datetime(pdly["dates"]), dtype=float).dropna()
        stat, lags, n = adf(y.values)
        hl, phi = half_life(y.values)
        st.append({"symbol": sym, "days": int(len(y)), "first": str(y.index[0].date()), "last": str(y.index[-1].date()),
                   "adf": round(stat, 2), "lags": int(lags), "stationary_at": next((k for k in ("1%", "5%", "10%") if stat < ADF_CRIT[k]), None),
                   "half_life_days": round(hl, 1) if hl else None, "phi": round(phi, 3)})
    bt_all = pd.read_csv(os.path.join(RES, "strategy_b_dev_alldata_trades.csv"))
    bt_all = bt_all[bt_all.slip_bp == SLIP]
    hits = {sym: {"trades": int(len(g)), "won": round(float((g.net_rs > 0).mean()), 3)} for sym, g in bt_all.groupby("symbol")}
    out["stationarity"] = {"rows": st, "critical": ADF_CRIT, "b_win_rate_training": hits,
                           "source": "dashboard/data.json premium_daily (same-expiry premium over GOLDM, bp); results/strategy_b_dev_alldata_trades.csv"}

    # 4. parameter neighbourhood of Strategy C's chosen setting
    p = json.load(open(os.path.join(RES, "strategy_c_params.json")))
    chosen = {k: p[k] for k in ("ref", "k", "stress", "exit", "hold")}

    def parse(s):
        d = dict(kv.split("=") for kv in s.split())
        f = lambda v: None if v == "None" else (float(v) if v.replace(".", "", 1).isdigit() else v)
        return {"ref": d["ref"], "k": f(d["k"]), "stress": f(d["stress"]), "exit": f(d["exit"]), "hold": None if d["hold"] == "None" else int(float(d["hold"]))}
    tot = grid[yrs].sum(axis=1)
    settings = {s: parse(s) for s in grid.index}
    me = next(s for s, v in settings.items() if all(v[k] == chosen[k] for k in chosen))
    nb = [s for s, v in settings.items() if sum(v[k] != settings[me][k] for k in chosen) == 1]
    out["neighbourhood"] = {"chosen": me, "chosen_net": round(float(tot[me])), "neighbours": len(nb),
                            "neighbours_positive": int((tot[nb] > 0).sum()), "all_settings": int(len(tot)),
                            "all_positive": int((tot > 0).sum()), "years": yrs, "slip_bp": 5,
                            "source": "results/strategy_c_dev_grid.csv"}

    # 5. premium regimes, monthly
    reg = []
    for sym in ("GOLDTEN", "GOLDGUINEA", "GOLDPETAL"):
        y = pd.Series(pdly[sym], index=pd.to_datetime(pdly["dates"]), dtype=float).dropna()
        mo = y.groupby(y.index.to_period("M")).mean()
        mo = mo[y.groupby(y.index.to_period("M")).size() >= 5]          # months with at least 5 market days
        bks = segment(mo.values)
        edges = [0] + bks + [len(mo)]
        regimes = [{"from": str(mo.index[a]), "to": str(mo.index[b - 1]), "mean_bp": round(float(mo.iloc[a:b].mean()), 1)} for a, b in zip(edges, edges[1:])]
        breaks = [{"month": str(mo.index[i]), "before_bp": regimes[j]["mean_bp"], "after_bp": regimes[j + 1]["mean_bp"],
                   "nearest_event": nearest_event(str(mo.index[i]))} for j, i in enumerate(bks)]
        reg.append({"symbol": sym, "months": int(len(mo)), "regimes": regimes, "breaks": breaks})
    out["regimes"] = {"rows": reg, "method": "binary segmentation of monthly mean premium, BIC-type stopping with 3 parameters per break (false breaks in pure noise: about 3%), at least 3 months per regime",
                      "source": "dashboard/data.json premium_daily"}

    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

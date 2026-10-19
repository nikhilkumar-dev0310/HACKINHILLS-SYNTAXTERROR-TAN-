"""How robust is each result? Five checks on STORED results and development data; nothing sealed is re-run.

    python robustness.py          (after overfit.py; writes results/robustness.json)

1. Break-even slippage. Costs rise linearly with slippage while gross profit does not change, so each
   sealed or holdout result has one slippage at which its net profit is exactly zero. Read from the
   stored results at 0 and 10 bp (sealed_summary.csv; data.json backtests for the holdouts and Strategy A's
   first test, May-July 2025).
2. Probabilistic Sharpe ratio (Bailey & Lopez de Prado, 2012, "The Sharpe ratio efficient frontier",
   Journal of Risk 15(2)): the probability that the true per-trade Sharpe ratio is above zero, given the
   trades' number, skew and fat tails. Deflated Sharpe ratio (Bailey & Lopez de Prado, 2014, Journal of
   Portfolio Management 40(5)) for Strategy C: the same test against the best Sharpe expected by luck
   from its 72 tried settings. Trade logs from results/sealed_trades.csv, the holdout logs and the first test's
   log, at 5 bp.
3. Does the premium mean-revert, and how fast? For each small contract's premium over GOLDM (same expiry,
   the series on the site): an augmented Dickey-Fuller test (lags chosen by AIC, constant, MacKinnon
   critical values) and the AR(1) half-life in market days.
4. Parameter neighbourhood: of Strategy C's settings that differ from the chosen one in a single
   parameter, how many also made money on the development years (strategy_c_dev_grid.csv)?
5. Premium regimes: monthly average premium per contract type split into regimes by binary segmentation
   (BIC), each break dated and set next to the dated MCX event closest to it. Coincidence, not proof of cause.
6. Every rule ever tried. The deflated Sharpe in check 2 counts Strategy C's 72 settings; the honest count is
   every distinct rule the project scored on any data (Strategy A's grid, the methods round, Strategy B's k
   and C's grid, with rules that appear in two places counted once, and the no-carry variant overfit.py scored
   after every sealed run). The fair-price model (B) and C are deflated against that count too. Then every
   sealed result on its own (A's first test, both holdouts, each 2016-2023 window) is deflated three ways: against
   its own strategy's settings, against every rule scored before its window was opened (OPENED_AFTER, from the
   Git history), and against every rule ever scored. Each count only grows, so each deflated Sharpe only falls.
7. What trading actually costs. Break-even slippage only means something next to the slippage real trading
   would cost, so the half-spread is estimated from the daily data with two standard estimators: Roll (1984,
   Journal of Finance 39(4)), from the negative autocovariance of price changes, and Corwin & Schultz (2012,
   Journal of Finance 67(2)), from two-day high-low ranges with their overnight adjustment. Each day uses the
   most-traded contract of each type, over all MCX rows held (2003 on; the sealed tests are long run and nothing
   is re-run). A spread of a few bp is small next to gold's daily moves, so a month of daily data cannot pin it
   down: the two-day estimates are pooled over each test window (about a thousand pairs), with a 95% interval
   from resampling whole months. Each result's break-even is set against the half-spread of the legs it actually
   traded, in its own window. Where the estimator breaks down (a negative mean, as in the 2025-26 crash, when
   volatility swung from day to day) it is reported as not measurable rather than as zero. Roll's estimator
   needs bid-ask bounce to dominate day-to-day price changes; at daily frequency gold's own moves swamp it (it is
   undefined in about 4 months of 10), so it is shown only as a cross-check.
"""
import itertools
import json
import math
import os
from statistics import NormalDist

import numpy as np
import pandas as pd

import backtest as bt

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


def deflated(x, var_sr, trials):
    """Deflated Sharpe ratio of per-trade results x against the best of `trials` tries with no skill."""
    m, sd, g3, g4 = moments(x)
    sr, n = m / sd, len(x)
    sr0 = expected_max_sr(var_sr, trials)
    return N.cdf((sr - sr0) * math.sqrt(n - 1) / math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))), sr, sr0


def parse_setting(s):
    """A Strategy C grid label ("ref=all k=1.5 stress=None exit=0.0 hold=None") as a dict."""
    d = dict(kv.split("=") for kv in s.split())
    f = lambda v: None if v == "None" else (float(v) if v.replace(".", "", 1).isdigit() else v)
    return {"ref": d["ref"], "k": f(d["k"]), "stress": f(d["stress"]), "exit": f(d["exit"]), "hold": None if d["hold"] == "None" else int(float(d["hold"]))}


def method_key(m):
    """A methods-round label as a rule key; "zscore(N=10, entry=2.0)" is the same rule as Strategy A's N=10, z=2.0."""
    if m.startswith("zscore("):
        z = dict(kv.strip().split("=") for kv in m[len("zscore("):-1].split(","))
        return ("zscore", int(z["N"]), float(z["entry"]))
    return ("method", m)


def rule_sets(res=RES):
    """Every rule scored anywhere in the project, per family, as keys that compare equal when two families scored
    the same rule: the methods round re-scored Strategy A's frozen z-score setting, and Strategy B's rule with
    k = 1.5 or 2.0 is also one of Strategy C's grid settings (B's rules are C's with no stress filter, no exit
    buffer and no holding cap). "checks" holds rules scored only as an after-the-fact check: overfit.py's
    Strategy B without the carry adjustment, scored on the development years."""
    a = pd.read_csv(os.path.join(res, "train_sweep.csv"))[["lookback", "entry_z"]].drop_duplicates()
    A = {("zscore", int(r.lookback), float(r.entry_z)) for r in a.itertuples()}
    M = {method_key(m) for m in pd.read_csv(os.path.join(res, "methods_train.csv")).method.drop_duplicates()}
    fkey = lambda s: ("fair", s["ref"], s["k"], s["stress"], s["exit"], s["hold"])
    b_rule = lambda k: {"ref": "all", "k": float(k), "stress": None, "exit": 0.0, "hold": None}
    B = {fkey(b_rule(k)) for k in pd.read_csv(os.path.join(res, "fairvalue_dev.csv")).k.drop_duplicates()}
    C = {fkey(parse_setting(x)) for x in pd.read_csv(os.path.join(res, "strategy_c_dev_grid.csv")).setting.drop_duplicates()}
    of = os.path.join(res, "overfit.json")
    nc = json.load(open(of)).get("no_carry") if os.path.exists(of) else None
    k_b = json.load(open(os.path.join(res, "fairvalue_params.json")))["k"]
    checks = {("fair, no carry",) + fkey(b_rule(k_b))[1:]} if nc else set()
    return {"A": A, "methods": M, "B": B, "C": C, "checks": checks}


# Which families had been scored when each sealed window was opened, from the Git history: Strategy A's grid and its
# first TEST in the first commit (962dab7); the methods round on TRAIN after it (08507a9); B's k grid pre-registered
# (045ab2b) before both holdouts ran (3e9e82d); C's grid frozen (a984901) before 2016-2023 ran (6df3bbd); the
# no-carry check on 8 Oct 2026 (4791f1c), after every sealed run, so it counts only in "ever".
OPENED_AFTER = {"test": ("A",), "holdout": ("A", "methods", "B"),
                "test3": ("A", "methods", "B", "C"), "test2": ("A", "methods", "B", "C")}
OWN = {"A": ("A",), "B": ("B",), "C": ("C",)}


def count_rules(sets, families):
    """Distinct rules in the union of the given families."""
    return len(set().union(*(sets[f] for f in families)))


def rules_tried(res=RES):
    """Every distinct rule scored anywhere in the project, by family, each counted once. A family's count is the
    rules it added that no other family scored (C's grid absorbs B's two shared settings)."""
    s = rule_sets(res)
    others = lambda f: set().union(*(v for k, v in s.items() if k != f))
    fam = {"A": len(s["A"]), "methods": len(s["methods"] - s["A"]), "B": len(s["B"] - s["C"]), "C": len(s["C"]),
           "checks": len(s["checks"] - others("checks"))}
    meth = pd.read_csv(os.path.join(res, "methods_train.csv")).method.drop_duplicates()
    in_a = [m for m in meth if method_key(m) in s["A"]]
    b_in_c = sorted(k[2] for k in s["B"] & s["C"])
    total = count_rules(s, s.keys())
    assert total == sum(fam.values()), "families overlap in a way the counts do not cover"
    return fam, total, {"methods_repeating_a": in_a, "b_k_in_c": b_in_c}


# ---------------------------------------------------------------- 7. what trading costs: half-spread estimators
def roll_spread(close):
    """Roll (1984): spread = 2 sqrt(-cov(r_t, r_t-1)) of log price changes, as a fraction of price.
    None when the covariance is not negative (the estimator is undefined there)."""
    r = np.diff(np.log(np.asarray(close, float)))
    if len(r) < 3:
        return None
    c = float(np.cov(r[1:], r[:-1], ddof=1)[0, 1])
    return 2 * math.sqrt(-c) if c < 0 else None


def cs_spread(high, low, close):
    """Corwin & Schultz (2012): a spread estimate for every pair of consecutive days, from their high-low
    ranges, with the overnight adjustment (a day whose whole range sits above or below the previous close is
    shifted by that gap). Returned raw, negatives included: averaged over a month they are close to unbiased,
    whereas setting each day's negative estimate to zero first adds a large upward bias when the spread is
    small next to the day's price swing (as gold's is; tests/test_robustness.py measures both). Callers
    average, then set a negative average to zero."""
    H, L, C = (np.asarray(v, float) for v in (high, low, close))
    h2, l2, c0 = H[1:].copy(), L[1:].copy(), C[:-1]
    gap = np.where(l2 > c0, l2 - c0, np.where(h2 < c0, h2 - c0, 0.0))
    h2, l2 = h2 - gap, l2 - gap
    beta = np.log(H[:-1] / L[:-1]) ** 2 + np.log(h2 / l2) ** 2
    gamma = np.log(np.maximum(H[:-1], h2) / np.minimum(L[:-1], l2)) ** 2
    k = 3 - 2 * math.sqrt(2)
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / k - np.sqrt(gamma / k)
    return 2 * (np.exp(alpha) - 1) / (1 + np.exp(alpha))


def most_traded(d):
    """Each day's most-traded contract of each type, traded rows with a usable high-low range."""
    t = d[~d.no_trade & (d.volume_lots > 0) & (d.high > 0) & (d.low > 0) & (d.high >= d.low)].copy()
    t["grams"] = t.volume_lots * t.symbol.map({"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1})
    return t.loc[t.groupby(["date", "symbol"]).grams.idxmax()].sort_values(["symbol", "expiry_date", "date"])


def cs_pairs(top):
    """Every Corwin-Schultz two-day estimate, pairs of days only within one contract: symbol, date, estimate."""
    rows = []
    for (sym, _), g in top.groupby(["symbol", "expiry_date"]):
        if len(g) >= 2:
            est = cs_spread(g.high.values, g.low.values, g.close.values)
            rows += [(sym, dt, v) for dt, v in zip(g.date.values[1:], est)]
    return pd.DataFrame(rows, columns=["symbol", "date", "cs"]).assign(date=lambda x: pd.to_datetime(x.date))


def pooled_half_spread(x, seed=20261019, draws=1000):
    """Half-spread (bp) from a stretch of two-day estimates: their mean, with a 95% interval from resampling
    whole calendar months (estimates within a month are not independent). A mean a little below zero is noise
    around a spread of about nothing and reads as zero; one clearly below zero (under -1 bp) is a spread no market
    has, so the estimator has broken down there (large swings in volatility from day to day): None. Both ends of the
    interval are floored at zero like the estimate (a spread is never negative), so the low end never passes the high
    one; raw_bp keeps the unfloored mean."""
    v, mo = x.cs.values, x.date.dt.to_period("M").values
    blocks = [v[mo == m] for m in pd.unique(mo)]
    rng = np.random.default_rng(seed)
    bs = np.array([np.concatenate([blocks[i] for i in rng.integers(len(blocks), size=len(blocks))]).mean() for _ in range(draws)])
    m = float(v.mean()) / 2 * 1e4
    lo, hi = (round(max(0.0, float(np.percentile(bs, q)) / 2 * 1e4), 2) for q in (2.5, 97.5))
    return {"half_bp": round(max(0.0, m), 2) if m >= -1 else None, "lo": lo, "hi": hi,
            "pairs": int(len(v)), "months": len(blocks), "raw_bp": round(m, 2)}


def roll_months(top):
    """Roll's estimate for each type and calendar month (at least 10 days, one contract)."""
    roll = []
    for (sym, mo), g in top.assign(month=top.date.dt.to_period("M").astype(str)).groupby(["symbol", "month"]):
        g = g.sort_values("date")
        if g.expiry_date.nunique() > 1:      # the most-traded contract changed in the month: use the one with more days
            g = g[g.expiry_date == g.expiry_date.value_counts().idxmax()]
        if len(g) >= 10:
            s_ = roll_spread(g.close.values)
            roll.append({"symbol": sym, "month": mo, "roll_half_bp": s_ / 2 * 1e4 if s_ is not None else None})
    return pd.DataFrame(roll)


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
    # phi a rounding error below 1 (a random walk or a trend) has no half-life, not one of 10^15 days
    return (math.log(2) / -math.log(phi)) if 0 < phi < 1 - 1e-9 else None, float(phi)


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
    for key, test, strat in (("A_hold", "holdout", "A"), ("B_hold", "holdout", "B"), ("A_test", "test", "A")):
        r = {x["slip"]: x["net"] for x in D["backtests"][key]["rows"]}
        rows.append({"test": test, "strategy": strat, "net0": round(r[0]), "net5": round(r[5]), "net10": round(r[10]),
                     "breakeven_bp": round(breakeven(r[0], r[10]), 2) if r[0] > 0 else None})
    out["breakeven"] = {"rows": rows, "realistic_bp": 5, "source": "results/sealed_summary.csv; dashboard/data.json backtests"}

    # 2. probabilistic and deflated Sharpe, per trade at 5 bp
    t = pd.read_csv(os.path.join(RES, "sealed_trades.csv"))
    t = t[t.slip_bp == SLIP]
    logs = {("holdout", "A"): pd.read_csv(os.path.join(RES, "holdout_trades.csv")),
            ("holdout", "B"): pd.read_csv(os.path.join(RES, "fairvalue_holdout_trades.csv")),
            ("test", "A"): pd.read_csv(os.path.join(RES, "test_trades.csv"))}
    nets = {(test, strat[0]): g.net_rs for (test, strat), g in t.groupby(["test", "strategy"])}
    nets.update({key: g[g.slip_bp == SLIP].net_rs for key, g in logs.items()})
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
                     "source": "results/sealed_trades.csv, holdout_trades.csv, fairvalue_holdout_trades.csv, test_trades.csv, strategy_c_dev_grid.csv"}

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

    tot = grid[yrs].sum(axis=1)
    settings = {s: parse_setting(s) for s in grid.index}
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

    # 6. every rule ever tried: the fair-price model (B) and C deflated against the honest count
    fam, total, overlap = rules_tried()
    sets = rule_sets()
    opened_c = count_rules(sets, OPENED_AFTER["test3"])
    drows = []
    for strat, own in (("B", count_rules(sets, OWN["B"])), ("C", count_rules(sets, OWN["C"]))):
        x = t[t.strategy.str.startswith(strat)].net_rs
        var = float(gsr.var(ddof=1)) / (len(x) / 8.0)        # as in check 2: cross-setting spread, per trade
        d_all, sr, sr0_all = deflated(x, var, total)
        d_own, _, sr0_own = deflated(x, var, own)
        d_op, _, _ = deflated(x, var, opened_c)
        drows.append({"strategy": strat, "trades": int(len(x)), "net": round(float(x.sum())), "sr_per_trade": round(sr, 3),
                      "own_trials": int(own), "sr_luck_own": round(sr0_own, 3), "dsr_own": round(d_own, 3),
                      "opened_trials": int(opened_c), "dsr_opened": round(d_op, 3),
                      "sr_luck_all": round(sr0_all, 3), "dsr_all": round(d_all, 3)})
    # every sealed result on its own: against its own strategy's settings, every rule scored before its window was
    # opened, and every rule ever scored. The cross-setting spread is scaled to per-trade units by the result's own
    # trades per year over its declared window.
    fp, fvp, cpar = (json.load(open(os.path.join(RES, f))) for f in ("frozen_params.json", "fairvalue_params.json", "strategy_c_params.json"))
    span = {("test", "A"): fp["test"], ("holdout", "A"): [str(bt.HOLDOUT_START.date()), str(bt.HOLDOUT_END.date())],
            ("holdout", "B"): fvp["holdout"], **{(w, st_): cpar["sealed_windows"][w] for w in ("test3", "test2") for st_ in "ABC"}}
    per = []
    for (test, strat), (a_, b_) in span.items():
        x = nets[(test, strat)]
        years = (pd.Timestamp(b_) - pd.Timestamp(a_)).days / 365.25
        var = float(gsr.var(ddof=1)) / (len(x) / years)
        n = {"own": count_rules(sets, OWN[strat]), "opened": count_rules(sets, OPENED_AFTER[test]), "ever": total}
        d = {k: deflated(x, var, v) for k, v in n.items()}
        per.append({"test": test, "strategy": strat, "from": a_, "to": b_, "trades": int(len(x)), "net": round(float(x.sum())),
                    "sr_per_trade": round(d["own"][1], 3), "psr": round(psr(x)[0], 3),
                    **{f"{k}_trials": int(v) for k, v in n.items()},
                    **{f"sr_luck_{k}": round(v[2], 3) for k, v in d.items()}, **{f"dsr_{k}": round(v[0], 3) for k, v in d.items()}})
    out["trials"] = {"families": fam, "total": int(total), "overlap": overlap, "rows": drows, "per_result": per,
                     "opened_after": {w: list(f) for w, f in OPENED_AFTER.items()},
                     "opened_counts": {w: count_rules(sets, f) for w, f in OPENED_AFTER.items()}, "slip_bp": SLIP,
                     "windows": "rows: sealed tests 2016-2019 and 2020-2023, pooled; per_result: each sealed result alone",
                     "source": "results/train_sweep.csv, methods_train.csv, fairvalue_dev.csv, strategy_c_dev_grid.csv, overfit.json, "
                               "sealed_trades.csv, holdout_trades.csv, fairvalue_holdout_trades.csv, test_trades.csv"}

    # 7. what trading actually costs: half-spread estimates against each result's break-even slippage
    allrows = pd.concat([pd.read_csv(os.path.join(HERE, "clean", f), parse_dates=["date", "expiry_date"])
                         for f in ("gold_futures_history.csv", "sealed_rows.csv", "gold_futures.csv")
                         if os.path.exists(os.path.join(HERE, "clean", f))], ignore_index=True)
    top = most_traded(allrows)
    cp, rl = cs_pairs(top), roll_months(top)
    last = cp.date.max()
    WIN = {"test3": ("2016-01-01", "2019-12-31"), "test2": ("2020-01-01", "2023-10-09"), "test": tuple(fp["test"]), "holdout": ("2025-08-06", "2026-05-29"),
           "recent": (str((last - pd.DateOffset(years=1)).date()), str(last.date()))}
    win = {w: {"from": a_, "to": b_, **{sym: pooled_half_spread(g) for sym, g in cp[cp.date.between(a_, b_)].groupby("symbol")}}
           for w, (a_, b_) in WIN.items()}
    crow = []
    for sym in ("GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"):
        r_ = rl[rl.symbol == sym]
        rv = r_.roll_half_bp.dropna()
        crow.append({"symbol": sym, "first": str(cp[cp.symbol == sym].date.min().date()), "pairs": int((cp.symbol == sym).sum()),
                     "roll_half_bp": round(float(rv.median()), 1) if len(rv) else None, "roll_months": int(len(r_)), "roll_defined": int(len(rv))})
    # each result against its own legs in its own window (per trade, the mean of its two legs; then over trades),
    # at the estimate and at the top of its 95% interval; not measurable if a leg's estimate broke down
    legs = {(test, strat[0]): [x.split("-") if "-" in x else [x, "GOLDM"] for x in g.symbol] for (test, strat), g in t.groupby(["test", "strategy"])}
    legs[("holdout", "A")] = [x.split("-") for x in logs[("holdout", "A")].query("slip_bp == @SLIP").pair]
    legs[("holdout", "B")] = [[x, "GOLDM"] for x in logs[("holdout", "B")].query("slip_bp == @SLIP").symbol]
    legs[("test", "A")] = [x.split("-") for x in logs[("test", "A")].query("slip_bp == @SLIP").pair]
    for r_ in out["breakeven"]["rows"]:
        w = win[r_["test"]]
        L = legs[(r_["test"], r_["strategy"])]
        ok = all(w[x]["half_bp"] is not None for pair in L for x in pair)
        r_["est_slip_bp"] = round(float(np.mean([np.mean([w[x]["half_bp"] for x in pair]) for pair in L])), 1) if ok else None
        r_["est_slip_hi_bp"] = round(float(np.mean([np.mean([w[x]["hi"] for x in pair]) for pair in L])), 1) if ok else None
        r_["survives_est"] = bool(ok and r_["breakeven_bp"] is not None and r_["breakeven_bp"] > r_["est_slip_hi_bp"])
    out["costs"] = {"rows": crow, "windows": win, "realistic_bp": 5,
                    "method": "half the estimated bid-ask spread, bp of price: mean of the two-day Corwin-Schultz estimates over the window on each day's most-traded contract, 95% interval by resampling whole months; Roll per month as a cross-check",
                    "source": "clean/gold_futures_history.csv, clean/sealed_rows.csv, clean/gold_futures.csv"}

    json.dump(out, open(OUT, "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

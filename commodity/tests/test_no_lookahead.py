"""No look-ahead, anywhere a signal is computed: rewriting the future must not change the past.

For every module that turns prices into a signal, a synthetic market is run twice: once as is, once with
every price after a cut-off day rewritten. Everything decided before the cut-off must come out identical.
Repeated over many random markets and cut-off days, so one lucky case cannot hide a leak.
"""
import importlib.util
import unittest

import numpy as np
import pandas as pd

import accuracy as ac
import backtest as bt
import fairvalue as fv
import strategy_c as sc
from _util import cases, pair_frame

SEEDS = range(8)
CUTS = (0.45, 0.65, 0.85)
GRID = [(s, c) for s in SEEDS for c in CUTS]
HAS_SCIPY = importlib.util.find_spec("scipy") is not None


def fv_frames(seed, n=160, cycles=3, sym="GOLDPETAL"):
    """Synthetic fair-price frames: several overlapping cycles of one contract type against GOLDM."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2024-01-01", periods=n + 60 * cycles)
    frames = {}
    for c in range(cycles):
        idx = days[c * 60:c * 60 + n]
        exp = idx[-1] + pd.Timedelta(days=2)
        prem = 40 + np.cumsum(rng.normal(0, 3, len(idx))) * 0.3 + rng.normal(0, 8, len(idx))
        m = 6000 * np.exp(np.cumsum(rng.normal(0, 0.008, len(idx))))
        x = m * np.exp(prem / 1e4)
        f = pd.DataFrame(index=idx)
        f["prem_bp"], f["x_fill"], f["m_fill"], f["x_close"], f["m_close"] = prem, x, m, x, m
        f["x_grams"] = rng.integers(500, 5000, len(idx)).astype(float)
        f["ok"] = rng.random(len(idx)) > 0.05
        f["bleft"] = np.busday_count(idx.values.astype("datetime64[D]"), np.datetime64(exp.date()))
        f["symbol"], f["expiry"], f["m_expiry"] = sym, exp.date(), exp.date()
        frames[(sym, exp)] = f
    return frames


def rewrite_after(frames, cut, seed):
    rng = np.random.default_rng(1000 + seed)
    out = {}
    for k, f in frames.items():
        g = f.copy()
        late = g.index > cut
        g.loc[late, "prem_bp"] = g.loc[late, "prem_bp"] + rng.normal(0, 60, late.sum())
        g.loc[late, ["x_fill", "x_close"]] = g.loc[late, ["x_fill", "x_close"]].mul(np.exp(g.loc[late, "prem_bp"] / 1e4 - f.loc[late, "prem_bp"] / 1e4), axis=0)
        out[k] = g
    return out


def cut_day(index, q):
    return index[int(len(index) * q)]


@cases(GRID, name=lambda g: f"seed{g[0]}_cut{int(g[1] * 100)}")
class FutureRewrite(unittest.TestCase):
    def check_pairs_strategy_trades_before_cut_unchanged(self, g):
        """Strategy A (pairs z-score): trades closed before the cut are identical"""
        seed, q = g
        p = pair_frame(list(np.random.default_rng(seed).normal(0, 6, 120)))
        cut = cut_day(p.index, q)
        alt = p.copy()
        alt.loc[alt.index > cut, "a"] *= np.exp(np.random.default_rng(seed + 50).normal(0, 0.01, (alt.index > cut).sum()))
        alt["spread_bp"] = 1e4 * np.log(alt.a / alt.b)
        done = lambda tr: [t for t in tr if pd.Timestamp(t["exit"]) < cut]
        for lb, z in ((5, 1.5), (10, 2.0), (15, 2.5)):
            self.assertEqual(done(bt.run_pair(p, lb, z, p.index[0], p.index[-1], 5)),
                             done(bt.run_pair(alt, lb, z, alt.index[0], alt.index[-1], 5)))

    def check_fair_price_z_before_cut_unchanged(self, g):
        """Strategy B: usual premium, its spread and z use previous days only"""
        seed, q = g
        a = fv.add_z(fv_frames(seed))
        idx = sorted(set().union(*[f.index for f in a.values()]))
        cut = cut_day(pd.DatetimeIndex(idx), q)
        b = fv.add_z(rewrite_after(fv_frames(seed), cut, seed))
        for k in a:
            x, y = a[k].loc[a[k].index <= cut, ["ref_bp", "sd_bp", "z"]], b[k].loc[b[k].index <= cut, ["ref_bp", "sd_bp", "z"]]
            pd.testing.assert_frame_equal(x, y)

    def check_fair_price_trades_before_cut_unchanged(self, g):
        """Strategy B: trades closed before the cut are identical"""
        seed, q = g
        a = fv.add_z(fv_frames(seed))
        idx = pd.DatetimeIndex(sorted(set().union(*[f.index for f in a.values()])))
        cut = cut_day(idx, q)
        b = fv.add_z(rewrite_after(fv_frames(seed), cut, seed))
        done = lambda tr: [t for t in tr if pd.Timestamp(t["exit"]) < cut]
        run = lambda fr: fv.simulate(list(fr.values()), 1.5, idx[0], idx[-1], 5)
        self.assertEqual(done(run(a)), done(run(b)))

    def check_retrained_reference_before_cut_unchanged(self, g):
        """Strategy C: both reference windows (all past days, previous 365 days) use the past only"""
        seed, q = g
        a = fv_frames(seed)
        idx = pd.DatetimeIndex(sorted(set().union(*[f.index for f in a.values()])))
        cut = cut_day(idx, q)
        b = rewrite_after(fv_frames(seed), cut, seed)
        for ref in ("all", "1y"):
            A, B = sc.add_ref(fv_frames(seed), ref), sc.add_ref(b, ref)
            for k in A:
                pd.testing.assert_series_equal(A[k].loc[A[k].index <= cut, f"z_{ref}"], B[k].loc[B[k].index <= cut, f"z_{ref}"])

    def check_retrained_trades_before_cut_unchanged(self, g):
        """Strategy C (frozen rules): trades closed before the cut are identical"""
        seed, q = g
        rules = {"ref": "all", "k": 1.5, "stress": None, "exit": 0.5, "hold": 10}
        a = sc.add_ref(fv_frames(seed), "all")
        idx = pd.DatetimeIndex(sorted(set().union(*[f.index for f in a.values()])))
        cut = cut_day(idx, q)
        b = sc.add_ref(rewrite_after(fv_frames(seed), cut, seed), "all")
        done = lambda tr: [t for t in tr if pd.Timestamp(t["exit"]) < cut]
        run = lambda fr: sc.simulate(list(fr.values()), rules, idx[0], idx[-1], 5, pd.Series(dtype=float))
        self.assertEqual(done(run(a)), done(run(b)))

    def check_stress_filter_before_cut_unchanged(self, g):
        """Strategy C's volatility percentile uses the previous 365 days and today only"""
        seed, q = g
        idx = pd.bdate_range("2022-01-03", periods=420)
        close = 50_000 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0, 0.009, len(idx))))
        d = pd.DataFrame({"date": idx, "symbol": "GOLDM", "no_trade": False, "close": close,
                          "prev_close": np.r_[close[0], close[:-1]], "grams": 1e6})
        cut = cut_day(idx, q)
        e = d.copy()
        e.loc[e.date > cut, "close"] *= np.exp(np.random.default_rng(seed + 9).normal(0, 0.05, (e.date > cut).sum()))
        e["prev_close"] = np.r_[e.close.iloc[0], e.close.values[:-1]]
        pd.testing.assert_series_equal(sc.stress_pct(d)[:cut], sc.stress_pct(e)[:cut])

    def check_carry_before_cut_unchanged(self, g):
        """Carry uses same-day prices, with a past-only fallback on days it cannot be measured"""
        seed, q = g
        rng = np.random.default_rng(seed)
        days = pd.bdate_range("2025-01-01", periods=120)
        rows = []
        for i, dt in enumerate(days):
            spot = 9000 * np.exp(0.0004 * i + rng.normal(0, 0.004))
            for m in range(3):
                exp = (dt + pd.offsets.MonthEnd(m + 1)).normalize()
                if rng.random() < 0.15 and m:
                    continue                                 # some days miss a contract: the fallback is used
                rows.append({"date": dt, "symbol": "GOLDPETAL", "expiry_date": exp,
                             "close": spot * np.exp(0.07 * (exp - dt).days / 365)})
        t = pd.DataFrame(rows)
        cut = cut_day(days, q)
        u = t.copy()
        u.loc[u.date > cut, "close"] *= np.exp(rng.normal(0, 0.03, (u.date > cut).sum()))
        pd.testing.assert_series_equal(ac.carry_table(t)[1][:cut], ac.carry_table(u)[1][:cut])

    @unittest.skipUnless(HAS_SCIPY, "scipy not installed")
    def check_method_signals_before_cut_unchanged(self, g):
        """The method comparison (z-score and Ornstein-Uhlenbeck s-score) uses previous days only"""
        import methods
        seed, q = g
        s = pd.Series(np.random.default_rng(seed).normal(0, 6, 90), index=pd.bdate_range("2025-01-01", periods=90))
        cut = cut_day(s.index, q)
        u = s.copy()
        u[u.index > cut] += 40
        pd.testing.assert_frame_equal(methods.sig_zscore(s, 10, 2.0)[:cut], methods.sig_zscore(u, 10, 2.0)[:cut])
        pd.testing.assert_series_equal(methods.ou_scores(s, 20)[0][:cut], methods.ou_scores(u, 20)[0][:cut])


@cases(SEEDS, name=lambda s: f"seed{s}")
class FillTiming(unittest.TestCase):
    def check_pairs_fill_the_day_after_the_signal(self, seed):
        """Every pairs entry is filled the market day AFTER a close whose past-only z crossed the threshold,
        never on the signal day itself (random noise may add trades of its own; each must obey the rule)"""
        s = list(np.random.default_rng(seed).normal(0, 2, 20)) + [80.0] + [0.0] * 25
        p = pair_frame(s)
        prev = p.spread_bp.shift(1)
        z = (p.spread_bp - prev.rolling(10, min_periods=10).mean()) / prev.rolling(10, min_periods=10).std()
        tr = bt.run_pair(p, 10, 2.0, p.index[0], p.index[-1], 0)
        self.assertTrue(tr)
        for t in tr:
            i = p.index.get_loc(pd.Timestamp(t["entry"]))
            self.assertGreater(i, 0)
            self.assertGreaterEqual(abs(z.iloc[i - 1]), 2.0, ("entry without a signal the day before", t["entry"]))

    def test_a_lone_spike_is_entered_the_next_day(self):
        """Steady +/-1 bp wiggle (|z| about 1, below the 2.0 threshold), then one 80 bp spike: the only trade
        enters the day after the spike"""
        s = [1.0, -1.0] * 10 + [80.0] + [0.0] * 25
        p = pair_frame(s)
        tr = bt.run_pair(p, 10, 2.0, p.index[0], p.index[-1], 0)
        self.assertEqual(len(tr), 1)
        self.assertEqual(pd.Timestamp(tr[0]["entry"]), p.index[21])

    def check_fair_price_fills_the_next_usable_day(self, seed):
        """Strategy B: every entry and exit is on a day after a decision, at that day's average price"""
        fr = fv.add_z(fv_frames(seed))
        idx = pd.DatetimeIndex(sorted(set().union(*[f.index for f in fr.values()])))
        for t in fv.simulate(list(fr.values()), 1.0, idx[0], idx[-1], 0):
            f = next(f for f in fr.values() if f.expiry.iloc[0] == t["expiry"])
            e = pd.Timestamp(t["entry"])
            prior = f.index[f.index < e]
            self.assertTrue(len(prior) > 0, "an entry cannot be on the first day: the signal needs a prior close")
            self.assertGreaterEqual(abs(f.z[prior].dropna()).max(), 1.0)
            self.assertTrue(f.at[e, "ok"])


if __name__ == "__main__":
    unittest.main()

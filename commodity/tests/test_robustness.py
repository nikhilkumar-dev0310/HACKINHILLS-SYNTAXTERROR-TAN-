"""robustness.py: each statistic on cases with a known answer, then the stored results recomputed.

Break-even slippage, probabilistic and deflated Sharpe ratios, the ADF test, AR(1) half-life, regime
segmentation and event matching are each checked on synthetic data whose answer is known, before the
stored results/robustness.json is checked against the files it was computed from.
"""
import json
import math
import unittest

import numpy as np
import pandas as pd

import robustness as rb
from _util import cases, result, site

STORED = json.load(open("results/robustness.json"))


class BreakEven(unittest.TestCase):
    def test_zero_profit_at_the_break_even(self):
        """Net falls linearly with slippage: interpolating at the break-even gives zero"""
        n0, n10 = 50_000.0, -30_000.0
        be = rb.breakeven(n0, n10)
        self.assertAlmostEqual(n0 + (n10 - n0) / 10 * be, 0.0, places=6)
        self.assertAlmostEqual(be, 6.25)

    def test_more_profit_tolerates_more_slippage(self):
        self.assertGreater(rb.breakeven(80_000, 0), rb.breakeven(40_000, -40_000))

    def test_refuses_net_that_rises_with_slippage(self):
        with self.assertRaises(ValueError):
            rb.breakeven(10_000, 20_000)

    def test_slippage_cost_is_linear_in_the_stored_results(self):
        """The 5 bp net lies exactly between the 0 and 10 bp nets, so a straight line is the right model"""
        for r in STORED["breakeven"]["rows"]:
            self.assertLess(abs((r["net0"] + r["net10"]) / 2 - r["net5"]), 2, r)


@cases([r["test"] + "_" + r["strategy"] for r in STORED["breakeven"]["rows"]])
class EachBreakEven(unittest.TestCase):
    def check_matches_the_stored_results(self, key):
        """Each stored break-even is recomputed from the sealed summary or the holdout backtest"""
        test, strat = key.rsplit("_", 1)
        r = next(x for x in STORED["breakeven"]["rows"] if x["test"] == test and x["strategy"] == strat)
        if test == "holdout":
            rows = {x["slip"]: x["net"] for x in site()["backtests"][f"{strat}_hold"]["rows"]}
            n0, n10 = rows[0], rows[10]
        else:
            s = result("sealed_summary.csv")
            g = s[(s.test == test) & s.strategy.str.startswith(strat)].set_index("slip_bp").net
            n0, n10 = g[0], g[10]
        self.assertEqual(r["net0"], round(n0))
        if n0 > 0:
            self.assertAlmostEqual(r["breakeven_bp"], rb.breakeven(n0, n10), places=1)
        else:
            self.assertIsNone(r["breakeven_bp"])


class SharpeTests(unittest.TestCase):
    rng = np.random.default_rng(7)

    def test_no_edge_gives_about_a_half(self):
        x = self.rng.normal(0, 1, 4000)
        x -= x.mean()
        self.assertAlmostEqual(rb.psr(x)[0], 0.5, delta=0.02)

    def test_clear_edge_gives_near_certainty(self):
        self.assertGreater(rb.psr(self.rng.normal(0.5, 1, 400))[0], 0.999)

    def test_clear_loss_gives_near_zero(self):
        self.assertLess(rb.psr(self.rng.normal(-0.5, 1, 400))[0], 0.001)

    def test_currency_scale_does_not_matter(self):
        x = self.rng.normal(0.1, 1, 300)
        self.assertAlmostEqual(rb.psr(x)[0], rb.psr(x * 1000)[0], places=9)

    def test_flipping_the_sign_flips_the_probability(self):
        x = self.rng.normal(0.05, 1, 300)
        x = x - x.mean() + 0.05      # symmetric about its mean apart from the shift, so skew is ~0
        p, _ = rb.psr(x)
        q, _ = rb.psr(-x)
        self.assertAlmostEqual(p + q, 1.0, delta=0.05)

    def test_more_trades_more_confidence(self):
        base = self.rng.normal(0.1, 1, 50)
        base = (base - base.mean()) / base.std(ddof=1) + 0.1
        self.assertGreater(rb.psr(np.tile(base, 8))[0], rb.psr(base)[0])

    def test_best_of_more_tries_is_luckier(self):
        self.assertGreater(rb.expected_max_sr(0.04, 100), rb.expected_max_sr(0.04, 10))
        self.assertGreater(rb.expected_max_sr(0.09, 72), rb.expected_max_sr(0.04, 72))
        self.assertEqual(rb.expected_max_sr(0.0, 72), 0.0)

    def test_stored_probabilities_are_probabilities(self):
        for r in STORED["sharpe"]["rows"]:
            self.assertTrue(0 <= r["psr"] <= 1, r)
        d = STORED["sharpe"]["deflated_c"]
        self.assertTrue(0 <= d["dsr"] <= 1)
        self.assertEqual(d["trials"], 72)
        self.assertLessEqual(d["dsr"], next(r["psr"] for r in STORED["sharpe"]["rows"] if r["test"] == "test3" and r["strategy"] == "C"))

    def test_stored_sharpe_recomputes_from_the_trade_logs(self):
        t = result("sealed_trades.csv")
        t = t[t.slip_bp == rb.SLIP]
        for r in STORED["sharpe"]["rows"]:
            if r["test"] == "holdout":
                continue
            g = t[(t.test == r["test"]) & t.strategy.str.startswith(r["strategy"])]
            p, sr = rb.psr(g.net_rs)
            self.assertEqual(r["trades"], len(g))
            self.assertAlmostEqual(r["psr"], p, places=3)
            self.assertAlmostEqual(r["sr_per_trade"], sr, places=3)


class Stationarity(unittest.TestCase):
    def series(self, phi, n=1500, seed=1):
        r = np.random.default_rng(seed)
        y = np.zeros(n)
        for i in range(1, n):
            y[i] = phi * y[i - 1] + r.normal()
        return y

    def test_fast_mean_reversion_is_stationary(self):
        for seed in range(5):
            self.assertLess(rb.adf(self.series(0.5, seed=seed))[0], rb.ADF_CRIT["1%"])

    def test_random_walk_usually_is_not(self):
        rejected = sum(rb.adf(np.cumsum(np.random.default_rng(s).normal(size=800)))[0] < rb.ADF_CRIT["5%"] for s in range(40))
        self.assertLessEqual(rejected, 6)          # about 5% expected by construction

    def test_lag_choice_stays_in_range(self):
        _, lags, n = rb.adf(self.series(0.8), max_lag=6)
        self.assertTrue(0 <= lags <= 6)
        self.assertGreater(n, 1000)

    def test_half_life_of_known_processes(self):
        self.assertAlmostEqual(rb.half_life(self.series(0.5, n=20000))[0], 1.0, delta=0.08)
        self.assertAlmostEqual(rb.half_life(self.series(0.9, n=20000))[0], math.log(2) / -math.log(0.9), delta=0.5)

    def test_no_half_life_without_mean_reversion(self):
        hl, phi = rb.half_life(np.arange(200, dtype=float))
        self.assertIsNone(hl)

    def test_stored_rows_recompute_from_the_site_series(self):
        p = site()["premium_daily"]
        for r in STORED["stationarity"]["rows"]:
            y = pd.Series(p[r["symbol"]], dtype=float).dropna().values
            self.assertEqual(r["days"], len(y))
            self.assertAlmostEqual(r["adf"], rb.adf(y)[0], places=2)
            self.assertAlmostEqual(r["half_life_days"], rb.half_life(y)[0], places=1)


class Regimes(unittest.TestCase):
    def test_finds_a_clear_step(self):
        x = np.r_[np.zeros(12), np.full(12, 100.0)] + np.random.default_rng(3).normal(0, 3, 24)
        self.assertEqual(rb.segment(x), [12])

    def test_finds_two_steps(self):
        x = np.r_[np.zeros(10), np.full(8, 150.0), np.full(10, 20.0)] + np.random.default_rng(4).normal(0, 4, 28)
        self.assertEqual(rb.segment(x), [10, 18])

    def test_noise_alone_rarely_shows_a_break(self):
        """False-break rate on pure noise, measured over 300 series of 20-36 months: at most 6%"""
        fp = sum(len(rb.segment(np.random.default_rng(s).normal(50, 10, n))) > 0 for s in range(100) for n in (20, 30, 36))
        self.assertLessEqual(fp / 300, 0.06)

    def test_regimes_respect_the_minimum_length(self):
        x = np.r_[np.zeros(15), [500.0], np.zeros(15)]
        for b in rb.segment(x, min_len=3):
            self.assertTrue(3 <= b <= len(x) - 3)

    def test_events_only_matched_within_a_month(self):
        self.assertIsNotNone(rb.nearest_event("2026-02"))
        self.assertIsNone(rb.nearest_event("2024-12"))

    def test_stored_regimes_cover_every_month_once(self):
        for r in STORED["regimes"]["rows"]:
            months = [pd.Period(x["from"], "M") for x in r["regimes"]] + [pd.Period(r["regimes"][-1]["to"], "M") + 1]
            spans = sum((pd.Period(x["to"], "M") - pd.Period(x["from"], "M")).n + 1 for x in r["regimes"])
            self.assertEqual(spans, r["months"])
            self.assertEqual(months, sorted(months))
            self.assertEqual(len(r["breaks"]), len(r["regimes"]) - 1)


class Neighbourhood(unittest.TestCase):
    def test_counts(self):
        n = STORED["neighbourhood"]
        g = result("strategy_c_dev_grid.csv").set_index("setting")
        self.assertEqual(n["all_settings"], len(g))
        self.assertEqual(n["all_positive"], int((g[n["years"]].sum(axis=1) > 0).sum()))
        self.assertLessEqual(n["neighbours_positive"], n["neighbours"])
        self.assertIn(n["chosen"], g.index)

    def test_chosen_setting_is_the_frozen_one(self):
        p = json.load(open("results/strategy_c_params.json"))
        n = STORED["neighbourhood"]["chosen"]
        for k in ("ref", "k", "stress", "exit", "hold"):
            self.assertIn(f"{k}=", n)
        self.assertIn(f"k={p['k']}", n)
        self.assertIn(f"hold={p['hold']}", n)


if __name__ == "__main__":
    unittest.main()

"""robustness.py: each statistic on cases with a known answer, then the stored results recomputed.

Break-even slippage, probabilistic and deflated Sharpe ratios, the ADF test, AR(1) half-life, regime
segmentation and event matching are each checked on synthetic data whose answer is known, before the
stored results/robustness.json is checked against the files it was computed from. So are the count of every
rule ever tried, the two half-spread estimators (Roll; Corwin and Schultz) and the delivery premium readings
(delivery.py, results/delivery.json).
"""
import json
import math
import unittest

import numpy as np
import pandas as pd

from _util import cases, result, site          # first: it puts commodity/ on the import path

import delivery as dl
import robustness as rb

STORED = json.load(open("results/robustness.json"))
LOGS = {("holdout", "A"): "holdout_trades.csv", ("holdout", "B"): "fairvalue_holdout_trades.csv", ("test", "A"): "test_trades.csv"}


def sealed_log(test, strat):
    """One sealed result's trades at the stored slippage, from the file the result was recorded in."""
    if (test, strat) in LOGS:
        g = result(LOGS[(test, strat)])
        return g[g.slip_bp == rb.SLIP]
    t = result("sealed_trades.csv")
    return t[(t.slip_bp == rb.SLIP) & (t.test == test) & t.strategy.str.startswith(strat)]


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

    def test_first_test_agrees_with_its_own_write_up(self):
        """Strategy A's first sealed test, May-July 2025: the commodity README said "about 3.5 bp" when it ran"""
        r = next(x for x in STORED["breakeven"]["rows"] if x["test"] == "test" and x["strategy"] == "A")
        self.assertAlmostEqual(r["breakeven_bp"], 3.5, delta=0.05)
        self.assertIn("Breakeven slippage: about 3.5 bp per leg per side", open("README.md", encoding="utf-8").read())

    def test_slippage_cost_is_linear_in_the_stored_results(self):
        """The 5 bp net lies exactly between the 0 and 10 bp nets, so a straight line is the right model"""
        for r in STORED["breakeven"]["rows"]:
            self.assertLess(abs((r["net0"] + r["net10"]) / 2 - r["net5"]), 2, r)


@cases([r["test"] + "_" + r["strategy"] for r in STORED["breakeven"]["rows"]])
class EachBreakEven(unittest.TestCase):
    def check_matches_the_stored_results(self, key):
        """Each stored break-even is recomputed from the sealed summary, the holdout backtest or the first test's log"""
        test, strat = key.rsplit("_", 1)
        r = next(x for x in STORED["breakeven"]["rows"] if x["test"] == test and x["strategy"] == strat)
        if test == "holdout":
            rows = {x["slip"]: x["net"] for x in site()["backtests"][f"{strat}_hold"]["rows"]}
            n0, n10 = rows[0], rows[10]
        elif test == "test":
            g = result("test_trades.csv").groupby("slip_bp").net_rs.sum()
            n0, n10 = g[0], g[10]
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
        for r in STORED["sharpe"]["rows"]:
            g = sealed_log(r["test"], r["strategy"])
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


class RulesTried(unittest.TestCase):
    """Every rule the project scored, each counted once, and the deflated Sharpe against that count"""
    def test_families_add_up(self):
        fam, total, _ = rb.rules_tried()
        self.assertEqual(total, sum(fam.values()))
        self.assertEqual(STORED["trials"]["total"], total)
        self.assertEqual(STORED["trials"]["families"], fam)

    def test_method_labels_become_rule_keys(self):
        """The methods round's z-score label is the same rule as A's grid point; every other method is its own"""
        self.assertEqual(rb.method_key("zscore(N=10, entry=2.0)"), ("zscore", 10, 2.0))
        self.assertEqual(rb.method_key("kalman(W=20, c=1.0)"), ("method", "kalman(W=20, c=1.0)"))
        self.assertIn(rb.method_key("zscore(N=10, entry=2.0)"), rb.rule_sets()["A"])

    def test_the_no_carry_check_counts_as_a_new_rule(self):
        """overfit.py scored B's rules without the carry adjustment: a rule no other family scored"""
        s = rb.rule_sets()
        has = "no_carry" in json.load(open("results/overfit.json"))
        self.assertEqual(len(s["checks"]), int(has))
        for f, v in s.items():
            if f != "checks":
                self.assertFalse(s["checks"] & v, f)

    def test_counts_when_each_window_was_opened(self):
        """9 rules before the first test; A, the methods and B's 3 settings before the holdout (C did not exist
        yet, so B's shared settings count as B's); everything but the later check before 2016-2023"""
        s, (fam, total, _) = rb.rule_sets(), rb.rules_tried()
        oc = STORED["trials"]["opened_counts"]
        self.assertEqual(oc["test"], len(s["A"]))
        self.assertEqual(oc["holdout"], len(s["A"]) + fam["methods"] + len(s["B"]))
        self.assertEqual(oc["test3"], total - fam["checks"])
        self.assertEqual(oc["test2"], oc["test3"])
        self.assertTrue(oc["test"] <= oc["holdout"] <= oc["test3"] <= total)
        self.assertEqual(STORED["trials"]["opened_after"], {w: list(f) for w, f in rb.OPENED_AFTER.items()})

    def test_each_family_is_counted_from_its_sweep(self):
        fam, _, ov = rb.rules_tried()
        a = result("train_sweep.csv")[["lookback", "entry_z"]].drop_duplicates()
        self.assertEqual(fam["A"], len(a))
        self.assertEqual(fam["C"], result("strategy_c_dev_grid.csv").setting.nunique())
        self.assertEqual(fam["methods"], result("methods_train.csv").method.nunique() - len(ov["methods_repeating_a"]))
        self.assertEqual(fam["B"] + len(ov["b_k_in_c"]), result("fairvalue_dev.csv").k.nunique())

    def test_overlaps_are_real_overlaps(self):
        """A rule counted once must really appear in both places"""
        _, _, ov = rb.rules_tried()
        grid = [rb.parse_setting(x) for x in result("strategy_c_dev_grid.csv").setting]
        for k in ov["b_k_in_c"]:
            self.assertIn({"ref": "all", "k": float(k), "stress": None, "exit": 0.0, "hold": None}, grid)
        for m in ov["methods_repeating_a"]:
            self.assertTrue(m.startswith("zscore("))

    def test_more_rules_never_raise_the_deflated_sharpe(self):
        for r in STORED["trials"]["rows"]:
            self.assertLessEqual(r["dsr_all"], r["dsr_opened"] + 1e-9, r)
            self.assertLessEqual(r["dsr_opened"], r["dsr_own"] + 1e-9, r)
            self.assertGreaterEqual(r["sr_luck_all"], r["sr_luck_own"] - 1e-9, r)
        for r in STORED["trials"]["per_result"]:
            self.assertTrue(r["own_trials"] <= r["opened_trials"] <= r["ever_trials"], r)
            self.assertTrue(r["dsr_ever"] <= r["dsr_opened"] + 1e-9 and r["dsr_opened"] <= r["dsr_own"] + 1e-9, r)
            self.assertTrue(r["sr_luck_own"] <= r["sr_luck_opened"] + 1e-9 and r["sr_luck_opened"] <= r["sr_luck_ever"] + 1e-9, r)
            self.assertLessEqual(r["dsr_own"], r["psr"] + 1e-9, r)             # beating luck is harder than beating zero

    def test_every_sealed_result_is_deflated_once(self):
        """One row per sealed result, the same results the break-even table lists"""
        per = [(r["test"], r["strategy"]) for r in STORED["trials"]["per_result"]]
        self.assertEqual(len(per), len(set(per)))
        self.assertEqual(set(per), {(r["test"], r["strategy"]) for r in STORED["breakeven"]["rows"]})

    def test_each_result_counts_the_rules_of_its_own_window(self):
        s, (_, total, _) = rb.rule_sets(), rb.rules_tried()
        for r in STORED["trials"]["per_result"]:
            self.assertEqual(r["own_trials"], len(s[r["strategy"]]), r)
            self.assertEqual(r["opened_trials"], STORED["trials"]["opened_counts"][r["test"]], r)
            self.assertEqual(r["ever_trials"], total, r)

    def test_per_result_rows_recompute_from_the_trade_logs(self):
        sh = {(r["test"], r["strategy"]): r for r in STORED["sharpe"]["rows"]}
        for r in STORED["trials"]["per_result"]:
            x = sealed_log(r["test"], r["strategy"]).net_rs
            self.assertEqual(r["trades"], len(x), r)
            self.assertEqual(r["net"], round(float(x.sum())), r)
            self.assertAlmostEqual(r["sr_per_trade"], x.mean() / x.std(ddof=1), places=3)
            self.assertAlmostEqual(r["psr"], sh[(r["test"], r["strategy"])]["psr"], places=3)
            years = (pd.Timestamp(r["to"]) - pd.Timestamp(r["from"])).days / 365.25
            self.assertTrue(0.2 < years < 4.1, r)                                # a declared window, not a typo
            self.assertAlmostEqual(r["sr_luck_ever"], rb.expected_max_sr(self.var_per_trade(len(x), years), r["ever_trials"]), places=3)

    @staticmethod
    def var_per_trade(n, years):
        grid = result("strategy_c_dev_grid.csv").set_index("setting")
        yrs = [c for c in grid.columns if c != "2026"]
        gsr = (grid[yrs].mean(axis=1) / grid[yrs].std(axis=1, ddof=1)).replace([np.inf, -np.inf], np.nan).dropna()
        return float(gsr.var(ddof=1)) / (n / years)

    def test_windows_are_the_declared_ones(self):
        """Each result's window comes from the parameters frozen before it ran"""
        fp, fvp, cp = (json.load(open(f"results/{f}")) for f in ("frozen_params.json", "fairvalue_params.json", "strategy_c_params.json"))
        want = {("test", "A"): fp["test"], ("holdout", "B"): fvp["holdout"]}
        want.update({(w, st): cp["sealed_windows"][w] for w in ("test3", "test2") for st in "ABC"})
        for r in STORED["trials"]["per_result"]:
            if (r["test"], r["strategy"]) in want:
                self.assertEqual([r["from"], r["to"]], want[(r["test"], r["strategy"])], r)

    def test_deflated_matches_the_closed_form(self):
        rng = np.random.default_rng(3)
        x = rng.normal(0.2, 1, 60)
        d, sr, sr0 = rb.deflated(x, 0.02, 50)
        self.assertAlmostEqual(sr0, rb.expected_max_sr(0.02, 50))
        p_at_luck, _ = rb.psr(x, sr0)
        self.assertAlmostEqual(d, p_at_luck, places=9)

    def test_stored_rows_recompute_from_the_trade_logs(self):
        t = result("sealed_trades.csv")
        t = t[t.slip_bp == STORED["trials"]["slip_bp"]]
        for r in STORED["trials"]["rows"]:
            x = t[t.strategy.str.startswith(r["strategy"])].net_rs
            self.assertEqual(r["trades"], len(x))
            self.assertEqual(r["net"], round(float(x.sum())))
            self.assertAlmostEqual(r["sr_per_trade"], x.mean() / x.std(ddof=1), places=3)


class HalfSpreads(unittest.TestCase):
    """Roll (1984) and Corwin-Schultz (2012) on simulated markets whose spread is known"""
    @staticmethod
    def market(spread, days=400, steps=400, vol=0.004, seed=1):
        """A mid price walking within each day; trades at mid +- half the spread. Returns daily high, low, close."""
        rng = np.random.default_rng(seed)
        mid = 100 * np.exp(np.cumsum(rng.normal(0, vol / np.sqrt(steps), days * steps))).reshape(days, steps)
        side = rng.choice([-1, 1], (days, steps))
        px = mid * (1 + side * spread / 2)
        return px.max(1), px.min(1), px[:, -1]

    def test_corwin_schultz_recovers_a_known_spread(self):
        """Averaged over many days the raw two-day estimates come back to the true spread, even when the spread
        is small next to the day's price swing"""
        for vol in (0.01, 0.004):
            for s in (0.001, 0.002):
                h, l, c = self.market(s, vol=vol, days=1500)
                self.assertAlmostEqual(float(np.mean(rb.cs_spread(h, l, c))), s, delta=s * 0.2 + 0.0003)

    def test_flooring_each_day_first_would_overstate_it(self):
        """Why the floor comes after the average: with no spread at all, zeroing each negative day reads a wide one"""
        h, l, c = self.market(0.0, vol=0.01, days=1500, seed=4)
        raw = rb.cs_spread(h, l, c)
        self.assertLess(abs(float(raw.mean())), 0.0006)
        self.assertGreater(float(np.maximum(raw, 0).mean()), 0.002)

    def test_corwin_schultz_is_scale_free(self):
        h, l, c = self.market(0.0015, days=60)
        np.testing.assert_allclose(rb.cs_spread(h, l, c), rb.cs_spread(h * 37, l * 37, c * 37))

    def test_roll_recovers_bid_ask_bounce(self):
        """Bounce alone (no news): the estimator gets the spread back"""
        rng = np.random.default_rng(7)
        s = 0.002
        close = 100 * (1 + rng.choice([-1, 1], 5000) * s / 2)
        self.assertAlmostEqual(rb.roll_spread(close), s, delta=s * 0.1)

    def test_roll_undefined_without_negative_covariance(self):
        self.assertIsNone(rb.roll_spread(100 * np.exp(np.cumsum(np.full(50, 0.001)) + np.linspace(0, 0.01, 50) ** 2)))
        self.assertIsNone(rb.roll_spread([100, 101]))

    def test_pooled_half_spread_on_a_known_market(self):
        h, l, c = self.market(0.002, vol=0.004, days=1200)
        x = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=len(h) - 1), "cs": rb.cs_spread(h, l, c)})
        p = rb.pooled_half_spread(x)
        self.assertLessEqual(p["lo"], 10.0)
        self.assertGreaterEqual(p["hi"], 10.0)                    # the true half-spread is 10 bp
        self.assertAlmostEqual(p["half_bp"], 10.0, delta=2.5)

    def test_a_clearly_negative_mean_is_not_measurable(self):
        x = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=300), "cs": np.full(300, -0.0006)})
        p = rb.pooled_half_spread(x)
        self.assertIsNone(p["half_bp"])
        self.assertEqual((p["lo"], p["hi"]), (0.0, 0.0))                 # floored like the estimate: never lo above hi
        self.assertLess(p["raw_bp"], -1)
        x["cs"] = -0.00001                                          # a hair below zero: about nothing, read as zero
        self.assertEqual(rb.pooled_half_spread(x)["half_bp"], 0.0)

    def test_stored_windows_are_sane(self):
        for w, m in STORED["costs"]["windows"].items():
            self.assertIn(w, ("test3", "test2", "test", "holdout", "recent"))
            for sym, v in m.items():
                if not isinstance(v, dict):
                    continue
                self.assertGreater(v["pairs"], 50, (w, sym))
                self.assertTrue(0 <= v["lo"] <= v["hi"], (w, sym))
                if v["half_bp"] is not None:
                    self.assertGreaterEqual(v["half_bp"], 0)
                    self.assertLessEqual(v["half_bp"], v["hi"] + 1e-9, (w, sym))
                else:
                    self.assertLess(v["raw_bp"], -1)
        for r in STORED["costs"]["rows"]:
            self.assertLessEqual(r["roll_defined"], r["roll_months"])

    def test_every_verdict_follows_from_its_numbers(self):
        """Covered only if the break-even clears even the top of the measured cost's 95% range"""
        for r in STORED["breakeven"]["rows"]:
            if r["est_slip_bp"] is None:
                self.assertFalse(r["survives_est"], r)
                continue
            self.assertLessEqual(r["est_slip_bp"], r["est_slip_hi_bp"] + 1e-9)
            self.assertEqual(r["survives_est"], r["breakeven_bp"] is not None and r["breakeven_bp"] > r["est_slip_hi_bp"], r)

    def test_measured_cost_is_the_mean_of_the_legs_traded(self):
        """B and C trade a small contract against GOLDM, so their cost sits between the two legs' half-spreads"""
        w = STORED["costs"]["windows"]
        for r in STORED["breakeven"]["rows"]:
            if r["strategy"] in ("B", "C") and r["est_slip_bp"] is not None:
                m, small = w[r["test"]]["GOLDM"]["half_bp"], [w[r["test"]][s]["half_bp"] for s in ("GOLDGUINEA", "GOLDPETAL")]
                self.assertGreaterEqual(r["est_slip_bp"], (m + min(small)) / 2 - 0.06, r)
                self.assertLessEqual(r["est_slip_bp"], (m + max(small)) / 2 + 0.06, r)


DELIV = json.load(open("results/delivery.json"))


class DeliveryPremium(unittest.TestCase):
    """delivery.py: three readings of the premium in every cycle, and the summaries built from them"""
    @staticmethod
    def frame(prem, ok=None):
        idx = pd.bdate_range("2026-01-01", periods=len(prem))
        exp = idx[-1]
        f = pd.DataFrame({"prem_bp": prem, "ok": ok if ok is not None else [True] * len(prem)}, index=idx)
        f["bleft"] = np.busday_count(idx.values.astype("datetime64[D]"), np.datetime64(exp.date()))
        return f, pd.Series(10000.0, index=idx)

    def test_readings_on_a_known_cycle(self):
        prem = list(np.linspace(40, 60, 30)) + [90.0, 120.0]          # flat-ish, then up in the last days
        f, price = self.frame(prem)
        r = dl.readings(f, price)
        e = f[f.bleft <= dl.ENTRY_BDAYS].index[0]
        p = f[f.bleft >= 5].index[-1]
        self.assertEqual(r["entry"], str(e.date()))
        self.assertEqual(r["exit"], str(p.date()))
        self.assertAlmostEqual(r["entry_bp"], f.prem_bp[e])
        self.assertAlmostEqual(r["settle_bp"], 120.0)
        self.assertAlmostEqual(r["early_exit_bp"], f.prem_bp[e] - f.prem_bp[p])
        self.assertAlmostEqual(r["entry_rs_g"], 10000.0 * f.prem_bp[e] / 1e4)

    def test_no_reading_without_a_settlement(self):
        f, price = self.frame(list(np.linspace(40, 60, 40)))
        self.assertIsNone(dl.readings(f.iloc[:-5], price))          # the last row is a week before expiry

    def test_no_reading_if_only_liquid_inside_the_window(self):
        ok = [False] * 28 + [True] * 4
        f, price = self.frame(list(np.linspace(40, 60, 32)), ok)
        self.assertIsNone(dl.readings(f, price))

    def test_every_cycle_is_ordered_and_consistent(self):
        for c in DELIV["cycles"]:
            self.assertLessEqual(c["entry"], c["exit"])
            self.assertLessEqual(c["exit"], c["settle"])
            self.assertLessEqual(c["settle"], c["expiry"])
            self.assertAlmostEqual(c["early_exit_bp"], c["entry_bp"] - c["exit_bp"], places=1)
            self.assertAlmostEqual(c["window_change_bp"], c["settle_bp"] - c["exit_bp"], places=1)

    def test_summaries_recompute_from_the_cycles(self):
        c = pd.DataFrame(DELIV["cycles"])
        v0 = DELIV["rules"]["verified_from"]
        for r in DELIV["rows"]:
            g = c[c.symbol == r["symbol"]]
            self.assertEqual(r["all"]["cycles"], len(g))
            ver = g[g.expiry >= v0]
            if r["verified"]:
                self.assertEqual(r["verified"]["cycles"], len(ver))
                for k in ("entry_bp", "exit_bp", "settle_bp", "early_exit_bp"):
                    self.assertAlmostEqual(r["verified"][k], round(float(ver[k].median()), 1), places=1)

    def test_the_site_shows_only_verified_cycles(self):
        S = site().get("delivery")
        if S is None:
            self.skipTest("delivery.py not run")
        self.assertTrue(all(c["expiry"] >= DELIV["rules"]["verified_from"] for c in S["cycles"]))
        self.assertEqual(S["rows"], DELIV["rows"])
        self.assertIsNone(S["retail"])


if __name__ == "__main__":
    unittest.main()

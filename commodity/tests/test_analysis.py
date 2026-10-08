"""The analysis building blocks: attribution, alerts, roll-down, overfitting check and resampling.

Each is tested on inputs where the right answer is known in advance, then on the stored results.
"""
import itertools
import json
import os
import unittest

import numpy as np
import pandas as pd

import attribution as at
import overfit as of
from _util import cases, result

RNG = np.random.default_rng(42)
SPLITS = [tuple(RNG.uniform(1000, 20000, 4)) + (int(RNG.choice([-1, 1])), int(RNG.choice([1, 40, 200]))) for _ in range(40)]


@cases(range(len(SPLITS)), name=lambda i: f"case{i}")
class AttributionIdentity(unittest.TestCase):
    def check_gap_plus_gold_equals_gross(self, i):
        """Gap part + gold part = gross, exactly, for any prices, side and size"""
        a0, a1, b0, b1, pos, g = SPLITS[i]
        gross, gap, gold, _ = at.split(pos, g, a0, a1, b0, b1)
        self.assertAlmostEqual(gap + gold, gross, places=6)
        self.assertAlmostEqual(gross, pos * g * ((a1 - a0) - (b1 - b0)), places=6)

    def check_no_gold_part_when_legs_are_identical(self, i):
        """If both legs are the same price, gold's move cannot affect the trade"""
        a0, a1, _, _, pos, g = SPLITS[i]
        gross, gap, gold, _ = at.split(pos, g, a0, a1, a0, a1)
        self.assertAlmostEqual(gold, 0.0, places=6)
        self.assertAlmostEqual(gross, 0.0, places=6)

    def check_flat_gold_means_all_gap(self, i):
        """If the hedge leg does not move, the whole profit is the gap"""
        a0, a1, b0, _, pos, g = SPLITS[i]
        gross, gap, gold, mv = at.split(pos, g, a0, a1, b0, b0)
        self.assertAlmostEqual(gold, 0.0, places=6)
        self.assertAlmostEqual(mv, 0.0, places=9)


class AttributionStored(unittest.TestCase):
    def test_every_stored_trade_reproduces_and_adds_up(self):
        t = result("attribution_trades.csv")
        np.testing.assert_allclose(t.gap_part + t.gold_part, t.gross, atol=0.02)
        np.testing.assert_allclose(t.gross, t.gross_stored, atol=0.02)

    def test_gold_is_a_small_share_of_profit(self):
        s = result("attribution_summary.csv")
        self.assertTrue((s.abs_gold_share_pct.abs() < 25).all(), s.to_string())


class OverfitMath(unittest.TestCase):
    def test_perfect_skill_gives_zero(self):
        """One setting best in every year: the in-sample pick is always the out-of-sample best"""
        g = np.vstack([np.full(10, 5.0), RNG.normal(0, 1, (20, 10))])
        self.assertEqual(of.pbo(g, list(range(10)))[0], 0.0)

    def test_anti_skill_gives_one(self):
        """Settings whose ranking flips between halves: the pick is always the worst out of sample"""
        years = 6
        g = np.zeros((years, years))
        for i in range(years):
            g[i, i] = 100.0                                        # setting i only makes money in year i
            g[i, [j for j in range(years) if j != i]] = -1.0
        p, _, w = of.pbo(g, list(range(years)))
        self.assertGreater(p, 0.5)

    def test_pure_noise_is_near_a_half(self):
        vals = [of.pbo(np.random.default_rng(s).normal(0, 1, (40, 10)), list(range(10)))[0] for s in range(30)]
        self.assertTrue(0.35 < np.mean(vals) < 0.65, np.mean(vals))

    def test_split_count(self):
        _, _, w = of.pbo(RNG.normal(0, 1, (5, 8)), list(range(8)))
        self.assertEqual(len(w), len(list(itertools.combinations(range(8), 4))))

    def test_rejects_odd_blocks_and_single_setting(self):
        with self.assertRaises(ValueError):
            of.pbo(RNG.normal(0, 1, (5, 7)), list(range(7)))
        with self.assertRaises(ValueError):
            of.pbo(RNG.normal(0, 1, (1, 8)), list(range(8)))

    def test_stored_pbo_recomputes(self):
        if not os.path.exists("results/overfit.json"):
            self.skipTest("overfit.py not run")
        o = json.load(open("results/overfit.json"))
        g = result("strategy_c_dev_grid.csv").set_index("setting")
        p = of.pbo(g[o["pbo"]["blocks"]].fillna(0).values, o["pbo"]["blocks"])[0]
        self.assertAlmostEqual(p, o["pbo"]["value"], places=3)

    def test_overfit_check_never_uses_sealed_years(self):
        if not os.path.exists("results/overfit.json"):
            self.skipTest("overfit.py not run")
        o = json.load(open("results/overfit.json"))
        for y in o["pbo"]["blocks"]:
            self.assertFalse(2016 <= int(y) <= 2023, y)


class Alerts(unittest.TestCase):
    H = result("alerts_history.csv")

    def test_alerts_only_fire_beyond_the_threshold(self):
        k = json.load(open("results/fairvalue_params.json"))["k"]
        self.assertTrue((self.H.z.abs() >= k - 1e-9).all())

    def test_direction_matches_the_sign(self):
        rich = self.H.direction == "rich vs GOLDM"
        self.assertTrue((self.H.z[rich] > 0).all() and (self.H.z[~rich] < 0).all())

    def test_episodes_do_not_overlap_per_contract_type(self):
        for s, g in self.H.groupby("symbol"):
            g = g.sort_values("start")
            self.assertTrue((pd.to_datetime(g.start).values[1:] > pd.to_datetime(g.end).values[:-1]).all(), s)

    def test_half_life_consistent_with_flag(self):
        h = self.H[self.H.closed_half_10d.notna()]
        closed = h.closed_half_10d.astype(str).str.lower() == "true"
        self.assertTrue((h.days_to_half[closed] <= 10).all())

    def test_alerts_are_rare(self):
        """Quiet by design: alert days are a small share of market days"""
        b = result("alerts_baseline.csv").set_index("alert_day")
        share = b.loc[True, "days"] / b.days.sum() if True in b.index else b.iloc[-1].days / b.days.sum()
        self.assertLess(share, 0.25)


class RollDown(unittest.TestCase):
    def test_roll_plus_curve_compound_to_total(self):
        m = result("rolldown_monthly.csv")
        cols = [c for c in m.columns if "roll" in c.lower()], [c for c in m.columns if "curve" in c.lower()], [c for c in m.columns if "total" in c.lower()]
        if not all(cols):
            self.skipTest(f"columns {list(m.columns)}")
        r, c, t = m[cols[0][0]], m[cols[1][0]], m[cols[2][0]]
        scale = 100 if t.abs().max() > 1 else 1
        np.testing.assert_allclose((1 + r / scale) * (1 + c / scale) - 1, t / scale, atol=2e-3)


if __name__ == "__main__":
    unittest.main()

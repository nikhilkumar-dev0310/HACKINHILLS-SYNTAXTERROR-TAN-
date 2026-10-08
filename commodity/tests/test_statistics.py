"""The resampling and carry calculations behind the site's 95% ranges and fair prices, on known cases.

uncertainty.bootstrap (weekly resampling of trade profits), accuracy.week_boot_mean and testbed.week_boot
(weekly resampling of means), accuracy.carry_table (carry from adjacent expiries, past-only fallback) and
testbed.part_a (the data-integrity rates).
"""
import unittest

import numpy as np
import pandas as pd

import accuracy
import testbed
import uncertainty
from _util import cases, clean


def trades(nets, start="2025-01-06", per_week=2):
    days = pd.bdate_range(start, periods=len(nets) * 5 + 5)
    entries = [days[(i // per_week) * 5 + i % per_week] for i in range(len(nets))]
    return pd.DataFrame({"entry": [d.strftime("%Y-%m-%d") for d in entries], "net_rs": nets})


class TradeBootstrap(unittest.TestCase):
    def test_range_contains_the_total(self):
        rng = np.random.default_rng(1)
        n, total, ci, share = uncertainty.bootstrap(trades(list(rng.normal(500, 2000, 60))))
        self.assertLessEqual(ci[0], total)
        self.assertGreaterEqual(ci[1], total)

    def test_weeks_are_the_resampling_unit(self):
        n, *_ = uncertainty.bootstrap(trades([100.0] * 20, per_week=2))
        self.assertEqual(n, 10)

    def test_all_winning_weeks_give_certainty(self):
        *_, share = uncertainty.bootstrap(trades([1000.0 + i for i in range(30)]))
        self.assertEqual(share, 1.0)

    def test_all_losing_weeks_give_zero(self):
        *_, share = uncertainty.bootstrap(trades([-1000.0 - i for i in range(30)]))
        self.assertEqual(share, 0.0)

    def test_identical_weeks_have_no_spread(self):
        n, total, ci, share = uncertainty.bootstrap(trades([250.0] * 16, per_week=1))
        self.assertAlmostEqual(ci[0], total)
        self.assertAlmostEqual(ci[1], total)


@cases([("accuracy", accuracy.week_boot_mean), ("testbed", testbed.week_boot)], name=lambda x: x[0])
class MeanBootstrap(unittest.TestCase):
    def series(self, values):
        idx = pd.MultiIndex.from_arrays([["X"] * len(values), pd.bdate_range("2025-01-06", periods=len(values))], names=["pair", "date"])
        return pd.Series(values, index=idx)

    def run_it(self, fn, values):
        s = self.series(values)
        if fn is accuracy.week_boot_mean:
            est, lo, hi, _ = fn(s)
        else:
            est, lo, hi = fn(s.values, s.index.get_level_values("date").to_period("W"))
        return est, lo, hi

    def check_estimate_is_the_plain_mean(self, it):
        v = list(np.random.default_rng(2).normal(30, 10, 60))
        est, lo, hi = self.run_it(it[1], v)
        self.assertAlmostEqual(est, np.mean(v))

    def check_range_brackets_the_mean(self, it):
        v = list(np.random.default_rng(3).normal(30, 10, 60))
        est, lo, hi = self.run_it(it[1], v)
        self.assertTrue(lo <= est <= hi)

    def check_more_noise_wider_range(self, it):
        r = np.random.default_rng(4)
        base = r.normal(0, 1, 80)
        _, lo1, hi1 = self.run_it(it[1], list(30 + 5 * base))
        _, lo2, hi2 = self.run_it(it[1], list(30 + 20 * base))
        self.assertGreater(hi2 - lo2, hi1 - lo1)


class Carry(unittest.TestCase):
    def frame(self, closes, dates, gap_days=30):
        rows = []
        for d, (near, far) in zip(dates, closes):
            rows.append({"date": d, "symbol": "GOLDPETAL", "expiry_date": pd.Timestamp("2025-03-31"), "close": near})
            rows.append({"date": d, "symbol": "GOLDPETAL", "expiry_date": pd.Timestamp("2025-03-31") + pd.Timedelta(days=gap_days), "close": far})
        return pd.DataFrame(rows)

    def test_carry_from_adjacent_expiries(self):
        """Far contract 0.5% dearer, 30 days later: carry = ln(1.005) x 365 / 30 a year"""
        d = pd.bdate_range("2025-02-03", periods=5)
        c, daily = accuracy.carry_table(self.frame([(10000, 10050)] * 5, d))
        self.assertAlmostEqual(daily.iloc[0], np.log(1.005) * 365 / 30, places=10)

    def test_expiries_too_far_apart_are_ignored(self):
        d = pd.bdate_range("2025-02-03", periods=3)
        c, daily = accuracy.carry_table(self.frame([(10000, 10050)] * 3, d, gap_days=90))
        self.assertTrue(c.empty)
        self.assertTrue(daily.isna().all())

    def test_missing_day_falls_back_to_past_days_only(self):
        """A day with no usable pair takes the median of earlier days, never later ones"""
        d = pd.bdate_range("2025-02-03", periods=6)
        f = self.frame([(10000, 10050)] * 3 + [(10000, 10200)] * 3, d)
        f = pd.concat([f, pd.DataFrame([{"date": d[-1] + pd.Timedelta(days=1), "symbol": "GOLDPETAL",
                                          "expiry_date": pd.Timestamp("2025-03-31"), "close": 10000}])])
        c, daily = accuracy.carry_table(f)
        last = daily.iloc[-1]
        self.assertAlmostEqual(last, np.median(daily.iloc[:-1].tail(20)))


class Integrity(unittest.TestCase):
    def test_clean_development_data_has_no_hard_errors(self):
        rows = testbed.part_a(clean("dev")).set_index("check").error_rate
        self.assertEqual(rows["Duplicate (date, symbol, expiry)"], 0)
        self.assertEqual(rows["Row dated after its expiry"], 0)

    def test_planted_errors_are_caught(self):
        d = clean("dev").head(200).copy()
        d = pd.concat([d, d.iloc[[0]]], ignore_index=True)                      # one duplicate
        d.iloc[1, d.columns.get_loc("date")] = d.iloc[1].expiry_date + pd.Timedelta(days=1)   # one row after expiry
        rows = testbed.part_a(d).set_index("check").error_rate
        self.assertGreater(rows["Duplicate (date, symbol, expiry)"], 0)
        self.assertGreater(rows["Row dated after its expiry"], 0)

    def test_percent_format(self):
        self.assertEqual(testbed.pct(0.0123), "1.23%")


if __name__ == "__main__":
    unittest.main()

"""The daily job's publish gate: good updates pass, every kind of bad update is rejected.

Feeds tools/daily_update.check_update() a copy of the real data plus a synthetic new trading day,
then breaks that day in each way the gate is meant to catch.
"""
import os
import sys
import unittest

import pandas as pd

from _util import ROOT, SYMS, clean

sys.path.insert(0, os.path.join(ROOT, "tools"))
import daily_update as du  # noqa: E402

os.chdir(ROOT)


def base():
    old = clean("dev").copy()
    last = old.date.max()
    day = last + pd.offsets.BDay(1)
    rows = old[old.date == last].copy()
    rows["prev_close"] = rows.close
    rows["date"] = day
    rows = rows[rows.expiry_date > day]
    rows["close"] = rows.close * 1.002
    rows["high"] = rows[["high", "close"]].max(axis=1) * 1.001
    rows["low"] = rows[["low", "close"]].min(axis=1) * 0.999
    rows["rs_per_g"] = rows.rs_per_g * 1.002
    rows["days_to_expiry"] = (rows.expiry_date - rows.date).dt.days
    new = pd.concat([old, rows], ignore_index=True)
    return old, new, last, day


class Gate(unittest.TestCase):
    def test_a_clean_new_day_passes(self):
        old, new, last, day = base()
        fresh, both, note = du.check_update(old, new, last)
        self.assertEqual(set(fresh.date), {day})
        self.assertEqual(len(both), len(old))

    def test_rejects_a_changed_published_price(self):
        old, new, last, _ = base()
        new.loc[new.date == last - pd.offsets.BDay(3), "close"] += 10
        with self.assertRaises(SystemExit) as e:
            du.check_update(old, new, last)
        self.assertIn("changed their close", str(e.exception))

    def test_rejects_a_day_missing_a_contract_type(self):
        for s in SYMS:
            with self.subTest(missing=s):
                old, new, last, day = base()
                new = new[~((new.date == day) & (new.symbol == s))]
                with self.assertRaises(SystemExit) as e:
                    du.check_update(old, new, last)
                self.assertIn(s, str(e.exception))

    def test_rejects_a_missing_or_zero_close(self):
        for bad in (0.0, -5.0, float("nan")):
            with self.subTest(close=bad):
                old, new, last, day = base()
                i = new.index[(new.date == day) & (new.volume_lots > 0)][0]
                new.loc[i, "close"] = bad
                with self.assertRaises(SystemExit):
                    du.check_update(old, new, last)

    def test_rejects_a_close_outside_the_range_on_a_normal_day(self):
        old, new, last, day = base()
        i = new.index[(new.date == day) & (new.volume_lots > 0) & (new.expiry_date != day)][0]
        new.loc[i, "close"] = new.loc[i, "high"] * 1.05
        with self.assertRaises(SystemExit) as e:
            du.check_update(old, new, last)
        self.assertIn("outside the day's range", str(e.exception))

    def test_allows_a_due_date_rate_close_on_expiry_day(self):
        old, new, last, day = base()
        i = new.index[(new.date == day) & (new.volume_lots > 0)][0]
        new.loc[i, "expiry_date"] = day
        new.loc[i, "close"] = new.loc[i, "high"] * 1.01
        fresh, _, note = du.check_update(old, new, last)
        self.assertIn("Due Date Rate", note)

    def test_rejects_a_unit_or_column_error(self):
        for factor in (10.0, 0.1, 3.0):
            with self.subTest(factor=factor):
                old, new, last, day = base()
                i = new.index[(new.date == day) & (new.volume_lots > 0)][0]
                for c in ("close", "high", "low", "rs_per_g"):
                    new.loc[i, c] *= factor
                with self.assertRaises(SystemExit) as e:
                    du.check_update(old, new, last)
                self.assertIn("unit or column error", str(e.exception))

    def test_untraded_rows_are_not_price_checked(self):
        old, new, last, day = base()
        i = new.index[new.date == day][0]
        new.loc[i, ["volume_lots", "no_trade"]] = [0, True]
        new.loc[i, "close"] = new.loc[i, "high"] * 1.5
        du.check_update(old, new, last)

    def test_the_chain_never_reruns_a_frozen_strategy(self):
        for frozen in ("backtest.py", "fairvalue.py", "strategy_c.py", "methods.py", "overfit.py"):
            self.assertNotIn(frozen, du.CHAIN)

    def test_the_chain_rebuilds_the_site_last(self):
        self.assertEqual(du.CHAIN[-2:], ["dashboard/export.py", "dashboard/build.py"])


class Workflow(unittest.TestCase):
    Y = open(os.path.join(ROOT, "..", ".github", "workflows", "daily-data.yml")).read()

    def test_runs_on_the_team_computer(self):
        self.assertIn("runs-on: [self-hosted, parity-mcx]", self.Y)

    def test_runs_tests_before_it_commits(self):
        self.assertLess(self.Y.index("tools/run_tests.py"), self.Y.index("git commit"))

    def test_scheduled_after_mcx_publishes(self):
        self.assertIn('cron: "0 22 * * 1-5"', self.Y)       # 03:30 IST Tue-Sat
        self.assertIn('cron: "30 2 * * 2-6"', self.Y)       # 08:00 IST retry

    def test_low_priority(self):
        self.assertIn("nice -n 10", self.Y)

    def test_commits_only_data_and_site(self):
        line = next(l for l in self.Y.splitlines() if "git add" in l)
        for p in ("raw_clean", "clean", "results", "dashboard/data.json", "dashboard/index.html"):
            self.assertIn(p, line)
        self.assertNotIn("strategy", line)


if __name__ == "__main__":
    unittest.main()

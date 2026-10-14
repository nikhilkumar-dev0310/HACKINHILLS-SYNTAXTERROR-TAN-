"""The daily job's publish gate: good updates pass, every kind of bad update is rejected.

Feeds tools/daily_update.check_update() a copy of the real data plus a synthetic new trading day,
then breaks that day in each way the gate is meant to catch.
"""
import inspect
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
    full = old.groupby("date").symbol.nunique()
    old = old[old.date <= full[full == len(SYMS)].index.max()]     # start from a day with all four types
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
        held_day = sorted(old.date.unique())[-3]           # a real trading day (3 business days back can be a holiday)
        new.loc[new.date == held_day, "close"] += 10
        with self.assertRaises(SystemExit) as e:
            du.check_update(old, new, last)
        self.assertIn("changed their close", str(e.exception))

    def test_publishes_a_day_missing_one_or_two_contract_types(self):
        for miss in [[s] for s in SYMS] + [["GOLDGUINEA", "GOLDPETAL"], ["GOLDM", "GOLDTEN"]]:
            with self.subTest(missing=miss):
                old, new, last, day = base()
                new = new[~((new.date == day) & new.symbol.isin(miss))]
                fresh, _, note = du.check_update(old, new, last)
                self.assertEqual(set(fresh.symbol), set(SYMS) - set(miss))
                for s in miss:
                    self.assertIn(s, note)

    def test_rejects_a_day_with_fewer_than_two_contract_types(self):
        for keep in SYMS:
            with self.subTest(only=keep):
                old, new, last, day = base()
                new = new[~((new.date == day) & (new.symbol != keep))]
                with self.assertRaises(SystemExit) as e:
                    du.check_update(old, new, last)
                self.assertIn("has no rows for", str(e.exception))

    def test_late_rows_for_an_earlier_day_are_backfilled_and_checked(self):
        """A day published without GOLDGUINEA: when MCX returns it later, those rows count as new and are checked"""
        old, new, last, day = base()
        gap = (old.date == last) & (old.symbol == "GOLDGUINEA")
        held = old[~gap]
        fresh, both, note = du.check_update(held, new, last)
        self.assertEqual(len(fresh[fresh.date == last]), int(gap.sum()))
        self.assertIn("backfill", note)
        i = new.index[(new.date == last) & (new.symbol == "GOLDGUINEA") & (new.volume_lots > 0)][0]
        for c in ("close", "high", "low", "rs_per_g"):
            new.loc[i, c] *= 10
        with self.assertRaises(SystemExit):
            du.check_update(held, new, last)

    def test_gaps_are_found_and_chased(self):
        old, new, last, day = base()
        self.assertEqual(len(du.lagging(new)), 0)
        part = new[~((new.date == day) & (new.symbol == "GOLDPETAL"))]
        lag = du.lagging(part)
        self.assertEqual(set(lag.symbol), {"GOLDPETAL"})
        self.assertTrue((lag.held_to == last).all())
        self.assertEqual(len(lag), new[(new.date == day) & (new.symbol == "GOLDPETAL")].shape[0])

    def test_an_expired_contract_is_not_a_gap(self):
        old = clean("dev")
        lag = du.lagging(old)
        self.assertFalse((lag.expiry_date < lag.held_to).any())
        done = old.groupby(["symbol", "expiry_date"]).date.max().reset_index()
        done = done[done.expiry_date < old.date.max() - pd.Timedelta(days=10)]
        self.assertFalse(lag.merge(done, on=["symbol", "expiry_date"]).shape[0])

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
        """Market views first, robustness on the exported daily series, then one more export and build"""
        self.assertLess(du.CHAIN.index("dashboard/export.py"), du.CHAIN.index("robustness.py"))
        src = inspect.getsource(du.main)
        self.assertLess(src.index("for s in CHAIN"), src.rindex('"dashboard/export.py"'))
        self.assertLess(src.rindex('"dashboard/export.py"'), src.rindex('"dashboard/build.py"'))


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

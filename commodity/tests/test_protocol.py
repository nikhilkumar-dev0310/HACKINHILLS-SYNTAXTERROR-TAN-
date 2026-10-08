"""The test protocol itself: rules frozen before the sealed data, sealed results never touched afterwards.

Each frozen file is pinned by its SHA-256 fingerprint. Editing a frozen rule, or re-running a sealed test
and overwriting its results, changes the fingerprint and fails this suite. The code is also checked to use
exactly the frozen values, so the rules on disk and the rules that ran cannot drift apart.

With full Git history (the Tests workflow checks out every commit), it also confirms from the history that
each frozen file was written once and never edited, and that every rule was committed before the sealed
results it governs.
"""
import hashlib
import json
import os
import subprocess
import unittest

import pandas as pd

import backtest as bt
import fairvalue as fv
import ingest
import strategy_c as sc
from _util import cases

# SHA-256 of each file as committed when it was frozen (see the commit named in each comment).
PINNED = {
    "results/frozen_params.json": "0af1f464092f38da6c8715e649b8c57baa7fb8713e54d1c8c15171653072aeb9",           # Strategy A rules
    "results/fairvalue_params.json": "6ece1dcd8f11e89345effd8c8b94fd7978edf36128ce1d798fa8bf7008e8ee58",         # Strategy B rules, 045ab2b
    "results/strategy_c_params.json": "cfc9de75fa022a7880c8e320003602882f126452cb3e8f5bc825ca91f88229af",        # Strategy C rules, a984901
    "results/method_choice.json": "ef9f674b45379d38ff9f19f3995ce2702736dbb8dae3050eb7c1e956c3787898",
    "results/sealed_run_done.json": "91f13fe403e4959aef10480424dd8c2dd681faa5c3da7aa5e237a4ac4f13202e",          # sealed run, 6df3bbd
    "results/sealed_summary.csv": "d067ba58fe6dec9910be21336d06f328b08f1872cc906a33dec500d584aa24d1",
    "results/sealed_trades.csv": "7097e7c6429638d9da95e10c777b53ad549cc83afe13d9878975e068ee4bc764",
    "results/holdout_trades.csv": "76b71a74ed26049ee5c82374f0e88649fd493318fb1ee6e0d954182bfe6fbe9f",
    "results/fairvalue_holdout_trades.csv": "5ac21128b013d3b89960f730b8eb68468cd3551c65432048d5c90b832e66baae",
}
# rules file -> the sealed results it governs (the rule must be committed first)
GOVERNS = {
    "results/frozen_params.json": "results/holdout_trades.csv",
    "results/fairvalue_params.json": "results/fairvalue_holdout_trades.csv",
    "results/strategy_c_params.json": "results/sealed_trades.csv",
}


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def full_history():
    return git("rev-parse", "--is-shallow-repository") == "false"


def js(path):
    with open(path) as f:
        return json.load(f)


@cases(sorted(PINNED))
class Pinned(unittest.TestCase):
    def check_fingerprint_unchanged(self, path):
        """The frozen file is byte for byte what was committed when it was frozen"""
        self.assertEqual(sha(path), PINNED[path], f"{path} changed after it was frozen")

    def check_written_once_in_git(self, path):
        """Git history shows the file was committed once and never edited"""
        if not full_history():
            self.skipTest("shallow checkout: no history to read")
        commits = git("log", "--format=%H", "--", path).split()
        self.assertEqual(len(commits), 1, f"{path} has {len(commits)} commits")


@cases(sorted(GOVERNS))
class Order(unittest.TestCase):
    def check_rule_committed_before_its_sealed_results(self, rules):
        """The rules were in Git before the sealed results they govern"""
        if not full_history():
            self.skipTest("shallow checkout: no history to read")
        t_rule = int(git("log", "-1", "--format=%ct", "--", rules))
        t_res = int(git("log", "-1", "--format=%ct", "--", GOVERNS[rules]))
        self.assertLessEqual(t_rule, t_res)


class CodeUsesTheFrozenRules(unittest.TestCase):
    def test_strategy_a_windows_and_size(self):
        p = js("results/frozen_params.json")
        self.assertEqual(bt.TRAIN_END, pd.Timestamp(p["train_end"]))
        self.assertEqual((bt.TEST_START, bt.TEST_END), tuple(map(pd.Timestamp, p["test"])))
        self.assertEqual(bt.POSITION_GRAMS, p["position_grams"])
        self.assertEqual(bt.EXIT_Z, p["exit_z"])
        self.assertEqual(bt.MIN_GRAMS_TRADED, p["min_grams_traded"])
        self.assertEqual((bt.DEFAULT["lookback"], bt.DEFAULT["entry_z"]), (p["lookback"], p["entry_z"]))

    def test_strategy_a_holdout_starts_after_its_test(self):
        self.assertGreater(bt.HOLDOUT_START, bt.TEST_END)
        self.assertGreater(bt.TEST_START, bt.TRAIN_END)

    def test_strategy_b_rules(self):
        p = js("results/fairvalue_params.json")
        self.assertEqual(fv.GRAMS, p["grams_per_leg"])
        self.assertEqual(fv.DEV_END, pd.Timestamp(p["dev_end"]))
        self.assertEqual((fv.HOLD_START, fv.HOLD_END), tuple(map(pd.Timestamp, p["holdout"])))
        self.assertEqual(fv.EXIT_BDAYS, p["exit_bdays"])
        self.assertEqual(fv.NO_ENTRY_BDAYS, p["no_entry_bdays"])
        self.assertEqual(fv.MIN_HISTORY, p["min_history_days"])
        self.assertEqual(sc.B_RULES["k"], p["k"])

    def test_strategy_b_holdout_starts_after_its_development_data(self):
        self.assertGreater(fv.HOLD_START, fv.DEV_END)

    def test_strategy_c_rules_match_the_sealed_run(self):
        p, done = js("results/strategy_c_params.json"), js("results/sealed_run_done.json")
        for k, v in done["rules_c"].items():
            self.assertEqual(p[k], v, k)

    def test_strategy_c_sealed_windows(self):
        p = js("results/strategy_c_params.json")
        self.assertEqual({k: tuple(v) for k, v in p["sealed_windows"].items()}, {k: tuple(v) for k, v in sc.TESTS.items()})

    def test_loader_and_strategy_c_agree_on_the_sealed_windows(self):
        self.assertEqual(sorted(tuple(w) for w in ingest.SEALED), sorted(tuple(w) for w in sc.TESTS.values()))

    def test_strategy_c_was_chosen_from_its_declared_grid(self):
        p = js("results/strategy_c_params.json")
        for k in ("ref", "k", "stress", "exit", "hold"):
            self.assertIn(p[k], sc.GRID[k], k)

    def test_c_was_selected_on_development_years_only(self):
        p = js("results/strategy_c_params.json")
        for y in p["dev_years"]:
            for a, b in p["sealed_windows"].values():
                self.assertFalse(int(a[:4]) <= y <= int(b[:4]), f"{y} is a sealed year")

    def test_development_windows_avoid_the_sealed_years(self):
        for a, b in sc.DEV_WINDOWS:
            for s0, s1 in sc.TESTS.values():
                self.assertTrue(pd.Timestamp(b) < pd.Timestamp(s0) or pd.Timestamp(a) > pd.Timestamp(s1), (a, b, s0, s1))

    def test_sealed_run_marker_exists(self):
        """strategy_c.py refuses a second sealed run while this marker exists"""
        self.assertTrue(os.path.exists("results/sealed_run_done.json"))
        self.assertTrue(js("results/sealed_run_done.json")["run_at"].startswith("2026-10-04"))

    def test_purity_is_the_same_in_every_module(self):
        self.assertEqual(ingest.PURITY, fv.PURITY)
        self.assertEqual(ingest.PURITY, sc.PURITY)
        self.assertEqual(ingest.QUOTE_GRAMS, fv.QUOTE_GRAMS)
        self.assertEqual(ingest.QUOTE_GRAMS, sc.QUOTE_GRAMS)


if __name__ == "__main__":
    unittest.main()

"""The six pair verdicts (pair_verdict.py): they reuse stored trades, add up to the published backtests, and follow the stated rule."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pair_verdict as pv  # noqa: E402

V = json.load(open("results/pair_verdicts.json"))
ROWS = {r["pair"]: r for r in V["rows"]}
DATA = json.load(open("dashboard/data.json"))


class PairVerdicts(unittest.TestCase):
    def test_all_six_pairs_once(self):
        self.assertEqual(sorted(ROWS), sorted(p for p, _, _ in pv.PAIRS))
        self.assertEqual(sorted(ROWS), sorted(p["pair"] for p in DATA["pairs"]))

    def test_verdict_follows_the_rule(self):
        for p, r in ROWS.items():
            with self.subTest(pair=p):
                self.assertEqual(r["verdict"], pv.verdict(r["trades"], r["lo"], r["net_ex_crash"]))
                self.assertIn(r["verdict"], {"EDGE", "CRASH ONLY", "NO EDGE", "UNTESTABLE"})

    def test_range_and_parts_consistent(self):
        for p, r in ROWS.items():
            if r["lo"] is not None:
                with self.subTest(pair=p):
                    self.assertLessEqual(r["lo"], r["hi"])
                    self.assertLessEqual(abs(r["net_crash"] + r["net_ex_crash"] - r["net"]), 1, msg="crash and non-crash parts must add up")

    def test_holdout_totals_match_published_backtests(self):
        b = sum(r["windows"].get("holdout", {}).get("net", 0) for r in V["rows"] if r["strategy"] == "B")
        a = sum(r["windows"].get("holdout", {}).get("net", 0) for r in V["rows"] if r["strategy"] == "A")
        b5 = next(x["net"] for x in DATA["backtests"]["B_hold"]["rows"] if x["slip"] == 5)
        a5 = next(x["net"] for x in DATA["backtests"]["A_hold"]["rows"] if x["slip"] == 5)
        self.assertLessEqual(abs(b - b5), 3)
        self.assertLessEqual(abs(a - a5), 3)

    def test_sealed_totals_match_published_sealed_run(self):
        for test in ("test3", "test2"):
            for st in ("A", "B"):
                got = sum(r["windows"].get(test, {}).get("net", 0) for r in V["rows"] if r["strategy"] == st)
                want = DATA["sealed"]["rows"]
                want = next(x["net"] for x in want if x["test"] == test and x["strategy"] == st and x["slip"] == 5)
                with self.subTest(test=test, strategy=st):
                    self.assertLessEqual(abs(got - want), 3)

    def test_retrained_strategy_left_out(self):
        t = pv.out_of_sample()
        self.assertEqual(set(t.strategy), {"A", "B"})

    def test_site_carries_the_same_verdicts(self):
        self.assertEqual(DATA["pair_verdicts"]["rows"], V["rows"])


if __name__ == "__main__":
    unittest.main()

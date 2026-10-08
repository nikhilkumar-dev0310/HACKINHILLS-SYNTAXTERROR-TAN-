"""The website's numbers: every figure in dashboard/data.json must match the files it was computed from.

The site never types a number in; it reads data.json. These tests recompute the headline figures from
the clean data and the result files, and check the built page itself (no NaN, no undefined, links that
resolve, every jargon word defined).
"""
import json
import math
import os
import re
import unittest

import numpy as np
import pandas as pd

from _util import SYMS, all_rows, cases, clean, result, site

S = site()
HTML = open("dashboard/index.html", encoding="utf-8").read()
APP = "".join(open(os.path.join("dashboard/app", f), encoding="utf-8").read() for f in os.listdir("dashboard/app") if f.endswith((".jsx", ".js")))


def walk(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, o


SECTIONS = [k for k in S if S[k] is not None]


@cases(SECTIONS)
class EachSection(unittest.TestCase):
    def check_numbers_are_finite(self, key):
        """No NaN or infinity anywhere in the section"""
        bad = [p for p, v in walk(S[key], key) if isinstance(v, float) and not math.isfinite(v)]
        self.assertEqual(bad, [])

    def check_not_empty(self, key):
        """Every section the site reads has content"""
        self.assertTrue(S[key] not in ([], {}, ""))


@cases(SYMS)
class EachQuote(unittest.TestCase):
    def check_quote_is_the_latest_close(self, sym):
        """The price card shows that contract's close on the last market day"""
        q = next(q for q in S["quotes"] if q["symbol"] == sym)
        d = clean("dev")
        last = d[(d.symbol == sym) & (d.date == pd.Timestamp(q["date"])) & (d.expiry_date == pd.Timestamp(q["expiry"]))]
        self.assertEqual(len(last), 1)
        self.assertAlmostEqual(q["close"], float(last.close.iloc[0]), places=2)
        self.assertEqual(pd.Timestamp(q["date"]), d.date.max())

    def check_price_series_ends_today(self, sym):
        """The overview price line ends on the last market day"""
        self.assertEqual(pd.Timestamp(S["prices"]["dates"][-1]), clean("dev").date.max())
        self.assertEqual(len(S["prices"][sym]), len(S["prices"]["dates"]))


class Headline(unittest.TestCase):
    def test_rows_and_contracts(self):
        """meta: the development file the analysis pages use; meta.all: every row held, 2003 to today"""
        d, a = clean("dev"), all_rows()
        self.assertEqual(S["meta"]["rows"], len(d))
        self.assertEqual(S["meta"]["contracts"], d.groupby(["symbol", "expiry_date"]).ngroups)
        self.assertEqual(S["meta"]["all"]["rows"], len(a))
        self.assertEqual(S["meta"]["all"]["contracts"], a.groupby(["symbol", "expiry_date"]).ngroups)

    def test_first_and_last_dates(self):
        d, a = clean("dev"), all_rows()
        self.assertEqual(pd.Timestamp(S["meta"]["first"]), d.date.min())
        self.assertEqual(pd.Timestamp(S["meta"]["last"]), d.date.max())
        self.assertEqual(pd.Timestamp(S["meta"]["all"]["first"]), a.date.min())

    def test_contract_calendar_lists_every_dev_contract(self):
        d = clean("dev")
        self.assertEqual(len(S["contracts"]), d.groupby(["symbol", "expiry_date"]).ngroups)

    def test_backtest_totals_equal_the_trade_logs(self):
        files = {"A_test": "test_trades.csv", "A_hold": "holdout_trades.csv", "B_dev": "fairvalue_dev_trades.csv", "B_hold": "fairvalue_holdout_trades.csv"}
        for key, f in files.items():
            with self.subTest(key=key):
                t = result(f)
                if "k" in t:
                    t = t[t.k == json.load(open("results/fairvalue_params.json"))["k"]]
                t5 = t[t.slip_bp == 5]
                self.assertEqual(len(S["trades"][key]), len(t5))

    def test_sealed_table_matches_the_sealed_summary(self):
        s = result("sealed_summary.csv")
        for r in S["sealed"]["rows"]:
            m = s[(s.test == r["test"]) & (s.strategy.str[0] == r["strategy"]) & (s.slip_bp == r["slip"])]
            self.assertEqual(len(m), 1, r)
            self.assertAlmostEqual(r["net"], float(m.net.iloc[0]), delta=1.0)
            self.assertEqual(r["trades"], int(m.trades.iloc[0]))

    def test_alert_history_matches_its_file(self):
        self.assertEqual(len(S["alerts"]["history"]), len(result("alerts_history.csv")))

    def test_signal_threshold_is_the_frozen_k(self):
        self.assertEqual(S["signals"]["threshold"], json.load(open("results/fairvalue_params.json"))["k"])

    def test_overfit_section_matches_its_file(self):
        if S.get("overfit") is None:
            self.skipTest("overfit.py not run")
        self.assertEqual(S["overfit"], json.load(open("results/overfit.json")))

    def test_attribution_parts_add_up(self):
        for r in S["attribution"]:
            self.assertAlmostEqual(r["gap_part"] + r["gold_part"], r["gross"], delta=1.0)

    def test_provenance_files_exist(self):
        have = set(os.listdir("raw_clean"))
        self.assertEqual([f["file"] for f in S["provenance"]["files"] if f["file"] not in have], [])


class BuiltPage(unittest.TestCase):
    def test_no_nan_or_undefined_in_the_page(self):
        body = HTML.split("<script", 1)[0]
        for w in ("NaN", "undefined", "Infinity"):
            self.assertNotIn(w, body)

    def test_data_is_embedded(self):
        self.assertIn('"meta"', HTML)
        self.assertGreater(len(HTML), 300_000)

    def test_link_preview_and_404_built(self):
        self.assertIn('property="og:image"', HTML)
        self.assertTrue(os.path.exists("dashboard/404.html"))
        self.assertTrue(os.path.exists("dashboard/og.png"))

    def test_vercel_build_script_copies_existing_files(self):
        sh = open("tools/vercel_build.sh").read()
        for src in re.findall(r"cp (commodity/\S+)", sh):
            self.assertTrue(os.path.exists(os.path.join("..", src)), src)

    def test_every_term_used_has_a_definition(self):
        lib = open("dashboard/app/lib.js", encoding="utf-8").read()
        gl = lib[lib.index("export const GLOSSARY"):]
        defined = set(re.findall(r"^\s+([a-z0-9_]+): \[", gl, re.M))
        used = set(re.findall(r'<Term k="([a-z0-9_]+)"', APP))
        self.assertEqual(sorted(used - defined), [])

    def test_every_source_file_named_on_the_site_exists(self):
        lib = open("dashboard/app/lib.js", encoding="utf-8").read()
        for f in re.findall(r'file: "([^"]+)"', lib):
            if "*" in f:
                continue
            self.assertTrue(os.path.exists(f), f)

    def test_no_hard_coded_rupee_figures_in_the_app_text(self):
        """Profit figures come from data.json; the code never types a rupee amount of five or more digits"""
        self.assertEqual(re.findall(r"₹\s?\d[\d,]{5,}", APP), [])


if __name__ == "__main__":
    unittest.main()

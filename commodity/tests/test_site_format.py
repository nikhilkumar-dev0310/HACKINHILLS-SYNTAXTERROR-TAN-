"""The site's own formatting helpers (dashboard/app/lib.js), run in Node with the real exported data.

Every rupee figure, date and pair name on the site goes through these functions, so each is checked on
known inputs: Indian digit grouping (₹1,90,340), a true minus sign, unambiguous dates, pair labels.
Skipped if Node is not installed.
"""
import json
import os
import shutil
import subprocess
import unittest

from _util import cases

NODE = shutil.which("node")
LIB = os.path.abspath("dashboard/app/lib.js")
DATA = os.path.abspath("dashboard/data.json")

CASES = {
    "inr_lakh_grouping": ("inr(190340)", "₹1,90,340"),
    "inr_crore_grouping": ("inr(12345678)", "₹1,23,45,678"),
    "inr_small": ("inr(999)", "₹999"),
    "inr_true_minus": ("inr(-48734)", "−₹48,734"),
    "inr_rounds": ("inr(12989.6)", "₹12,990"),
    "inr_decimals": ("inr(14965.94, 1)", "₹14,965.9"),
    "inr_zero": ("inr(0)", "₹0"),
    "sgn_plus": ("sgn(2.25, 1, ' bp')", "+2.3 bp"),
    "sgn_minus": ("sgn(-0.25, 2, 'σ')", "−0.25σ"),
    "sgn_zero_has_no_sign": ("sgn(0, 1)", "0.0"),
    "fdate_day_month_year": ("fdate('2026-01-05')", "5 Jan 2026"),
    "fdate_end_of_year": ("fdate('2019-12-31')", "31 Dec 2019"),
    "fdate_leap_day": ("fdate('2024-02-29')", "29 Feb 2024"),
    "fmon_short": ("fmon('2025-08-14')", "Aug 25"),
    "mm_true_minus": ("mm(-3)", "−3"),
    "mm_positive_unchanged": ("mm(7)", "7"),
    "slug_plain": ("slug('What makes Parity different')", "what-makes-parity-different"),
    "slug_trims_symbols": ("slug('  ₹ per gram (pure) ')", "per-gram-pure"),
    "pname_pair": ("pname('GUINEA-PETAL')", "GOLDGUINEA − GOLDPETAL"),
    "r2_rounds": ("r2(1.23456)", 1.23),
    "r2_nan_is_null": ("r2(NaN)", None),
}


def run(expr):
    js = f"""
const data = JSON.parse(require('fs').readFileSync({json.dumps(DATA)}, 'utf8'));
globalThis.window = {{ __PARITY_DATA__: data, matchMedia: () => ({{ matches: false }}) }};
globalThis.matchMedia = globalThis.window.matchMedia;
import({json.dumps('file://' + LIB)}).then(m => {{
  with (m) {{ process.stdout.write(JSON.stringify({expr})); }}
}}).catch(e => {{ console.error(e); process.exit(1); }});
"""
    r = subprocess.run([NODE, "-e", js], capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise AssertionError(r.stderr[-800:])
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "node not installed")
@cases(sorted(CASES))
class EachFormat(unittest.TestCase):
    def check_formats_as_expected(self, key):
        """A formatting helper gives the exact text the site shows"""
        expr, want = CASES[key]
        self.assertEqual(run(expr), want)


@unittest.skipUnless(NODE, "node not installed")
class LibraryLoads(unittest.TestCase):
    def test_pairs_and_sources_load_from_the_data(self):
        got = run("({pairs: Object.keys(P).length, views: VIEWS.length, src: Object.keys(SRC).length})")
        self.assertEqual(got["pairs"], len(json.load(open(DATA))["pairs"]))
        self.assertEqual(got["views"], 8)
        self.assertGreater(got["src"], 10)


if __name__ == "__main__":
    unittest.main()

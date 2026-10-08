"""The demo video says only what the data says: every number in its subtitles is checked.

presentation/round2/Parity_demo.srt holds the video's captions word for word. Results that never change
(the sealed holdout, the crash split, the overfitting check) must match exactly; counts that only grow
(automated tests, years of data, contracts) must not overstate today's figure.
"""
import json
import os
import re
import unittest

from _util import all_rows, site

SRT = "presentation/round2/Parity_demo.srt"
TEXT = open(SRT, encoding="utf-8").read() if os.path.exists(SRT) else ""
CAPS = [" ".join(b.splitlines()[2:]) for b in TEXT.strip().split("\n\n") if b.strip()]   # SRT: index, times, text
FLAT = " ".join(CAPS)
D = site()


def inr_in(v):
    s = str(abs(round(v))); h, t = s[:-3], s[-3:]
    while len(h) > 2: t = h[-2:] + "," + t; h = h[:-2]
    return "₹" + (h + "," + t if h else t)


A = [t for t in D["trades"]["A_hold"] if t["ok_tender"]]
JAN = [t["net5"] for t in A if t["entry"].startswith("2026-01")]


@unittest.skipUnless(TEXT, "no subtitles yet")
class Subtitles(unittest.TestCase):
    def test_hook_profit_is_the_sealed_holdout_at_5_bp(self):
        self.assertIn(f"{inr_in(sum(t['net5'] for t in A))} profit, on a year our rules never saw", FLAT)

    def test_crash_month_split(self):
        rest = sum(t["net5"] for t in A) - sum(JAN)
        self.assertIn(f"January 2026 alone made {inr_in(sum(JAN))}", FLAT)
        self.assertIn(f"The other {len(A) - len(JAN)} trades lost {inr_in(-rest)}", FLAT)
        self.assertLess(rest, 0)

    def test_overfitting_figure(self):
        o = D["overfit"]["pbo"]
        self.assertIn(f"Best of {o['settings']} settings? A {round(100 * o['value'])}% chance", FLAT)

    def test_break_even_claim(self):
        be = max(r["breakeven_bp"] for r in D["robustness"]["breakeven"]["rows"] if r["breakeven_bp"] is not None)
        m = re.search(r"Past (\d+) bp of slippage, no result survives", FLAT)
        self.assertTrue(m)
        self.assertGreaterEqual(int(m.group(1)), be - 0.5)

    def test_cost_line_today(self):
        m = re.search(r"The biggest gap is (\d+(?:\.\d+)?) bp\. A trade needs (\d+(?:\.\d+)?)", FLAT)
        self.assertTrue(m)
        self.assertLess(float(m.group(1)), float(m.group(2)))

    def test_counts_never_overstate(self):
        tests = int(re.search(r"Checked by ([\d,]+) automated tests", FLAT).group(1).replace(",", ""))
        self.assertLessEqual(tests, D["tests"]["tests"])
        years = int(re.search(r"(\d+) years of official MCX data", FLAT).group(1))
        a = all_rows()
        self.assertLessEqual(years, a.date.max().year - a.date.min().year)
        contracts = int(re.search(r"official MCX data\. (\d+) contracts", FLAT).group(1))
        self.assertLessEqual(contracts, a.groupby(["symbol", "expiry_date"]).ngroups)

    def test_headline_share_that_disappears(self):
        m = re.search(r"Up to (\d+)% of the headline disappears", FLAT)
        self.assertTrue(m)
        self.assertTrue(0 < int(m.group(1)) < 100)

    def test_captions_are_short(self):
        """Key words, not paragraphs: no caption longer than 80 characters"""
        self.assertTrue(CAPS)
        self.assertLessEqual(max(map(len, CAPS)), 80)


if __name__ == "__main__":
    unittest.main()

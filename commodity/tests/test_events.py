"""The dated event notes on the site's charts (EVENTS in dashboard/app/lib.js), checked against the MCX data.

A note that states a price move ("GOLDM −5.5%", "settles 12% lower") must match the MCX settlement
prices of that day, so no event note can drift from the data it annotates.
"""
import re
import unittest

import pandas as pd

import robustness as rb
from _util import all_rows, cases

LIB = open("dashboard/app/lib.js", encoding="utf-8").read()
BLOCK = re.search(r"export const EVENTS = \[(.*?)\n\];", LIB, re.S).group(1)
EVENTS = [dict(re.findall(r'(\w+): "((?:[^"\\]|\\.)*)"', line)) for line in BLOCK.strip().splitlines()]
D = all_rows()
LOT = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}


def day(date, sym):
    x = D[(D.date == pd.Timestamp(date)) & (D.symbol == sym) & ~D.no_trade].copy()
    x["chg"] = 100 * (x.close / x.prev_close - 1)
    x["kg"] = x.volume_lots * LOT[sym] / 1000
    return x.sort_values("expiry_date")


@cases([e["date"] for e in EVENTS])
class EachEvent(unittest.TestCase):
    def e(self, date):
        return next(x for x in EVENTS if x["date"] == date)

    def check_has_tag_text_and_source(self, date):
        """Every note has a short tag, a sentence and a source"""
        e = self.e(date)
        self.assertTrue(0 < len(e["tag"]) <= 18, e["tag"])
        self.assertTrue(e["text"].endswith("."))
        self.assertTrue(len(e["src"]) > 5)

    def check_falls_inside_the_data(self, date):
        """Every note sits inside the dates the site covers"""
        dev = D[D.date >= "2023-10-10"]
        self.assertTrue(dev.date.min() <= pd.Timestamp(date) <= dev.date.max())

    def check_stated_goldm_move_matches_mcx(self, date):
        """'GOLDM +5.5%' style claims match the most-traded GOLDM contract's settlement change that day"""
        m = re.search(r"GOLDM ([+−-])(\d+\.\d)%", self.e(date)["text"])
        if not m:
            return
        x = day(date, "GOLDM")
        top = x.loc[x.kg.idxmax()]
        want = float(m.group(2)) * (-1 if m.group(1) in "−-" else 1)
        self.assertAlmostEqual(top.chg, want, delta=0.06)

    def check_stated_limit_moves_match_mcx(self, date):
        """'settles 12% lower' style claims: every named contract's near month moved by that much"""
        t = self.e(date)["text"]
        m = re.search(r"small contract settle (\d+(?:\.\d)?)% lower", t)
        if not m:
            return
        pct = -float(m.group(1))
        for sym in ("GOLDTEN", "GOLDGUINEA", "GOLDPETAL"):
            x = day(date, sym)
            x = x[x.kg >= 1]
            self.assertAlmostEqual(x.iloc[0].chg, pct, delta=0.06, msg=sym)
        if "most-traded contract settles" in t:
            g = day(date, "GOLDM")
            want = -float(re.search(r"most-traded contract settles (\d+\.\d)% lower", t).group(1))
            self.assertAlmostEqual(g.loc[g.kg.idxmax()].chg, want, delta=0.06)

    def check_weekend_sessions_are_in_the_data(self, date):
        """A note about a special Saturday or Sunday session has MCX rows on that day"""
        if pd.Timestamp(date).dayofweek >= 5:
            self.assertTrue((D.date == pd.Timestamp(date)).any())


class Collection(unittest.TestCase):
    def test_in_date_order_and_unique(self):
        dates = [e["date"] for e in EVENTS]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(len(dates), len(set(dates)))

    def test_robustness_events_are_all_on_the_site(self):
        site_dates = {e["date"] for e in EVENTS}
        for d, _ in rb.EVENTS:
            self.assertIn(d, site_dates)

    def test_six_expiries_from_september_2025(self):
        """The 'six expiries' note: listed expiries per small contract rise from at most 4 to at least 6 that month"""
        d = D[D.symbol.isin(["GOLDGUINEA", "GOLDPETAL"])]
        n = d.groupby([d.date.dt.to_period("M"), "symbol"]).expiry_date.nunique().unstack()
        self.assertTrue((n.loc["2025-06":"2025-08"] <= 4).all().all())
        self.assertTrue((n.loc["2025-10":"2026-03"] >= 6).all().all())


if __name__ == "__main__":
    unittest.main()

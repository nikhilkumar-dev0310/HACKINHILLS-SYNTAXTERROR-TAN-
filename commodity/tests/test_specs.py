"""Contract specifications: every module must agree on lot size, quote size and purity.

The same facts are typed in several scripts (each script stays runnable on its own). These tests make
sure no copy drifts: one wrong lot size would silently change trade sizes, costs or liquidity filters.
"""
import unittest

from _util import SYMS, cases

import accuracy
import attribution
import backtest
import fairvalue
import ingest
import lifecycle
import strategy_c
import testbed

LOT = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}           # grams per lot (MCX)
QUOTE = {"GOLDM": 10, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}         # grams per quoted price
PURITY = {"GOLDM": 0.995, "GOLDTEN": 0.999, "GOLDGUINEA": 0.999, "GOLDPETAL": 0.999}
LOT_TABLES = {"accuracy": accuracy.LOT_GRAMS, "attribution": attribution.LOT, "fairvalue": fairvalue.LOT_GRAMS,
              "lifecycle": lifecycle.LOT, "testbed": testbed.LOT_GRAMS}


@cases(SYMS)
class SpecsPerContract(unittest.TestCase):
    def check_lot_size_agrees_everywhere(self, s):
        """Lot size in grams is the same in every module"""
        for mod, table in LOT_TABLES.items():
            self.assertEqual(table[s], LOT[s], mod)

    def check_quote_grams(self, s):
        """Price is quoted per the MCX unit (10 g, 8 g or 1 g)"""
        self.assertEqual(ingest.QUOTE_GRAMS[s], QUOTE[s])
        self.assertEqual(fairvalue.QUOTE_GRAMS[s], QUOTE[s])
        self.assertEqual(strategy_c.QUOTE_GRAMS[s], QUOTE[s])

    def check_purity(self, s):
        """Fineness used to convert to pure gold"""
        self.assertEqual(ingest.PURITY[s], PURITY[s])
        self.assertEqual(fairvalue.PURITY[s], PURITY[s])

    def check_lot_is_whole_multiple_of_quote_or_vice_versa(self, s):
        """A lot is a whole number of quote units, or the quote unit a whole number of lots"""
        a, b = LOT[s], QUOTE[s]
        self.assertTrue(a % b == 0 or b % a == 0)

    def check_listed_in_pairs_universe(self, s):
        """Every contract type except GOLDM can be paired same-expiry (GOLDM is the fair-price anchor)"""
        if s == "GOLDM":
            self.assertNotIn(s, backtest.LOT_GRAMS)
        else:
            self.assertEqual(backtest.LOT_GRAMS[s], LOT[s])


class PositionSizes(unittest.TestCase):
    def test_pairs_position_is_whole_lots_of_every_leg(self):
        for s, g in backtest.LOT_GRAMS.items():
            self.assertEqual(backtest.POSITION_GRAMS % g, 0, s)

    def test_fair_price_position_is_whole_lots_of_every_leg(self):
        for s, g in fairvalue.LOT_GRAMS.items():
            self.assertEqual(fairvalue.GRAMS % g, 0, s)

    def test_goldm_is_the_least_pure(self):
        self.assertLess(PURITY["GOLDM"], min(v for k, v in PURITY.items() if k != "GOLDM"))

    def test_symbol_universe(self):
        self.assertEqual(ingest.SYMBOLS, set(SYMS))


if __name__ == "__main__":
    unittest.main()

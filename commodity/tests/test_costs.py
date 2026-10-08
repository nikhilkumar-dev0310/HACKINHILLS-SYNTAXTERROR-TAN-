"""Transaction costs: every fee and tax charged on the right side, at the right rate, on the right base.

A worked example is computed by hand from the published rates and must match the code to the paisa.
"""
import unittest

import backtest as bt
import fairvalue as fv
from _util import cases

PRICES = [1_500.0, 6_000.0, 10_000.0, 15_000.0]       # Rs per gram, from 2004 levels to 2026 levels
SLIPS = [0, 2.5, 5, 10]


def by_hand(price, grams, side, slip):
    turnover = price * grams
    brokerage = min(20.0, 0.0003 * turnover)               # Rs 20 per order, capped at 0.03%
    exchange = turnover * 2.10 / 1e5                       # MCX: Rs 2.10 per lakh
    sebi = turnover * 10 / 1e7                             # Rs 10 per crore
    gst = 0.18 * (brokerage + exchange + sebi)
    ctt = turnover * 0.0001 if side == "sell" else 0.0     # CTT 0.01%, sell side only
    stamp = turnover * 0.00002 if side == "buy" else 0.0   # stamp duty 0.002%, buy side only
    return brokerage + exchange + sebi + gst + ctt + stamp + turnover * slip / 1e4


@cases([(p, side, s) for p in PRICES for side in ("buy", "sell") for s in SLIPS], name=lambda c: f"{int(c[0])}_{c[1]}_{c[2]}bp")
class CostByHand(unittest.TestCase):
    def check_pairs_leg_cost_matches_hand_calculation(self, c):
        """Pairs strategy: 40 g leg cost equals the published schedule computed by hand"""
        p, side, s = c
        self.assertAlmostEqual(bt.leg_cost(p, side, s), by_hand(p, bt.POSITION_GRAMS, side, s), places=6)

    def check_fair_price_leg_cost_matches_hand_calculation(self, c):
        """Fair-price strategy: 200 g leg cost equals the published schedule computed by hand"""
        p, side, s = c
        self.assertAlmostEqual(fv.leg_cost(p, side, s), by_hand(p, fv.GRAMS, side, s), places=6)


@cases(PRICES, name=lambda p: int(p))
class CostShape(unittest.TestCase):
    def check_costs_are_positive(self, p):
        """No leg is ever free"""
        for side in ("buy", "sell"):
            self.assertGreater(bt.leg_cost(p, side, 0), 0)
            self.assertGreater(fv.leg_cost(p, side, 0), 0)

    def check_sell_side_pays_more_than_buy_side(self, p):
        """CTT (0.01%, sell) is larger than stamp duty (0.002%, buy)"""
        self.assertGreater(bt.leg_cost(p, "sell", 0), bt.leg_cost(p, "buy", 0))

    def check_slippage_adds_exactly_its_bp_of_turnover(self, p):
        """Each bp of slippage adds one hundredth of a percent of turnover"""
        for side in ("buy", "sell"):
            d = fv.leg_cost(p, side, 7) - fv.leg_cost(p, side, 0)
            self.assertAlmostEqual(d, p * fv.GRAMS * 7 / 1e4, places=6)

    def check_round_trip_cost_in_a_sane_band(self, p):
        """A round trip on both legs costs 3 to 10 bp of one leg's value before slippage"""
        rt = 2 * (fv.leg_cost(p, "buy", 0) + fv.leg_cost(p, "sell", 0))
        bp = rt / (p * fv.GRAMS) * 1e4
        self.assertTrue(3 < bp < 10, bp)

    def check_brokerage_cap_binds_only_on_small_orders(self, p):
        """The Rs 20 flat brokerage applies once 0.03% of turnover exceeds it"""
        turnover = p * fv.GRAMS
        expect = min(20.0, 0.0003 * turnover)
        no_tax = fv.leg_cost(p, "buy", 0) - turnover * (bt.EXCHANGE_FEE + bt.SEBI_FEE) * (1 + bt.GST) - turnover * bt.STAMP_BUY
        self.assertAlmostEqual(no_tax, expect * (1 + bt.GST), places=6)


class Rates(unittest.TestCase):
    def test_published_rates(self):
        self.assertAlmostEqual(bt.EXCHANGE_FEE, 2.10 / 1e5)
        self.assertAlmostEqual(bt.CTT_SELL, 0.0001)
        self.assertAlmostEqual(bt.STAMP_BUY, 0.00002)
        self.assertAlmostEqual(bt.SEBI_FEE, 1e-6)
        self.assertAlmostEqual(bt.GST, 0.18)

    def test_gst_is_not_charged_on_taxes(self):
        p, g = 10_000.0, bt.POSITION_GRAMS
        with_ctt = bt.leg_cost(p, "sell", 0) - bt.leg_cost(p, "buy", 0)
        self.assertAlmostEqual(with_ctt, p * g * (bt.CTT_SELL - bt.STAMP_BUY), places=6)

    def test_slippage_grid_includes_perfect_realistic_and_poor(self):
        self.assertEqual(bt.SLIPPAGE_BP, [0, 5, 10])


if __name__ == "__main__":
    unittest.main()

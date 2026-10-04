"""Unit tests for the strategy code: costs, no look-ahead, forced exits, the stress filter and the sealed guard.

    python -m unittest discover -s tests -v

Synthetic prices only, except the last two tests, which read the stored results and confirm that the
recorded runs respect the contract calendar and that the sealed windows cannot be run a second time.
"""
import os
import sys
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.chdir(HERE)

import backtest as bt          # noqa: E402
import fairvalue as fv         # noqa: E402
import strategy_c as sc        # noqa: E402


def pair_frame(spread_bp, start="2025-01-01", expiry=None, price=10_000.0):
    """A synthetic two-leg pair on consecutive calendar days, in the shape backtest.load_pairs() builds."""
    idx = pd.date_range(start, periods=len(spread_bp), freq="D")
    expiry = pd.Timestamp(expiry) if expiry else idx[-1]
    b = np.full(len(idx), price)
    a = b * np.exp(np.asarray(spread_bp, float) / 1e4)
    p = pd.DataFrame({"a": a, "b": b, "liq_ok": True, "dte": (expiry - idx).days}, index=idx)
    p["spread_bp"] = 1e4 * np.log(p.a / p.b)
    return p


class Costs(unittest.TestCase):
    def test_sell_pays_ctt_buy_pays_stamp(self):
        px = 10_000.0
        turnover = px * bt.POSITION_GRAMS
        diff = bt.leg_cost(px, "sell", 0) - bt.leg_cost(px, "buy", 0)
        self.assertAlmostEqual(diff, turnover * (bt.CTT_SELL - bt.STAMP_BUY), places=6)

    def test_slippage_is_linear(self):
        px = 10_000.0
        turnover = px * bt.POSITION_GRAMS
        for side in ("buy", "sell"):
            c0, c5, c10 = (bt.leg_cost(px, side, s) for s in (0, 5, 10))
            self.assertAlmostEqual(c5 - c0, turnover * 5 / 1e4, places=6)
            self.assertAlmostEqual(c10 - c5, c5 - c0, places=6)

    def test_fairvalue_costs_match_backtest_rates(self):
        px = 10_000.0
        ratio = fv.GRAMS / bt.POSITION_GRAMS
        # brokerage is capped at a flat Rs 20 per order, so compare only the turnover-proportional part
        prop = lambda m, g: m.leg_cost(px, "sell", 5) - min(bt.BROKERAGE_FLAT, bt.BROKERAGE_CAP * px * g) * (1 + bt.GST)
        self.assertAlmostEqual(prop(fv, fv.GRAMS), prop(bt, bt.POSITION_GRAMS) * ratio, places=4)


class NoLookAhead(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.spread = list(rng.normal(0, 5, 60))

    def test_signal_on_day_t_fills_on_day_t_plus_1(self):
        s = [0.0, 2, -2, 1, -1, 0, 2, -2, 1, -1, 0, 2, -2, 1, -1] + [60.0] + [0.0] * 30
        p = pair_frame(s)
        tr = bt.run_pair(p, lookback=10, entry_z=2.0, start=p.index[0], end=p.index[-1], slip_bp=0)
        self.assertTrue(tr, "the spike should trigger a trade")
        spike_day = p.index[15].date()
        self.assertEqual(tr[0]["entry"], (p.index[15] + pd.Timedelta(days=1)).date())
        self.assertGreater(tr[0]["entry"], spike_day)

    def test_future_prices_do_not_change_past_trades(self):
        p = pair_frame(self.spread)
        cut = p.index[40]
        full = bt.run_pair(p, 10, 1.5, p.index[0], p.index[-1], 0)
        q = p.copy()
        q.loc[q.index > cut, "a"] *= 1.05                  # rewrite the future
        q["spread_bp"] = 1e4 * np.log(q.a / q.b)
        alt = bt.run_pair(q, 10, 1.5, q.index[0], q.index[-1], 0)
        done = lambda trades: [t for t in trades if pd.Timestamp(t["exit"]) < cut]
        self.assertEqual(done(full), done(alt))

    def test_stress_filter_uses_only_the_past(self):
        idx = pd.bdate_range("2023-01-02", periods=400)
        rng = np.random.default_rng(3)
        close = 60_000 * np.exp(np.cumsum(rng.normal(0, 0.008, len(idx))))
        d = pd.DataFrame({"date": idx, "symbol": "GOLDM", "no_trade": False, "close": close,
                          "prev_close": np.r_[close[0], close[:-1]], "grams": 1e6})
        base = sc.stress_pct(d)
        d2 = d.copy()
        d2.loc[d2.index >= 300, "close"] *= 1.10            # a shock after day 300
        d2["prev_close"] = np.r_[d2.close.iloc[0], d2.close.values[:-1]]
        shocked = sc.stress_pct(d2)
        before = idx[299]
        pd.testing.assert_series_equal(base[:before], shocked[:before])


class ContractCalendar(unittest.TestCase):
    def test_pairs_exit_before_the_force_exit_day(self):
        p = pair_frame(list(np.random.default_rng(11).normal(0, 6, 45)))
        for t in bt.run_pair(p, 5, 1.0, p.index[0], p.index[-1], 0):
            dte = (p.index[-1] - pd.Timestamp(t["exit"])).days
            self.assertGreaterEqual(dte, bt.FORCE_EXIT_DAYS, t)

    def test_no_new_entry_close_to_expiry(self):
        p = pair_frame(list(np.random.default_rng(5).normal(0, 6, 45)))
        for t in bt.run_pair(p, 5, 1.0, p.index[0], p.index[-1], 0):
            dte_entry = (p.index[-1] - pd.Timestamp(t["entry"])).days
            # decided at a close with dte > NO_ENTRY_DAYS, filled one day later
            self.assertGreaterEqual(dte_entry, bt.NO_ENTRY_DAYS)

    def test_recorded_runs_respect_the_tender_rules(self):
        s = pd.read_csv(os.path.join(bt.RES, "lifecycle_summary.csv")).set_index("run")
        for run in ("B_dev", "B_hold"):
            self.assertEqual(s.at[run, "outside_tender"], s.at[run, "trades"], run)
        for run in s.index:
            self.assertEqual(s.at[run, "inside_life"], s.at[run, "trades"], run)
            self.assertGreaterEqual(s.at[run, "outside_exchange_tender"], s.at[run, "outside_tender"], run)


class SealedGuard(unittest.TestCase):
    def test_sealed_windows_cannot_run_twice(self):
        if not os.path.exists(os.path.join(bt.RES, "sealed_run_done.json")):
            self.skipTest("sealed run not done in this checkout")
        with self.assertRaises(SystemExit):
            sc.sealed()


if __name__ == "__main__":
    unittest.main()

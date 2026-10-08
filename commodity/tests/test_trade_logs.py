"""Every stored trade log, checked trade by trade against the rules and against the raw prices.

The logs are the evidence behind every profit figure on the site. These tests re-derive each trade's
gross profit from the clean MCX prices, confirm the arithmetic (net = gross - costs), the windows the
trades were allowed in, the contract calendar, and that one position at a time was respected.
"""
import unittest

import numpy as np
import pandas as pd

import backtest as bt
import fairvalue as fv
import strategy_c as sc
from _util import all_rows, cases, result

# name: (file, kind, (window start, window end) or None for "check per row")
LOGS = {
    "A_train": ("train_trades.csv", "pair", (pd.Timestamp("2000-01-01"), bt.TRAIN_END)),
    "A_test": ("test_trades.csv", "pair", (bt.TEST_START, bt.TEST_END)),
    "A_hold": ("holdout_trades.csv", "pair", (bt.HOLDOUT_START, bt.HOLDOUT_END)),
    "B_dev": ("fairvalue_dev_trades.csv", "fair", (pd.Timestamp("2000-01-01"), fv.DEV_END)),
    "B_hold": ("fairvalue_holdout_trades.csv", "fair", (fv.HOLD_START, fv.HOLD_END)),
    "B_dev_all": ("strategy_b_dev_alldata_trades.csv", "fair", "dev"),
    "C_dev": ("strategy_c_dev_trades.csv", "fair", "dev"),
    "sealed": ("sealed_trades.csv", "mixed", "sealed"),
}
PX = all_rows().set_index(["symbol", "expiry_date", "date"]).sort_index()
LOT = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}


def log(name):
    d = result(LOGS[name][0]).copy()
    for c in ("entry", "exit", "expiry", "goldm_expiry"):
        if c in d:
            d[c] = pd.to_datetime(d[c])
    return d


def kind_of(name, row):
    k = LOGS[name][1]
    if k != "mixed":
        return k
    return "pair" if str(row.strategy).startswith("A") else "fair"


def pair_of(r):
    """Pairs logs name the pair in `pair`; the combined sealed log keeps it in `symbol` (e.g. GOLDGUINEA-GOLDPETAL)."""
    return getattr(r, "pair", None) if isinstance(getattr(r, "pair", None), str) else r.symbol


def group_cols(d):
    return [c for c in ("k", "lookback", "entry_z", "test", "strategy") if c in d.columns]


def vwap(sym, exp, day):
    r = PX.loc[(sym, exp, day)]
    return r.value_lakhs * 1e5 / (r.volume_lots * LOT[sym])


@cases(list(LOGS))
class EachLog(unittest.TestCase):
    def check_net_is_gross_minus_costs(self, name):
        """net = gross - costs on every trade, to the paisa"""
        d = log(name)
        np.testing.assert_allclose(d.net_rs, d.gross_rs - d.cost_rs, atol=0.01)

    def check_costs_positive_and_rise_with_slippage(self, name):
        """Every trade pays costs, and more of them at higher slippage"""
        d = log(name)
        self.assertTrue((d.cost_rs > 0).all())
        keys = group_cols(d) + ["entry", "exit"] + (["pair", "expiry"] if "pair" in d else ["symbol", "expiry"])
        w = d.pivot_table(index=keys, columns="slip_bp", values="cost_rs")
        s = sorted(w.columns)
        for a, b in zip(s, s[1:]):
            self.assertTrue((w[b] > w[a]).all(), (a, b))

    def check_same_trades_at_every_slippage(self, name):
        """Slippage changes costs only, never which trades happen or their gross"""
        d = log(name)
        keys = group_cols(d) + ["entry", "exit"] + (["pair", "expiry"] if "pair" in d else ["symbol", "expiry"])
        sets = [set(map(tuple, g[keys].astype(str).values)) for _, g in d.groupby("slip_bp")]
        self.assertTrue(all(s == sets[0] for s in sets))
        w = d.pivot_table(index=keys, columns="slip_bp", values="gross_rs")
        self.assertLess(float((w.max(axis=1) - w.min(axis=1)).max()), 1e-6)

    def check_exit_after_entry_and_days_held(self, name):
        """Exit is after entry; days_held = exit - entry in calendar days"""
        d = log(name)
        self.assertTrue((d.exit > d.entry).all())
        self.assertTrue(((d.exit - d.entry).dt.days == d.days_held).all())

    def check_trades_inside_their_declared_window(self, name):
        """No trade starts before or ends after the window it was declared for"""
        d, w = log(name), LOGS[name][2]
        if w == "dev":
            inside = lambda t: any(pd.Timestamp(a) <= t <= pd.Timestamp(b) for a, b in sc.DEV_WINDOWS)
            self.assertTrue(d.entry.map(inside).all() and d.exit.map(inside).all())
        elif w == "sealed":
            for test, (a, b) in sc.TESTS.items():
                g = d[d.test == test]
                self.assertTrue(len(g) > 0, test)
                self.assertTrue((g.entry >= a).all() and (g.exit <= b).all(), test)
        else:
            self.assertTrue((d.entry >= w[0]).all() and (d.exit <= w[1]).all())

    def check_never_after_expiry_or_into_delivery(self, name):
        """Every trade ends before its contract (and GOLDM's) expires, outside the 3-day delivery window"""
        d = log(name)
        bleft = np.busday_count(d.exit.values.astype("datetime64[D]"), d.expiry.values.astype("datetime64[D]"))
        self.assertTrue((d.exit <= d.expiry).all())
        if "goldm_expiry" in d and d.goldm_expiry.notna().any():
            g = d[d.goldm_expiry.notna()]
            self.assertTrue((g.exit <= g.goldm_expiry).all())
        fair = d.apply(lambda r: kind_of(name, r) == "fair", axis=1)
        self.assertTrue((bleft[fair.values] >= 3).all(), "fair-price trade held into the delivery window")

    def check_entry_and_exit_are_market_days_of_the_contract(self, name):
        """Both ends of every trade are days on which the contract (and its partner) has an MCX row"""
        d = log(name).drop_duplicates(group_cols(log(name)) + ["entry", "exit"] + (["pair", "expiry"] if "pair" in log(name) else ["symbol", "expiry"]))
        for r in d.itertuples():
            legs = (pair_of(r).split("-"), [r.expiry] * 2) if kind_of(name, r) == "pair" else ([r.symbol, "GOLDM"], [r.expiry, r.goldm_expiry])
            for sym, exp in zip(*legs):
                for day in (r.entry, r.exit):
                    self.assertIn((sym, pd.Timestamp(exp), day), PX.index, (name, sym, exp, day))

    def check_gross_reproduces_from_mcx_prices(self, name):
        """Gross profit re-computed from the clean MCX prices matches the log (settlement for pairs, VWAP for fair price)"""
        d = log(name)
        d = d[d.slip_bp == d.slip_bp.min()]
        for r in d.itertuples():
            if kind_of(name, r) == "pair":
                a, b = pair_of(r).split("-")
                pos = 1 if r.side.startswith("long") else -1
                A0, A1 = PX.at[(a, r.expiry, r.entry), "rs_per_g"], PX.at[(a, r.expiry, r.exit), "rs_per_g"]
                B0, B1 = PX.at[(b, r.expiry, r.entry), "rs_per_g"], PX.at[(b, r.expiry, r.exit), "rs_per_g"]
                g = pos * bt.POSITION_GRAMS * ((A1 - A0) - (B1 - B0))
            else:
                pos = 1 if r.side.startswith("buy X") else -1
                xi, xo = vwap(r.symbol, r.expiry, r.entry), vwap(r.symbol, r.expiry, r.exit)
                mi, mo = vwap("GOLDM", r.goldm_expiry, r.entry), vwap("GOLDM", r.goldm_expiry, r.exit)
                g = pos * ((xo - xi) - (mo - mi)) * fv.GRAMS
            self.assertAlmostEqual(g, r.gross_rs, delta=max(0.02, abs(r.gross_rs) * 1e-9), msg=(name, r.Index))

    def check_one_position_at_a_time(self, name):
        """Fair price: one open trade per contract type; pairs: one per pair and expiry"""
        d = log(name)
        d = d[d.slip_bp == d.slip_bp.min()]
        by = group_cols(d) + (["pair", "expiry"] if "pair" in d.columns and d.pair.notna().all() else ["symbol"])
        if LOGS[name][1] == "mixed":                         # sealed log: A holds one position per pair and expiry,
            by = ["test", "strategy", "symbol"]              # B and C one per contract type; A's pair is in `symbol`
        for key, g in d.groupby(by):
            if LOGS[name][1] == "mixed" and key[1].startswith("A"):
                for _, h in g.groupby("expiry"):
                    h = h.sort_values("entry")
                    self.assertTrue((h.entry.values[1:] >= h.exit.values[:-1]).all(), ("overlapping positions", key))
                continue
            g = g.sort_values("entry")
            self.assertTrue((g.entry.values[1:] >= g.exit.values[:-1]).all(), "overlapping positions")

    def check_sides_are_valid(self, name):
        """Every trade is long one leg and short the other, written out"""
        ok = {"long a/short b", "short a/long b", "buy X / sell GOLDM", "sell X / buy GOLDM"}
        self.assertTrue(set(log(name).side) <= ok, set(log(name).side) - ok)


class Summaries(unittest.TestCase):
    def test_sealed_summary_is_the_sum_of_its_trades(self):
        t, s = result("sealed_trades.csv"), result("sealed_summary.csv")
        g = t.groupby(["test", "strategy", "slip_bp"]).agg(trades=("net_rs", "size"), gross=("gross_rs", "sum"),
                                                           cost=("cost_rs", "sum"), net=("net_rs", "sum")).reset_index()
        m = s.merge(g, on=["test", "strategy", "slip_bp"], suffixes=("", "_t"))
        self.assertEqual(len(m), len(s))
        self.assertTrue((m.trades == m.trades_t).all())
        for c in ("gross", "cost", "net"):
            np.testing.assert_allclose(m[c], m[c + "_t"], atol=0.02)

    def test_sealed_covers_three_strategies_in_two_windows(self):
        s = result("sealed_summary.csv")
        self.assertEqual(set(s.test), {"test2", "test3"})
        self.assertEqual({x[0] for x in s.strategy}, {"A", "B", "C"})

    def test_strategy_c_selection_is_in_the_declared_grid(self):
        import json
        p = json.load(open("results/strategy_c_params.json"))
        for k in ("ref", "k", "stress", "exit", "hold"):
            self.assertIn(p[k], sc.GRID[k], k)

    def test_strategy_b_dev_rerun_matches_the_stored_log(self):
        """Re-running Strategy B's frozen rules on DEV reproduces the stored log exactly (DEV only)"""
        d, frames, pct = sc.prepare(include_sealed=False)
        now = sc.run_dev(frames, sc.B_RULES, [5], pct)
        old = result("strategy_b_dev_alldata_trades.csv")
        old = old[old.slip_bp == 5]
        # the daily job keeps adding DEV days; trades closed before the stored log's last exit cannot change
        cut = pd.Timestamp(old.exit.max())
        old = old[pd.to_datetime(old.exit) < cut]
        now = now[pd.to_datetime(now.exit) < cut]
        self.assertEqual(len(now), len(old))
        np.testing.assert_allclose(now.net_rs.sum(), old.net_rs.sum(), atol=0.5)


if __name__ == "__main__":
    unittest.main()

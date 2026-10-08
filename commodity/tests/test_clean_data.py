"""The cleaned dataset, contract by contract: one test per check per contract, so a failure names the contract.

Covers all three clean files (DEV, pre-2016 history and the sealed windows), every contract MCX listed
for the four gold futures since Nov 2003, and keeps working as the daily job adds new days.
"""
import os
import unittest

import numpy as np
import pandas as pd

import ingest
from _util import SYMS, all_rows, cases, clean

LOT = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
D = all_rows().sort_values(["symbol", "expiry_date", "date"]).reset_index(drop=True)
GROUPS = {k: g for k, g in D.groupby(["symbol", "expiry_date"])}
KEYS = sorted(GROUPS, key=lambda k: (k[1], k[0]))
RAW = set(os.listdir("raw_clean"))
# Weekend sessions MCX held after Saturday trading ended in 2014: Budget days and Diwali Muhurat trading.
SPECIAL = {"2015-02-28", "2016-10-30", "2019-10-27", "2020-02-01", "2020-11-14", "2023-11-12", "2025-02-01", "2026-02-01"}
CHECKED_THROUGH = pd.Timestamp("2026-10-06")
# Known quirks in MCX's own files, each checked by hand against the source file and kept as data, not "fixed":
TURNOVER_UNIT_SLIP = {pd.Timestamp("2005-08-17")}        # GOLDM turnover printed at 1/100 of its size, that day only
CRASH_DAYS = {pd.Timestamp("2026-01-30")}                 # gold's crash: GOLDM closed 17.6% lower inside the day's own range
EXPIRY_EXCEPTIONS = {("GOLDM", pd.Timestamp("2024-10-31"))}  # MCX listed this GOLDM contract to expire 31 Oct 2024


def name(k):
    return f"{k[0]}_{k[1].date()}"


@cases(KEYS, name)
class EachContract(unittest.TestCase):
    def g(self, k):
        return GROUPS[k]

    def check_dates_strictly_increasing(self, k):
        """One row per market day, in order"""
        self.assertTrue(self.g(k).date.is_monotonic_increasing and self.g(k).date.is_unique)

    def check_no_row_after_expiry(self, k):
        """A contract never trades after its expiry date"""
        self.assertLessEqual(self.g(k).date.max(), k[1])

    def check_days_to_expiry(self, k):
        """days_to_expiry = expiry minus date, in calendar days"""
        g = self.g(k)
        self.assertTrue(((g.expiry_date - g.date).dt.days == g.days_to_expiry).all())

    def check_price_per_pure_gram(self, k):
        """rs_per_g = close / quote grams / purity"""
        g = self.g(k)
        expect = g.close / ingest.QUOTE_GRAMS[k[0]] / ingest.PURITY[k[0]]
        np.testing.assert_allclose(g.rs_per_g, expect, rtol=1e-12)

    def check_no_trade_flag(self, k):
        """no_trade is set exactly when no lots traded or MCX gave no open price"""
        g = self.g(k)
        self.assertTrue(((g.volume_lots.eq(0) | g.open.isna()) == g.no_trade).all())

    def check_traded_rows_have_positive_ordered_prices(self, k):
        """On traded days: prices positive, low <= open, high; low <= high"""
        t = self.g(k)[~self.g(k).no_trade]
        if t.empty:
            return
        self.assertTrue((t[["open", "high", "low", "close"]] > 0).all().all())
        self.assertTrue((t.low <= t.high).all())
        self.assertTrue(((t.open >= t.low - 0.5) & (t.open <= t.high + 0.5)).all())

    def check_close_inside_range_except_expiry_settlement(self, k):
        """From 2015, a close outside the day's range only on expiry day (Due Date Rate settlement)"""
        t = self.g(k)[~self.g(k).no_trade & (self.g(k).date >= "2015-01-01")]
        off = t[(t.close < t.low - 0.5) | (t.close > t.high + 0.5)]
        self.assertTrue((off.date == off.expiry_date).all(), off[["date", "low", "close", "high"]].to_string())

    def check_average_traded_price_inside_range(self, k):
        """Turnover / grams traded sits inside the day's range, allowing for MCX rounding turnover to Rs 1,000"""
        t = self.g(k)[~self.g(k).no_trade & (self.g(k).volume_lots > 0) & ~self.g(k).date.isin(TURNOVER_UNIT_SLIP)]
        if t.empty:
            return
        grams = t.volume_lots * LOT[k[0]]
        vw = t.value_lakhs * 1e5 / grams * ingest.QUOTE_GRAMS[k[0]]
        tol = 1000 / grams * ingest.QUOTE_GRAMS[k[0]] + 0.02 * t.close
        out = (vw < t.low - tol) | (vw > t.high + tol)
        self.assertFalse(out.any(), t[out][["date", "low", "high"]].assign(vwap=vw[out]).to_string())

    def check_counts_are_non_negative_integers(self, k):
        """Volume, open interest and turnover are never negative"""
        g = self.g(k)
        self.assertTrue((g.volume_lots >= 0).all() and (g.open_interest_lots >= 0).all() and (g.value_lakhs.fillna(0) >= 0).all())

    def check_rows_come_from_a_downloaded_file(self, k):
        """Every row names its MCX source file, and that file is in raw_clean/"""
        files = set(self.g(k).source_file)
        self.assertLessEqual(len(files), 2)
        self.assertTrue(files <= RAW, files - RAW)

    def check_expiry_follows_the_exchange_calendar(self, k):
        """From 2016: GOLDM expires by the 5th; the others in the last days of the month; never on a weekend"""
        if k[1] < pd.Timestamp("2016-01-01") or k in EXPIRY_EXCEPTIONS:
            return
        self.assertLess(k[1].dayofweek, 5)
        if k[0] == "GOLDM":
            self.assertLessEqual(k[1].day, 5)
        else:
            self.assertGreaterEqual(k[1].day, 26)

    def check_day_on_day_moves_within_mcx_bands(self, k):
        """From 2015, no close moves more than 15% from the previous traded close of the same contract, except on
        expiry day (settled at MCX's Due Date Rate from the spot price) and the 30 Jan 2026 crash"""
        t = self.g(k)[~self.g(k).no_trade & (self.g(k).date >= "2015-01-01")]
        r = (t.close / t.close.shift(1) - 1).abs().dropna()
        gap = t.date.diff().dt.days.dropna()
        r = r[gap.reindex(r.index) <= 5]                       # consecutive trading, not a long dormant spell
        r = r[~t.date.reindex(r.index).isin(CRASH_DAYS) & (t.date.reindex(r.index) != k[1])]
        self.assertTrue((r <= 0.15).all(), r[r > 0.15].to_string())


class Dataset(unittest.TestCase):
    def test_no_duplicate_rows(self):
        self.assertFalse(D.duplicated(["date", "symbol", "expiry_date"]).any())

    def test_only_the_four_gold_futures(self):
        self.assertEqual(set(D.symbol), set(SYMS))

    def test_weekend_rows_only_on_known_special_sessions(self):
        wk = D[(D.date.dt.dayofweek >= 5) & (D.date >= "2014-04-01")].date.dt.strftime("%Y-%m-%d").unique()
        unknown = [d for d in wk if d not in SPECIAL]
        # after the last checked day, allow the windows MCX uses for special sessions (Diwali Oct-Nov, Budget 1 Feb)
        unknown = [d for d in unknown if pd.Timestamp(d) <= CHECKED_THROUGH or not (pd.Timestamp(d).month in (10, 11) or d[5:] == "02-01")]
        self.assertEqual(unknown, [])

    def test_three_files_split_by_date_exactly_as_declared(self):
        lo3, hi3 = map(pd.Timestamp, ingest.SEALED[0])
        lo2, hi2 = map(pd.Timestamp, ingest.SEALED[1])
        sealed_win = lambda s: s.between(lo3, hi3) | s.between(lo2, hi2)
        self.assertTrue(sealed_win(clean("sealed").date).all())
        self.assertFalse(sealed_win(clean("dev").date).any())
        self.assertFalse(sealed_win(clean("history").date).any())
        self.assertTrue((clean("history").date < ingest.HISTORY_BEFORE).all())
        self.assertTrue((clean("dev").date >= ingest.HISTORY_BEFORE).all())

    def test_every_contract_type_trades_on_recent_days(self):
        last = clean("dev")
        recent = last[last.date >= last.date.max() - pd.Timedelta(days=10)]
        self.assertEqual(set(recent.symbol), set(SYMS))

    def test_same_expiry_contracts_agree_within_6_percent(self):
        """Per pure gram, two small contracts with the same expiry never differ by more than 6% on a day both
        traded at least 1 kg (the strategies' own liquidity floor), outside the delivery week"""
        kg = D.volume_lots * D.symbol.map(LOT) / 1000
        bleft = np.busday_count(D.date.values.astype("datetime64[D]"), D.expiry_date.values.astype("datetime64[D]"))
        # outside each contract's last 5 business days, which the strategies never trade: delivery-week prices
        # can split hard (Jan 2017: GOLDGUINEA +4%, GOLDPETAL -5% in the same week, both on several kg)
        t = D[~D.no_trade & (kg >= 1) & (D.symbol != "GOLDM") & (bleft > 5)]
        g = t.groupby(["date", "expiry_date"]).rs_per_g.agg(["min", "max", "size"])
        g = g[g["size"] > 1]
        self.assertLess((g["max"] / g["min"]).max(), 1.06)

    def test_prev_close_chains_on_almost_every_row(self):
        """MCX's previous close equals our previous row's close on at least 99% of rows"""
        p = D.groupby(["symbol", "expiry_date"]).close.shift(1)
        ok = (D.prev_close - p).abs() < 0.5
        self.assertGreater(ok[p.notna()].mean(), 0.99)

    def test_history_reaches_back_to_2003(self):
        self.assertLessEqual(D.date.min(), pd.Timestamp("2003-12-31"))


if __name__ == "__main__":
    unittest.main()

"""Reading one MCX Bhavcopy download (ingest.read_one), on small hand-made files that reproduce each format trap.

MCX's "Bhavcopy commodity-wise" download is an HTML table saved with an .xls name. Its dates read like
"29 Aug 2025", its expiries like "04SEP2026", symbols arrive padded with spaces, and options rows sit
alongside futures. Each test builds one such file and checks the parser handles it.
"""
import os
import shutil
import tempfile
import unittest

import pandas as pd

import ingest
from _util import cases

HEAD = ["Date", "Instrument Name", "Symbol", "Expiry Date", "Option Type", "Strike Price", "Open", "High", "Low",
        "Close", "Previous Close", "Volume(Lots)", "Volume(in 000's)", "Value(Lacs)", "Open Interest(Lots)"]


def row(date="29 Aug 2025", inst="FUTCOM", sym="GOLDPETAL", exp="30SEP2025", close=10000, **kw):
    r = {"Date": date, "Instrument Name": inst, "Symbol": sym, "Expiry Date": exp, "Option Type": "", "Strike Price": 0,
         "Open": close - 5, "High": close + 10, "Low": close - 10, "Close": close, "Previous Close": close - 3,
         "Volume(Lots)": 120, "Volume(in 000's)": 0.12, "Value(Lacs)": 12.0, "Open Interest(Lots)": 900}
    r.update(kw)
    return r


class Files(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, rows, head=HEAD, name="BhavCopy.xls"):
        cells = lambda vals, tag: "".join(f"<{tag}>{v}</{tag}>" for v in vals)
        html = "<table>" + "<tr>" + cells(head, "th") + "</tr>" + "".join("<tr>" + cells([r.get(h, "") for h in head], "td") + "</tr>" for r in rows) + "</table>"
        p = os.path.join(self.dir, name)
        open(p, "w", encoding="utf-8").write(html)
        return p

    def read(self, rows, **kw):
        return ingest.read_one(self.write(rows, **kw))


@cases(["01 Feb 2026", "12 Mar 2025", "13 Jan 2024", "29 Aug 2025", "31 Dec 2019", "05 May 2010"])
class EachDate(Files):
    def check_day_and_month_never_swap(self, s):
        """'DD Mon YYYY' is read with a fixed format, so 01 Feb is 1 February, never 2 January"""
        t, _ = self.read([row(date=s)])
        self.assertEqual(t.date.iloc[0], pd.Timestamp(pd.to_datetime(s, format="%d %b %Y")))
        self.assertEqual(t.date.iloc[0].strftime("%d %b %Y"), s)


@cases(["04SEP2026", "30SEP2025", "05JAN2024", "31OCT2024", "28FEB2025", " 05FEB2026 "])
class EachExpiry(Files):
    def check_compact_expiry_is_parsed(self, s):
        """Compact expiry 'DDMONYYYY' (stray spaces allowed) becomes a date"""
        t, _ = self.read([row(exp=s)])
        self.assertEqual(t.expiry_date.iloc[0], pd.to_datetime(s.strip(), format="%d%b%Y"))


@cases(["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"])
class EachSymbol(Files):
    def check_padding_is_stripped(self, sym):
        """'  GOLDM ' is read as 'GOLDM'"""
        t, _ = self.read([row(sym=f"  {sym}   ")])
        self.assertEqual(t.symbol.iloc[0], sym)
        self.assertIn(t.symbol.iloc[0], ingest.SYMBOLS)


class Parsing(Files):
    def test_keeps_futures_drops_options(self):
        t, _ = self.read([row(), row(inst="OPTFUT", close=500), row(inst=" FUTCOM ", sym="GOLDM", close=99000)])
        self.assertEqual(len(t), 2)
        self.assertEqual(sorted(t.symbol), ["GOLDM", "GOLDPETAL"])

    def test_renames_to_the_clean_column_names(self):
        t, _ = self.read([row()])
        self.assertEqual(list(t.columns), list(ingest.COLS.values()))

    def test_values_are_read_as_numbers(self):
        t, _ = self.read([row(close=14992)])
        r = t.iloc[0]
        self.assertEqual((r.open, r.high, r.low, r.close, r.prev_close), (14987, 15002, 14982, 14992, 14989))
        self.assertEqual((r.volume_lots, r.open_interest_lots), (120, 900))
        self.assertAlmostEqual(r.value_lakhs, 12.0)

    def test_missing_column_is_refused(self):
        with self.assertRaises(ValueError):
            self.read([row()], head=[h for h in HEAD if h != "Previous Close"])

    def test_fingerprint_depends_only_on_content(self):
        a = ingest.read_one(self.write([row()], name="a.xls"))[1]
        b = ingest.read_one(self.write([row()], name="copy (3).xls"))[1]
        c = ingest.read_one(self.write([row(close=10001)], name="c.xls"))[1]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_many_rows_keep_their_order(self):
        rows = [row(date=d.strftime("%d %b %Y"), close=10000 + i) for i, d in enumerate(pd.bdate_range("2025-08-01", periods=15))]
        t, _ = self.read(rows)
        self.assertTrue(t.date.is_monotonic_increasing)
        self.assertEqual(list(t.close), [10000 + i for i in range(15)])


class Conversion(unittest.TestCase):
    def test_rupees_per_pure_gram(self):
        """A GOLDPETAL close of 14,992 per 1 g of 999 gold is 15,007.0 per pure gram; GOLDM 1,48,911 per 10 g of 995 is 14,965.9"""
        self.assertAlmostEqual(14992 / ingest.QUOTE_GRAMS["GOLDPETAL"] / ingest.PURITY["GOLDPETAL"], 15007.0, places=1)
        self.assertAlmostEqual(148911 / ingest.QUOTE_GRAMS["GOLDM"] / ingest.PURITY["GOLDM"], 14965.9, places=1)

    def test_sealed_windows_are_declared_in_order_and_do_not_overlap(self):
        (a1, b1), (a2, b2) = [tuple(map(pd.Timestamp, w)) for w in ingest.SEALED]
        self.assertLess(a1, b1)
        self.assertLess(b1, a2)
        self.assertLess(a2, b2)
        self.assertLessEqual(pd.Timestamp(ingest.HISTORY_BEFORE), a1)


if __name__ == "__main__":
    unittest.main()

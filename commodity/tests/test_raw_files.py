"""Provenance: every MCX file in raw_clean/ is re-read from scratch and checked against the clean data.

One test per downloaded file. A file is either an exact copy of another (skipped by ingest.py, as the
site says) or every one of its gold futures rows appears in the clean data with identical prices.
"""
import hashlib
import os
import unittest

import pandas as pd

import ingest
from _util import all_rows, cases, raw_files

D = all_rows().set_index(["symbol", "expiry_date", "date"]).sort_index()
FILES = raw_files()
HASH = {}
for p in FILES:
    HASH.setdefault(hashlib.md5(open(p, encoding="utf-8", errors="replace").read().encode()).hexdigest(), []).append(os.path.basename(p))
USED = set(all_rows().source_file)
COLS = ["open", "high", "low", "close", "volume_lots"]


@cases(FILES, name=lambda p: os.path.basename(p)[:-4])
class EachRawFile(unittest.TestCase):
    def check_file_rows_match_clean_data(self, path):
        """The file parses, holds one gold contract, and its rows equal the clean data exactly (or it is a duplicate)"""
        t, h = ingest.read_one(path)
        name = os.path.basename(path)
        twins = HASH[h]
        if name not in USED:
            self.assertGreater(len(twins), 1, f"{name} is unused but has no identical twin")
            self.assertTrue(any(tw in USED for tw in twins), "neither copy was used")
            return
        self.assertEqual(t.symbol.nunique(), 1)
        self.assertEqual(t.expiry_date.nunique(), 1)
        self.assertIn(t.symbol.iloc[0], ingest.SYMBOLS)
        self.assertLessEqual(t.date.max(), t.expiry_date.iloc[0])
        key = t.set_index(["symbol", "expiry_date", "date"]).sort_index()
        mine = D.loc[key.index, COLS]
        pd.testing.assert_frame_equal(key[COLS].astype(float), mine.astype(float), check_names=False)


class RawSet(unittest.TestCase):
    def test_every_clean_row_has_a_raw_file(self):
        self.assertEqual(USED - {os.path.basename(p) for p in FILES}, set())

    def test_exact_copies_are_counted_once(self):
        dup_files = sum(len(v) - 1 for v in HASH.values())
        used = len(USED)
        self.assertEqual(used + dup_files, len(FILES))

    def test_site_states_the_same_file_counts(self):
        from _util import site
        S = site()
        self.assertEqual(S["meta"]["files"], len(FILES))
        self.assertEqual(len(S["provenance"]["files"]), len(USED))


if __name__ == "__main__":
    unittest.main()

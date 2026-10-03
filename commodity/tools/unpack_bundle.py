"""Write the round 3 bundle (tools/mcx_fetch.js) into raw_clean/, following DOWNLOADS_ROUND2.md round 3.

    python tools/unpack_bundle.py path/to/mcx_gold_round3.json.gz

- Contracts not held yet: written as raw_clean/<SYMBOL>_<DDMONYYYY>.xls.
- Contracts held and expired before 1 Oct 2026: existing file kept; the fresh copy is only compared
  with it (counts of matching and differing closes are printed, never prices).
- Contracts still trading (expiry on or after 1 Oct 2026): the old file is replaced by the fresh one.
"""
import gzip
import io
import json
import os
import sys
import tempfile

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from ingest import RAW, read_one  # noqa: E402

LIVE_FROM = pd.Timestamp("2026-10-01")


def parse(content):
    with tempfile.NamedTemporaryFile("w", suffix=".xls", delete=False, encoding="utf-8") as f:
        f.write(content)
    try:
        t, _ = read_one(f.name)
    finally:
        os.unlink(f.name)
    return t


def main(path):
    bundle = json.load(gzip.open(path, "rt", encoding="utf-8"))
    held = {}
    for p in sorted(os.listdir(RAW)):
        if p.endswith(".xls"):
            t, _ = read_one(os.path.join(RAW, p))
            held.setdefault((t.symbol.iloc[0], t.expiry_date.iloc[0]), []).append(p)
    new = live = same = differ = extra = 0
    diffs = []
    for name, content in sorted(bundle.items()):
        t = parse(content)
        key = (t.symbol.iloc[0], t.expiry_date.iloc[0])
        if key in held and key[1] < LIVE_FROM:
            old = pd.concat([read_one(os.path.join(RAW, p))[0] for p in held[key]]).drop_duplicates("date").set_index("date")
            both = t.set_index("date").join(old[["close"]], rsuffix="_old", how="inner")
            bad = int((both.close != both.close_old).sum())
            same += len(both) - bad
            extra += int((~t.date.isin(old.index)).sum())
            differ += bad
            if bad:
                diffs.append(f"{name}: {bad} of {len(both)} closes differ")
            continue
        if key in held:
            for p in held[key]:
                os.remove(os.path.join(RAW, p))
            live += 1
        else:
            new += 1
        open(os.path.join(RAW, name), "w", encoding="utf-8").write(content)
    print(f"bundle files: {len(bundle)}   new contracts written: {new}   live contracts refreshed: {live}")
    print(f"held contracts checked against MCX today: {same} closes match, {differ} differ; "
          f"{extra} rows MCX has that the held files lack (not added: existing files stay as they are)")
    for d in diffs:
        print("  ", d)


if __name__ == "__main__":
    main(sys.argv[1])

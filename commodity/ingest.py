"""Ingest MCX gold futures Bhavcopy downloads (Commodity Wise tab) into one clean table.

Input : raw_clean/*.xls  (each is an HTML table saved with an .xls extension)
Output: clean/gold_futures.csv and a printed validation report.

Run from the folder that contains raw_clean/:
    python ingest.py
"""
import glob
import hashlib
import io
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw_clean")
OUT = os.path.join(HERE, "clean")
SEALED = [("2016-01-01", "2019-12-31"), ("2020-01-01", "2023-10-09")]   # see DOWNLOADS_ROUND2.md
HISTORY_BEFORE = "2016-01-01"   # round 3: older DEV days go to their own file (training only)
SYMBOLS = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}

# Normalization convention: rupees per gram of pure gold.
QUOTE_GRAMS = {"GOLDM": 10, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
PURITY = {"GOLDM": 0.995, "GOLDTEN": 0.999, "GOLDGUINEA": 0.999, "GOLDPETAL": 0.999}

COLS = {
    "Date": "date", "Symbol": "symbol", "Expiry Date": "expiry_date",
    "Open": "open", "High": "high", "Low": "low", "Close": "close",
    "Previous Close": "prev_close", "Volume(Lots)": "volume_lots",
    "Open Interest(Lots)": "open_interest_lots", "Value(Lacs)": "value_lakhs",
}


def read_one(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    t = pd.read_html(io.StringIO(raw))[0]
    missing = set(COLS) - set(t.columns)
    if missing:
        raise ValueError(f"missing columns {sorted(missing)}")
    t = t[t["Instrument Name"].astype(str).str.strip() == "FUTCOM"]
    t = t[list(COLS)].rename(columns=COLS)
    t["symbol"] = t["symbol"].astype(str).str.strip()
    t["date"] = pd.to_datetime(t["date"], format="%d %b %Y")
    t["expiry_date"] = pd.to_datetime(t["expiry_date"].astype(str).str.strip(), format="%d%b%Y")
    return t, hashlib.md5(raw.encode()).hexdigest()


def main():
    files = sorted(glob.glob(os.path.join(RAW, "*.xls")))
    if not files:
        sys.exit(f"No .xls files found in {RAW}")

    frames, problems, seen = [], [], {}
    print(f"{'file':28} {'rows':>4}  {'first':10}  {'last':10}  {'max_gap':>7}  notes")
    for p in files:
        name = os.path.basename(p)
        try:
            t, h = read_one(p)
        except Exception as e:
            problems.append(f"{name}: unreadable ({e})")
            continue
        notes = []
        if h in seen:
            problems.append(f"{name}: identical content to {seen[h]}, skipped")
            continue
        seen[h] = name
        syms, exps = t["symbol"].unique(), t["expiry_date"].unique()
        if len(syms) != 1 or len(exps) != 1:
            notes.append(f"MIXED symbols={list(syms)} expiries={len(exps)}")
        sym, exp = syms[0], pd.Timestamp(exps[0])
        expected = f"{sym}_{exp.strftime('%d%b%Y').upper()}.xls"
        if name != expected:
            notes.append(f"content says {expected}")
        if sym not in SYMBOLS:
            notes.append("not a gold symbol")
        gap = t["date"].sort_values().diff().dt.days.max()
        gap = 0 if pd.isna(gap) else int(gap)          # a one-row contract has no gap
        if gap > 5:
            notes.append(f"gap of {gap} days, check for a holiday or truncation")
        if t["date"].max() > exp:
            notes.append("rows after expiry")
        t["source_file"] = name
        frames.append(t)
        print(f"{name:28} {len(t):>4}  {t.date.min().date()}  {t.date.max().date()}  {gap:>7}  {'; '.join(notes)}")
        problems += [f"{name}: {n}" for n in notes]

    d = pd.concat(frames, ignore_index=True)
    dup = d.duplicated(["date", "symbol", "expiry_date"], keep=False)
    if dup.any():
        problems.append(f"{int(dup.sum())} duplicate (date, symbol, expiry) rows")

    d["no_trade"] = d["volume_lots"].eq(0) | d["open"].isna()
    bad_range = (~d["no_trade"]) & ((d["close"] < d["low"]) | (d["close"] > d["high"]))
    if bad_range.any():
        problems.append(f"{int(bad_range.sum())} rows with close outside [low, high]")

    d["rs_per_g"] = d["close"] / d["symbol"].map(QUOTE_GRAMS) / d["symbol"].map(PURITY)
    d["days_to_expiry"] = (d["expiry_date"] - d["date"]).dt.days
    d = d.sort_values(["symbol", "expiry_date", "date"]).reset_index(drop=True)

    os.makedirs(OUT, exist_ok=True)
    # Sealed test windows (DOWNLOADS_ROUND2.md): their rows never enter the working dataset.
    sealed = pd.Series(False, index=d.index)
    for lo, hi in SEALED:
        sealed |= d.date.between(pd.Timestamp(lo), pd.Timestamp(hi))
    d[sealed].to_csv(os.path.join(OUT, "sealed_rows.csv"), index=False, date_format="%Y-%m-%d")
    print(f"Sealed-window rows set aside (not analysed): {int(sealed.sum())}")
    d = d[~sealed]
    old = d.date < pd.Timestamp(HISTORY_BEFORE)
    d[old].to_csv(os.path.join(OUT, "gold_futures_history.csv"), index=False, date_format="%Y-%m-%d")
    print(f"Pre-{HISTORY_BEFORE[:4]} DEV rows (training history, clean/gold_futures_history.csv): {int(old.sum())}")
    d = d[~old]
    d.to_csv(os.path.join(OUT, "gold_futures.csv"), index=False, date_format="%Y-%m-%d")

    print(f"\nRows: {len(d)}   Contracts: {d.groupby(['symbol','expiry_date']).ngroups}   "
          f"No-trade rows: {int(d['no_trade'].sum())}")
    print("Problems:" if problems else "Problems: none")
    for p in problems:
        print("  -", p)


if __name__ == "__main__":
    main()

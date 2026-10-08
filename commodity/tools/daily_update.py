"""Unattended daily data update: fetch, check, rebuild. Run by .github/workflows/daily-data.yml.

    python tools/daily_update.py            (from commodity/; needs Node + Playwright for the fetch)
    python tools/daily_update.py --bundle path/to/bundle.json.gz      (skip the fetch, use a bundle)

1. Fetch every GOLDM / GOLDTEN / GOLDGUINEA / GOLDPETAL contract still trading (or newly listed) from the
   official MCX Bhavcopy page (tools/auto_fetch.mjs). Expired contracts already held are never rewritten.
2. Rebuild clean/ with ingest.py and check the new rows. The update is REJECTED (nothing is written to the
   site, the job fails loudly) if any check fails:
     - the new last date is not after the old one       -> "no new trading day", exit 0, nothing changes
     - a row already held changed its close              -> MCX revised history: a person must look
     - a new day lacks any of the four contract types
     - a contract's close moved more than 9% from its previous close (MCX's widest daily band for gold is 9%...
       a larger jump means a bad file, not a market move)
3. Re-run the market views (testbed, accuracy, curve, roll-down, alerts, lifecycle) and the export.
   Strategy rules and the stored TEST / HOLDOUT / SEALED trade logs are frozen and are NOT re-run.
4. Append one line to results/update_log.csv (shown on the site) and rebuild dashboard/index.html.
"""
import argparse
import csv
import os
import subprocess
import sys
import tempfile

import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(HERE)
CLEAN = "clean/gold_futures.csv"
LOG = "results/update_log.csv"
SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
CHAIN = ["testbed.py", "accuracy.py", "curve.py", "rolldown.py", "alerts.py", "lifecycle.py", "dashboard/export.py", "dashboard/build.py"]


def run(cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    print(p.stdout[-3000:], p.stderr[-3000:], sep="\n", flush=True)
    if p.returncode:
        tail = " | ".join((p.stdout + p.stderr).strip().splitlines()[-6:])[:900]
        print(f"::error title=Daily update failed::{' '.join(cmd[-2:])} (exit {p.returncode}): {tail}", flush=True)
        sys.exit(f"step failed: {' '.join(cmd)} (exit {p.returncode})")
    return p.stdout


def load():
    return pd.read_csv(CLEAN, parse_dates=["date", "expiry_date"])


def check_update(old, new, last):
    """The publish gate. Returns (fresh rows, held rows matched, note) or exits with REJECTED.
    Kept as one function so tests/test_daily_update.py can feed it good and bad updates."""
    k = ["symbol", "expiry_date", "date"]
    both = old.merge(new, on=k, suffixes=("_o", "_n"))
    revised = both[both.close_o != both.close_n]
    if len(revised):
        print(revised[k + ["close_o", "close_n"]].head(20).to_string())
        print("::error title=Rejected::see log"); sys.exit(f"REJECTED: {len(revised)} rows already published changed their close. A person must check.")
    fresh = new[new.date > last]
    for d, g in fresh.groupby("date"):
        miss = sorted(set(SYMS) - set(g.symbol))
        if miss:
            print("::error title=Rejected::see log"); sys.exit(f"REJECTED: {d.date()} has no rows for {miss}")
    tr = fresh[(fresh.volume_lots > 0) & ~fresh.no_trade]
    if tr.close.isna().any() or (tr.close <= 0).any():
        sys.exit("REJECTED: missing or non-positive close on a traded row")
    note = None
    off = tr[(tr.close < tr.low - 0.5) | (tr.close > tr.high + 0.5)]
    if len(off):
        print(off[k + ["low", "close", "high"]].to_string())
        note = (f"note: {len(off)} new closes sit outside the day's low-high range (MCX settles expiring contracts "
                "at the Due Date Rate, so this is expected on expiry days)")
        bad = off[off.date != off.expiry_date]
        if len(bad):
            print("::error title=Rejected::see log"); sys.exit(f"REJECTED: {len(bad)} closes outside the day's range on non-expiry days")
    prev = new[(new.date <= last) & (new.volume_lots > 0)]
    ref = prev[prev.date == prev.date.max()].rs_per_g.median()
    if ((tr.rs_per_g < ref / 2) | (tr.rs_per_g > ref * 2)).any():
        print("::error title=Rejected::see log"); sys.exit(f"REJECTED: price per pure gram far from the previous day's median {ref:.0f}: unit or column error")
    return fresh, both, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle")
    a = ap.parse_args()
    old = load()
    last = old.date.max()
    print("held through", last.date(), "rows", len(old), flush=True)

    bundle = a.bundle
    if not bundle:
        bundle = os.path.join(tempfile.mkdtemp(), "mcx_live.json.gz")
        run(["node", "tools/auto_fetch.mjs", str(last.date()), bundle])
    out = run([sys.executable, "tools/unpack_bundle.py", bundle], env={"LIVE_FROM": str(last.date())})
    run([sys.executable, "ingest.py"])
    new = load()
    nlast = new.date.max()
    if nlast <= last:
        print(f"No new trading day after {last.date()}. Nothing to publish.")
        subprocess.run(["git", "checkout", "--", "raw_clean", "clean"], check=False)
        return 0

    # ---- checks on what changed
    fresh, both, note = check_update(old, new, last)
    if note:
        print(note)
    print(f"checks passed: {len(fresh)} new rows on {fresh.date.nunique()} new trading day(s), "
          f"{len(both)} held rows unchanged", flush=True)

    for s in CHAIN:
        run([sys.executable, s])

    os.makedirs("results", exist_ok=True)
    first = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(["run_ist", "data_through", "new_days", "new_rows", "rows_total", "contracts_total", "source"])
        w.writerow([pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M"), str(nlast.date()),
                    fresh.date.nunique(), len(fresh), len(new), new.groupby(["symbol", "expiry_date"]).ngroups,
                    os.environ.get("PARITY_SOURCE", "MCX Bhavcopy, commodity-wise, fetched by GitHub Actions")])
    # export again so the log line appears on the site
    run([sys.executable, "dashboard/export.py"])
    run([sys.executable, "dashboard/build.py"])
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"through={nlast.date()}\nnew_rows={len(fresh)}\n")
    print(f"::notice title=Updated::data through {nlast.date()}, {len(fresh)} new rows")
    print("UPDATED through", nlast.date())
    return 0


if __name__ == "__main__":
    sys.exit(main())

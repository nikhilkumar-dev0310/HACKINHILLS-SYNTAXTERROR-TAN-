"""Unattended daily data update: fetch, check, rebuild. Run by .github/workflows/daily-data.yml.

    python tools/daily_update.py            (from commodity/; needs Node + Playwright for the fetch)
    python tools/daily_update.py --bundle path/to/bundle.json.gz      (skip the fetch, use a bundle)

1. Fetch every GOLDM / GOLDTEN / GOLDGUINEA / GOLDPETAL contract still trading (or newly listed) from the
   official MCX Bhavcopy page (tools/auto_fetch.mjs). Expired contracts already held are never rewritten.
2. Rebuild clean/ with ingest.py and check the new rows. The update is REJECTED (nothing is written to the
   site, the job fails loudly) if any check fails:
     - the new last date is not after the old one       -> "no new trading day", exit 0, nothing changes
     - a row already held changed its close              -> MCX revised history: a person must look
     - a new day has fewer than two of the four contract types (MCX sometimes fails to return one or two: the day is
     published with what came back, and the missing contracts are filled in on a later run once MCX returns them)
     - a contract's close moved more than 9% from its previous close (MCX's widest daily band for gold is 9%...
       a larger jump means a bad file, not a market move)
3. Re-run the market views (testbed, accuracy, curve, roll-down, alerts, lifecycle, delivery premium) and the export.
   Strategy rules and the stored TEST / HOLDOUT / SEALED trade logs are frozen and are NOT re-run.
4. Append one line to results/update_log.csv (shown on the site) and rebuild dashboard/index.html.
"""
import argparse
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
CHAIN = ["testbed.py", "accuracy.py", "curve.py", "rolldown.py", "alerts.py", "lifecycle.py", "delivery.py", "dashboard/export.py",
         "robustness.py"]          # gap half-lives and regimes use the exported daily series; the export below picks them up


def run(cmd, env=None):
    print("$", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, env={**os.environ, **(env or {})}, capture_output=True, text=True)
    print(p.stdout[-3000:], p.stderr[-3000:], sep="\n", flush=True)
    if p.returncode:
        tail = " | ".join((p.stdout + p.stderr).strip().splitlines()[-6:])[:900]
        print(f"::error title=Daily update failed::{' '.join(cmd[-2:])} (exit {p.returncode}): {tail}", flush=True)
        sys.exit(f"step failed: {' '.join(cmd)} (exit {p.returncode})")
    return p.stdout


MIN_TYPES = 2          # a new day is published if at least this many of the four contract types came back
LOOKBACK_DAYS = 60     # how far back a contract still missing days is chased before it is left as a known gap


def lagging(df):
    """Contracts with a gap at the end of their history: another contract traded on a later day that this one
    should also have (on or before its expiry and on or before the latest day held), but no row came from MCX.
    These are fetched again on every run until MCX returns them (or LOOKBACK_DAYS pass)."""
    last = df.date.max()
    days = pd.Series(sorted(df.date.unique()))
    g = df.groupby(["symbol", "expiry_date"]).date.max().reset_index().rename(columns={"date": "held_to"})
    g = g[g.held_to >= last - pd.Timedelta(days=LOOKBACK_DAYS)]
    owe = [days[(days > r.held_to) & (days <= min(r.expiry_date, last))] for r in g.itertuples()]
    g["missing_days"] = [len(o) for o in owe]
    return g[g.missing_days > 0].reset_index(drop=True)


def reject(msg):
    """Stop the publish with the reason in the GitHub annotation itself, so it can be read without the log."""
    print(f"::error title=Rejected::{msg}", flush=True)
    sys.exit(f"REJECTED: {msg}")


def load():
    return pd.read_csv(CLEAN, parse_dates=["date", "expiry_date"])


def check_update(old, new, last):
    """The publish gate. Returns (fresh rows, held rows matched, note) or exits with REJECTED.
    Fresh rows are every row not held before: new days, and late rows for earlier days that MCX did not return
    on a previous run (backfill). All of them go through the same price checks.
    Kept as one function so tests/test_daily_update.py can feed it good and bad updates."""
    k = ["symbol", "expiry_date", "date"]
    both = old.merge(new, on=k, suffixes=("_o", "_n"))
    revised = both[both.close_o != both.close_n]
    if len(revised):
        print(revised[k + ["close_o", "close_n"]].head(20).to_string())
        reject(f"{len(revised)} rows already published changed their close. A person must check.")
    held = pd.MultiIndex.from_frame(old[k])
    fresh = new[~pd.MultiIndex.from_frame(new[k]).isin(held)]
    notes = []
    for d, g in fresh[fresh.date > last].groupby("date"):
        miss = sorted(set(SYMS) - set(g.symbol))
        if len(SYMS) - len(miss) < MIN_TYPES:
            reject(f"{d.date()} has no rows for {miss}")
        if miss:
            notes.append(f"{d.date()}: no rows yet for {', '.join(miss)} (filled in when MCX returns them)")
    late = fresh[fresh.date <= last]
    if len(late):
        notes.append(f"backfill: {len(late)} late rows for earlier days ({', '.join(sorted(late.symbol.unique()))})")
    tr = fresh[(fresh.volume_lots > 0) & ~fresh.no_trade]
    if tr.close.isna().any() or (tr.close <= 0).any():
        reject("missing or non-positive close on a traded row")
    off = tr[(tr.close < tr.low - 0.5) | (tr.close > tr.high + 0.5)]
    if len(off):
        print(off[k + ["low", "close", "high"]].to_string())
        notes.append(f"note: {len(off)} new closes sit outside the day's low-high range (MCX settles expiring contracts "
                     "at the Due Date Rate, so this is expected on expiry days)")
        bad = off[off.date != off.expiry_date]
        if len(bad):
            reject(f"{len(bad)} closes outside the day's range on non-expiry days")
    prev = new[(new.date <= last) & (new.volume_lots > 0)]
    ref = prev[prev.date == prev.date.max()].rs_per_g.median()
    if ((tr.rs_per_g < ref / 2) | (tr.rs_per_g > ref * 2)).any():
        reject(f"price per pure gram far from the previous day's median {ref:.0f}: unit or column error")
    return fresh, both, ("\n".join(notes) or None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle")
    a = ap.parse_args()
    old = load()
    last = old.date.max()
    gaps = lagging(old)
    since = min([last] + list(gaps.held_to))            # chase every contract still missing days, then today's
    print("held through", last.date(), "rows", len(old), flush=True)
    for r in gaps.itertuples():
        print(f"  waiting for MCX: {r.symbol} {r.expiry_date.date()} held to {r.held_to.date()} ({r.missing_days} days missing)")

    bundle = a.bundle
    if not bundle:
        bundle = os.path.join(tempfile.mkdtemp(), "mcx_live.json.gz")
        run(["node", "tools/auto_fetch.mjs", str(since.date()), bundle])
    run([sys.executable, "tools/unpack_bundle.py", bundle], env={"LIVE_FROM": str(since.date())})
    run([sys.executable, "ingest.py"])
    new = load()
    nlast = new.date.max()
    k = ["symbol", "expiry_date", "date"]
    if not (~pd.MultiIndex.from_frame(new[k]).isin(pd.MultiIndex.from_frame(old[k]))).any():
        print(f"No new rows after {last.date()} (and no late ones). Nothing to publish.")
        subprocess.run(["git", "checkout", "--", "raw_clean", "clean"], check=False)
        with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:   # tells the workflow to skip the commit
            f.write(f"updated=false\nthrough={last.date()}\nnew_rows=0\n")
        return 0

    # ---- checks on what changed
    fresh, both, note = check_update(old, new, last)
    if note:
        print(note)
    late = fresh[fresh.date <= last]
    pending = lagging(new)
    print(f"checks passed: {len(fresh)} new rows ({len(late)} of them late rows for earlier days), "
          f"{fresh[fresh.date > last].date.nunique()} new trading day(s), {len(both)} held rows unchanged", flush=True)

    for s in CHAIN:
        run([sys.executable, s])

    os.makedirs("results", exist_ok=True)
    cols = ["run_ist", "data_through", "new_days", "new_rows", "rows_total", "contracts_total", "source", "backfilled_rows", "pending"]
    log = pd.read_csv(LOG, dtype=str, keep_default_na=False) if os.path.exists(LOG) else pd.DataFrame(columns=cols)
    log = log.reindex(columns=cols, fill_value="")      # older logs lack the last two columns
    log.loc[len(log)] = [pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M"), str(nlast.date()),
                         fresh[fresh.date > last].date.nunique(), len(fresh), len(new), new.groupby(["symbol", "expiry_date"]).ngroups,
                         os.environ.get("PARITY_SOURCE", "MCX Bhavcopy, commodity-wise, fetched by GitHub Actions"), len(late),
                         " ".join(sorted(pending.symbol.unique()))]
    log.to_csv(LOG, index=False)
    # export again so the log line appears on the site
    run([sys.executable, "dashboard/export.py"])
    run([sys.executable, "dashboard/build.py"])
    run([sys.executable, "dashboard/intro/gen.py"])      # the intro's figures come from the same data.json
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"updated=true\nthrough={nlast.date()}\nnew_rows={len(fresh)}\n")
    if len(pending):
        print(f"::warning title=Waiting for MCX::published without {', '.join(f'{r.symbol} {r.expiry_date.date()}' for r in pending.itertuples())}; "
              "the next runs fetch them again and add the missing days when MCX returns them")
    print(f"::notice title=Updated::data through {nlast.date()}, {len(fresh)} new rows ({len(late)} backfilled)")
    print("UPDATED through", nlast.date())
    return 0


if __name__ == "__main__":
    sys.exit(main())

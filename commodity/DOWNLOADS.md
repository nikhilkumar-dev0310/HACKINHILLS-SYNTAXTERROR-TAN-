# Holdout downloads checklist

Second sealed test, declared 2026-10-01 before downloading: frozen parameters (lookback 10, entry z 2.0)
run once on dates 2025-08-01 to 2026-09-30. Do not tune anything on these files.

## How to download each file
MCX Bhavcopy page, Commodity Wise tab: Instrument FUTCOM, pick the Commodity and Expiry below,
From Date 01/01/2025, To Date 30/09/2026, Show, then Download. Expiry is the last trading day of
the month; pick whichever date the dropdown lists for that month. If a month is missing, write MISSING.

Put every file in `raw_clean/` (any name is fine; ingest.py checks contents).

| Batch | Expiry month | GOLDGUINEA | GOLDPETAL | GOLDTEN |
|---|---|---|---|---|
| A | Aug 2025 | [ ] | [ ] | [ ] |
| A | Sep 2025 | [ ] | [ ] | [ ] |
| A | Oct 2025 | [ ] | [ ] | [ ] |
| A | Nov 2025 | [ ] | [ ] | [ ] |
| A | Dec 2025 | [ ] | [ ] | [ ] |
| B | Jan 2026 | [ ] | [ ] | [ ] |
| B | Feb 2026 | [ ] | [ ] | [ ] |
| B | Mar 2026 | [ ] | [ ] | [ ] |
| B | Apr 2026 | [ ] | [ ] | [ ] |
| B | May 2026 | [ ] | [ ] | [ ] |
| C | Jun 2026 | [ ] | [ ] | [ ] |
| C | Jul 2026 | [ ] | [ ] | [ ] |
| C | Aug 2026 | [ ] | [ ] | [ ] |
| C | Sep 2026 | [ ] | [ ] | [ ] |

Batch A (15 files) first; send it, then B (15), then C (12).
Skip anything expiring Oct 2026 or later.

## Optional: extend TRAIN with earlier GUINEA and PETAL cycles
GOLDGUINEA and GOLDPETAL existed before GOLDTEN. Their contract cycles expiring Jan-Dec 2024 would add
TRAIN history for the GUINEA-PETAL pair (use From Date 01/01/2023). These are TRAIN data only.

| Expiry month | GOLDM 2024 |
|---|---|
| Jan 2024 | [ ] |
| Feb 2024 | [ ] |
| Mar 2024 | [ ] |
| Apr 2024 | [ ] |
| May 2024 | [ ] |
| Jun 2024 | [ ] |
| Jul 2024 | [ ] |
| Aug 2024 | [ ] |
| Sep 2024 | [ ] |
| Oct 2024 | [ ] |
| Nov 2024 | [ ] |
| Dec 2024 | [ ] |

| Expiry month | GOLDGUINEA | GOLDPETAL |
|---|---|---|
| Jan 2024 | [ ] | [ ] |
| Feb 2024 | [ ] | [ ] |
| Mar 2024 | [ ] | [ ] |
| Apr 2024 | [ ] | [ ] |
| May 2024 | [ ] | [ ] |
| Jun 2024 | [ ] | [ ] |
| Jul 2024 | [ ] | [ ] |
| Aug 2024 | [ ] | [ ] |
| Sep 2024 | [ ] | [ ] |
| Oct 2024 | [ ] | [ ] |
| Nov 2024 | [ ] | [ ] |
| Dec 2024 | [ ] | [ ] |

## Also needed now: GOLDM (fair-price strategy uses it as the anchor)
GOLDM expires on the 3rd-5th of the month. Same download method.

| Expiry month | GOLDM |
|---|---|
| Sep 2025 | [ ] |
| Oct 2025 | [ ] |
| Nov 2025 | [ ] |
| Dec 2025 | [ ] |
| Jan 2026 | [ ] |
| Feb 2026 | [ ] |
| Mar 2026 | [ ] |
| Apr 2026 | [ ] |
| May 2026 | [ ] |
| Jun 2026 | [ ] |
| Jul 2026 | [ ] |
| Aug 2026 | [ ] |
| Sep 2026 | [ ] |

## Priority
1. Batches A and B plus GOLDM Sep 2025 - Jun 2026: these cover the fair-price HOLDOUT
   (2025-08-06 to 2026-05-29). This is the test that matters most.
2. Batch C and GOLDM Jul - Sep 2026.
3. Optional 2024 history (GUINEA, PETAL above, plus GOLDM Jan-Dec 2024): more DEV data. If it
   arrives before the holdout run, `fairvalue.py dev` is rerun and k may change; that is allowed
   because the HOLDOUT is still unseen.

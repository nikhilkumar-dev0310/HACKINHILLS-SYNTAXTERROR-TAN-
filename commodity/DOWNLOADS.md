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
Not needed: GOLDM (never shares an expiry with the others), and Oct 2026 or later (not expired).

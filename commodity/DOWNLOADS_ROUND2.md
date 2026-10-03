# MCX Bhavcopy downloads, round 2 (declared 2026-10-02, before any of this data is seen)

## How
mcxindia.com > Market Data > Bhavcopy, commodity-wise. For each file:
- Commodity: the symbol. Expiry Date: the one in that month from the dropdown
  (GOLDGUINEA / GOLDPETAL: end of month; GOLDM: around the 5th).
- From Date: 01/01 of the year BEFORE the expiry year (covers the whole contract life). To Date: the expiry date.
- No renaming needed; files are identified by their content. Put them in commodity/raw_clean/ and push.
- GOLDTEN started 1 Apr 2025: nothing older exists, skip it.

## Plan (fixed now, before download)
- DEV for any improvement: all market days from 2024-01-01 onward (2025-26 data is already used).
- NEW SEALED TEST: market days 2020-01-01 to 2023-12-31. Improvements are frozen on DEV, then run
  ONCE on this window. Events inside it: Mar 2020 crash, Aug 2020 peak and fall.

## Batch A - fill gaps (10 files)
| Expiry month | GOLDGUINEA | GOLDPETAL | GOLDM |
|---|---|---|---|
| May 2026 | have | have | [ ] |
| Jan 2025 | [ ] | [ ] | [ ] |
| Feb 2025 | [ ] | [ ] | [ ] |
| Mar 2025 | [ ] | [ ] | [ ] |

## Batch B - 2024, DEV (36 files; includes the 23 Jul 2024 duty-cut crash)
| Expiry month | GOLDGUINEA | GOLDPETAL | GOLDM |
|---|---|---|---|
| Jan 2024 | [ ] | [ ] | [ ] |
| Feb 2024 | [ ] | [ ] | [ ] |
| Mar 2024 | [ ] | [ ] | [ ] |
| Apr 2024 | [ ] | [ ] | [ ] |
| May 2024 | [ ] | [ ] | [ ] |
| Jun 2024 | [ ] | [ ] | [ ] |
| Jul 2024 | [ ] | [ ] | [ ] |
| Aug 2024 | [ ] | [ ] | [ ] |
| Sep 2024 | [ ] | [ ] | [ ] |
| Oct 2024 | [ ] | [ ] | [ ] |
| Nov 2024 | [ ] | [ ] | [ ] |
| Dec 2024 | [ ] | [ ] | [ ] |

## Batch C - 2020, sealed test (36 files)
| Expiry month | GOLDGUINEA | GOLDPETAL | GOLDM |
|---|---|---|---|
| Jan 2020 | [ ] | [ ] | [ ] |
| Feb 2020 | [ ] | [ ] | [ ] |
| Mar 2020 | [ ] | [ ] | [ ] |
| Apr 2020 | [ ] | [ ] | [ ] |
| May 2020 | [ ] | [ ] | [ ] |
| Jun 2020 | [ ] | [ ] | [ ] |
| Jul 2020 | [ ] | [ ] | [ ] |
| Aug 2020 | [ ] | [ ] | [ ] |
| Sep 2020 | [ ] | [ ] | [ ] |
| Oct 2020 | [ ] | [ ] | [ ] |
| Nov 2020 | [ ] | [ ] | [ ] |
| Dec 2020 | [ ] | [ ] | [ ] |

## Batch D - 2021 to 2023, sealed test (108 files)
| Expiry month | GOLDGUINEA | GOLDPETAL | GOLDM |
|---|---|---|---|
| Jan 2021 | [ ] | [ ] | [ ] |
| Feb 2021 | [ ] | [ ] | [ ] |
| Mar 2021 | [ ] | [ ] | [ ] |
| Apr 2021 | [ ] | [ ] | [ ] |
| May 2021 | [ ] | [ ] | [ ] |
| Jun 2021 | [ ] | [ ] | [ ] |
| Jul 2021 | [ ] | [ ] | [ ] |
| Aug 2021 | [ ] | [ ] | [ ] |
| Sep 2021 | [ ] | [ ] | [ ] |
| Oct 2021 | [ ] | [ ] | [ ] |
| Nov 2021 | [ ] | [ ] | [ ] |
| Dec 2021 | [ ] | [ ] | [ ] |
| Jan 2022 | [ ] | [ ] | [ ] |
| Feb 2022 | [ ] | [ ] | [ ] |
| Mar 2022 | [ ] | [ ] | [ ] |
| Apr 2022 | [ ] | [ ] | [ ] |
| May 2022 | [ ] | [ ] | [ ] |
| Jun 2022 | [ ] | [ ] | [ ] |
| Jul 2022 | [ ] | [ ] | [ ] |
| Aug 2022 | [ ] | [ ] | [ ] |
| Sep 2022 | [ ] | [ ] | [ ] |
| Oct 2022 | [ ] | [ ] | [ ] |
| Nov 2022 | [ ] | [ ] | [ ] |
| Dec 2022 | [ ] | [ ] | [ ] |
| Jan 2023 | [ ] | [ ] | [ ] |
| Feb 2023 | [ ] | [ ] | [ ] |
| Mar 2023 | [ ] | [ ] | [ ] |
| Apr 2023 | [ ] | [ ] | [ ] |
| May 2023 | [ ] | [ ] | [ ] |
| Jun 2023 | [ ] | [ ] | [ ] |
| Jul 2023 | [ ] | [ ] | [ ] |
| Aug 2023 | [ ] | [ ] | [ ] |
| Sep 2023 | [ ] | [ ] | [ ] |
| Oct 2023 | [ ] | [ ] | [ ] |
| Nov 2023 | [ ] | [ ] | [ ] |
| Dec 2023 | [ ] | [ ] | [ ] |

If MCX returns nothing for a year, stop there and say so; nothing will be filled in.

## Addendum (declared 2026-10-03, before any 2016-2019 data is downloaded)
- SECOND SEALED TEST: market days 2016-01-01 to 2019-12-31, GOLDGUINEA, GOLDPETAL, GOLDM.
  Improved rules are frozen on DEV (2024-01-01 onward) first, then run ONCE on 2020-2023 and ONCE
  on 2016-2019. Neither window is used to choose or tune anything.
- Batch E: GOLDGUINEA, GOLDPETAL, GOLDM, all expiries Jan 2016 - Dec 2019 (144 files).
  From Date 01/07 of the previous year, To Date 31/12 of the expiry year.
- Still missing from earlier rounds: GOLDTEN expiring 31 Aug 2026.

## Amendment (2026-10-03, after the 2024 files arrived, before any 2020-2023 data)
The 2024 contracts were downloaded from 01/07/2023, so they contain market days from 10 Oct 2023.
Those days have now been seen. The first sealed test is therefore shortened to
2020-01-01 to 2023-10-09. Days 2023-10-10 to 2023-12-31 are used for neither development nor testing.
ingest.py now writes rows inside sealed windows to clean/sealed_rows.csv and keeps them out of
clean/gold_futures.csv, so no analysis script can read them before the one sealed run.

## Round 3 declaration (2026-10-04, before any of this data is downloaded)
- Download: every GOLDM, GOLDTEN, GOLDGUINEA and GOLDPETAL futures contract MCX lists in its
  commodity-wise Bhavcopy (GOLDM from 2004, GOLDGUINEA from 2008, GOLDPETAL from 2011, GOLDTEN from
  2025), whole contract life, through mcxindia.com's own Bhavcopy endpoint and its own XLS export.
  No other symbols.
- Existing files stay as they are (they produced the recorded results). New files are added only
  for contracts not yet held, plus contracts still trading (expiry on or after 1 Oct 2026), which
  are refreshed to the latest day.
- DEV (training) = all market days before 2016-01-01, plus all market days from 2024-01-01 onward.
  2023-10-10 to 2023-12-31 stays unused for testing. Sealed windows are unchanged:
  2016-01-01 to 2019-12-31 and 2020-01-01 to 2023-10-09; ingest.py walls their rows off and no
  analysis script reads them.
- Training: any improved rule (for example a stress-regime filter for the fair-price strategy,
  entry threshold, exit and holding rules) is chosen on DEV only, judged by walk-forward folds
  inside DEV after full costs, then frozen in Git. The frozen rules run ONCE on 2020-01-01 to
  2023-10-09 and ONCE on 2016-01-01 to 2019-12-31. Results are recorded as they come out.
- Costs: today's MCX fee, CTT, stamp duty, SEBI fee, brokerage and GST are applied to every year,
  including years before CTT existed (2013), which is conservative for older data.

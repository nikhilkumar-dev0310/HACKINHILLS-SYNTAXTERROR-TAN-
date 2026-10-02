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

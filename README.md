# Parity · MCX gold futures, priced per gram of pure gold

[![Tests](https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/actions/workflows/tests.yml/badge.svg)](https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/actions/workflows/tests.yml)
[![Daily data](https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/actions/workflows/daily-data.yml/badge.svg)](https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/actions/workflows/daily-data.yml)

**Hack in Hills '26 · Problem 03: Commodity Derivatives Intelligence** · Team **SYNTAX TERROR (TAN)**: Nikhil Kumar (lead), Sai Ganesh, Ishaan Chhabra

MCX lists four gold futures that differ only in size and purity: GOLDM (100 g bar, 995), GOLDTEN (10 g, 999),
GOLDGUINEA (8 g coin, 999) and GOLDPETAL (1 g, 999). Per gram of pure gold they should cost the same.
Parity measures whether they do, tests whether any gap can be traded after real costs, and says each day
whether a gap is worth a look.

| | |
|---|---|
| **Live site** | **https://parity-gold-site.vercel.app** (updates itself every trading day) |
| 3D intro | https://parity-gold-site.vercel.app/intro (plays whenever the site's link is opened from outside; `?nointro` skips it) |
| Pitch | https://parity-gold-site.vercel.app/pitch.html |
| Report (PDF) | https://parity-gold-site.vercel.app/report.pdf · [`commodity/report/`](commodity/report/) |
| Demo video | **https://parity-gold-site.vercel.app/demo** · [`commodity/presentation/round2/Parity_demo.mp4`](commodity/presentation/round2/Parity_demo.mp4) (1 min 28 s, subtitles in `.srt`; how it holds attention: [`ENGAGEMENT.md`](commodity/presentation/round2/ENGAGEMENT.md)) |
| Prototype video, vertical | [`commodity/presentation/round2/Parity_demo_vertical.mp4`](commodity/presentation/round2/Parity_demo_vertical.mp4) (9:16 for Instagram and LinkedIn, repo and live links on screen) |
| Round 1 deck | [`commodity/presentation/round1/`](commodity/presentation/round1/) |
| Full technical write-up | [`commodity/README.md`](commodity/README.md) |

## The answer

**They mostly match. Where they don't, the gap is usually too small to pay for the costs of trading it.**
The best rule made money in the January 2026 crash, and not reliably in eight more years of sealed tests.
A rigorous "no persistent edge after costs" is the finding, and every number behind it can be checked.

Net profit on years the rules never saw, at 5 bp slippage per leg, after every MCX fee and tax:

| Sealed test (run once, rules frozen in Git first) | Strategy A (pairs) | Strategy B (fair price) | Strategy C (B, retrained) |
|---|---:|---:|---:|
| Aug 2025 – May 2026 holdout | +₹1,90,340 | +₹12,990 | n/a |
| 2016 – 2019 | −₹48,734 | +₹35,873 | +₹21,415 |
| 2020 – 2023 | −₹62,774 | +₹6,962 | −₹3,707 |

Strategy A's holdout profit came almost entirely from the January 2026 crash; outside it, the rule loses after costs.

### Skill, tuning or luck?

Three standard checks, run on training years only so the sealed results stay untouched ([`commodity/overfit.py`](commodity/overfit.py)):

- **Probability of backtest overfitting: 65%.** Over all 252 ways of splitting the ten training years in half,
  the best of Strategy C's 72 settings on one half landed in the bottom half on the other 65% of the time
  (Bailey, Borwein, López de Prado and Zhu, 2017). Picking the best setting mostly picks noise, which is why
  the tuned Strategy C did not beat the untuned B in the sealed years.
- **Placebo: Strategy B beat 94.75% of 2,000 random-timing strategies** with the same contracts, holding times
  and costs. Its timing carries some information, but only about 1 in 19 random runs did as well: borderline.
- **Without the carry adjustment** the same rules made ₹1,02,383 on 73 trades, against ₹79,982 on 72 with it.
  The adjustment puts each fair price at the right level but did not add profit on these years; we report that.
- **How much can go wrong:** every result that made money before slippage breaks even at between 3.5 and 11.9 bp of
  slippage per leg; we test at 5. Strategy C's deflated Sharpe ratio is 4%: its sealed result is what picking the best
  of 72 settings gives by chance ([`commodity/robustness.py`](commodity/robustness.py)).
- **Every rule we ever tried: 91 distinct rules** (9 in Strategy A's grid, 8 research methods, 1 more for B, 72 in C,
  1 later check without the carry adjustment; a rule that appears twice is counted once). Against all of them, the
  fair-price model's sealed profit has a deflated Sharpe ratio of 5% (50% against its own 3 settings alone): about
  what the best of 91 tries earns by luck. Each sealed result is also deflated on its own, against the rules scored
  before its window was opened (9 before the first test, 20 before the holdout, 90 before 2016–2023, from the Git
  history): the fair-price model scores 46% on the holdout, 27% on 2016–2019 and 7% on 2020–2023, below 50% every time.
- **What a trade actually costs:** pooled over each 2016–2023 sealed window, the quoted half-spread estimated from daily
  highs and lows (Corwin and Schultz, 2012) was under 3 bp per order even at the top of its 95% range, below every
  positive break-even. In May–July 2025 it was wider: Strategy A's first test broke even at 3.5 bp against a measured
  3.8 bp on the legs it traded, so even its profit before slippage sat inside the spread. From August 2025 that
  estimator breaks down, and the site says "not measurable" rather than guess.
- **The delivery premium** ([`commodity/delivery.py`](commodity/delivery.py)): a buyer of GOLDPETAL or GOLDGUINEA who
  sells before the delivery window gives up only how far the premium fell while held; one who takes delivery pays the
  whole premium. At the final settlement the premium rises, GOLDTEN's included, so much of that rise is spot gold
  settling above the futures, not the coins themselves. Read from the cycles since April 2025, when GOLDM and GOLDTEN
  agreeing per pure gram confirms the purity conversion.
- **Do the gaps come back?** GOLDTEN and GOLDGUINEA gaps halve in about 7 and 8 market days and pass a stationarity
  test. GOLDPETAL's level jumped abruptly in November 2024 (about −150 bp to about +90 bp over GOLDM); we found no
  exchange notice that explains it, and say so.

## What is in it

- **Data:** over 55,000 daily rows from the official MCX Bhavcopy, every contract of the four gold futures since
  November 2003 (over 700 contracts), each file identified by its contents. Updated every trading day by a
  scheduled job on a team computer (MCX blocks cloud servers), which publishes only if every check passes.
- **Like for like:** every price converted to rupees per gram of pure gold (995 vs 999 purity, 1 g to 100 g lots).
- **Relative value:** all six pairs, and a carry-adjusted fair price for each small contract against GOLDM.
- **Term structure:** carry measured from the data; roll-down separated from changes in the curve.
- **Backtests without look-ahead:** signal at today's close, fill at the next day's price; full MCX fee schedule
  (transaction fee, CTT, stamp duty, SEBI fee, brokerage, GST) plus 0–10 bp slippage on every leg.
- **Profit split** into the gap part and the gold-price part, trade by trade.
- **Contract calendar:** listing, liquidity build-up, tender period; every trade placed inside it.
- **Alerts** that stay quiet unless a contract is ±1.5σ from fair price, with the history of what each alert did next.
- **Data quality:** every flagged row explained; nothing silently changed.

## Tests

[![Tests](https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/actions/workflows/tests.yml/badge.svg)](https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/actions/workflows/tests.yml)

About 10,000 automated tests (297 distinct checks, run per contract, per raw file and per trade log so a failure
names exactly what broke). They run on GitHub on every push, and on the team computer before the daily job may
publish; the latest run is shown on the site's Data quality page. Standard-library `unittest`, no extra packages.

| File | What it proves |
|---|---|
| `test_protocol.py` | Frozen rules and sealed results are byte-for-byte what was committed (SHA-256), each written once, rules committed before the results they govern, and the code uses exactly the frozen values |
| `test_no_lookahead.py` | Changing future prices never changes a past trade; fills are always the day after the signal |
| `test_trade_logs.py` | Every stored trade re-derived from the raw MCX prices: gross, costs, windows, calendar, one position at a time |
| `test_clean_data.py` | Every contract since 2003: dates, prices, expiry calendar, per-gram conversion, with each MCX file quirk named |
| `test_raw_files.py`, `test_ingest.py` | Every raw file matches the clean data; MCX's date and expiry formats are parsed without day/month swaps |
| `test_costs.py`, `test_specs.py` | Each fee by hand, slippage linear, lot sizes and purities consistent everywhere |
| `test_analysis.py` | Profit split adds up, overfitting statistic behaves on known cases, alerts fire only beyond the threshold |
| `test_daily_update.py` | The publish gate rejects changed history, missing contracts, bad prices and unit errors |
| `test_site_data.py`, `test_site_build.py`, `test_site_format.py` | The site shows exactly the computed numbers; every term defined, every source file real; rupee and date formatting checked in Node |
| `test_robustness.py`, `test_statistics.py` | Break-even slippage, Sharpe tests, the count of rules tried (in all, and before each sealed window was opened), both half-spread estimators, the delivery premium, ADF, half-life, regime breaks and the bootstraps, each on cases with a known answer, then the stored results recomputed |
| `test_events.py` | Every dated note on the charts, including each stated price move, matches the MCX prices of that day |
| `test_video.py` | Every number in the demo video's subtitles matches the data; counts never overstate |
| `test_docs.py` | This README's results table, figures, data claims, test counts and links match the computed files; the published test report is complete |

```bash
cd commodity
pip install -r tools/requirements.txt
python tools/run_tests.py                   # about a minute; writes results/test_report.json
```

## Reproduce

```bash
cd commodity
python ingest.py              # validate every MCX file, write clean/ (sealed years to their own file)
python backtest.py train      # Strategy A on training dates; sealed runs refuse to run twice
python fairvalue.py dev       # Strategy B, development window
python strategy_c.py dev      # Strategy C grid on development years
python overfit.py             # overfitting, placebo and no-carry checks (training years only)
python robustness.py          # break-even slippage, Sharpe tests, rules tried, trading costs, half-lives, regimes
python delivery.py            # the premium a month out, at the last safe exit and at final settlement
python dashboard/export.py && node dashboard/build_app.mjs && python dashboard/build.py   # rebuild the site
```

## Layout

```
commodity/
  raw_clean/        MCX Bhavcopy downloads, as downloaded
  clean/            validated data: development, pre-2016 history, sealed years (separate file)
  results/          every computed table; frozen rules and sealed results pinned by tests
  tests/            the test suite
  dashboard/        the site (React, built to one self-contained HTML page)
  report/           17-page report and data book (PDF)
  presentation/     pitch, Round 1 deck, demo video
  tools/            daily update job, MCX fetcher, Vercel build
```

## Licence and data use

The analysis, code, documents and the compiled **Parity data book** are © 2026 Team SYNTAX TERROR (TAN).
All rights reserved: see [`LICENSE`](LICENSE). They are published so judges and readers can check the work;
reusing them, in particular in another hackathon submission, needs the team's written permission.
The underlying prices are MCX's public end-of-day Bhavcopy, available from [mcxindia.com](https://www.mcxindia.com/).

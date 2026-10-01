# Gold spread analysis (MCX GOLDTEN / GOLDGUINEA / GOLDPETAL)

## Setup (once)
Put `ingest.py`, `backtest.py` and this README in the same folder as `raw_clean/`
(for you: `~/Documents/commodity/data/`). Then:

    source ~/Documents/commodity/venv/bin/activate
    cd ~/Documents/commodity/data
    pip install pandas lxml numpy scipy

## Run
    python ingest.py            # validates every file, writes clean/gold_futures.csv
    python backtest.py train    # sweep on dates <= 2025-04-30, applies the pre-declared rule
    python backtest.py test     # ONLY after more data is added and you agree; runs once
    python backtest.py holdout  # second sealed test, 2025-08-01 to 2026-09-30, runs once
    python methods.py           # research-backed alternatives, compared on TRAIN dates only
    python uncertainty.py       # bootstrap interval for TEST, spread level per contract cycle
    python testbed.py           # accuracy testbed: data error rates and 95% margins
    python accuracy.py          # all four contracts: carry, GOLDM pairs, precision per contract
    python fairvalue.py dev     # GOLDM-anchored fair-price strategy, development window
    python fairvalue.py holdout # its sealed test, runs once on 2025-08-06 to 2026-05-29

## Design
- Normalized price: close / quote grams (10, 8, 1) / purity 0.999, in Rs per gram of pure gold.
- Pairs: only contracts with the same expiry date. GOLDM never shares an expiry with the others,
  so it is excluded from pairs. Contracts not yet expired are excluded.
- Spread: 10,000 x ln(price_a / price_b), in basis points.
- Signal: z = (today's spread - mean of previous N days) / sd of previous N days.
  Decided at day t's close, executed at the next close both legs traded (no look-ahead).
- Exit at z = 0, or 3 calendar days before expiry. No entries in the last 7 days.
  Skip days where either leg traded under 1 kg.
- Position: 40 g per leg (40 PETAL lots, 5 GUINEA lots, 4 TEN lots). Lot sizes checked against the
  Volume(In 000's) column in the files.
- Split by calendar date: TRAIN up to 2025-04-30, TEST 2025-05-01 to 2025-07-31.

## Costs (per leg, per side)
| Item | Rate | Status |
|---|---|---|
| MCX transaction fee | Rs 2.10 per lakh of turnover | MCX filing, effective 1 Oct 2024 |
| Commodity transaction tax | 0.01%, sell side | Confirmed (non-agri futures) |
| Stamp duty | 0.002%, buy side | Assumption from broker charge sheets |
| SEBI fee | Rs 10 per crore | Assumption |
| Brokerage | Rs 20 per order, max 0.03% | Assumption (discount broker) |
| GST | 18% on brokerage + fees | Assumption |
| Slippage | 0 / 5 / 10 bp | Settlement close is not a fill, so tested as a range |

## Parameter rule (declared before results)
Grid: N in {5, 10, 15}, entry z in {1.5, 2.0, 2.5}. Pick the highest net P&L at 5 bp slippage among
settings with at least 8 trades across at least 2 pairs; else default N=10, z=2.0.

## Change log
- Fixed: the first version included today in the z window, which caps |z| at (N-1)/sqrt(N)
  (1.79 for N=5), so high thresholds could never trigger. Now uses the previous N days only.
  Fixed before any TEST run.
- Added 18 more contracts (31 total). Before any TEST run: TEST window extended to 2025-07-31 (last
  expiry with all three symbols), and TRAIN selection rerun on the larger TRAIN set with the same rule.
  Frozen: lookback 10, entry z 2.0.

- 2026-10-01: TEST has been used. Declared a second sealed HOLDOUT (2025-08-01 to 2026-09-30) before
  downloading its data; it reuses the frozen parameters unchanged. See DOWNLOADS.md.

## Results (40 g per leg, Rs)
TRAIN (to 30 Apr 2025, 10 pairs): all 27 settings lose before costs. Frozen setting: 9 trades, gross -3,939.

TEST (1 May - 31 Jul 2025, run once, 9 pairs, 19 trades):
| Slippage per leg per side | Gross | Costs | Net | Hit rate |
|---|---|---|---|---|
| 0 bp | 14,624 | 4,331 | +10,292 | 68% |
| 5 bp | 14,624 | 19,090 | -4,466 | 32% |
| 10 bp | 14,624 | 33,848 | -19,224 | 16% |

- Breakeven slippage: about 3.5 bp per leg per side.
- 80% of gross came from the 9 trades involving GOLDTEN; GUINEA-PETAL lost after costs.
- 5 trades entered on 21 May 2025 (one GOLDTEN move seen through several pairs) made 49% of gross,
  so the 19 trades are far from 19 independent bets.
- Gold exposure: equal-gram legs; correlation of trade P&L with the gold move is -0.23 (n=19).

Verdict: no persistent edge after realistic costs. TEST was profitable only if fills at the settlement
price are near-perfect, and TRAIN with the same setting lost money before costs.

## Research round (2026-10-01): better methods, more data, uncertainty

### Methods compared on TRAIN only (`methods.py`)
TEST was already used, so it is not touched. All candidates use only past data, the same costs, and a
delivery-safe exit (MCX delivery is compulsory and staggered over the last 3 trading days: exit 5
business days before expiry, no entries in the last 10). Selection rule declared before running:
best TRAIN net at 5 bp with >= 8 trades over >= 2 pairs, promoted only if that net is positive.

| Method (source) | Trades | Gross | Net at 0 / 5 / 10 bp |
|---|---|---|---|
| z-score N=10, z=2.0 (Gatev et al. 2006) | 9 | -3,939 | -5,919 / -12,498 / -19,076 |
| OU s-score W=20 (Avellaneda & Lee 2010) | 13 | +385 | -2,477 / -11,989 / -21,501 |
| OU s-score W=30 | 6 | +365 | -959 / -5,366 / -9,774 |
| OU + cost filter W=20 (Bertram 2010; Leung & Li 2015) | 1 | -1,136 | -1,351 / -2,054 / -2,757 |
| OU + cost filter W=30 | 2 | -1,667 | -2,102 / -3,539 / -4,975 |
| Kalman W=20, c=1.0 (Elliott et al. 2005) | 11 | -340 | -2,765 / -10,828 / -18,890 |
| Kalman W=20, c=1.5 | 11 | +1,692 | -738 / -8,827 / -16,917 |
| Kalman W=30, c=1.0 | 8 | -1,647 | -3,411 / -9,283 / -15,156 |
| Kalman W=30, c=1.5 | 6 | -225 | -1,549 / -5,956 / -10,362 |

Decision: no method promoted (none positive at 5 bp). HOLDOUT runs the frozen baseline only.
- Kalman (noise-aware) has the best gross: thin-contract settlements are noisy, and a simulation with
  known parameters shows plain AR(1) estimates a 0.8-day half-life when the truth is 3.1 days, while the
  Kalman fit recovers the parameters (mean reversion 0.83 vs true 0.80).
- The cost filter leaves 1-2 trades: expected reversions rarely reach twice the round-trip cost.
- TRAIN is small (3 pairs with enough history), so these comparisons are weak evidence.

### Uncertainty of the TEST result (`uncertainty.py`)
19 trades fall in only 9 entry weeks; resampling by week (10,000 draws):
| Slippage | Net | 95% interval | Draws > 0 |
|---|---|---|---|
| 0 bp | +10,292 | +847 to +23,140 | 99% |
| 5 bp | -4,466 | -9,849 to +2,350 | 9% |
| 10 bp | -19,224 | -25,405 to -13,824 | 0% |

### Main finding: GOLDTEN trades at a persistent discount
Per gram of pure gold (descriptive, all cycles, `results/spread_levels.csv`):
- PETAL minus TEN: +59 to +93 bp in all 8 cycles, positive on 98-100% of days.
- GUINEA minus TEN: +38 to +97 bp in all 7 cycles, positive on 90-100% of days.
- GUINEA minus PETAL: changes sign between cycles (-34 to +35 bp).
A gap that holds its level cycle after cycle is a structural premium of the smaller contracts, not a
temporary mispricing, which is why reversion trades fail. It also does not close at expiry, so it
cannot be arbitraged by holding to delivery. Why it exists (for example, higher per-gram minting and
delivery cost of 1 g and 8 g products) is a hypothesis we have not verified.

### Data
- More MCX history is the most useful addition. GOLDGUINEA and GOLDPETAL trade before GOLDTEN's 2025
  listing, so their 2024 contract cycles would enlarge TRAIN for the GUINEA-PETAL pair. Same download
  method as DOWNLOADS.md.
- NSE lists equivalent contracts (GOLDGUINEA 8 g, GOLD1G, GOLD10G, all 999 purity); their trading
  volume has not been checked, so they are a possible second exchange, not yet a dataset.
- Continuous "front-month" series from charting sites are not used: they stitch contracts together,
  which the problem statement warns against.

### Verified references (DOI checked against Crossref or RePEc)
- Gatev, Goetzmann & Rouwenhorst (2006). Pairs Trading: Performance of a Relative-Value Arbitrage Rule. Review of Financial Studies 19(3). doi:10.1093/rfs/hhj020
- Elliott, van der Hoek & Malcolm (2005). Pairs trading. Quantitative Finance 5(3). doi:10.1080/14697680500149370
- Avellaneda & Lee (2010). Statistical arbitrage in the US equities market. Quantitative Finance 10(7). doi:10.1080/14697680903124632
- Bertram (2010). Analytic solutions for optimal statistical arbitrage trading. Physica A 389(11). doi:10.1016/j.physa.2010.01.045
- Leung & Li (2015). Optimal mean reversion trading with transaction costs and stop-loss exit. Int. J. Theoretical and Applied Finance 18(3). doi:10.1142/S021902491550020X
- Do & Faff (2010). Does Simple Pairs Trading Still Work? Financial Analysts Journal 66(4). doi:10.2469/faj.v66.n4.1
- Rad, Low & Faff (2016). The profitability of pairs trading strategies: distance, cointegration and copula methods. Quantitative Finance. doi:10.1080/14697688.2016.1164337
- Krauss (2017). Statistical Arbitrage Pairs Trading Strategies: Review and Outlook. Journal of Economic Surveys 31(2). doi:10.1111/joes.12153
- Politis & Romano (1994). The Stationary Bootstrap. JASA 89(428). doi:10.1080/01621459.1994.10476870
- Pavabutr & Chaihetphon (2010). Price discovery in the Indian gold futures market. Journal of Economics and Finance 34(4). doi:10.1007/s12197-008-9068-9
- Mahajan & Chandra (2019). Stochastic Spread Pairs Trading in the Indian Commodity Market. arXiv:1907.08397

## Accuracy testbed (`testbed.py`)

### A. Data errors: 0 unexplained in 1,919 rows
| Check | Error rate |
|---|---|
| Duplicates, rows after expiry, open/close outside [low, high], non-positive prices | 0.00% |
| Missing trading day inside a contract's life | 0.00% |
| Normalized price >5% from same-cycle median (catches unit or lot-size mistakes) | 0.00% |
| Previous Close != prior row's Close | 0.74% (14 rows), all right after a no-trade day |

On a no-trade day the file's Close repeats the old price; MCX's actual settlement for that day only
appears as the next day's Previous Close. These rows are flagged `no_trade` and never used in pairs.
Same-cycle deviations: median 0.25%, 99th percentile 1.25%, max 1.67%.

### B. Settlement close vs average traded price (VWAP = turnover / grams traded)
| Measure | Median gap | 90th percentile |
|---|---|---|
| Single contract | 15-24 bp | 55-87 bp |
| Spread between two contracts (gold's move cancels) | 6.5-9 bp | 20-25 bp |

The spread gap shows how far the settlement spread is from where trading actually happened. A median of
~8 bp per pair (~4 bp per leg) means 0 bp slippage is unrealistic and the 5 bp per leg assumption is in a
realistic range. Gaps are unbiased on average (mean -1 to +4 bp).

### C. 95% margins on the main numbers (week-block bootstrap)
| Quantity | Estimate | 95% interval | Margin, % of estimate |
|---|---|---|---|
| Mean spread PETAL-TEN | 80.4 bp | 71.7 to 90.1 | +/-11% |
| Mean spread GUINEA-TEN | 63.7 bp | 53.7 to 74.4 | +/-16% |
| Mean spread GUINEA-PETAL | -8.0 bp | -20.0 to +5.6 | +/-159% (not different from zero) |
| TEST net P&L, 0 bp | +10,292 | +847 to +23,140 | +/-108% |
| TEST net P&L, 5 bp | -4,466 | -9,849 to +2,350 | +/-137% |
| TEST net P&L, 10 bp | -19,224 | -25,405 to -13,824 | +/-30% |

The GOLDTEN discount is measured to within about +/-11-16%. The strategy P&L is not: its margin is
larger than the estimate itself at realistic slippage.

## Precision of all four contracts (`accuracy.py`)

### Cost of carry, measured from the data (% per year, adjacent expiries of the same symbol)
| Year | GOLDM | GOLDTEN | GOLDGUINEA | GOLDPETAL |
|---|---|---|---|---|
| 2025 | 5.05 | 4.52 | 5.49 | 5.30 |
| 2026 | 8.27 | 9.26 | 11.38 | 10.25 |
The four contracts agree within each year. GOLDM expires ~5 days after its partners, so it is moved to
the partner's expiry with the same-day carry (median adjustment ~8 bp).

### All six pairs, per gram of pure gold (a minus b), settlement close
| Pair | Mean | 95% interval | Same sign in cycles |
|---|---|---|---|
| GOLDM - GOLDTEN | +4.1 bp | -0.7 to +9.0 | 5/7 |
| GOLDM - GOLDGUINEA | -60.3 bp | -74.1 to -47.9 | 6/6 |
| GOLDM - GOLDPETAL | -79.5 bp | -91.0 to -68.7 | 7/7 |
| GOLDTEN - GOLDGUINEA | -63.7 bp | -74.5 to -53.6 | 7/7 |
| GOLDTEN - GOLDPETAL | -80.4 bp | -90.2 to -71.1 | 8/8 |
| GOLDGUINEA - GOLDPETAL | -8.0 bp | -19.9 to +6.6 | 3/7 |

- GOLDM (100 g, 995) and GOLDTEN (10 g, 999) are priced the same per pure gram. This independently
  confirms the purity normalization: an error there would show up as a ~40 bp gap.
- The premium sits on the small contracts: GUINEA (8 g) ~60-64 bp and PETAL (1 g) ~80 bp above the bars.
- Using the day's average traded price (VWAP) instead of the settlement close leaves the levels unchanged
  and lowers daily spread noise by 5-9% (except GUINEA-PETAL).

### Precision per contract
| Contract | Median kg traded/day | No-trade days | Close vs VWAP, median |
|---|---|---|---|
| GOLDM | 352.4 | 0.40% | 22.5 bp |
| GOLDTEN | 17.1 | 0.74% | 24.4 bp |
| GOLDGUINEA | 5.8 | 1.72% | 17.6 bp |
| GOLDPETAL | 10.0 | 0.18% | 17.9 bp |

GOLDM trades 20-60x more gold than the others, so it is the most reliable reference price.

### Margin with the holdout data
Margins shrink with the square root of independent weeks. Assuming similar variability, ~60 more weeks
(Aug 2025 - Sep 2026) would take TEN-PETAL from +/-9.5 to about +/-5.8 bp and GOLDM-TEN from +/-4.9 to
about +/-2.9 bp.

## GOLDM-anchored fair-price strategy (`fairvalue.py`), pre-registered 2026-10-01

Built from the precision result: GOLDM is the most liquid and agrees with GOLDTEN per pure gram, while
GUINEA and PETAL carry a stable premium. For each smaller contract X, fair price = GOLDM moved to X's
expiry with same-day carry + X's usual premium (mean of all previous days, past only). Trade when X's
premium is k standard deviations away from usual; buy the cheap side, sell the other, 200 g per leg.
Fills at the next day's average traded price. One position per contract type at a time. Exits:
premium back to usual, 5 business days before expiry, or end of window.

Windows, declared before any holdout data was downloaded:
- DEV: market days up to 2025-08-05 (every day seen in any file analyzed before).
- HOLDOUT: 2025-08-06 to 2026-05-29, market days in none of the files analyzed so far. Days from
  2026-06-01 were seen through the Nov 2026 - Feb 2027 contracts and are not used for evaluation.

DEV results (in-sample: k was chosen here), Rs, 200 g per leg:
| k | Trades | Net at 0 / 5 / 10 bp |
|---|---|---|
| 1.0 | 15 | +102,931 / +47,069 / -8,792 |
| 1.5 (chosen by the declared rule) | 8 | +107,802 / +78,186 / +48,571 |
| 2.0 | 4 | +60,283 / +45,459 / +30,635 |

Robustness of k=1.5 at 5 bp:
- Fills at next-day close instead of VWAP: +91,670 (not an artifact of VWAP).
- 95% interval (week blocks): +4,279 to +197,647, but from only 5 independent weeks.
- 4 of the 8 trades and about 80% of the profit come from the gold swings of 1-15 April 2025; without
  them, 4 trades make +15,502.

Reading: GUINEA and PETAL overshoot GOLDM in sharp gold moves and return to their usual premium within
days. DEV supports the idea but cannot prove it; the sealed HOLDOUT is the test.

## HOLDOUT results (run once, 2026-10-01, after 39 new files: Aug 2025 - May 2026 contracts)
Data check first: 70 contracts, 0 integrity errors. 6 rows were >5% from same-cycle peers; all are
GOLDM on 21, 29 and 30 Jan 2026, when gold crashed about 10% in a day and GOLDM settled at its day low
(lower price band) while the small contracts settled higher. Real data, kept, no rule changed.
GOLDM expiring May 2026 was not downloaded, so the Apr 2026 cycle is missing from the fair-price test.

### Fair-price strategy (k = 1.5 frozen; 200 g per leg; next-day VWAP fills), 2025-08-06 to 2026-05-29
| Slippage | Trades | Gross | Costs | Net | Hit rate |
|---|---|---|---|---|---|
| 0 bp | 12 | 86,572 | 11,764 | +74,808 | 83% |
| 5 bp | 12 | 86,572 | 73,582 | +12,990 | 58% |
| 10 bp | 12 | 86,572 | 135,400 | -48,828 | 25% |
- 95% interval at 5 bp (week blocks): -18,671 to +50,806; 75% of draws positive; only 6 entry weeks.
- GUINEA +27,799 (4 trades), PETAL +6,877 (3), TEN -21,686 (5). Works where the premium is real
  (GUINEA, PETAL); on TEN, where there is no premium, it trades noise and loses.
- The GUINEA/PETAL premium over bars roughly doubled in 2026 (to ~130-140 bp), so the past-only
  "usual premium" lagged and positions were held up to 107 days.

### Same-expiry z-score baseline (frozen N=10, z=2.0; 40 g per leg; settlement fills), 2025-08-01 on
| Slippage | Trades | Net | 95% interval | Share of draws > 0 |
|---|---|---|---|---|
| 0 bp | 156 | +365,755 | +50,445 to +813,603 | 100% |
| 5 bp | 156 | +190,340 | -97,634 to +619,835 | 86% |
| 10 bp | 156 | +14,926 | -251,631 to +401,270 | 50% |
- All of it comes from January 2026: 30 trades made +267,750 at 5 bp; the other 126 trades lost
  -77,410 (hit rate 27%). The top 5 January trades are 54% of the total.
- Repriced at each day's VWAP instead of settlement: +168,114 (January +228,317, rest -60,204).

### Verdict
Neither strategy has a dependable edge at 5 bp outside one extreme month. The z-score baseline earns
money only when gold moves violently and the small contracts lag (Jan 2026); in normal months it
loses after costs, as it did in TRAIN. The fair-price strategy stayed positive at 0-5 bp on
GUINEA and PETAL, but with 6 independent weeks its interval includes zero. What the data does
establish firmly: per gram of pure gold GOLDM = GOLDTEN, and GUINEA/PETAL carry a persistent premium
that widened from ~60-80 bp (2025) to ~130-140 bp (2026).

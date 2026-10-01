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

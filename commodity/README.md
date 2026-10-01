# Gold spread analysis (MCX GOLDTEN / GOLDGUINEA / GOLDPETAL)

## Setup (once)
Put `ingest.py`, `backtest.py` and this README in the same folder as `raw_clean/`
(for you: `~/Documents/commodity/data/`). Then:

    source ~/Documents/commodity/venv/bin/activate
    cd ~/Documents/commodity/data
    pip install pandas lxml numpy

## Run
    python ingest.py            # validates every file, writes clean/gold_futures.csv
    python backtest.py train    # sweep on dates <= 2025-04-30, applies the pre-declared rule
    python backtest.py test     # ONLY after more data is added and you agree; runs once
    python backtest.py holdout  # second sealed test, 2025-08-01 to 2026-09-30, runs once

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

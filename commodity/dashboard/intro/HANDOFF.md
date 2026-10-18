# Prototype handoff: glass v2, phone layout, 3D scroll intro

Branch `glass-proto`. Nothing here is on `main` or the live site yet.

## 1. Glass v2 + phone layout (approved)
Already wired into the site on this branch:
- `app/styles.css`, block **GLASS v2 + PHONE RHYTHM**:
  - Warmer gold ambient lights.
  - Frosted panel tokens (`--g-fill`, `--g-rim`, `--g-hi`, `--g-shadow`, `--g-blur`).
  - Real `backdrop-filter` only on large panels, and only on laptops (`hover:hover`, `pointer:fine`, ≥1101px).
  - Phone rhythm: 16px sides, 20px inside cards, 12px between tiles, 24px between sections.
  - Equal-height 2-up number tiles; the "on this page" chips become one swipeable row.
- `app/main.jsx`: `useSheen()` makes a soft reflection follow the mouse across `.card`, `.take` and `.more`.

To ship:
1. Rebuild with `node dashboard/build_app.mjs && python3 dashboard/build.py`.
2. Run `python3 tools/run_tests.py`, then restore `results/test_report.json`.
3. Merge to `main`, then force-push `main:holdout-2`.

Check the phone layout on a real iPhone. The headless browser used for screenshots doesn't render `backdrop-filter`.

## 2. 3D scroll intro (prototype, not wired in)
- `intro/intro.tpl.html` (page) and `intro/gen.py`. `gen.py` fills every figure from `dashboard/data.json` and writes `intro.html`.
- Uses three.js **0.170.0** via an importmap (jsDelivr), plus `RoomEnvironment` and `RoundedBoxGeometry`.
- Six beats: problem → per gram → cost line → ±1.5σ check → evidence → team.
- The camera holds still while each card is read, then glides to the next beat.
- Phones step the camera back and put the gold above the card.
- Reduced motion turns off smoothing and bobbing.
- If frames run long, the resolution drops a step.
- `intro/shot.py` takes screenshots of each beat (desktop or phone). It needs three r170 in `intro/node_modules/three`.

Suggested integration (the team had no preference; this is the default):
- Serve the intro at `/intro`.
- Show it once per browser session before the site, with **Skip intro** always visible. Put a "Replay intro" link in the footer.
- Returning visitors go straight in.
- Re-run `gen.py` in the daily chain so the intro's numbers stay current.

## Also noticed
- On 17 Oct the second daily run committed with the message "Daily data: MCX Bhavcopy through  (+ rows)", with the date and row count blank. It probably ran when there were no new rows. Make it skip the commit, or write "no new rows".

# Prototype handoff: glass v2, phone layout, 3D scroll intro

Shipped on `main` (live at https://parity-gold-site.vercel.app, intro at https://parity-gold-site.vercel.app/intro).

## 1. Glass v2 + phone layout (approved)
Already wired into the site on this branch:
- `app/styles.css`, block **GLASS v2 + PHONE RHYTHM**:
  - Warmer gold ambient lights.
  - Frosted panel tokens (`--g-fill`, `--g-rim`, `--g-hi`, `--g-shadow`, `--g-blur`).
  - Real `backdrop-filter` only on large panels, and only on laptops (`hover:hover`, `pointer:fine`, ≥1101px).
  - Phone rhythm: 16px sides, 20px inside cards, 12px between tiles, 24px between sections.
  - Equal-height 2-up number tiles; the "on this page" chips become one swipeable row.
- `app/main.jsx`: `useSheen()` makes a soft reflection follow the mouse across `.card`, `.take` and `.more`.

To rebuild after a change:
1. Rebuild with `node dashboard/build_app.mjs && python3 dashboard/build.py`.
2. Run `python3 tools/run_tests.py`, then restore `results/test_report.json`.
3. Push to `main`, then force-push `main:holdout-2`.

Check the phone layout on a real iPhone. The headless browser used for screenshots doesn't render `backdrop-filter`.

## 2. 3D scroll intro (wired in: served at /intro)
- `intro/intro.tpl.html` (page) and `intro/gen.py`. `gen.py` fills every figure from `dashboard/data.json` and writes `intro.html`.
- Uses three.js **0.170.0** via an importmap (jsDelivr), plus `RoomEnvironment` and `RoundedBoxGeometry`.
- Nine beats: problem → recast → per gram → every day → cost line → ±1.5σ check → quiet → evidence → team.
  - **Recast:** each piece melts into grains that pour into four identical cubes, one gram of pure gold each.
    Labels show the pure grams per quote; `gen.py` checks that close ÷ pure grams matches `rs_per_g`.
  - **Every day:** a 3D ribbon per contract shows its distance from its usual premium (`hurdle`, thinned 3:1 keeping peaks).
    It draws left to right with scroll, with a dated bead on the leading edge.
  - **Quiet:** every alert episode (`alerts.history`) sits on a dark three-lane rail. A scanner sweeps across with scroll,
    and each flare rises as it passes. A counter tallies the alerts so far.
- The camera holds still while each card is read, then glides to the next beat.
- Phones step the camera back and put the gold above the card.
- Reduced motion turns off smoothing and bobbing.
- If frames run long, the resolution drops a step.
- `intro/shot.py` takes screenshots of each beat (desktop or phone). It needs three r170 in `intro/node_modules/three`.

Integration (done):
- `gen.py` also writes `intro/index.html`, a full page. `tools/vercel_build.sh` copies it to `site/intro/index.html`, so it is served at `/intro`.
- `template.html` sends the first visit of each browser session from `/` to `/intro`. It sets the
  `sessionStorage` flag `parity:intro` before leaving, so the redirect can't loop. These go straight to the site:
  deep links (`/#section`), `?nointro`, `file://`, the artifact copy, and bots or headless browsers.
- **Skip intro** stays in the top bar. The footer has a "Replay intro" link.
- `tools/daily_update.py` runs `gen.py` after `build.py`. The daily workflow runs it again after the tests and commits `dashboard/intro/index.html`.

Motion (open-source, MIT, pinned on jsDelivr):
- **Lenis 1.3.26** (darkroomengineering/lenis) for smooth wheel scrolling. Phones keep native touch scrolling. A card that scrolls inside itself keeps its own wheel.
- **Motion 13.4.6** (motiondivision/motion):
  - Headlines rise word by word out of a mask.
  - Card text and rows follow in a stagger with a light blur.
  - Numbers roll into place digit by digit, like an odometer, and finish on the exact string from `data.json`.
  - Each card gets a gold-foil glint as it settles.
  - On desktop, a ticker tape of the four quotes runs along the bottom. It speeds up and leans with scroll velocity.
  - The chapter counter (bottom left) rolls like an odometer.
- Cards tip back and rise into place with scroll. The gold headline sheen tracks scroll. The "how we know" slabs fan open with scroll.
- The gold no longer spins on its own. Only a small slow float and sway remain on the first and last beats.
- Arrow keys and Page Up/Down step between beats.
- Reduced motion turns all of this off. If either library fails to load, the intro still works without it.

## Also noticed
- Fixed: on 17 Oct the second daily run committed with the message "Daily data: MCX Bhavcopy through  (+ rows)".
  When MCX has no new rows, `daily_update.py` now writes `updated=false`. The workflow then skips the tests and the commit.

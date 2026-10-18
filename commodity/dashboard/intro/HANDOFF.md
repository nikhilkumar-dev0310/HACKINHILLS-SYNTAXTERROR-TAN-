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
- `template.html` sends anyone who opens the site's link from outside the site to `/intro`, every time.
  These go straight to the site:
  - reloads and back/forward;
  - arrivals from the site's own pages (same-origin referrer), such as the intro's Enter and Skip;
  - deep links (`/#section`) and `?nointro`;
  - `file://`, the artifact copy, and bots or headless browsers.
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

## Scroll model and performance (19 Oct 2026)
- **Continuous scrub.** The old model held each beat still for its first third. Now scroll maps linearly to scene time
  (`sceneB()`), so every pixel of scroll moves something.
  - Beats are 280vh (230svh on phones), so the pace is slower.
  - A scene peaks when its card sits mid-screen (`LEAD = 0.25`).
  - The camera follows a centripetal Catmull–Rom curve through the beat keys and never stops.
- **Centrepieces.**
  - Per gram: a beam balance swings, then settles almost level. Its tilt is the spread, exaggerated.
  - Unusual?: GOLDPETAL's bell curve, with the ±thr tails lit as alert zones. Today's z drops onto it.
  - How we know: a vault wheel turns and the door swings open. The rows pour out as gold bars, and the three counts slide out on plaques.
  - Team: the recast grains forge the Parity two-bar mark (the site's logo path).
- **Touches.**
  - The pieces drop in on arrival, with a dust puff on landing.
  - Dust trails along the camera path appear with scroll speed.
  - Focus pulls blur the 3D stage up to 1.6px between beats, on laptops only, and stop once resolution has dropped.
- **Frame rate.**
  - Fake glass instead of transmission, which rendered the scene twice.
  - No live backdrop blur over the canvas on cards or labels.
  - Film grain baked into the backdrop instead of a blend layer.
  - The dust cloud rotates as a whole instead of updating every mote on the CPU.
  - Layout reads are batched, and beat positions are cached.
  - Shaders are precompiled at load. The old build froze for about 1 s the first time a scene appeared.
  - Adaptive resolution, both down and up. When nothing moves, frames render at half rate.
  - Measured on a Mac at 1280×800, scrolling the whole intro in 600 frames: worst frame 18 ms, none over 33 ms.
    The previous build had 3 frames over 33 ms, the worst at 1016 ms.

## Polish (19 Oct 2026, later)
- The coin turns its face to the camera every frame, so it always reads as a circle, and it still tilts with the balance beam.
- The balance and the vault are steel and graphite, so the gold they hold contrasts with them.
- The vault river has 900 bars (380 on phones), packed tighter and flowing faster.
- Recast cubes are 6×6×6, so 864 grains forge a finer Parity mark at the finale.
- Opening: the camera sweeps down from overhead (about 3 s on arrival) into a low hero angle at table height.
  Phones step back slightly so all four pieces fit.
- Finale, once the scroll ends:
  - the camera parallax deepens;
  - the mark tilts toward the cursor;
  - grains near the cursor scatter and spring back;
  - the ring of pieces swings with the cursor.
  On touch screens this starts only once the finale is reached.

## The treasure room (19 Oct 2026)
- **Portal.** Behind the vault door is a full treasure room. A stencil portal (`portal`, `roomMats`) means it is seen only
  through the open doorway until the camera passes the door plane. After that it surrounds you, and the finale's forge
  happens inside it. The finale pieces and grains are also stencil-tested while the camera is outside, so they never
  show around the vault.
- **Contents**, all instanced:
  - stacked bar pyramids along the walls and at the back;
  - coin mounds and coin towers;
  - chalices, orbs and nuggets;
  - two warm lamps.
  The centre stays low and clear behind the mark.
- **Blur and depth.**
  - Fog closes in only inside the vault. It is a uniform change; the fog itself is set up at load so no shader recompiles.
  - Soft bokeh discs drift in the air.
  - Billboarded light shafts fall from above.
  - The field of view kicks wider for a moment as you pass the door.
- **Phones** step back less as they head into the vault, so they end up inside.
- **Light theme:** the top bar switches to light ink and a dark pill inside the vault (`html.in-vault`).
- **Frame rate:** a full scroll still holds 60 fps on the Mac test machine (worst frame 18 ms).

## Balance, vault and interior redesign (19 Oct 2026)
- **Balance:** a precision balance.
  - A stepped graphite plinth with a steel trim ring, and a fluted steel column between collars.
  - A tapered steel beam with four graphite cradles and a jewel bearing at the hub.
  - A graduated dial (5° ticks, centre tick lit) that the needle reads as the beam settles.
- **Vault:** a bank-vault door set in a riveted graphite wall plate, with a stepped steel frame, two hinge barrels,
  a door with stepped concentric rings, a five-spoke wheel with knobs, and a combination dial.
  - Sequence: the dial spins, the wheel turns, ten radial locking bolts draw back, then the door swings open.
- **Interior:**
  - Panelled bronze-brown walls and dark stone tiles, both as canvas textures.
  - Two warm lamps, plus a warm fill light that rises only inside (an intensity change).
  - Lighter, thinner fog and subtler bokeh.
  - The walls are kept deep so the gold contrasts.
- `resize()` ignores a zero-size viewport. A page that loaded while hidden logged a NaN bounding-sphere error.
- **Frame rate:** a full scroll holds 60 fps once the page has settled (worst frame 18 ms on two runs).
  The first pass straight after load can show a few slow frames while shaders finish compiling.

## Vault set, fuller room, finale placement (19 Oct 2026)
- **Default:** opening https://parity-gold-site.vercel.app from anywhere outside the site always plays the intro (see `template.html`).
- **Vault:**
  - It is set into a stone ashlar wall over a stone floor (`vaultSet`); the wall and floor rise into place with it.
  - A soft contact-shadow ring sits round the door.
  - Brushed-steel and mottled-graphite finishes.
  - The portal and the room's front face sit just behind the wall, so the fly-through never goes dark.
- **River:** it waits until the door is well open, then each bar leaves from its own point across the doorway, spills forward and falls.
- **Room:**
  - stone pillars along both walls, and steel shelving stacked with bars between them;
  - six open chests brimming with coins, and loose coins across the floor (the camera's aisle stays clear);
  - more bar stacks and coin mounds.
- **Finale:** the cursor-reactive mark sits up and to the right on laptops, and stays centred above the card on phones.
- **UI:** a larger Enter Parity button, and a dark band behind the price tape in both themes.
- **Fixes:**
  - The bokeh count was fractional (80/3), which caused the NaN bounding-sphere error. It is now rounded.
  - Textures are uploaded to the GPU at load.

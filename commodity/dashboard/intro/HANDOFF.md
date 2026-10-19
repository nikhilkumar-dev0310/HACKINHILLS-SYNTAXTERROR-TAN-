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
- Opening ("true scale", 19 Oct): the camera starts close on the 1 g GOLDPETAL piece and the first scrolls pull back past the 8 g coin and the 10 g bar to the 100 g bar, while a mass counter (top right) steps 1 g, 8 g, 10 g, 100 g. It replaces the drop-in opening. `OPEN_B`, `ZOOM` and `MASS_AT` in `intro.tpl.html` set it.
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

## Pari, a dense hoard, a richer room (19 Oct 2026)
- **Pari**, the gold-bar mascot from the demo (`presentation/round2/pipeline/render_pari3.py`), is built in 3D for the finale:
  - an ingot body with eyes and a smile, stick arms and legs;
  - stands on its own coin peak; on laptops below-left of the mark, on phones right of it;
  - hops up as the finale arrives, then waves, blinks and bobs, and turns to follow the cursor;
  - a "Hi, I'm Pari" bubble appears on laptops.
- **The hoard is solid** (it no longer reads as see-through):
  - One coin-textured gold dune (`dH`) is banked against the walls, rises behind the forge and swells into mounds.
  - The camera's aisle stays clear.
  - Bars, coins (4,200 on laptops), coin towers, chalices, urns, orbs, nuggets and stray bars all sit on its surface.
- **Variety:**
  - jewels (ruby, emerald, sapphire, amethyst, diamond) and jewelled crowns;
  - gold shields leaning on the piles;
  - two candle chandeliers;
  - shelves whose lowest levels are buried in gold.
- **Chests**, rebuilt:
  - planked wood with brass straps, corners and rims, and a lock plate;
  - a domed lid with end caps and brass bands;
  - a heap of coins inside, and coins spilling over the front.
- **River:** coins tumble edge over edge with the bars.

## Metal and overlaps pass (19 Oct 2026)
- **Reflections:** the environment is now a lit studio built in code, which is what makes the gold read as polished metal.
  - light warm-neutral walls, a broad overhead softbox, tall side softboxes;
  - a warm front fill, dark contrast bands, and two hot keys.
  - All gold is tuned to it: metalness 1, roughness 0.14–0.3, with clearcoat on the hero pieces.
  - `RoomEnvironment` is no longer used.
- **Overlaps removed:**
  - the glass plaques at the vault (the card lists the same counts);
  - the ring of four pieces round the finale's mark;
  - the second chandelier, which sat cut off at the top of the finale.
- **Layout fixes:**
  - the stone wall is wider and taller, so its edge never shows;
  - the balance's coin rides smaller, clear of the dial;
  - Pari stands on a broad, smooth rise below the mark, with clutter kept off it, and the greeting sits beside Pari.
- **Numbers** count up as plain tabular text instead of rolling digit strips, so nothing shifts or overlaps mid-animation.

## Real models, no phasing, a plain stage for the mark (18 Oct 2026)
- **Props are real CC0 models from Poly Haven**, repacked to 2.2 MB in `intro/models/` (credits in `models/CREDITS.md`):
  - treasure chest, brass goblets, two brass vases and a brass pot;
  - a chandelier, lion heads on the walls, kite shields and an ornate dagger.
  - They load in the background with `GLTFLoader` + `MeshoptDecoder` and are stencil-tested like the rest of the room.
  - `tools/vercel_build.sh` publishes the folder to `/intro/models/`.
- **Removed:** every hand-built prop (shelves, pillars, crowns, gems, urns, chalices, orbs, the procedural chests and
  chandelier) and the coin towers. Bars, coins and the gold dune remain.
- **Nothing passes through anything:**
  - one coin per 13 cm cell, lying close to the surface;
  - no stray bars, and no jitter in the stacks;
  - the pieces stand in front of the bar columns, and leave the stage forward rather than down through the balance;
  - the gold river spills away from the open door and never through the floor;
  - the mark's grains gather from the air above and in front.
- **The mark** sits on a plain, soft-edged dark backdrop, so the cursor's scatter reads clearly.
- **Reflections:** a photographed HDRI was tried. Its pure-white softboxes washed the gold to silver, so the warm built
  studio stays.
- **Scroll mapping** guards against a zero-size viewport (a hidden tab measured 0 and crashed the camera curve).

## Real gold models, real shadows, open chests, a livelier Pari, no lag at the vault (18 Oct 2026)
- **The gold is real CC0 models from TextureCan** (credits in `models/CREDITS.md`):
  - a stamped "FINE GOLD 999.9" bar and a coin, kept as mesh plus normal map (the colour stays the intro's own gold);
  - the coin's $ was replaced on both faces by an embossed Parity mark;
  - `gold_coin_plain.glb` has plain faces, for the GOLDGUINEA piece, which carries its own engraving.
  - They are used for the room's stacks, stray bars, loose coins and coin towers, for the river, and for the shapes of
    the four pieces on stage. Each piece is fitted to its old bounding box, so poses, grains and labels are unchanged.
  - Until they load (14–23 KB each), same-size stand-ins hold their places. The materials carry a 1 px flat normal map
    from the start, so the swap needs no new shader.
- **Nothing intersects in the room:**
  - every chest, pile, prop, shield, dagger, stray bar and coin tower claims floor space first;
  - coins are Poisson-spaced at least a coin's width apart and lie along the dune's surface;
  - stacks are stepped like brickwork and sit on the lowest point under their footprint.
- **The river runs in lanes:**
  - each piece has its own scattered lane across the doorway (at least 12.5 cm apart) and a fixed place along it, and all
    pieces move at one speed, so no two pass through each other;
  - pieces near the lens shrink away, so the camera never flies through one;
  - the pieces are now at true proportions.
- **Chests:**
  - four of seven are open: the lid and hasp turn back on the hinge, with a heap of gold and coins inside;
  - all are sunk a little into the gold, with a spill of coins in front.
- **Pari:**
  - the peak is flattened where Pari stands, and its soles rest on the gold through every squash, so no feet sink in;
  - it pops in just above the peak and drops onto it (phones: it pops up in place, smaller, under the mark);
  - it then breathes, sways, blinks at uneven moments (sometimes twice), and turns to the cursor with a lag, leaning
    into the turn;
  - every few seconds it does something different, never the same twice running: wave, hop, look around, point up at
    the mark, cheer or spin, each eased in and out with squash and stretch.
  - It keeps the studio's bright reflections, like the four pieces.
- **Realism:**
  - **Shadows:** the chandelier's lamp is a shadow-casting spot (2048² map, PCF soft), drawn once (`shadowMap.autoUpdate`
    off) from the chests, piles and props.
  - **Contact shade:** soft shade round everything standing on the dune, and in its low ground, is baked into the dune's
    vertex colours.
  - **Reflections:** room materials reflect the room (`roomEnv`: bronze walls, a lamplit ceiling, a floor of gold, the
    chandelier, glints), built like the studio; a live cube capture would have compiled a second set of shaders.
  - **Variety:** every bar and coin has a slightly different shade (instance colours).
  - **Glints:** a small shader of points that flash briefly on stack tops, coin towers, heaps and loose coins.
- **The mark's background:**
  - no dark plate: the back wall behind the mark is a plain pool of warm lamplight;
  - the back of the dune stays low behind it, and no light shaft, pile or bokeh sits between the camera and the mark.
- **The vault door is solid:** the door and frame are lathes (open shells), now drawn on both faces. Seen from behind
  once it swung open, the door used to vanish.
- **The lag before the vault came from three things, all fixed:**
  - **Lights:** the room's lamps were inside the room group, so they left the scene's light count while the room was
    hidden. Every model material then compiled without them and recompiled the moment the room appeared. The lamps now
    hang at the top of the scene; only their intensity changes.
  - **Drawing too early:** the room was drawn from 0.6 beats before the vault while the door was still shut. It now
    draws only once the door starts to open.
  - **First-use costs:** buffers, textures and shadows are paid in a staged warm-up. Once the models are in and the
    reader is idle after the opening (or at the latest when the vault rises), the room is drawn unseen over three frames
    (its stencil test fails while the doorway is hidden).
  - Measured at 1024×640: a first-pass sweep from beat 6 through the vault into the finale held 60 fps (worst frame
    17.7 ms). The one-time warm-up is about 70–100 ms, early on.
- **The props were re-packed lighter:**
  - the chest is 24k triangles, from 79k;
  - the lion head, chandelier and first vase were simplified;
  - the models folder is 1.9 MB.
- **`?debug`** exposes `window.__intro.at(b)` (pin the story to scene time `b`) and `window.__scene`, for checking a
  scene by hand.
- **Tests:** the machine's Python 3.15 beta now segfaults on `import numpy.random`. The suite was run in a scratch
  Python 3.12 venv built from `tools/requirements.txt` plus scipy: 10,357 passed, 0 failed.


## Pari answers clicks, detailed coin piles, true gold colour (18 Oct 2026)
- **Clicking (or tapping) Pari** in the finale picks a reaction, never the same twice running:
  - **giggle:** squinting, grinning, wobbling;
  - **boing:** squashed flat, then sprung up tall;
  - **twirl:** two spins with the arms out;
  - **surprise:** wide eyes, arms up.
  - The bubble shows a matching line for 2.6 s ("Hee hee, that tickles!", "Boing!", "Wheee!", "You found me!").
  - Ten coins hop up from a ring just outside Pari, land on the gold around it (never under its feet, never on
    another coin), lie flat and fade.
  - **Clicking elsewhere in the room:** Pari turns towards the spot and points that way.
  - The cursor becomes a hand over Pari.
  - Clicks on the card, links, buttons and chapter dots are ignored.
  - With reduced motion, Pari does not react.
  - **Phones:** jump heights are a quarter, and Pari comes in at the very end of the scroll, so nothing reaches the mark
    above.
- **Coin piles have real detail:**
  - **Surface:** the hoard's surface is a generated colour and normal map of about 300 coins lying on coins
    (1024², 512² on phones). Each coin has its own tilt, a bevelled edge, a raised rim ring and the Parity mark struck on
    most, and casts a soft shadow onto the coins beneath.
  - **Built in idle time:** the textures are drawn a few dozen coins at a time in `requestIdleCallback`, so no frame
    waits, and they swap in without a shader change.
  - **3D coins:** there are now 2,700 (1,000 on phones), with about a fifth standing half-buried at an angle, edge up,
    and 40 coin towers. The finale draws 1.16M triangles in 183 calls.
- **Gold colour:** gold's colour is its reflectance (pure gold reflects about 1.00, 0.77 and 0.34 of red, green and
  blue, linear).
  - The old values (`0xffc95a` and similar) were pushed well past that, towards orange, and inside the room that
    compounded: gold mirrored a gold-coloured room.
  - All gold now uses `G999 = 0xffd985`, with 995 a shade paler (`G995 = 0xf3d595`). This covers the pieces, river, room,
    Pari, chart columns and the bell's dot.
  - The room's mirrored surroundings are calmer and paler, and the per-piece shades vary in brightness rather than
    drifting red.

## Designer motion, a cursor light, and a Pari to play with (19 Oct 2026)
- **Cursor (laptops):**
  - a soft gold light trails the cursor over the stage (`.cglow`, screen blend; multiply in light mode);
  - the glass card under the cursor catches the light and its border glints near it (`.sheen`, as on the site in dark
    mode);
  - a click sends out a gold ripple;
  - "Enter Parity", "Watch the demo", "Skip intro" and the brand lean towards the cursor (magnetic, using the CSS
    `translate` property so they never fight the card's transform).
- **Cards, all scroll-driven:**
  - each card opens out of a rounded slit as it arrives (an `inset()` clip wipe whose negative inset at rest keeps the
    shadow);
  - it tilts a few degrees towards the cursor and leans with scroll speed (`--tlx/--tly/--sk`);
  - the body text lights up word by word as its scene arrives (one CSS variable per card, `--rp`);
  - the eyebrow decodes like a ticker board;
  - table rules draw in from a gold tip;
  - the gold button's label rolls over on hover, with a shine sweeping across it.
  - All reads happen before all writes in `cardsFrame`, so it is still one layout per frame.
- **Fluidity:** the camera rides a spring a beat behind the scroll (tau 0.13 s), so every move eases in and out, and it
  drifts a breath at rest. Frames keep full rate while the camera is still catching up (`camLag`).
- **Pari:**
  - its eyes follow the cursor (up to the edge of its face);
  - it notices the cursor arriving;
  - **click:** eight reactions, never the same twice running: giggle, boing, twirl, surprise, dance, backflip (phones
    get a boing), shy (hides its eyes) and heart (gold hearts float up). Each has a line in its bubble.
  - **combos:** three clicks within 1.2 s make it dizzy, with stars circling its head; six within 4 s hit the jackpot:
    three bursts of coins and the whole hoard sparkling (a `boost` uniform on the glint shader). Combos play out
    without being interrupted.
  - **press and hold** charges a super jump: it crouches and trembles, then jumps higher the longer you held, with a
    spin. The jump stays under the mark (phones a quarter as high).
  - kicked-up coins fly to the sides and back, never across its face.
- **Reduced motion:** none of it runs.

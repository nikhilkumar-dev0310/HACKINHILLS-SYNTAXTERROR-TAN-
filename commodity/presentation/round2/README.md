# Round 2 demo video

`Parity_demo.mp4`: 1 min 28 s, 1080p, sound on. Published at https://parity-gold-site.vercel.app/demo.html. `Parity_demo.srt` holds every caption, Pari's lines and the words on each card as subtitles; `tests/test_video.py` checks each number in it against the data.

**v4.1 (16 Oct 2026): Pari as a guide, and what we do differently.** Re-shot on data through 14 Oct 2026. Pari, the gold-bar mascot, asks the opening question and reacts with twelve short lines (never repeating a caption); a "What we do differently 1/4 to 4/4" run (every cost, sealed tests, honest reporting, the luck test); the honest twist; a "How close are we?" card that ticks off the brief line by line and names the one open gap. The site footage plays at real speed in a rounded frame; focus is the camera's framing with a softened, darkened surround (no outlines); camera moves carry motion blur. Sound: one family of soft mallet tones in the music's key, placed just above the music; music changes on the beat with one-bar fades and an opening filter; risers end in a reverb tail; mastered to −16 LUFS, −1.5 dBTP. Research and rules: [`ENGAGEMENT.md`](ENGAGEMENT.md), v4 section.

To rebuild: `python3 pipeline/capture4.py` (about 25 min; writes `frames4/` and `timeline4_capture.json`; the edit decisions are in `timeline4.json` and Pari's extra lines in `banter4.json`), then `pipeline/run4.sh` (about 15 min) writes `Parity_demo_v4.mp4` and `.srt`, which are copied over the published names.

## Previous cut (v3, 8 Oct 2026)

A story, not a tour. It opens on the strategy's profit on unseen data and asks why we aren't trading it; asks the viewer to guess whether any gap is worth trading today before revealing the answer; shows four fast proofs (23 years of MCX data, slippage you control, the typical-report-vs-ours switch, the contract calendar and the sealed years); then the peak, "Too good to be true?", and the honest twist (January 2026 made the money; outside the crash the rule loses; picking the best of 72 settings is mostly noise); and ends on a true open question: tomorrow's answer is on the live site, not in the video. Why each choice was made, with the research behind it: [`ENGAGEMENT.md`](ENGAGEMENT.md). A voice-over script is in [`VOICEOVER.md`](VOICEOVER.md); save a recording as `pipeline/voice.wav` and rebuild, and the music ducks under it.

To rebuild: `python3 pipeline/capture3.py` (about 20 min), then `pipeline/run3.sh` (about 10 min). Every number on screen is read from `dashboard/data.json` or the page itself, so a rebuild always matches the site.

## Previous cut (v2, kept reproducible)
Structure: a 15-second hook (four prices, one gold), eight chapters that each answer one question (front page, the brief, relative value, term structure, backtest, signals, contracts, data quality), and a recap with the team and a QR code to the live site. Re-shot on 7 Oct 2026 on the current site (data through 6 Oct 2026); chapter 8 now shows the daily automatic update. Every number in a caption is read from `dashboard/data.json`, so a re-shoot always matches the site.

To re-shoot: `python3 pipeline/capture.py` (about 30 min on 2 CPUs), then `pipeline/run_fast.sh` (about 10 min).

## How it is made (`pipeline/`)
1. `capture.py` drives the dashboard frame by frame on a paused clock, so every frame is exact: guided cursor, clicks, scrolling, slider drags, search. It writes `frames/` and `timeline.json`.
2. `render_overlays.py` renders the intro, chapter cards, outro, captions and the Pari mascot from `overlays.html`.
3. `compose.py` adds camera moves, captions with Pari, chapter cards and the progress bar.
4. `audio.py` synthesises the music bed and interface sounds from the timeline; `make_srt.py` writes the subtitles.

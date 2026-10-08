# Round 2 demo video

`Parity_demo.mp4`: about 1 min 45 s, 1080p, with a music bed whose intensity follows the story, quiet sound effects synced to what happens on screen, and a subtle visual attention layer (breathing camera, spotlight, caption light sweep, bloom on the key moments). `Parity_demo.srt` holds the captions as subtitles.

**v3 (8 Oct 2026): a story, not a tour.** It opens on the strategy's profit on unseen data and asks why we aren't trading it; asks the viewer to guess whether any gap is worth trading today before revealing the answer; shows four fast proofs (23 years of MCX data, slippage you control, the typical-report-vs-ours switch, the contract calendar and the sealed years); then the peak, "Too good to be true?", and the honest twist (January 2026 made the money; outside the crash the rule loses; picking the best of 72 settings is mostly noise); and ends on a true open question: tomorrow's answer is on the live site, not in the video. Why each choice was made, with the research behind it: [`ENGAGEMENT.md`](ENGAGEMENT.md). A voice-over script is in [`VOICEOVER.md`](VOICEOVER.md); save a recording as `pipeline/voice.wav` and rebuild, and the music ducks under it.

To rebuild: `python3 pipeline/capture3.py` (about 20 min), then `pipeline/run3.sh` (about 10 min). Every number on screen is read from `dashboard/data.json` or the page itself, so a rebuild always matches the site.

## Previous cut (v2, kept reproducible)
Structure: a 15-second hook (four prices, one gold), eight chapters that each answer one question (front page, the brief, relative value, term structure, backtest, signals, contracts, data quality), and a recap with the team and a QR code to the live site. Re-shot on 7 Oct 2026 on the current site (data through 6 Oct 2026); chapter 8 now shows the daily automatic update. Every number in a caption is read from `dashboard/data.json`, so a re-shoot always matches the site.

To re-shoot: `python3 pipeline/capture.py` (about 30 min on 2 CPUs), then `pipeline/run_fast.sh` (about 10 min).

## How it is made (`pipeline/`)
1. `capture.py` drives the dashboard frame by frame on a paused clock, so every frame is exact: guided cursor, clicks, scrolling, slider drags, search. It writes `frames/` and `timeline.json`.
2. `render_overlays.py` renders the intro, chapter cards, outro, captions and the Pari mascot from `overlays.html`.
3. `compose.py` adds camera moves, captions with Pari, chapter cards and the progress bar.
4. `audio.py` synthesises the music bed and interface sounds from the timeline; `make_srt.py` writes the subtitles.

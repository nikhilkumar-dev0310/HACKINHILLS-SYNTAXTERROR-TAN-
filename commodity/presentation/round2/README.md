# Round 2 demo video

`Parity_demo.mp4`: 3 min 16 s, 1080p, 43 MB, captioned, with a light music bed and soft interface sounds. The faster cut is made from the same capture: `pipeline/warp.py` squeezes still moments, plays motion at 1.4x and keeps every caption on screen long enough to read (`compose_fast.py`, `audio_fast.py`, `make_srt_fast.py`). `Parity_demo.srt` holds the same captions as subtitles, and doubles as a narration script if a team member records a voice-over.

Structure: a 15-second hook (four prices, one gold), eight chapters that each answer one question (front page, the brief, relative value, term structure, backtest, signals, contracts, data quality), and a recap with the team and a QR code to the live site. Re-shot on 7 Oct 2026 on the current site (data through 6 Oct 2026); chapter 8 now shows the daily automatic update. Every number in a caption is read from `dashboard/data.json`, so a re-shoot always matches the site.

To re-shoot: `python3 pipeline/capture.py` (about 30 min on 2 CPUs), then `pipeline/run_fast.sh` (about 10 min).

## How it is made (`pipeline/`)
1. `capture.py` drives the dashboard frame by frame on a paused clock, so every frame is exact: guided cursor, clicks, scrolling, slider drags, search. It writes `frames/` and `timeline.json`.
2. `render_overlays.py` renders the intro, chapter cards, outro, captions and the Pari mascot from `overlays.html`.
3. `compose.py` adds camera moves, captions with Pari, chapter cards and the progress bar.
4. `audio.py` synthesises the music bed and interface sounds from the timeline; `make_srt.py` writes the subtitles.

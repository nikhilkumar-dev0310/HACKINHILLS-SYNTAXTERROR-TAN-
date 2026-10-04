# Round 2 demo video

`Parity_demo.mp4`: 4 min 55 s, 1080p, captioned, with music and interface sounds. `Parity_demo.srt` holds the same captions as subtitles, and doubles as a narration script if a team member records a voice-over.

Structure: a 15-second hook (four prices, one gold), eight chapters that each answer one question (front page, the brief, relative value, term structure, backtest, signals, contracts, data quality), and a 15-second recap with the team and a QR code to the repository.

## How it is made (`pipeline/`)
1. `capture.py` drives the dashboard frame by frame on a paused clock, so every frame is exact: guided cursor, clicks, scrolling, slider drags, search. It writes `frames/` and `timeline.json`.
2. `render_overlays.py` renders the intro, chapter cards, outro, captions and the Pari mascot from `overlays.html`.
3. `compose.py` adds camera moves, captions with Pari, chapter cards and the progress bar.
4. `audio.py` synthesises the music bed and interface sounds from the timeline; `make_srt.py` writes the subtitles.

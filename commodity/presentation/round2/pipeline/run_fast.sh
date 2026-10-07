#!/bin/sh
# Rebuild the fast cut from captured frames: motion -> re-timing -> captions -> compose -> audio -> mux -> subtitles.
set -e
cd "$(dirname "$0")"
python3 motion.py
python3 warp.py > warp.log
TLF=timeline_fast.json python3 render_overlays.py caps
python3 compose_fast.py
python3 audio_fast.py
ffmpeg -y -loglevel error -i video_fast_noaudio.mp4 -i audio_fast.wav -c:v libx264 -preset slow -b:v 1700k -maxrate 2500k -bufsize 4000k \
  -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart -shortest ../Parity_demo.mp4
python3 make_srt_fast.py && mv Parity_demo_fast.srt ../Parity_demo.srt
echo ALL DONE

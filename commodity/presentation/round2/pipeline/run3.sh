#!/bin/sh
# v3 demo: overlays -> compose -> sound -> loudness-normalised mux -> subtitles. Capture first: python3 capture3.py
set -e
cd "$(dirname "$0")"
python3 render3.py
python3 compose3.py
python3 audio3.py
# two-pass loudness normalisation to -16 LUFS integrated; true peak capped at -1.5 dBTP so it stays under -1 after AAC encoding
M=$(ffmpeg -hide_banner -nostats -i audio3.wav -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$M" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['input_i'],d['input_tp'],d['input_lra'],d['input_thresh'],d['target_offset'])")
set -- $mi
ffmpeg -y -loglevel error -i video3_noaudio.mp4 -i audio3.wav \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=$1:measured_TP=$2:measured_LRA=$3:measured_thresh=$4:offset=$5:linear=true" -ar 48000 \
  -c:v libx264 -preset slow -crf 20 -maxrate 4500k -bufsize 9000k -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -shortest ../Parity_demo.mp4
python3 make_srt3.py
ffmpeg -hide_banner -nostats -i ../Parity_demo.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
echo ALL DONE

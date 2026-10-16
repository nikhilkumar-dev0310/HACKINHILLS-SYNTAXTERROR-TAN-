#!/bin/sh
# v4 demo: overlays -> compose -> sound -> mastered mux -> subtitles. Capture first: python3 capture4.py
# Master: -16 LUFS integrated, true peak -1.5 dBTP, loudness range target 7 LU (see ../ENGAGEMENT.md, v4).
set -e
cd "$(dirname "$0")"
[ -f ov4/chips/title.png ] || python3 render4.py
python3 compose4.py
python3 audio4.py
M=$(ffmpeg -hide_banner -nostats -i audio4.wav -af loudnorm=I=-16:TP=-1.5:LRA=7:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
mi=$(echo "$M" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['input_i'],d['input_tp'],d['input_lra'],d['input_thresh'],d['target_offset'])")
set -- $mi
ffmpeg -y -loglevel error -i video4_noaudio.mp4 -i audio4.wav \
  -af "loudnorm=I=-16:TP=-1.5:LRA=7:measured_I=$1:measured_TP=$2:measured_LRA=$3:measured_thresh=$4:offset=$5:linear=true" -ar 48000 \
  -c:v libx264 -preset slow -crf 20 -maxrate 4500k -bufsize 9000k -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart -shortest ../Parity_demo_v4.mp4
python3 make_srt4.py
ffmpeg -hide_banner -nostats -i ../Parity_demo_v4.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|LRA:|Peak:)" | tail -3
echo ALL DONE

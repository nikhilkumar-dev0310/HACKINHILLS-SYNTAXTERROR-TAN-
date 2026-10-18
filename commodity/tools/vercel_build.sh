#!/bin/sh
# Vercel build for parity-gold-site: copies the finished files into site/ (the Output Directory).
# Vercel settings: Build Command `sh commodity/tools/vercel_build.sh`, Output Directory `site`, Install Command `echo skip`.
set -e
mkdir -p site
cp commodity/dashboard/index.html site/index.html                               # the dashboard
mkdir -p site/intro && cp commodity/dashboard/intro/index.html site/intro/index.html  # 3D intro at /intro, shown once per session
cp commodity/presentation/parity-pitch.html site/pitch.html                     # interactive pitch
cp commodity/report/Gold_Futures_Spread_Intelligence.pdf site/report.pdf        # 17-page report
cp commodity/dashboard/404.html site/404.html                                   # page for addresses that do not exist
cp commodity/dashboard/og.png site/og.png                                       # link-preview image (spare copy)
cp commodity/presentation/round2/Parity_demo.mp4 site/demo.mp4                  # demo video, linked from /demo
cp commodity/presentation/demo.html site/demo.html                              # player page with captions
mkdir -p site/demo && cp commodity/presentation/demo.html site/demo/index.html # so /demo works without .html
{ echo "WEBVTT"; echo; sed 's/\([0-9][0-9]:[0-9][0-9]:[0-9][0-9]\),\([0-9][0-9][0-9]\)/\1.\2/g' commodity/presentation/round2/Parity_demo.srt; } > site/demo.vtt
ls -la site

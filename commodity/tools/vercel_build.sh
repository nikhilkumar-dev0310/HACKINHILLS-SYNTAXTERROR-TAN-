#!/bin/sh
# Vercel build for parity-gold-site: copies the finished files into site/ (the Output Directory).
# Vercel settings: Build Command `sh commodity/tools/vercel_build.sh`, Output Directory `site`, Install Command `echo skip`.
set -e
mkdir -p site
cp commodity/dashboard/index.html site/index.html                               # the dashboard
cp commodity/presentation/parity-pitch.html site/pitch.html                     # interactive pitch
cp commodity/report/Gold_Futures_Spread_Intelligence.pdf site/report.pdf        # 17-page report
cp commodity/dashboard/404.html site/404.html                                   # page for addresses that do not exist
cp commodity/dashboard/og.png site/og.png                                       # link-preview image (spare copy)
ls -la site

# Parity (dashboard)

Are MCX's four gold futures priced the same? One self-contained page built from the real results, no sample data.
React app, bundled and inlined into a single HTML file: no internet or Node needed to view it.

## Run it locally
    cd commodity
    python -m http.server 8000 --directory dashboard
then open http://localhost:8000 (or just double-click dashboard/index.html).

## Rebuild after new data
    cd commodity
    python ingest.py && python accuracy.py && python testbed.py
    python dashboard/export.py    # results/ + clean data + Git log -> dashboard/data.json
    python dashboard/build.py     # template.html + app/styles.css + data.json + app.bundle.js -> index.html (+ artifact.html)

## Change the design or features
Source is in `app/` (React, JSX): `main.jsx` (shell, search, what's new, tab bar), `views.jsx` (the eight pages),
`charts.js` (SVG charts and event notes), `ui.jsx` (shared parts), `lib.js` (formats, events, glossary), `styles.css`.

    node dashboard/build_app.mjs  # app/*.jsx -> app.bundle.js (needs esbuild, react, react-dom)
    python dashboard/build.py

Never edit `index.html`, `artifact.html` or `app.bundle.js` by hand.
Sealed-test rows (clean/sealed_rows.csv) are never read by the dashboard.

## Keyboard
`Ctrl K` / `⌘ K` or `/` search · `1`–`8` sections (can be turned off in the sidebar) · `Esc` closes menus.

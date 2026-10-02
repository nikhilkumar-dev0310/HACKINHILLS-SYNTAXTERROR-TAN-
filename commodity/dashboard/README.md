# Gold Spread Lab (dashboard)

One self-contained page built from the real results, no sample data.

## Run it locally
    cd commodity
    python -m http.server 8000 --directory dashboard
then open http://localhost:8000 (or just double-click dashboard/index.html).

## Rebuild after new data
    cd commodity
    python ingest.py && python accuracy.py && python testbed.py
    python dashboard/export.py    # results/ + clean data -> dashboard/data.json
    python dashboard/build.py     # template.html + data.json -> index.html (+ artifact.html)

Edit `template.html` for design changes, never `index.html`.
Sealed-test rows (clean/sealed_rows.csv) are never read by the dashboard.

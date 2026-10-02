# Gold Spread Lab (dashboard)

One self-contained page built from the real results, no sample data.

    cd commodity
    python dashboard/export.py    # results/ + clean data -> dashboard/data.json
    python dashboard/build.py     # template.html + data.json -> dashboard/index.html

Open `index.html` in a browser. Edit `template.html` for design changes, never `index.html`.
Run `ingest.py`, `accuracy.py` and `testbed.py` first after adding new MCX files.

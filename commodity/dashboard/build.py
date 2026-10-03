"""Inline the styles, data and React bundle into template.html.

    python dashboard/export.py && python dashboard/build.py      (from commodity/)
    node dashboard/build_app.mjs   only after editing the React source in dashboard/app/

Writes two files:
  index.html     full web page: open it, serve it locally, or deploy it
  artifact.html  the same page without <html>/<head>, for publishing as a Claude artifact
Local preview:  python -m http.server 8000 --directory dashboard   then open http://localhost:8000
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
data = open(os.path.join(HERE, "data.json"), encoding="utf-8").read().replace("</", "<\\/")
assert "/*__DATA__*/null" in tpl
css = open(os.path.join(HERE, "app", "styles.css"), encoding="utf-8").read()
app = open(os.path.join(HERE, "app.bundle.js"), encoding="utf-8").read().replace("</script", "<\\/script")
body = tpl.replace("/*__CSS__*/", css).replace("/*__DATA__*/null", data).replace("/*__APP__*/", app)
open(os.path.join(HERE, "artifact.html"), "w", encoding="utf-8").write(body)
head, rest = body.split("</style>", 1)
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Parity: are MCX’s four gold futures priced the same? Gaps, carry and a sealed backtest from official Bhavcopy data.">\n'
        + head + "</style>\n</head>\n<body>\n" + rest + "\n</body>\n</html>\n")
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(page)
for f in ("index.html", "artifact.html"):
    print("wrote dashboard/" + f, os.path.getsize(os.path.join(HERE, f)) // 1024, "KB")

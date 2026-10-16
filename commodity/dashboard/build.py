"""Inline the styles, data and React bundle into template.html.

    python dashboard/export.py && python dashboard/build.py      (from commodity/)
    node dashboard/build_app.mjs   only after editing the React source in dashboard/app/

Writes two files:
  index.html     full web page: open it, serve it locally, or deploy it
  artifact.html  the same page without <html>/<head>, for publishing as a Claude artifact
Local preview:  python -m http.server 8000 --directory dashboard   then open http://localhost:8000
"""
import datetime as dt
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://parity-gold-site.vercel.app/"
# the link-preview image is served from the public repository, so it works whatever the host's build settings are
OG_IMG = "https://raw.githubusercontent.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/main/commodity/dashboard/og.png"
DESC = "Are MCX's four gold futures priced the same? Fair value, the futures curve, sealed backtests and quiet alerts, from official Bhavcopy data, updated every trading day."
META = "\n".join([
    f'<meta property="og:type" content="website">', f'<meta property="og:url" content="{SITE}">',
    '<meta property="og:site_name" content="Parity">', '<meta property="og:title" content="Parity · MCX gold futures, priced fairly">',
    f'<meta property="og:description" content="{DESC}">', f'<meta property="og:image" content="{OG_IMG}">',
    '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
    '<meta property="og:image:alt" content="Parity: one metal, four prices. MCX gold futures, updated every trading day.">',
    '<meta name="twitter:card" content="summary_large_image">', '<meta name="twitter:title" content="Parity · MCX gold futures, priced fairly">',
    f'<meta name="twitter:description" content="{DESC}">', f'<meta name="twitter:image" content="{OG_IMG}">',
    '<meta name="theme-color" content="#050506" media="(prefers-color-scheme: dark)">',
    '<meta name="theme-color" content="#f5f4f1" media="(prefers-color-scheme: light)">'])


def build_stamp():
    """Calendar version plus the commit this build was made on top of (the build itself lands in the next commit)."""
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30)))
    try:
        commit = subprocess.run(["git", "rev-parse", "--short=7", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = ""
    return {"version": now.strftime("%Y.%m.%d"), "built": now.strftime("%d %b %Y, %H:%M IST").lstrip("0"), "commit": commit}
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
data = open(os.path.join(HERE, "data.json"), encoding="utf-8").read().replace("</", "<\\/")
assert "/*__DATA__*/null" in tpl
css = open(os.path.join(HERE, "app", "styles.css"), encoding="utf-8").read()
app = open(os.path.join(HERE, "app.bundle.js"), encoding="utf-8").read().replace("</script", "<\\/script")
body = (tpl.replace("/*__CSS__*/", css).replace("/*__DATA__*/null", data).replace("/*__APP__*/", app)
        .replace("/*__BUILD__*/null", json.dumps(build_stamp())).replace("<!--__META__-->", META))
open(os.path.join(HERE, "artifact.html"), "w", encoding="utf-8").write(body)
head, rest = body.split("</style>", 1)
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Parity: are MCX’s four gold futures priced the same? Gaps, carry and a sealed backtest from official Bhavcopy data.">\n'
        + head + "</style>\n</head>\n<body>\n" + rest + "\n</body>\n</html>\n")
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(page)
# a plain page for addresses that do not exist on the host (the app itself handles unknown #sections)
nf = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found · Parity</title><meta name="robots" content="noindex">
<style>:root{color-scheme:dark light}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#050506;color:#f5f5f7;font:15px/1.6 Inter,system-ui,sans-serif}
@media (prefers-color-scheme:light){body{background:#ebe5da;color:#101215}.k,p{color:#5f6672!important}a{color:#835a07!important}}
main{max-width:460px;padding:24px;text-align:center}svg{width:56px;height:46px}.k{font:500 11px/1 ui-monospace,monospace;letter-spacing:.14em;text-transform:uppercase;color:#86868b}
h1{font:600 30px/1.15 "Space Grotesk",Inter,system-ui,sans-serif;letter-spacing:-.03em;margin:14px 0 8px}p{color:#a1a1a6;margin:0 0 22px}
a{display:inline-block;color:#f2b544;font-weight:600;text-decoration:none;border:1px solid currentColor;border-radius:999px;padding:9px 18px}a:hover{opacity:.85}</style></head>
<body><main><svg viewBox="9 11 30 26" aria-hidden="true"><path d="M14 13h20l3.2 8.6H10.8z" fill="#f2b544"/><path d="M14 26.4h20l3.2 8.6H10.8z" fill="#f2b544" transform="translate(3 0)"/></svg>
<div class="k">404 · page not found</div><h1>This address is not on Parity.</h1><p>The site lives on one page with eight sections. The link may be mistyped or out of date.</p>
<a href="/">Open Parity</a></main></body></html>
"""
open(os.path.join(HERE, "404.html"), "w", encoding="utf-8").write(nf)
for f in ("index.html", "artifact.html"):
    print("wrote dashboard/" + f, os.path.getsize(os.path.join(HERE, f)) // 1024, "KB")

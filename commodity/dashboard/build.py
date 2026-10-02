"""Inline data.json into template.html -> index.html (one self-contained page).

    python dashboard/export.py && python dashboard/build.py      (from commodity/)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
data = open(os.path.join(HERE, "data.json"), encoding="utf-8").read().replace("</", "<\\/")
assert "/*__DATA__*/null" in tpl
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(tpl.replace("/*__DATA__*/null", data))
print("wrote dashboard/index.html", os.path.getsize(os.path.join(HERE, "index.html")) // 1024, "KB")

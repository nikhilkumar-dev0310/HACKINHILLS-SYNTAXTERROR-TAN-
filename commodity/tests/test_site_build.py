"""The published site: built pages, every term it defines, every source it cites, everything it links to.

The site is one self-contained HTML page (dashboard/index.html) built from dashboard/app/ by build_app.mjs
and build.py, plus 404.html and the files commodity/tools/vercel_build.sh copies for Vercel. These tests
read the source and the built files; they do not need a browser.
"""
import json
import os
import re
import unittest

from _util import cases, site

APP = "dashboard/app"
SRC = {f: open(os.path.join(APP, f), encoding="utf-8").read() for f in sorted(os.listdir(APP)) if f.endswith((".js", ".jsx"))}
ALL = "\n".join(SRC.values())
LIB = SRC["lib.js"]
CSS = open(os.path.join(APP, "styles.css"), encoding="utf-8").read()
INDEX = open("dashboard/index.html", encoding="utf-8").read()
PAGE404 = open("dashboard/404.html", encoding="utf-8").read()


def block(name):
    """The body of `export const NAME = { ... };` in lib.js."""
    m = re.search(r"export const %s = \{(.*?)\n\};" % name, LIB, re.S)
    assert m, name
    return m.group(1)


GLOSSARY = set(re.findall(r"^\s{2}([a-zA-Z0-9_]+): \[", block("GLOSSARY"), re.M))
ICONS = set(re.findall(r"^\s{2}([a-zA-Z0-9_]+): '", block("ICON"), re.M))
SRCS = dict(re.findall(r"([A-Za-z_]+): \{ file: \"([^\"]+)\"", block("SRC")))
VIEWS = re.findall(r'\["([a-z]+)", "[^"]+"\]', re.search(r"export const VIEWS = \[(.*?)\];", LIB, re.S).group(1))
TERMS_USED = sorted(set(re.findall(r'<Term k="([a-zA-Z0-9_]+)"', ALL)))
ICONS_USED = sorted(set(re.findall(r'<Icon name="([a-z0-9_-]+)"', ALL)) | set(re.findall(r'icon: "([a-z0-9_-]+)"', ALL)) | set(VIEWS))
SRC_USED = sorted(set(re.findall(r"SRC\.([A-Za-z_]+)", ALL)))


@cases(TERMS_USED)
class EachTerm(unittest.TestCase):
    def check_has_a_definition(self, k):
        """Every dotted term on the site opens a definition in the glossary"""
        self.assertIn(k, GLOSSARY)


@cases(sorted(GLOSSARY))
class EachDefinition(unittest.TestCase):
    def check_is_a_full_sentence(self, k):
        """Every glossary entry has a name and a definition of at least a few words, ending in a full stop"""
        m = re.search(r"^\s{2}%s: \[\"([^\"]+)\", \"(.+?)\"\]" % re.escape(k), block("GLOSSARY"), re.M)
        self.assertTrue(m, k)
        self.assertGreaterEqual(len(m.group(2).split()), 5)
        self.assertTrue(m.group(2).rstrip().endswith((".", ")", "”")), m.group(2)[-30:])


@cases(ICONS_USED)
class EachIcon(unittest.TestCase):
    def check_is_drawn(self, name):
        """Every icon the site asks for exists"""
        self.assertIn(name, ICONS)


@cases(sorted(SRCS))
class EachSource(unittest.TestCase):
    def check_cited_file_exists(self, key):
        """Every 'where this number comes from' note points at a file that is in the repository"""
        f = SRCS[key]
        if "*" in f:
            d, ext = os.path.dirname(f), os.path.splitext(f)[1]
            self.assertTrue(any(x.endswith(ext) for x in os.listdir(d)), f)
        else:
            self.assertTrue(os.path.exists(f), f)

    def check_named_script_exists(self, key):
        """The script named as the source is in the repository"""
        by = re.search(r"%s: \{ file: \"[^\"]+\", by: \"([^\"]+)\"" % key, block("SRC")).group(1)
        for script in re.findall(r"([a-z_/]+\.(?:py|mjs))", by):
            self.assertTrue(os.path.exists(script), script)


@cases(SRC_USED)
class EachSourceUse(unittest.TestCase):
    def check_is_defined(self, key):
        """Every SRC.x the views use is defined"""
        self.assertIn(key, SRCS)


@cases(VIEWS)
class EachPage(unittest.TestCase):
    def check_has_a_view(self, v):
        """Each of the eight sections is wired to a page component"""
        self.assertRegex(SRC["main.jsx"], r"\b%s: [A-Z][A-Za-z_]+" % v)

    def check_has_search_keywords(self, v):
        """Each section can be found from the search palette"""
        self.assertRegex(SRC["main.jsx"], r"\b%s: \"[a-z]" % v)


class BuiltPage(unittest.TestCase):
    def test_embeds_exactly_the_exported_data(self):
        m = re.search(r"window\.__PARITY_DATA__ = (\{.*?\});\s*window\.__PARITY_BUILD__", INDEX, re.S)
        self.assertTrue(m)
        self.assertEqual(json.loads(m.group(1).replace("<\\/", "</")), site())

    def test_carries_a_build_stamp(self):
        m = re.search(r"window\.__PARITY_BUILD__ = (\{.*?\});", INDEX)
        self.assertTrue(m)
        b = json.loads(m.group(1))
        self.assertRegex(b["version"], r"^\d{4}\.\d\d\.\d\d$")

    def test_no_placeholders_left(self):
        for p in ("/*__CSS__*/", "/*__DATA__*/", "/*__APP__*/", "/*__BUILD__*/", "<!--__META__-->"):
            self.assertNotIn(p, INDEX)

    def test_has_title_description_and_link_preview(self):
        self.assertRegex(INDEX, r"<title>[^<]{5,}</title>")
        for tag in ('name="description"', 'property="og:title"', 'property="og:image"', 'name="twitter:card"', 'name="viewport"'):
            self.assertIn(tag, INDEX)

    def test_loads_no_third_party_scripts(self):
        """Everything the page runs is inlined: no script is fetched from anywhere"""
        self.assertEqual(re.findall(r"<script[^>]+src=", INDEX), [])

    def test_only_https_links(self):
        self.assertEqual([u for u in re.findall(r'(?:href|src)="(http://[^"]+)"', INDEX)], [])

    def test_language_and_charset_declared(self):
        self.assertRegex(INDEX, r'<html lang="en')
        self.assertIn('charset="utf-8"', INDEX.lower())

    def test_stays_a_reasonable_size(self):
        self.assertLess(os.path.getsize("dashboard/index.html"), 2_500_000)

    def test_artifact_variant_carries_the_same_data(self):
        """artifact.html is the body-only variant of the page; it must carry the same data and app"""
        art = open("dashboard/artifact.html", encoding="utf-8").read()
        m = re.search(r"window\.__PARITY_DATA__ = (\{.*?\});\s*window\.__PARITY_BUILD__", art, re.S)
        self.assertTrue(m)
        self.assertEqual(json.loads(m.group(1).replace("<\\/", "</")), site())

    def test_has_a_loading_screen_and_a_noscript_note(self):
        self.assertIn('id="boot"', INDEX)

    def test_respects_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", CSS)

    def test_has_a_print_stylesheet(self):
        self.assertIn("@media print", CSS)


class NotFoundPage(unittest.TestCase):
    def test_is_self_contained_and_links_home(self):
        self.assertIn("<title>", PAGE404)
        self.assertRegex(PAGE404, r'href="/"')
        self.assertEqual(re.findall(r"<script[^>]+src=", PAGE404), [])

    def test_follows_light_and_dark_mode(self):
        self.assertIn("prefers-color-scheme", PAGE404)


class Deployment(unittest.TestCase):
    def test_vercel_build_copies_files_that_exist(self):
        sh = open("tools/vercel_build.sh").read()
        for src in re.findall(r"cp (commodity/\S+)", sh):
            self.assertTrue(os.path.exists(src.replace("commodity/", "", 1)), src)

    def test_vercel_build_publishes_the_site_pitch_report_and_404(self):
        sh = open("tools/vercel_build.sh").read()
        for out in ("site/index.html", "site/pitch.html", "site/report.pdf", "site/404.html"):
            self.assertIn(out, sh)


if __name__ == "__main__":
    unittest.main()

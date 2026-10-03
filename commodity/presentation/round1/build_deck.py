"""Fill the official Hack in Hills '26 template with Parity's Round 1 content.

Keeps every template picture (header strip, sponsor logos, mountain photo) and the 'Thank you' slide as they are;
replaces the placeholder text on slides 1-7 with our content. All numbers come from the repository's results.
"""
import copy
from pptx import Presentation
from pptx.util import Emu, Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

INK, INK2, GOLD, GOLDBG, LINE, GOOD, BAD, WHITE = (RGBColor(0x1D, 0x1D, 0x1F), RGBColor(0x55, 0x55, 0x5A), RGBColor(0x83, 0x5A, 0x07),
                                                   RGBColor(0xFB, 0xF4, 0xE4), RGBColor(0xE2, 0xDD, 0xD2), RGBColor(0x14, 0x7A, 0x52),
                                                   RGBColor(0xB4, 0x3A, 0x2E), RGBColor(0xFF, 0xFF, 0xFF))
HEAD, BODY = "Montserrat", "Calibri"
REPO = "/home/claude/hackinhills-syntaxterror-tan-/commodity"

prs = Presentation("template.pptx")
S = prs.slides


def clear(slide):
    """Remove the template's text shapes and groups; keep its pictures."""
    for sh in list(slide.shapes):
        if sh.shape_type != 13:          # 13 = picture
            sh._element.getparent().remove(sh._element)


def text(slide, x, y, w, h, runs, size=20, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None, spacing=None):
    """runs: a string, or a list of paragraphs; each paragraph a string or list of (text, {opts})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name: tb.name = name
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing: p.space_after = Pt(spacing)
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run(); r.text = t
            f = r.font; f.size = Pt(o.get("size", size)); f.bold = o.get("bold", bold); f.name = o.get("font", font)
            f.color.rgb = o.get("color", color); f.italic = o.get("italic", False)
    return tb


def box(slide, x, y, w, h, fill=WHITE, line=LINE, radius=True, name=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius: sh.adjustments[0] = 0.06
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(1.25)
    sh.shadow.inherit = False
    if name: sh.name = name
    sh.text_frame.text = ""
    return sh


def title(slide, t, kicker):
    text(slide, 1.0, 1.62, 18, 0.45, kicker.upper(), size=15, color=GOLD, bold=True, font=HEAD, name="Kicker")
    text(slide, 1.0, 2.05, 18, 0.9, t, size=36, bold=True, font=HEAD, name="Title")


def bullets(slide, x, y, w, h, items, size=20, name=None, gap=8):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name: tb.name = name
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        pPr = p._p.get_or_add_pPr(); pPr.set("marL", str(Inches(0.3))); pPr.set("indent", str(-Inches(0.3)))
        bu = pPr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar", {"char": "•"})
        pPr.append(bu)
        for t, o in ([(it, {})] if isinstance(it, str) else it):
            r = p.add_run(); r.text = t; f = r.font; f.size = Pt(size); f.name = BODY; f.bold = o.get("bold", False)
            f.color.rgb = o.get("color", INK)
    return tb


def stat(slide, x, y, w, h, big, small, tone=GOLD, name=None):
    box(slide, x, y, w, h, fill=WHITE, name=name)
    text(slide, x + 0.3, y + 0.25, w - 0.6, 0.9, big, size=40, bold=True, color=tone, font=HEAD)
    text(slide, x + 0.3, y + 1.15, w - 0.6, h - 1.3, small, size=16, color=INK2)


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


# ------------------------------------------------------------------ 1 TEAM
s = S[0]; clear(s)
text(s, 1.0, 5.15, 6, 0.6, "TEAM", size=40, bold=True, font=HEAD, name="Title")
text(s, 1.0, 6.0, 8.2, 2.6, [[("Team name", {"bold": True, "color": GOLD, "size": 18})],
                              [("SYNTAX TERROR (TAN)", {"bold": True, "size": 34, "font": HEAD})],
                              [("Project: Parity · MCX gold futures intelligence", {"size": 20, "color": INK2})],
                              [("Problem 03 · Commodity Derivatives Intelligence", {"size": 20, "color": INK2})]], name="Team name")
rows = [("Nikhil Kumar", "Team lead · data pipeline, strategy research and backtests, dashboard"),
        ("Sai Ganesh", "Market research and pitch presentation"),
        ("Ishaan Chhabra", "Testing, data checks and documentation")]
box(s, 10.2, 5.2, 8.9, 5.0, name="Members card")
text(s, 10.6, 5.45, 8, 0.4, "MEMBERS AND ROLES", size=16, bold=True, color=GOLD, font=HEAD)
for i, (n, r) in enumerate(rows):
    y = 6.05 + i * 1.32
    text(s, 10.6, y, 8.1, 0.45, n, size=24, bold=True, name=f"Member {i + 1}")
    text(s, 10.6, y + 0.5, 8.1, 0.7, r, size=17, color=INK2)
notes(s, "Team SYNTAX TERROR (TAN): Nikhil Kumar leads and built the data pipeline, strategies and dashboard; Sai Ganesh on market research and the pitch; Ishaan Chhabra on testing and documentation.")

# ------------------------------------------------------------------ 2 PROBLEM
s = S[1]; clear(s)
title(s, "One metal, four prices", "Problem statement & theme")
text(s, 1.0, 3.05, 17.5, 1.0, "MCX lists four gold futures that differ only in size and purity. Per gram of pure gold they should cost the same. "
     "Do they, can a gap be traded after real costs, and when is one worth a trader's attention?", size=21, color=INK2)
cards = [("GOLDM", "100 g bar · 995", "₹1,49,055", "per 10 g", "₹14,980"), ("GOLDTEN", "10 g bar · 999", "₹1,49,436", "per 10 g", "₹14,959"),
         ("GOLDGUINEA", "8 g coin · 999", "₹1,19,993", "per 8 g", "₹15,014"), ("GOLDPETAL", "1 g · 999", "₹15,002", "per 1 g", "₹15,017")]
for i, (n, d, px, q, pg) in enumerate(cards):
    x = 1.0 + i * 4.45
    box(s, x, 4.3, 4.15, 2.75, name=f"Contract {n}")
    text(s, x + 0.3, 4.5, 3.6, 0.45, n, size=22, bold=True, font=HEAD)
    text(s, x + 0.3, 4.98, 3.6, 0.4, d, size=16, color=INK2)
    text(s, x + 0.3, 5.45, 3.6, 0.5, [[(px, {"bold": True, "size": 22}), ("  " + q, {"size": 15, "color": INK2})]])
    text(s, x + 0.3, 6.1, 3.6, 0.6, [[("→ " + pg, {"bold": True, "size": 24, "color": GOLD}), ("  per pure g", {"size": 15, "color": INK2})]])
text(s, 1.0, 7.17, 17.5, 0.4, "Most-traded contract of each, MCX closing prices, 1 Oct 2026. Four very different quotes become four near-equal prices per pure gram.",
     size=14, color=INK2)
cols = [("Problem", ["Raw quotes hide whether a contract is cheap or dear", "Gaps flip between structural and temporary", "Typical backtests skip costs, delivery periods and unseen data"]),
        ("Impact", ["The 8 g coin is 61–72 bp dearer than GOLDM, in all 41 cycles", "In the Dec 2025 – Mar 2026 crash, small contracts sat ~2.7% above GOLDM",
                    "A wrong normalisation would show a fake ~40 bp gap"]),
        ("Theme alignment", ["Problem 03: Commodity Derivatives Intelligence", "Relative value, term structure, walk-forward backtest",
                             "Trader alerts and contract lifecycle, as the brief asks"])]
for i, (h, its) in enumerate(cols):
    x = 1.0 + i * 5.95
    box(s, x, 7.75, 5.65, 2.95, fill=GOLDBG if i == 2 else WHITE, name=h)
    text(s, x + 0.3, 7.95, 5.0, 0.45, h.upper(), size=16, bold=True, color=GOLD, font=HEAD)
    bullets(s, x + 0.3, 8.45, 5.1, 2.2, its, size=16, gap=5)
notes(s, "Four contracts, one metal. Converted to rupees per gram of pure gold, they nearly match, and the gaps that remain are what Parity studies.")

# ------------------------------------------------------------------ 3 SOLUTION
s = S[2]; clear(s)
title(s, "Parity: is the gap real, and is it worth trading?", "Solution")
s.shapes.add_picture(f"dash-overview.png", Inches(10.3), Inches(3.05), width=Inches(8.9)).name = "Dashboard screenshot"
text(s, 10.3, 8.72, 8.9, 0.4, "The Parity dashboard: 8 pages, works offline in one HTML file.", size=13, color=INK2)
text(s, 1.0, 3.05, 8.8, 1.3, "A dashboard and alert system that puts all four contracts in ₹ per pure gram, measures every gap, "
     "tests whether trading it pays after costs, and stays quiet when there is nothing to act on.", size=19, color=INK2)
feats = [("Relative value", "all 6 pairs, 95% ranges, carry-adjusted expiries"),
         ("Fair-price signal", "anchored on GOLDM; alert only beyond ±1.5σ"),
         ("Walk-forward backtest", "next-day fills, MCX fees, CTT, stamp, GST, 0/5/10 bp slippage"),
         ("Contract calendar", "listing to expiry; every trade checked against the tender period"),
         ("Gap vs gold", "each trade's profit split into the gap and gold's own move")]
text(s, 1.0, 4.45, 8.8, 0.4, "KEY FEATURES", size=16, bold=True, color=GOLD, font=HEAD)
for i, (a, b) in enumerate(feats):
    y = 4.95 + i * 0.78
    text(s, 1.0, y, 8.8, 0.7, [[(a + "  ", {"bold": True, "size": 18}), (b, {"size": 17, "color": INK2})]], name=f"Feature {i + 1}")
box(s, 1.0, 9.0, 18.2, 1.65, fill=GOLDBG, line=None, name="Unique value")
text(s, 1.35, 9.18, 17.5, 1.35, [[("UNIQUE VALUE  ", {"bold": True, "size": 16, "color": GOLD, "font": HEAD})],
                                 [("Honest by design: every rule frozen in Git before its test data was read; three sealed tests, each run once; "
                                   "results shown even when they lose. 710 official MCX contracts, 0 unexplained data errors.", {"size": 19})]])
notes(s, "Parity answers three questions: do the four agree, can a gap be traded after costs, and is today worth a look. "
         "Its edge over a typical backtest is honesty: rules locked first, sealed tests run once.")

# ------------------------------------------------------------------ 4 ARCHITECTURE
s = S[3]; clear(s)
title(s, "From exchange files to a trader's screen", "Architecture")
flow = [("MCX Bhavcopy", "Official daily files, one contract at a time, 2003–2026"),
        ("ingest.py", "Dedupe, integrity checks, ₹ per pure gram, sealed years walled off"),
        ("Analysis", "pairs, carry and curve, fair price, backtests, lifecycle, alerts, bootstrap"),
        ("results/*.csv", "Every number written to a file, reproducible"),
        ("export.py", "One data.json for every output")]
bw, gap, y0 = 3.25, 0.5, 3.35
for i, (a, b) in enumerate(flow):
    x = 1.0 + i * (bw + gap)
    box(s, x, y0, bw, 2.05, fill=GOLDBG if i in (0, 4) else WHITE, name=f"Flow {i + 1}")
    text(s, x + 0.22, y0 + 0.2, bw - 0.44, 0.5, a, size=19, bold=True, font=HEAD if i != 3 else BODY)
    text(s, x + 0.22, y0 + 0.75, bw - 0.44, 1.25, b, size=15, color=INK2)
    if i < len(flow) - 1:
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + bw + 0.05), Inches(y0 + 1.02), Inches(x + bw + gap - 0.05), Inches(y0 + 1.02))
        c.line.color.rgb = GOLD; c.line.width = Pt(2.5)
        c.line._get_or_add_ln().append(c.line._get_or_add_ln().makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd", {"type": "triangle"}))
outs = [("React dashboard", "8 pages, search, CSV downloads, one offline HTML file"), ("Report PDF", "17 pages, every figure from the same data"),
        ("Interactive pitch", "17 scenes, data-driven, offline")]
for i, (a, b) in enumerate(outs):
    x = 1.0 + i * 6.1
    box(s, x, 5.95, 5.8, 1.35, name=f"Output {i + 1}")
    text(s, x + 0.25, 6.1, 5.3, 1.1, [[(a, {"bold": True, "size": 19})], [(b, {"size": 15, "color": INK2})]])
cols = [("Tech stack", ["Python 3, pandas, NumPy: ingest, analysis, backtests", "React 19 bundled with esbuild; charts drawn in SVG, no chart library",
                        "ReportLab and Matplotlib for the PDF", "Git: rules time-stamped before each test; unit tests"]),
        ("Data flow", ["Daily: new Bhavcopy → ingest → signals", "Signals at the close, trades at the next day's price",
                       "Sealed rows live in a separate file until one run"]),
        ("APIs used", ["No paid APIs and no API keys", "MCX's public Bhavcopy page, read in a browser",
                       "Runs fully offline once data is in"])]
for i, (h, its) in enumerate(cols):
    x = 1.0 + i * 6.1
    text(s, x, 7.65, 5.8, 0.45, h.upper(), size=16, bold=True, color=GOLD, font=HEAD)
    bullets(s, x, 8.15, 5.8, 2.6, its, size=16, gap=4)
notes(s, "One pipeline: official MCX files in, validated and converted, every analysis writes a CSV, and one export feeds the dashboard, report and pitch.")

# ------------------------------------------------------------------ 5 MARKET
s = S[4]; clear(s)
title(s, "Gold derivatives in India are growing fast", "Market research / analysis")
stat(s, 1.0, 3.2, 5.8, 2.5, "₹28,484 cr", "average daily turnover, MCX gold futures, FY2025-26 (₹8,449 cr in FY2024-25)", name="Stat futures")
stat(s, 7.2, 3.2, 5.8, 2.5, "23 tonnes", "gold traded per day in futures, FY2025-26 (11 tonnes the year before)", name="Stat tonnes")
stat(s, 13.4, 3.2, 5.8, 2.5, "57%", "bullion's share of MCX average daily turnover, Q2 FY26 (44% a year earlier)", name="Stat bullion")
text(s, 1.0, 5.85, 18, 0.4, "Sources: Business Today, 14 Aug 2026 (MCX data, FY2025-26); Business Standard, 7 Nov 2025 (MCX Q2 FY26 results).", size=13, color=INK2)
cols = [("Target users", ["Gold futures traders choosing which contract to trade", "Arbitrage and prop desks running spread trades",
                          "Jewellers and bullion dealers hedging with small lots", "Broker research teams publishing trade ideas"]),
        ("Market size", ["MCX offers gold in 1 kg, 100 g, 10 g, 8 g and 1 g lots", "Parity covers the four small contracts; in our files GOLDM trades a median 441 kg a day",
                         "MCX average daily turnover ₹4.11 lakh cr (futures and options), Q2 FY26"]),
        ("Potential revenue model", ["Free dashboard; paid daily alerts by email or Telegram", "White-label licence for brokers' research desks",
                                     "Data feed of normalised prices and fair-value signals"]),
        ("Expected growth", ["Futures turnover more than tripled in one year", "Small lots (10 g, 1 g) bring in retail hedgers",
                             "Same method extends to silver: SILVERM and SILVERMIC"])]
for i, (h, its) in enumerate(cols):
    x = 1.0 + (i % 2) * 9.2; y = 6.45 + (i // 2) * 2.2
    text(s, x, y, 8.9, 0.45, h.upper(), size=16, bold=True, color=GOLD, font=HEAD)
    bullets(s, x, y + 0.45, 8.9, 1.7, its, size=15, gap=2)
notes(s, "Market figures are from MCX data reported in Business Today (Aug 2026) and Business Standard (Nov 2025). The revenue model is our plan, not a measured result.")

# ------------------------------------------------------------------ 6 FUTURE
s = S[5]; clear(s)
title(s, "What comes next", "Future scope")
items = [("Live paper trading", "Run Strategy B day by day on new MCX files from October 2026, before any real money."),
         ("Intraday data", "Replace the end-of-day close with real fills to measure slippage instead of assuming 5 bp."),
         ("Alerts where traders are", "Email and Telegram alerts that fire only beyond ±1.5σ, with the cost of acting shown."),
         ("Longer premium history", "Measure the coin and 1 g premiums back to 2008 and 2011, now that the sealed run is done."),
         ("Safer rules", "Price-limit filter, and a spot cross-check against IBJA's published 999 and 995 rates."),
         ("More metals", "The same normalisation for silver (SILVERM, SILVERMIC) and other multi-size contracts.")]
for i, (a, b) in enumerate(items):
    x = 1.0 + (i % 3) * 6.1; y = 3.2 + (i // 3) * 3.45
    box(s, x, y, 5.8, 3.15, fill=GOLDBG if i == 0 else WHITE, name=a)
    text(s, x + 0.3, y + 0.25, 1.0, 0.7, f"0{i + 1}", size=30, bold=True, color=GOLD, font=HEAD)
    text(s, x + 0.3, y + 1.0, 5.2, 0.5, a, size=21, bold=True)
    text(s, x + 0.3, y + 1.55, 5.2, 1.5, b, size=16, color=INK2)
notes(s, "First, prove it live on paper. Then better data, alerts where traders already are, and the same method for silver.")

# ------------------------------------------------------------------ 7 EXTRA: results
s = S[6]; clear(s)
title(s, "Tested on eight years it had never seen", "Extra: results")
s.shapes.add_picture(f"{REPO}/report/sealed.png", Inches(1.0), Inches(3.1), width=Inches(10.2)).name = "Sealed tests chart"
text(s, 1.0, 7.05, 10.2, 0.4, "Net profit after all costs at 5 bp slippage, each window run once with rules frozen in Git first.", size=13, color=INK2)
pts = [[("Strategy A (pairs) is rejected: ", {"bold": True}), ("it lost in both windows even with perfect fills.", {})],
       [("Strategy B (fair price) made money in all 3 sealed tests: ", {"bold": True}), ("₹12,990, ₹35,873 and ₹6,962 net profit at 5 bp.", {})],
       [("Positive, not proven: ", {"bold": True}), ("each 95% range includes zero, and it loses at 10 bp in two of three.", {})],
       [("Crashes pay sometimes: ", {"bold": True}), ("January 2026 paid; March 2020 did not.", {})]]
bullets(s, 11.7, 3.2, 7.5, 5.5, pts, size=18, gap=10)
box(s, 1.0, 7.75, 18.2, 2.3, fill=GOLDBG, line=None, name="Data")
for i, (big, sm) in enumerate([("710", "MCX contracts, 2003–2026"), ("55,457", "daily records checked"), ("0", "unexplained data errors"), ("3", "sealed tests, each run once")]):
    x = 1.4 + i * 4.5
    text(s, x, 8.05, 4.2, 1.0, big, size=44, bold=True, color=GOLD, font=HEAD)
    text(s, x, 9.05, 4.2, 0.6, sm, size=17, color=INK2)
notes(s, "The honest answer: a small, positive, unproven edge whose size is decided by execution. Strategy A failed; Strategy B held up modestly.")

prs.save("parity-round1.pptx")
print("saved")

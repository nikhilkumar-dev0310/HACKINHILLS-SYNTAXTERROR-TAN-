"""Fill the official Hack in Hills '26 template with Parity's Round 1 content (v2: larger type, fewer words, icons).

Keeps every template picture (header strip, sponsor logos, mountain photo) and the template's 'Thank you' artwork;
replaces the placeholder text on slides 1-7. The canvas is 20 x 11.25 in, so body text is 20 pt or more.
All numbers come from the repository's results files and cited sources.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/claude/hackinhills-syntaxterror-tan-/commodity"
INK, INK2, GOLD, GOLDBG, LINE, GOOD, WHITE = (RGBColor(0x1D, 0x1D, 0x1F), RGBColor(0x4A, 0x4A, 0x50), RGBColor(0x83, 0x5A, 0x07),
                                              RGBColor(0xFB, 0xF4, 0xE4), RGBColor(0xDD, 0xD6, 0xC8), RGBColor(0x14, 0x7A, 0x52), RGBColor(0xFF, 0xFF, 0xFF))
HEAD, BODY = "Montserrat", "Calibri"
I = lambda n, w=False: os.path.join(HERE, "icons", n + ("_w" if w else "") + ".png")
A = "http://schemas.openxmlformats.org/drawingml/2006/main"

prs = Presentation(os.path.join(HERE, "template.pptx"))
S = prs.slides


def clear(slide):
    for sh in list(slide.shapes):
        if sh.shape_type != 13:
            sh._element.getparent().remove(sh._element)


def text(slide, x, y, w, h, paras, size=22, color=INK, bold=False, font=BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None, after=0, line=None):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name: tb.name = name
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = paras if isinstance(paras, list) else [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(after)
        if line: p.line_spacing = line
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run(); r.text = t; f = r.font
            f.size = Pt(o.get("size", size)); f.bold = o.get("bold", bold); f.name = o.get("font", font); f.color.rgb = o.get("color", color)
    return tb


def bullets(slide, x, y, w, h, items, size=22, after=8, name=None, color=INK):
    tb = text(slide, x, y, w, h, [""] * len(items), size=size, name=name)
    for p, it in zip(tb.text_frame.paragraphs, items):
        p.space_after = Pt(after)
        pPr = p._p.get_or_add_pPr(); pPr.set("marL", str(Inches(0.32))); pPr.set("indent", str(-Inches(0.32)))
        pPr.append(pPr.makeelement(f"{{{A}}}buClr", {})); pPr[-1].append(pPr.makeelement(f"{{{A}}}srgbClr", {"val": "835A07"}))
        pPr.append(pPr.makeelement(f"{{{A}}}buChar", {"char": "•"}))
        for r in list(p.runs): r._r.getparent().remove(r._r)
        for t, o in ([(it, {})] if isinstance(it, str) else it):
            r = p.add_run(); r.text = t; f = r.font; f.size = Pt(size); f.name = BODY; f.bold = o.get("bold", False); f.color.rgb = o.get("color", color)
    return tb


def box(slide, x, y, w, h, fill=WHITE, line=LINE, name=None, radius=0.05):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = radius
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb = line; sh.line.width = Pt(1.5)
    sh.shadow.inherit = False
    if name: sh.name = name
    return sh


def icon(slide, key, x, y, d=0.85, filled=True, name=None):
    """Icon inside a circle: gold circle with a white icon, or a soft circle with a gold icon."""
    c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid(); c.fill.fore_color.rgb = GOLD if filled else GOLDBG; c.line.fill.background(); c.shadow.inherit = False
    if name: c.name = name
    pad = d * 0.22
    slide.shapes.add_picture(I(key, filled), Inches(x + pad), Inches(y + pad), Inches(d - 2 * pad), Inches(d - 2 * pad))


def arrow(slide, x1, y1, x2, y2, w=3):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = GOLD; c.line.width = Pt(w)
    ln = c.line._get_or_add_ln(); ln.append(ln.makeelement(f"{{{A}}}tailEnd", {"type": "triangle", "w": "med", "len": "med"}))


def title(slide, t, kicker):
    text(slide, 1.0, 1.6, 18, 0.4, kicker.upper(), size=18, color=GOLD, bold=True, font=HEAD, name="Kicker")
    text(slide, 1.0, 2.0, 18, 0.85, t, size=40, bold=True, font=HEAD, name="Title")


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


# ------------------------------------------------------------------ chart for slide 7, sized for the deck
D = json.load(open(f"{REPO}/dashboard/data.json"))
rows = D["sealed"]["rows"]
net = lambda k, t: next(r["net"] for r in rows if r["strategy"] == k and r["test"] == t and r["slip"] == 5) / 1000
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 20, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#888",
                     "xtick.color": "#333", "ytick.color": "#555", "axes.axisbelow": True})
fig, ax = plt.subplots(figsize=(10.4, 5.4), dpi=200)
strat = [("A", "Strategy A", "#a3a3a3"), ("B", "Strategy B", "#835a07"), ("C", "Strategy C", "#d1aa55")]
for j, (k, n, c) in enumerate(strat):
    vals = [net(k, "test3"), net(k, "test2")]
    xs = [i + (j - 1) * 0.27 for i in range(2)]
    ax.bar(xs, vals, 0.25, color=c, label=n)
    for xv, v in zip(xs, vals):
        ax.text(xv, v + (2.5 if v >= 0 else -2.5), ("+" if v >= 0 else "−") + f"₹{abs(v):.0f}k", ha="center", va="bottom" if v >= 0 else "top", fontsize=19, fontweight="bold" if k == "B" else None)
ax.axhline(0, color="#333", lw=1.4)
ax.set_xticks([0, 1], ["2016 – 2019", "2020 – 2023"], fontsize=21)
ax.set_ylabel("Net profit, ₹ thousand", fontsize=18, color="#555")
ax.set_ylim(-82, 52); ax.grid(axis="y", color="#e6e6e6")
ax.legend(frameon=False, fontsize=18, ncol=3, loc="lower left", bbox_to_anchor=(0, 0.98))
fig.tight_layout(); fig.savefig(os.path.join(HERE, "deck_sealed.png")); plt.close(fig)

# ------------------------------------------------------------------ 1 TEAM
s = S[0]; clear(s)
text(s, 1.0, 5.05, 8, 0.75, "TEAM", size=44, bold=True, font=HEAD, name="Title")
text(s, 1.0, 5.95, 8.6, 0.4, "TEAM NAME", size=18, bold=True, color=GOLD, font=HEAD)
text(s, 1.0, 6.35, 8.6, 0.75, "SYNTAX TERROR (TAN)", size=40, bold=True, font=HEAD, name="Team name")
text(s, 1.0, 7.25, 8.6, 1.0, [[("Project: ", {"bold": True}), ("Parity, MCX gold futures intelligence", {})],
                              [("Problem 03: ", {"bold": True}), ("Commodity Derivatives Intelligence", {})]], size=22, color=INK2, after=4)
chips = [("check", "Working prototype", 3.35), ("database", "710 contracts", 2.65), ("shield", "3 sealed tests", 2.8)]
cx = 1.0
for k, t, w in chips:
    box(s, cx, 8.75, w, 0.7, fill=GOLDBG, line=None, radius=0.5, name=t)
    s.shapes.add_picture(I(k), Inches(cx + 0.18), Inches(8.88), Inches(0.44), Inches(0.44))
    text(s, cx + 0.72, 8.75, w - 0.8, 0.7, t, size=19, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    cx += w + 0.2
box(s, 10.4, 5.05, 8.6, 5.55, name="Members card")
text(s, 10.85, 5.35, 8, 0.4, "MEMBERS AND ROLES", size=18, bold=True, color=GOLD, font=HEAD)
team = [("Nikhil Kumar", "Team lead · data pipeline, strategy research and backtests, dashboard"),
        ("Sai Ganesh", "Market research and pitch presentation"),
        ("Ishaan Chhabra", "Testing, data checks and documentation")]
for i, (n, r) in enumerate(team):
    y = 5.95 + i * 1.5
    icon(s, "users" if i else "target", 10.85, y + 0.05, 0.8, filled=(i == 0))
    text(s, 11.9, y, 6.9, 0.5, n, size=28, bold=True, name=f"Member {i + 1}")
    text(s, 11.9, y + 0.52, 6.9, 0.85, r, size=20, color=INK2)
notes(s, "We are SYNTAX TERROR (TAN). Our project, Parity, answers Problem 03 with a working prototype built on 710 official MCX gold contracts.")

# ------------------------------------------------------------------ 2 PROBLEM
s = S[1]; clear(s)
title(s, "One metal, four prices. Which one is fair?", "Problem statement & theme")
cards = [("GOLDM", "100 g bar · 99.5% pure", "₹1,49,055", "per 10 g", "₹14,980"), ("GOLDTEN", "10 g bar · 99.9% pure", "₹1,49,436", "per 10 g", "₹14,959"),
         ("GOLDGUINEA", "8 g coin · 99.9% pure", "₹1,19,993", "per 8 g", "₹15,014"), ("GOLDPETAL", "1 g · 99.9% pure", "₹15,002", "per 1 g", "₹15,017")]
for i, (n, d, px, q, pg) in enumerate(cards):
    x = 1.0 + i * 4.55
    box(s, x, 3.15, 4.3, 3.05, name=f"Contract {n}")
    text(s, x + 0.3, 3.35, 3.8, 0.5, n, size=26, bold=True, font=HEAD)
    text(s, x + 0.3, 3.88, 3.8, 0.4, d, size=19, color=INK2)
    text(s, x + 0.3, 4.4, 3.8, 0.5, [[(px, {"bold": True}), ("  " + q, {"size": 19, "color": INK2})]], size=26)
    box(s, x + 0.3, 5.12, 3.7, 0.85, fill=GOLDBG, line=None, radius=0.2)
    text(s, x + 0.45, 5.12, 3.5, 0.85, [[(pg, {"bold": True, "color": GOLD, "size": 28}), (" per pure g", {"size": 19, "color": INK2})]], anchor=MSO_ANCHOR.MIDDLE)
text(s, 1.0, 6.35, 18, 0.4, "Most traded contract of each type, MCX closing prices, 1 October 2026. Different quotes, nearly the same gold price.", size=17, color=INK2)
cols = [("search", "Problem", ["Quotes differ by size and purity, so they cannot be compared at a glance",
                                "Is a price gap real, or just a unit mix-up?"]),
        ("activity", "Impact", ["The 8 g coin costs 0.6–0.7% more per gram, in all 41 contract months since late 2023",
                                "In the 2026 gold crash, small contracts sat 2.7% above GOLDM"]),
        ("target", "Theme alignment", ["Problem 03: Commodity Derivatives Intelligence",
                                       "Covers fair value, futures curve, backtest, alerts and contract calendar"])]
for i, (k, h, its) in enumerate(cols):
    x = 1.0 + i * 6.07
    box(s, x, 6.95, 5.8, 3.2, fill=GOLDBG if i == 2 else WHITE, name=h)
    icon(s, k, x + 0.3, 7.2, 0.72)
    text(s, x + 1.2, 7.2, 4.4, 0.72, h.upper(), size=20, bold=True, color=GOLD, font=HEAD, anchor=MSO_ANCHOR.MIDDLE)
    bullets(s, x + 0.3, 8.15, 5.25, 2.5, its, size=20, after=8)
notes(s, "Four MCX contracts hold the same metal but quote it four ways. Converted to rupees per gram of pure gold they nearly match. "
         "The gaps that remain are real money: the coin's steady premium, and a 2.7% gap during the 2026 crash.")

# ------------------------------------------------------------------ 3 SOLUTION (v3: live link, why Parity, result up front)
SITE = "https://parity-gold-site.vercel.app"
s = S[2]; clear(s)
title(s, "Parity tells a trader when a price gap is real", "Solution")
pic = s.shapes.add_picture(os.path.join(HERE, "dash-overview-v3.png"), Inches(1.0), Inches(3.05), width=Inches(10.2)); pic.name = "Dashboard screenshot"
pic.line.color.rgb = LINE; pic.line.width = Pt(1.5); pic.click_action.hyperlink.address = SITE
box(s, 1.0, 8.12, 3.0, 0.6, fill=GOOD, line=None, radius=0.5, name="Live badge")
text(s, 1.0, 8.12, 3.0, 0.6, "LIVE PROTOTYPE", size=17, bold=True, color=WHITE, font=HEAD, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
lt = text(s, 4.2, 8.12, 7.0, 0.6, [[("parity-gold-site.vercel.app", {"bold": True, "color": GOLD, "size": 21}), ("   8 pages, open in any browser", {"size": 17, "color": INK2})]], anchor=MSO_ANCHOR.MIDDLE, name="Live link")
lt.click_action.hyperlink.address = SITE
box(s, 1.0, 9.0, 10.2, 1.65, fill=GOLDBG, line=None, name="Result")
icon(s, "flask", 1.3, 9.3, 0.8)
text(s, 2.35, 9.17, 8.65, 1.4, [[("TESTED ONCE ON 8 YEARS IT NEVER SAW", {"bold": True, "size": 18, "color": GOLD, "font": HEAD})],
                               [("The fair-price rule made money in all 3 sealed tests, after every cost. The edge is small, and we say so.", {"size": 20})]], after=4)
feats = [("scale", "Fair comparison", "all four in ₹ per pure gram"), ("bell", "Quiet alerts", "only when a price strays far from fair"),
         ("flask", "Honest backtests", "after every fee, tax and slippage"), ("calendar", "Contract calendar", "every trade vs delivery dates")]
text(s, 11.75, 3.05, 7.2, 0.4, "WHAT IT DOES", size=18, bold=True, color=GOLD, font=HEAD)
for i, (k, h, d) in enumerate(feats):
    y = 3.55 + i * 0.78
    icon(s, k, 11.75, y, 0.62)
    text(s, 12.6, y, 6.4, 0.62, [[(h, {"bold": True, "size": 21}), ("  " + d, {"size": 18, "color": INK2})]], anchor=MSO_ANCHOR.MIDDLE)
box(s, 11.75, 6.85, 7.25, 3.8, name="Why Parity")
text(s, 12.05, 7.02, 6.8, 0.4, "WHY PARITY, NOT A SNAPSHOT", size=18, bold=True, color=GOLD, font=HEAD)
why = [("23 years of MCX data", "710 contracts, 2003–2026, every row checked"),
       ("8 sealed years, tested once", "rules frozen in Git before the data was opened"),
       ("Fair price off GOLDM", "the contract with 20–60× the volume, not thin pairs"),
       ("MCX's own rules", "every trade checked against the delivery period")]
for i, (h, d) in enumerate(why):
    y = 7.5 + i * 0.77
    text(s, 12.05, y, 0.6, 0.7, f"0{i + 1}", size=20, bold=True, color=GOLD, font=HEAD)
    text(s, 12.65, y, 6.2, 0.75, [[(h, {"bold": True, "size": 20})], [(d, {"size": 16, "color": INK2})]], after=0)
notes(s, "Parity is live at parity-gold-site.vercel.app. It compares the four contracts fairly, raises an alert only when a contract strays far from its fair price, "
         "backtests every rule after real costs, and checks every trade against the contract calendar. What sets it apart: 23 years of MCX data, eight years sealed and tested once, "
         "a fair price built off GOLDM, and the exchange's own delivery rules. Tested once on eight unseen years, the fair-price rule made money in all three sealed tests, but the edge is small, and we say so.")

# ------------------------------------------------------------------ 4 ARCHITECTURE
s = S[3]; clear(s)
title(s, "From exchange files to a trader's screen", "Architecture")
flow = [("database", "MCX files", "Official daily Bhavcopy, 2003–2026"), ("filter", "Clean & check", "Duplicates out, every row checked"),
        ("cpu", "Analyse", "Fair value, curve, backtests, alerts"), ("file", "Results", "Every number saved to a file"),
        ("layers", "Export", "One data file feeds every output")]
bw, gap = 3.16, 0.55
for i, (k, a, b) in enumerate(flow):
    x = 1.0 + i * (bw + gap)
    box(s, x, 3.15, bw, 2.75, fill=GOLDBG if i in (0, 4) else WHITE, name=f"Flow {i + 1}")
    icon(s, k, x + 0.25, 3.38, 0.75)
    text(s, x + 0.25, 4.27, bw - 0.45, 0.5, a, size=23, bold=True)
    text(s, x + 0.25, 4.8, bw - 0.45, 1.05, b, size=18, color=INK2)
    if i < len(flow) - 1:
        arrow(s, x + bw + 0.06, 4.52, x + bw + gap - 0.06, 4.52)
outs = [("monitor", "Dashboard", "for traders"), ("report", "Report", "17-page PDF"), ("play", "Pitch", "interactive story")]
for i, (k, a, b) in enumerate(outs):
    x = 1.0 + i * 6.07
    box(s, x, 6.3, 5.8, 1.15, name=f"Output {i + 1}")
    icon(s, k, x + 0.25, 6.45, 0.85, filled=False)
    text(s, x + 1.3, 6.3, 4.4, 1.15, [[(a + "  ", {"bold": True, "size": 23}), (b, {"size": 19, "color": INK2})]], anchor=MSO_ANCHOR.MIDDLE)
cols = [("code", "Tech stack", ["Python, pandas, NumPy", "React 19 built with esbuild", "ReportLab and Matplotlib"]),
        ("git", "How we keep it honest", ["Rules time-stamped in Git", "Sealed years kept in a separate file", "10 automated tests"]),
        ("globe", "APIs used", ["No paid APIs, no keys", "MCX's public Bhavcopy page", "Works fully offline"])]
for i, (k, h, its) in enumerate(cols):
    x = 1.0 + i * 6.07
    icon(s, k, x, 7.85, 0.62)
    text(s, x + 0.8, 7.85, 5.0, 0.62, h.upper(), size=19, bold=True, color=GOLD, font=HEAD, anchor=MSO_ANCHOR.MIDDLE)
    bullets(s, x, 8.65, 5.8, 1.9, its, size=20, after=4)
ct = text(s, 1.0, 10.55, 18, 0.4, [[("Live: ", {"color": INK2}), ("parity-gold-site.vercel.app", {"color": GOLD, "bold": True}), ("     Code: github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-", {"color": INK2})]], size=16)
ct.click_action.hyperlink.address = SITE
notes(s, "Official MCX files go in. They are cleaned and checked, every analysis writes its results to a file, and one export feeds the dashboard, report and pitch.")

# ------------------------------------------------------------------ 5 MARKET
s = S[4]; clear(s)
title(s, "Gold futures in India: big, and growing fast", "Market research / analysis")
stats = [("₹28,484 cr", "traded every day in MCX gold futures, FY2025-26"), ("3.4×", "growth in one year (₹8,449 cr a day in FY2024-25)"),
         ("57%", "of all MCX trading is bullion, Q2 FY26 (44% a year earlier)")]
for i, (b, sm) in enumerate(stats):
    x = 1.0 + i * 6.07
    box(s, x, 3.15, 5.8, 2.45, name=f"Stat {i + 1}")
    text(s, x + 0.35, 3.35, 5.2, 0.95, b, size=50, bold=True, color=GOLD, font=HEAD)
    text(s, x + 0.35, 4.4, 5.2, 1.1, sm, size=20, color=INK2)
text(s, 1.0, 5.72, 18, 0.4, "Sources: Business Today, 14 Aug 2026 (MCX data for FY2025-26); Business Standard, 7 Nov 2025 (MCX Q2 FY26 results).", size=16, color=INK2)
quads = [("users", "Target users", ["Traders choosing which gold contract to trade", "Arbitrage desks, jewellers hedging, broker research teams"]),
         ("coins", "Market size", ["MCX trades ₹4.11 lakh crore a day across all contracts (Q2 FY26)", "Gold comes in 1 kg, 100 g, 10 g, 8 g and 1 g lots"]),
         ("wallet", "Revenue model (our plan)", ["Free dashboard; paid alerts by email or Telegram", "Licence for broker research desks, and a data feed"]),
         ("trend", "Expected growth", ["Small lots (10 g, 1 g) are bringing in new traders", "Same method extends to silver: SILVERM, SILVERMIC"])]
for i, (k, h, its) in enumerate(quads):
    x = 1.0 + (i % 2) * 9.15; y = 6.35 + (i // 2) * 2.2
    icon(s, k, x, y, 0.72)
    text(s, x + 0.95, y, 7.9, 0.72, h.upper(), size=19, bold=True, color=GOLD, font=HEAD, anchor=MSO_ANCHOR.MIDDLE)
    bullets(s, x + 0.95, y + 0.8, 7.9, 1.35, its, size=20, after=3)
notes(s, "Gold futures on MCX trade about 28 thousand crore rupees a day, 3.4 times more than a year earlier. "
         "Market figures are from MCX data reported by Business Today and Business Standard; the revenue model is our plan.")

# ------------------------------------------------------------------ 6 FUTURE
s = S[5]; clear(s)
title(s, "What comes next", "Future scope")
items = [("activity", "Live paper trading", "Daily MCX update pipeline is built; next, a day-by-day paper record of the fair-price rule"),
         ("clock", "Intraday prices", "Measure real trading costs instead of assuming them"),
         ("bell", "Alerts on your phone", "Email and Telegram alerts that show the cost of acting"),
         ("layers", "Longer history", "Measure the coin and 1 g premiums back to 2008"),
         ("lock", "Safer rules", "Skip days stuck at the price limit; cross-check with spot gold rates"),
         ("coins", "More metals", "The same method for silver and other multi-size contracts")]
for i, (k, a, b) in enumerate(items):
    x = 1.0 + (i % 3) * 6.07; y = 3.15 + (i // 3) * 3.8
    box(s, x, y, 5.8, 3.5, fill=GOLDBG if i == 0 else WHITE, name=a)
    icon(s, k, x + 0.35, y + 0.35, 0.9)
    text(s, x + 4.6, y + 0.35, 0.9, 0.9, f"0{i + 1}", size=26, bold=True, color=LINE if i else GOLD, font=HEAD, align=PP_ALIGN.RIGHT)
    text(s, x + 0.35, y + 1.45, 5.1, 0.5, a, size=25, bold=True)
    text(s, x + 0.35, y + 2.05, 5.1, 1.3, b, size=20, color=INK2)
notes(s, "First, prove the rule live on paper. Then better data, alerts where traders already are, and the same method for silver.")

# ------------------------------------------------------------------ 7 EXTRA: results
s = S[6]; clear(s)
title(s, "Tested on 8 years it had never seen", "Extra: results")
s.shapes.add_picture(os.path.join(HERE, "deck_sealed.png"), Inches(1.0), Inches(3.05), width=Inches(10.4)).name = "Sealed tests chart"
text(s, 1.0, 8.5, 10.4, 0.4, "Net profit after all costs, 5 bp slippage. Each window run once, with rules frozen first.", size=16, color=INK2)
pts = [("Strategy A fails.", "It lost in both windows, even with perfect fills."),
       ("Strategy B holds up.", "It made money in all 3 sealed tests: ₹12,990, ₹35,873 and ₹6,962."),
       ("We say it plainly.", "The edge is small, and trading costs decide it.")]
for i, (h, d) in enumerate(pts):
    y = 3.25 + i * 1.75
    icon(s, ["zap", "check", "shield"][i], 11.9, y + 0.05, 0.75, filled=(i != 0))
    text(s, 12.9, y, 6.1, 1.6, [[(h, {"bold": True, "size": 24})], [(d, {"size": 20, "color": INK2})]], after=2)
box(s, 1.0, 9.0, 18.0, 1.7, fill=GOLDBG, line=None, name="Data")
for i, (b, sm) in enumerate([("710", "MCX contracts, 2003–2026"), ("55,457", "daily rows checked"), ("0", "unexplained data errors"), ("3", "sealed tests, each run once")]):
    x = 1.4 + i * 4.5
    text(s, x, 9.12, 4.2, 0.85, b, size=40, bold=True, color=GOLD, font=HEAD)
    text(s, x, 9.98, 4.2, 0.55, sm, size=18, color=INK2)
notes(s, "We tested on eight years the rules had never seen. The simple pairs rule failed. The fair-price rule made money in all three sealed tests, "
         "but the edge is small and depends on trading costs, and we say so.")

# ------------------------------------------------------------------ 8 THANK YOU: add the code link
s = S[7]
for sh in list(s.shapes):                      # the template's hand-lettered 'Thank you!' needs the Caveat font; retype it so any viewer shows it cleanly
    if sh.shape_type != 13:
        sh._element.getparent().remove(sh._element)
text(s, 1.0, 4.75, 18.0, 2.4, "Thank you!", size=150, bold=True, font="Caveat", align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, name="Thank you")
text(s, 1.0, 7.45, 18.0, 0.6, [[("SYNTAX TERROR (TAN)", {"bold": True, "color": GOLD}), ("  ·  Parity, MCX gold futures intelligence", {"color": INK2})]],
     size=26, font=HEAD, align=PP_ALIGN.CENTER)
text(s, 1.0, 8.2, 18.0, 0.5, "Nikhil Kumar  ·  Sai Ganesh  ·  Ishaan Chhabra", size=22, color=INK2, align=PP_ALIGN.CENTER)
q = s.shapes.add_picture(os.path.join(HERE, "qr-site.png"), Inches(17.35), Inches(8.55), Inches(1.75), Inches(1.75)); q.name = "Live site QR"; q.click_action.hyperlink.address = SITE
lk = text(s, 1.0, 8.85, 18.0, 0.5, [[("Try it live: ", {"color": INK2}), ("parity-gold-site.vercel.app", {"bold": True, "color": GOLD})]], size=24, align=PP_ALIGN.CENTER, name="Live link")
lk.click_action.hyperlink.address = SITE
text(s, 14.6, 10.4, 4.5, 0.4, "Scan for the live site", size=16, color=INK2, align=PP_ALIGN.RIGHT)

prs.save(os.path.join(HERE, "parity-round1.pptx"))
print("saved")

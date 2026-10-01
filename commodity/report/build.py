from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether, NextPageTemplate)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

D = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", D + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", D + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", D + "DejaVuSans-Oblique.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB"); addMapping("DV", 0, 1, "DVI"); addMapping("DV", 1, 1, "DVB")

import os
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
OUT = HERE + "Gold_Futures_Spread_Intelligence.pdf"

INK, INK2, MUTED = colors.HexColor("#1b1b1a"), colors.HexColor("#52514e"), colors.HexColor("#8a8984")
GOLD, GOLD_BG = colors.HexColor("#9a6b00"), colors.HexColor("#fbf5e6")
BLUE_BG, RULE = colors.HexColor("#eef4fc"), colors.HexColor("#dcdad3")
RED_BG = colors.HexColor("#fdf0ec")

ss = {}
ss["title"] = ParagraphStyle("title", fontName="DVB", fontSize=24, leading=30, textColor=INK, spaceAfter=6)
ss["sub"] = ParagraphStyle("sub", fontName="DV", fontSize=12, leading=17, textColor=INK2)
ss["h1"] = ParagraphStyle("h1", fontName="DVB", fontSize=16, leading=21, textColor=INK, spaceBefore=4, spaceAfter=8)
ss["h2"] = ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, textColor=GOLD, spaceBefore=10, spaceAfter=4)
ss["body"] = ParagraphStyle("body", fontName="DV", fontSize=9.5, leading=14.2, textColor=INK, spaceAfter=6)
ss["small"] = ParagraphStyle("small", fontName="DV", fontSize=8, leading=11, textColor=INK2, spaceAfter=4)
ss["cap"] = ParagraphStyle("cap", fontName="DVI", fontSize=8, leading=11, textColor=INK2, spaceAfter=8)
ss["cell"] = ParagraphStyle("cell", fontName="DV", fontSize=8.3, leading=11, textColor=INK)
ss["cellb"] = ParagraphStyle("cellb", parent=ss["cell"], fontName="DVB")
ss["bullet"] = ParagraphStyle("bullet", parent=ss["body"], leftIndent=12, bulletIndent=2, spaceAfter=3)
ss["box"] = ParagraphStyle("box", parent=ss["body"], spaceAfter=3)
ss["big"] = ParagraphStyle("big", fontName="DVB", fontSize=17, leading=20, textColor=INK, alignment=TA_CENTER)
ss["bigcap"] = ParagraphStyle("bigcap", fontName="DV", fontSize=7.8, leading=10, textColor=INK2, alignment=TA_CENTER)

W = A4[0] - 40 * mm


def P(t, s="body"): return Paragraph(t, ss[s])
def B(items): return [Paragraph(i, ss["bullet"], bulletText="•") for i in items]


def table(rows, widths, head=True, zebra=True, bold_first_col=False):
    data = []
    for r_i, r in enumerate(rows):
        data.append([Paragraph(str(c), ss["cellb"] if (head and r_i == 0) or (bold_first_col and c_i == 0) else ss["cell"])
                     for c_i, c in enumerate(r)])
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1efe8")), ("LINEBELOW", (0, 0), (-1, 0), 0.8, MUTED)]
    if zebra:
        for i in range(1 if head else 0, len(rows)):
            if i % 2 == 0: st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#faf9f6")))
    t.setStyle(TableStyle(st))
    return t


def box(flow, bg=GOLD_BG, edge=GOLD):
    t = Table([[flow]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, edge),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def tiles(items):
    cells = [[Paragraph(v, ss["big"]), Spacer(1, 3), Paragraph(c, ss["bigcap"])] for v, c in items]
    t = Table([cells], colWidths=[W / len(items)] * len(items))
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.5, RULE),
                           ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def img(name, w=W):
    from PIL import Image as PI
    iw, ih = PI.open(HERE + name).size
    return Image(HERE + name, width=w, height=w * ih / iw)


def on_page(c, doc):
    c.saveState()
    c.setFont("DV", 7.5); c.setFillColor(MUTED)
    c.drawString(20 * mm, 12 * mm, "Gold Futures Spread Intelligence  ·  Hack in Hills '26, Problem 03")
    c.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {doc.page}")
    c.restoreState()


def on_cover(c, doc):
    c.saveState(); c.setFillColor(GOLD); c.rect(0, A4[1] - 9 * mm, A4[0], 9 * mm, stroke=0, fill=1); c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
                      title="Gold Futures Spread Intelligence", author="Team SyntaxTerror",
                      subject="Hack in Hills '26, Problem 03: Commodity Derivatives Intelligence")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
doc.addPageTemplates([PageTemplate("cover", [frame], onPage=on_cover), PageTemplate("main", [frame], onPage=on_page)])

s = []
# ---------------------------------------------------------------- cover
s += [Spacer(1, 30 * mm), P("HACK IN HILLS '26  ·  PROBLEM 03: COMMODITY DERIVATIVES INTELLIGENCE", "small"), Spacer(1, 4),
      P("Gold Futures Spread Intelligence", "title"),
      P("One metal, four contracts: do India's gold futures agree on the price of gold, and can the gaps be traded after real costs?", "sub"),
      Spacer(1, 14 * mm),
      tiles([("70", "MCX contracts analysed<br/>(5,666 daily records)"),
             ("0", "unexplained data errors<br/>after integrity checks"),
             ("60–73 bp", "extra price of small gold<br/>contracts in normal months"),
             ("about 2.5%", "average gap during the<br/>Dec 2025 – Mar 2026 crash")]),
      Spacer(1, 14 * mm),
      box(P("<b>Status as of 2 October 2026.</b> All numbers come from official MCX Bhavcopy files and are reproducible "
            "with the scripts in our repository. Nothing in this report is estimated or invented unless it is clearly marked "
            "<i>projection</i> (Section 9).", "box"), BLUE_BG, colors.HexColor("#2a78d6")),
      Spacer(1, 40 * mm),
      P("Team SyntaxTerror  ·  github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-", "small"),
      NextPageTemplate("main"), PageBreak()]

# ---------------------------------------------------------------- contents + summary
s += [P("Contents", "h1")]
toc = [("1", "Summary in one page"), ("2", "The problem, in plain words"), ("3", "Words you will see"),
       ("4", "Our data and how we checked it"), ("5", "How we solve it, step by step"), ("6", "How we keep the test honest"),
       ("7", "Results: what the gaps look like"), ("8", "Results: can the gaps be traded?"),
       ("9", "What more data will add (with projections)"), ("10", "Limitations"), ("11", "References and files")]
s += [table([[a, b] for a, b in toc], [0.06, 0.94], head=False, zebra=False), Spacer(1, 10)]

s += [P("1. Summary in one page", "h1"),
      P("India's commodity exchange, MCX, lists four gold futures contracts that differ only in size and purity. "
        "Once their prices are converted to the same unit, rupees per gram of pure gold, they should be nearly identical. "
        "We checked that with 70 contracts of official exchange data, measured every gap, and tested two trading strategies "
        "on data they had never seen, after realistic costs."),
      P("What we found", "h2")]
s += B(["<b>The conversion works.</b> In normal months the 100 g bar (GOLDM) and the 10 g bar (GOLDTEN) are priced the same "
        "per pure gram: +2.8 basis points, with a 95% range of −0.7 to +6.2. A mistake in our purity correction would show up as a 40-point gap.",
        "<b>Small contracts cost more.</b> The 8 g coin (GOLDGUINEA) is about 60 bp (0.6%) dearer per gram, and the 1 g contract "
        "(GOLDPETAL) about 73 bp (0.73%). This held in every contract cycle we checked, so it is a lasting premium, not a passing mistake.",
        "<b>In a crash the gap explodes.</b> During the gold sell-off of December 2025 to March 2026, small contracts traded up to "
        "about 2.5% above GOLDM on average, with a monthly peak of 3.6%. The most traded contract moved first and furthest; the small ones lagged.",
        "<b>Trading the gaps is not reliably profitable yet.</b> Our simple strategy made money in the sealed test (+₹1.9 lakh at "
        "5 bp slippage), but all of it came from January 2026; in the other months it lost ₹77,410. Our fair-price strategy made "
        "+₹12,990, but its 95% range (−₹18,671 to +₹50,806) includes zero.",
        "<b>The answer is honest by design.</b> Every rule was fixed and time-stamped in Git before the test data was downloaded."])
s += [P("Why this matters", "h2"),
      P("Most backtests look profitable because they are tuned on the same data they are judged on, or they ignore costs. "
        "We did neither. The result is a map of when these gold contracts disagree, how large the disagreement is, and the conditions "
        "under which it can be traded: in sharp market falls, not in quiet months."),
      PageBreak()]

# ---------------------------------------------------------------- problem
s += [P("2. The problem, in plain words", "h1"),
      P("A <b>futures contract</b> is an agreement to buy or sell something at a fixed price on a future date. On MCX, people trade "
        "gold futures every day; the price moves with the gold price. Gold is sold in many sizes, so MCX offers four gold contracts "
        "for different budgets:"),
      table([["Contract", "Size of one lot", "Price is quoted per", "Purity", "Expires around", "Gold traded per day*"],
             ["GOLDM (Gold Mini)", "100 g", "10 g", "99.5%", "5th of the month", "649 kg"],
             ["GOLDTEN", "10 g", "10 g", "99.9%", "last day of month", "35 kg"],
             ["GOLDGUINEA", "8 g (coin)", "8 g", "99.9%", "last day of month", "12 kg"],
             ["GOLDPETAL", "1 g", "1 g", "99.9%", "last day of month", "22 kg"]],
            [0.2, 0.14, 0.17, 0.1, 0.2, 0.19]),
      P("* Median over all our data. GOLDM trades about 20–55 times more gold than the others, which makes it the most reliable price.", "cap"),
      P("Because each contract quotes its price for a different amount and purity of gold, the raw prices look very different "
        "(for example ₹97,214, ₹97,428, ₹78,086 and ₹9,820 on the same day). Underneath, they are all the same metal. "
        "The hackathon problem asks us to:"),
      ]
s += B(["<b>Put all four on a common basis</b>, so the prices can be compared fairly;",
        "<b>measure the gaps</b> between them: how big, how stable, and when they change;",
        "<b>test whether any gap can be traded</b> for profit after real costs (fees, taxes, and the cost of not getting the exact price);",
        "<b>present the analysis honestly</b>, without the shortcuts that make backtests look better than reality."])
s += [P("Why would the prices differ at all?", "h2"),
      P("Several real reasons can make the same gold cost slightly different amounts per gram in different contracts: smaller pieces "
        "cost more to mint and deliver per gram; small contracts trade less, so their prices update more slowly; and the "
        "contracts expire on different dates, so money tied up for longer costs interest (the <i>cost of carry</i>). "
        "Part of our job is to separate these normal, explainable gaps from gaps that are unusual and might be tradeable."),
      PageBreak()]

# ---------------------------------------------------------------- glossary
s += [P("3. Words you will see", "h1"),
      table([["Term", "Meaning in this report"],
             ["MCX", "Multi Commodity Exchange of India, where these gold futures trade."],
             ["Bhavcopy", "The exchange's official daily record of each contract: open, high, low, close, volume, value traded."],
             ["Expiry", "The date a futures contract ends. Each contract month is a separate contract (a <i>cycle</i>)."],
             ["Per pure gram", "Price divided by quote size and purity. Our common unit: ₹ per gram of 100% gold."],
             ["Basis point (bp)", "One hundredth of a percent. 100 bp = 1%. A 60 bp gap on ₹10,000 gold is ₹60 per gram."],
             ["Spread / gap / premium", "How much more one contract costs than another, per pure gram, in bp."],
             ["Cost of carry", "Interest-like cost that makes a later-expiring contract slightly dearer. We measure it from the data."],
             ["Settlement close", "The exchange's official end-of-day price. Not always a price anyone actually traded at."],
             ["VWAP", "Average traded price of the day = total value traded ÷ grams traded. A realistic fill price."],
             ["Slippage", "Getting a slightly worse price than planned. We test 0, 5 and 10 bp per trade leg."],
             ["Backtest", "Replaying a trading rule on past data to see what it would have earned."],
             ["Out-of-sample / sealed test", "Data the rule never saw while it was being designed. The only fair test."],
             ["95% range", "The range the true value most likely lies in, given how noisy the data is. If it includes zero, "
                           "the result could be luck."],
             ["Lakh", "₹1,00,000."]],
            [0.24, 0.76], bold_first_col=True),
      PageBreak()]

# ---------------------------------------------------------------- data
s += [P("4. Our data and how we checked it", "h1"),
      P("<b>Source.</b> MCX Bhavcopy, downloaded by hand one contract at a time from mcxindia.com (the site blocks automated "
        "downloads). We do not use stitched ‘continuous’ price series from charting sites, because joining different contracts "
        "together creates false jumps."),
      tiles([("70", "contracts"), ("5,666", "daily records"), ("1 Jan 2025", "first date"), ("25 Sep 2026", "last date")]),
      Spacer(1, 8),
      P("Every file is identified by its contents (not its file name), duplicates are removed automatically, and each row is "
        "checked before it is used:"),
      table([["Check", "What it catches", "Rows failing"],
             ["Duplicate rows", "Same contract and date twice", "0.00%"],
             ["Row after expiry", "Wrong dates", "0.00%"],
             ["Open or close outside the day's high–low", "Corrupt prices", "0.00%"],
             ["Zero or negative price", "Corrupt prices", "0.00%"],
             ["Missing trading day inside a contract's life", "Incomplete downloads", "0.00%"],
             ["Previous close ≠ last row's close", "Broken history", "0.29% (16 rows), all right after a no-trade day; explained, flagged and excluded"],
             ["Price > 5% away from same-month peers", "Wrong units or lot sizes", "0.11% (6 rows), all GOLDM on 21, 29 and 30 Jan 2026"]],
            [0.36, 0.26, 0.38]),
      Spacer(1, 6),
      P("The six flagged rows are real. On 30 January 2026 gold fell about 10% in a day; GOLDM settled at its day's low (its lower "
        "price limit) while the smaller contracts settled higher. News reports confirm the crash (Section 11). We kept these rows "
        "and did not change any rule because of them."),
      P("How far is the official close from a real trade?", "h2"),
      P("We compared each day's settlement close with that day's average traded price (VWAP). For a single contract the median "
        "gap is 20–26 bp. For the <i>gap between two contracts</i>, which is what we trade, the median is only 6.7–8.4 bp because the "
        "day's gold move cancels out. This is why we assume 5 bp of slippage per leg as the realistic case, and also show 0 and 10 bp."),
      PageBreak()]

# ---------------------------------------------------------------- method
s += [P("5. How we solve it, step by step", "h1"),
      P("Step 1: Convert every price to rupees per gram of pure gold", "h2"),
      P("<b>price per pure gram = settlement price ÷ grams per quote ÷ purity</b>"),
      table([["15 Jul 2025", "Official price", "÷ grams", "÷ purity", "₹ per pure gram"],
             ["GOLDM (Aug expiry)", "97,214", "10", "0.995", "9,770.25"],
             ["GOLDTEN (Jul expiry)", "97,428", "10", "0.999", "9,752.55"],
             ["GOLDGUINEA (Jul expiry)", "78,086", "8", "0.999", "9,770.52"],
             ["GOLDPETAL (Jul expiry)", "9,820", "1", "0.999", "9,829.83"]],
            [0.3, 0.18, 0.13, 0.13, 0.26]),
      P("Four very different prices become four almost equal ones. The remaining differences, a few tenths of a percent, are what we study.", "cap"),
      P("Step 2: Line up the expiry dates", "h2"),
      P("GOLDTEN, GOLDGUINEA and GOLDPETAL expire on the same day, so they can be compared directly. GOLDM expires about five days "
        "later, and a later contract naturally costs a little more (cost of carry). We measure that carry every day from the data "
        "itself, by comparing neighbouring expiries of the same contract, and adjust GOLDM to its partner's expiry date. The adjustment is small "
        "(median about 13 bp) but without it GOLDM would look slightly too expensive."),
      P("Step 3: Measure the gaps", "h2"),
      P("For every pair of contracts and every day we compute the gap in basis points: 10,000 × ln(price A ÷ price B). We then average "
        "by contract cycle and compute 95% ranges with a <i>week-block bootstrap</i>: we resample whole weeks rather than single days, "
        "because one day's gap is strongly linked to the next, and treating them as independent would make us look more certain than we are."),
      P("Step 4: Turn gaps into trading rules", "h2"),
      P("We tested two families of rules. Both buy the contract that looks cheap and sell the one that looks expensive in equal grams "
        "of gold, so a rise or fall in the gold price itself roughly cancels out. They profit only if the gap returns to normal."),
      table([["", "Strategy A: same-expiry z-score", "Strategy B: GOLDM-anchored fair price"],
             ["Idea", "If today's gap between two small contracts is unusually far from its recent average, bet that it returns.",
              "GOLDM is the most traded, so trust its price. Fair price of a small contract = GOLDM + that contract's usual premium. "
              "Trade when the small contract strays from its fair price."],
             ["‘Unusual’ means", "More than 2 standard deviations from the average of the previous 10 days",
              "More than 1.5 standard deviations from its average premium on all previous days"],
             ["Size", "40 g per leg", "200 g per leg (2 GOLDM lots vs 20 / 25 / 200 lots)"],
             ["Fills at", "Next day's settlement close", "Next day's average traded price (VWAP)"],
             ["Exit", "Gap back to normal, or just before expiry", "Premium back to usual, or 5 business days before expiry"],
             ["Research basis", "Gatev, Goetzmann & Rouwenhorst (2006)", "Built from our own measurement that GOLDM = GOLDTEN"]],
            [0.17, 0.38, 0.45], bold_first_col=True),
      Spacer(1, 6),
      P("We also compared research-backed alternatives (Ornstein–Uhlenbeck mean-reversion scores, a cost filter, and a Kalman filter "
        "that treats thin-market prices as noisy). None made money on the training data after costs, so none was promoted."),
      P("Step 5: Charge realistic costs", "h2"),
      table([["Cost item", "Rate used", "Source / status"],
             ["MCX transaction fee", "₹2.10 per lakh of turnover", "MCX filing, effective 1 Oct 2024"],
             ["Commodity transaction tax", "0.01% on the sell side", "Non-agricultural futures rate"],
             ["Stamp duty", "0.002% on the buy side", "Broker charge sheets (assumption)"],
             ["SEBI fee", "₹10 per crore", "Assumption"],
             ["Brokerage", "₹20 per order, max 0.03%", "Discount broker (assumption)"],
             ["GST", "18% on brokerage and fees", "Assumption"],
             ["Slippage", "0 / 5 / 10 bp per leg per side", "5 bp = realistic case (Section 4)"]],
            [0.3, 0.33, 0.37]),
      P("Each trade has four legs (buy and sell on entry and exit), so every cost is paid four times.", "cap"),
      PageBreak()]

# ---------------------------------------------------------------- honesty
s += [P("6. How we keep the test honest", "h1"),
      P("The most common way to fool yourself in trading research is to tune a rule until it looks good on the past, and then report "
        "that same past as the result. We split the data <b>by calendar date</b> into periods with different jobs, and wrote down "
        "every rule, and the exact test dates, <b>before</b> the test data existed on our computers. Git commit timestamps prove the order."),
      table([["Period", "Dates", "Used for"],
             ["Train / Development", "up to 30 Apr 2025 (A); up to 5 Aug 2025 (B)", "Designing rules and choosing settings by a pre-declared rule"],
             ["Test 1 (Strategy A only)", "1 May – 31 Jul 2025", "First sealed test, run once"],
             ["Sealed holdout", "Aug 2025 – May 2026", "Final test of both strategies, run once"],
             ["Next sealed test", "1 Jan 2020 – 31 Dec 2023", "Declared 2 Oct 2026, before the data is downloaded (Section 9)"]],
            [0.24, 0.33, 0.43]),
      Spacer(1, 6),
      table([["Time (IST)", "Commit", "What happened"],
             ["1 Oct 2026, 21:45", "e5e0a21", "Holdout window declared, download list written"],
             ["1 Oct 2026, 22:15", "045ab2b", "Strategy B rules and setting (k = 1.5) frozen"],
             ["1 Oct 2026, 23:01", "7acf18e", "Holdout data (39 MCX files) uploaded"],
             ["1 Oct 2026, 23:05", "3e9e82d", "Holdout run once; results recorded as they came out"],
             ["2 Oct 2026, 03:28", "35d7e7b", "Next sealed test (2020–2023) declared before download"]],
            [0.22, 0.13, 0.65]),
      Spacer(1, 6),
      P("Other safeguards", "h2")]
s += B(["Signals use only information available at that day's close; trades happen on the next day.",
        "One position per contract type at a time, so one market move is not counted as several independent wins.",
        "Positions close before MCX's compulsory delivery period at expiry.",
        "We report results at three slippage levels, the 95% range, and how concentrated the profit is.",
        "A bug found during development (the 10-day average included the current day) was fixed <i>before</i> any test was run, and is logged.",
        "An earlier AI-generated draft from another tool produced statistics for contracts that were not in our data and references "
        "that did not exist. We discarded all of it and rebuilt every number from the raw files; every reference in Section 11 was checked."])
s += [PageBreak()]

# ---------------------------------------------------------------- results: gaps
s += [P("7. Results: what the gaps look like", "h1"),
      img("premium.png"),
      P("Monthly average price of each small contract above GOLDM, per pure gram, after the carry adjustment. June 2026 is missing "
        "because the matching GOLDM contract (July 2026 expiry) has not been downloaded yet.", "cap"),
      P("The chart shows two different worlds. In normal months GOLDTEN sits on GOLDM's line and the coin and 1 g contracts sit "
        "about 20–140 bp above it. From December 2025 to March 2026, while gold crashed, every small contract became much dearer "
        "than GOLDM, then the gaps returned to normal by April–May 2026."),
      table([["Gap (A minus B, per pure gram)", "Normal months", "Dec 2025 – Mar 2026"],
             ["GOLDM − GOLDTEN", "+2.8 bp (−0.7 to +6.2)", "−89.0 bp (−147.6 to −43.6)"],
             ["GOLDM − GOLDGUINEA", "−59.8 bp (−69.0 to −50.3)", "−245.9 bp (−324.1 to −178.0)"],
             ["GOLDM − GOLDPETAL", "−72.8 bp (−80.1 to −65.6)", "−252.8 bp (−323.5 to −191.5)"],
             ["GOLDTEN − GOLDGUINEA", "−62.2 bp (−69.7 to −54.9)", "−157.0 bp (−190.0 to −127.7)"],
             ["GOLDTEN − GOLDPETAL", "−73.4 bp (−79.2 to −68.2)", "−164.0 bp (−192.7 to −139.0)"],
             ["GOLDGUINEA − GOLDPETAL, all months", "−8.2 bp (−14.5 to −1.5)", "(not split)"]],
            [0.38, 0.31, 0.31]),
      P("Brackets show the 95% range. Normal months: 57–65 weeks of data; crash period: 18 weeks. We chose the period split after "
        "looking at the chart, so it describes the data rather than testing a prediction.", "cap"),
      P("What this tells us", "h2")]
s += B(["<b>The purity correction is right.</b> If it were wrong, GOLDM and GOLDTEN would differ by about 40 bp in every month; they differ by 3.",
        "<b>The small-contract premium is structural.</b> It appeared in every one of 15–18 contract cycles, so it does not close "
        "and cannot be captured by simply holding to expiry. A likely reason, which we have not proved, is the higher cost of "
        "minting and delivering small pieces.",
        "<b>Stress reveals who leads.</b> In a fast fall, GOLDM (where most gold trades) reprices first; the small contracts follow later. "
        "That delay is the only place we found real money (Section 8)."])
s += [PageBreak()]

# ---------------------------------------------------------------- results: trading
s += [P("8. Results: can the gaps be traded?", "h1"),
      P("Training and first test (Strategy A, 2025)", "h2"),
      table([["Period", "Trades", "Net at 0 bp", "Net at 5 bp", "Net at 10 bp"],
             ["Train (to Apr 2025)", "9", "lost money even before costs (gross −₹3,939)", "", ""],
             ["Test 1 (May–Jul 2025)", "19", "+₹10,292", "−₹4,466", "−₹19,224"]],
            [0.26, 0.1, 0.32, 0.16, 0.16]),
      P("Break-even slippage was about 3.5 bp: profitable only with near-perfect fills. 95% range at 5 bp: −₹9,849 to +₹2,350.", "cap"),
      P("Sealed holdout, Aug 2025 – May 2026 (run once)", "h2"),
      table([["Strategy", "Trades", "Net at 0 bp", "Net at 5 bp", "Net at 10 bp", "95% range at 5 bp"],
             ["A: same-expiry z-score (40 g)", "156", "+₹3,65,755", "+₹1,90,340", "+₹14,926", "−₹97,634 to +₹6,19,835"],
             ["B: GOLDM fair price (200 g)", "12", "+₹74,808", "+₹12,990", "−₹48,828", "−₹18,671 to +₹50,806"]],
            [0.24, 0.1, 0.15, 0.15, 0.14, 0.22]),
      Spacer(1, 6),
      img("zscore_months.png"),
      P("Strategy A in the sealed holdout, net profit by month of entry (₹ thousand, after costs, 5 bp slippage).", "cap"),
      P("How to read these numbers", "h2")]
s += B(["<b>Strategy A's profit is one event.</b> 30 trades in January 2026 made +₹2,67,750. The other 126 trades lost ₹77,410 and "
        "won only 27% of the time. The top five January trades alone are 54% of the total. Repricing every trade at the day's "
        "average traded price instead of the settlement close still gives +₹1,68,114, so the January profit is not just a settlement-price illusion.",
        "<b>Strategy B works only where a real premium exists.</b> It made +₹27,799 on GOLDGUINEA and +₹6,877 on GOLDPETAL, but lost "
        "₹21,686 on GOLDTEN, where there is no premium and the strategy trades noise. It used only 6 independent weeks, so its 95% range includes zero.",
        "<b>Costs decide everything.</b> Both strategies are clearly profitable at 0 bp slippage and lose at 10 bp. Realistic "
        "execution, 5 bp, sits right on the edge."])
s += [box(P("<b>Our verdict today.</b> The gaps between India's gold contracts are real, measurable and explainable. Trading them "
            "in quiet markets does not pay after costs. Trading them during sharp crashes did pay in our data, because small contracts "
            "lag GOLDM. With only one such crash inside our sealed test, this is a promising lead, not a proven edge, and the next "
            "data round is designed to test exactly this.", "box")),
      PageBreak()]

# ---------------------------------------------------------------- future
s += [P("9. What more data will add (with projections)", "h1"),
      P("GOLDGUINEA has traded on MCX since 2008 and GOLDPETAL since 2011, so years of the same official data exist. GOLDTEN only "
        "started on 1 April 2025, so its history can only grow month by month. We have asked for these MCX downloads, in priority order:"),
      table([["Batch", "Contracts", "Files", "What it adds"],
             ["A", "GOLDM May 2026; GUINEA, PETAL, GOLDM Jan–Mar 2025", "10", "Fills gaps in current data"],
             ["B", "GUINEA, PETAL, GOLDM, all 2024 expiries", "36", "More development data, including the 23 Jul 2024 Budget day, when import duty was cut from 15% to 6%"],
             ["C", "Same three, all 2020 expiries", "36", "Sealed test; contains the COVID market crash (Mar 2020) and the Aug 2020 gold peak and fall"],
             ["D", "Same three, 2021–2023 expiries", "108", "Rest of the sealed test: three more years of normal and stressed markets"]],
            [0.08, 0.38, 0.08, 0.46]),
      P("Projected precision", "h2"),
      P("The 95% range of an average shrinks roughly with the square root of the number of independent weeks. Assuming future data is "
        "about as variable as today's data (an assumption, not a guarantee), the ranges would narrow like this:"),
      table([["Measurement (vs GOLDM, all months)", "Today", "+ 2024 (about +52 weeks)", "+ 2020–2024 (about +260 weeks)"],
             ["GOLDGUINEA premium, 95% range", "± 23.9 bp (81 weeks)", "± 18.7 bp", "± 11.7 bp"],
             ["GOLDPETAL premium, 95% range", "± 20.9 bp (82 weeks)", "± 16.4 bp", "± 10.3 bp"],
             ["GOLDTEN premium, 95% range", "± 14.1 bp (74 weeks)", "± 10.8 bp after one more year of new data", "not available: no history before Apr 2025"],
             ["Strategy B, average profit per trade", "6 independent weeks", "—", "range about 40% as wide if trading frequency stays similar"],
             ["Crash episodes available to test", "2 (Apr 2025, Jan 2026)", "3 (+ Jul 2024 duty cut)", "5 (+ Mar 2020, Aug 2020)"]],
            [0.3, 0.21, 0.24, 0.25]),
      P("<i>Projection</i>: computed from today's measured variability; actual ranges will be known only after the data arrives.", "cap"),
      P("Planned improvements, to be fixed before the next sealed test", "h2")]
s += B(["<b>Price-limit filter:</b> skip days when a contract settles at its daily limit (close equal to the day's low or high on a "
        "large move), because nobody can reliably trade at that price. Detectable from the Bhavcopy alone.",
        "<b>Faster-adapting ‘usual premium’:</b> Strategy B's average of all past days lagged the 2026 spike, so it held some trades "
        "for over 100 days. A recent-weeks average or a Kalman filter will be compared on development data only.",
        "<b>Stress detector:</b> trade only when GOLDM has moved sharply, since that is where the lag appeared. This rule will be written "
        "down before we see 2020–2023, and judged only there.",
        "<b>Drop GOLDTEN from Strategy B:</b> no premium to trade, as both our measurements and the holdout show.",
        "<b>Independent cross-checks:</b> IBJA's published daily 999 and 995 gold rates (recent days only) to verify our purity "
        "ratio and carry estimate against physical gold."])
s += [P("What we will report after each batch: the same tables as this report, updated; whether the sealed-test result clears zero "
        "at 5 bp; and whether profits still come from crashes only.", "body")]

# ---------------------------------------------------------------- limitations
s += [P("10. Limitations", "h1")]
s += B(["<b>Short history.</b> 21 months of data and one large crash. Strong conclusions about trading need several crashes; Section 9 addresses this.",
        "<b>Daily data only.</b> We see one official close and one average price per day, not every trade. Real fills could be "
        "better or worse than our 5 bp assumption, especially in a crash, when prices move fastest.",
        "<b>Some costs are assumptions.</b> Stamp duty, SEBI fee, brokerage and GST rates come from typical broker charge sheets.",
        "<b>Liquidity limits size.</b> GOLDGUINEA trades about 12 kg a day; larger positions than ours would move the price.",
        "<b>Why the premium exists is a hypothesis.</b> Minting and delivery costs fit the data, but we have not verified them from MCX's delivery records.",
        "<b>Gaps in data.</b> GOLDM expiring May and July 2026 have not been downloaded, so two cycles are missing from GOLDM comparisons."])
s += [P("11. References and files", "h1"),
      P("Research papers (DOIs checked against Crossref or RePEc)", "h2")]
refs = ["Gatev, Goetzmann &amp; Rouwenhorst (2006). Pairs Trading: Performance of a Relative-Value Arbitrage Rule. Review of Financial Studies 19(3). doi:10.1093/rfs/hhj020",
        "Elliott, van der Hoek &amp; Malcolm (2005). Pairs trading. Quantitative Finance 5(3). doi:10.1080/14697680500149370",
        "Avellaneda &amp; Lee (2010). Statistical arbitrage in the US equities market. Quantitative Finance 10(7). doi:10.1080/14697680903124632",
        "Bertram (2010). Analytic solutions for optimal statistical arbitrage trading. Physica A 389(11). doi:10.1016/j.physa.2010.01.045",
        "Leung &amp; Li (2015). Optimal mean reversion trading with transaction costs and stop-loss exit. IJTAF 18(3). doi:10.1142/S021902491550020X",
        "Politis &amp; Romano (1994). The Stationary Bootstrap. JASA 89(428). doi:10.1080/01621459.1994.10476870",
        "Do &amp; Faff (2010). Does Simple Pairs Trading Still Work? Financial Analysts Journal 66(4). doi:10.2469/faj.v66.n4.1",
        "Krauss (2017). Statistical Arbitrage Pairs Trading Strategies: Review and Outlook. Journal of Economic Surveys 31(2). doi:10.1111/joes.12153",
        "Pavabutr &amp; Chaihetphon (2010). Price discovery in the Indian gold futures market. Journal of Economics and Finance 34(4). doi:10.1007/s12197-008-9068-9"]
s += [Paragraph(r, ss["small"], bulletText="•") for r in refs]
s += [P("Data and news sources", "h2")]
srcs = ["MCX Bhavcopy, mcxindia.com (Market Data → Bhavcopy): all price data in this report.",
        "MCX to start 8 gm gold coin futures, Business Standard, May 2008 (GOLDGUINEA launch).",
        "10 gram gold futures contract available from today, Outlook Money, 1 Apr 2025 (GOLDTEN launch and specification).",
        "Gold and silver prices fall after Budget cuts customs duty to 6%, Business Today, 23 Jul 2024.",
        "Government raises import duty on gold and silver to 15%, StudyCafe, May 2026 (Notification 16/2026-Customs).",
        "Silver crashes ₹1.10 lakh, gold down ₹20,000 on MCX, News Arena, 30 Jan 2026; Motilal Oswal market note, 30 Jan 2026.",
        "IBJA daily rates, ibjarates.com (planned cross-check)."]
s += [Paragraph(r, ss["small"], bulletText="•") for r in srcs]
s += [P("Code (repository folder <i>commodity/</i>)", "h2"),
      table([["Script", "What it does"],
             ["ingest.py", "Reads every MCX file, removes duplicates, validates rows, converts to ₹ per pure gram"],
             ["testbed.py", "Data error rates, settlement-vs-traded price gaps, 95% ranges"],
             ["accuracy.py", "Cost of carry, all six contract pairs, precision of each contract"],
             ["backtest.py", "Strategy A: train, test and holdout, each run once"],
             ["methods.py", "Research-backed alternatives compared on training data"],
             ["fairvalue.py", "Strategy B: development and sealed holdout"],
             ["uncertainty.py", "Week-block bootstrap for the profit ranges"]],
            [0.2, 0.8])]

doc.build(s)
print(OUT)

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
ss["h1"] = ParagraphStyle("h1", fontName="DVB", fontSize=16, leading=21, textColor=INK, spaceBefore=18, spaceAfter=8, keepWithNext=1)
ss["h2"] = ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, textColor=GOLD, spaceBefore=10, spaceAfter=4, keepWithNext=1)
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


import json
DJ = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "data.json")))


def sg(v): return ("+" if v >= 0 else "−") + f"{abs(v):.1f}"
def fmt(x): return "not listed yet" if not x else f"{sg(x[0])} bp ({sg(x[1])} to {sg(x[2])})"
def inr(v):
    n = f"{abs(round(v)):d}"; head, tail = n[:-3], n[-3:]
    while len(head) > 2: tail = head[-2:] + "," + tail; head = head[:-2]
    return ("−" if v < 0 else "+") + "₹" + (head + "," + tail if head else tail)


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
      tiles([("710", "MCX gold contracts held<br/>(55,457 daily records, 2003–2026)"),
             ("0", "unexplained data errors<br/>after integrity checks"),
             ("61–72 bp", "extra price of the 8 g coin<br/>over GOLDM, 2024 to 2026"),
             ("3 of 3", "sealed tests Strategy B made<br/>money in at 5 bp (none proven)")]),
      Spacer(1, 14 * mm),
      box(P("<b>Status as of 4 October 2026.</b> All numbers come from official MCX Bhavcopy files and are reproducible "
            "with the scripts in our repository. Nothing in this report is estimated or invented unless it is clearly marked "
            "<i>projection</i>; Section 9 compares the earlier projections with what the data later showed.", "box"), BLUE_BG, colors.HexColor("#2a78d6")),
      Spacer(1, 40 * mm),
      P("Team SyntaxTerror  ·  github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-", "small"),
      NextPageTemplate("main"), PageBreak()]

# ---------------------------------------------------------------- contents + summary
s += [P("Contents", "h1")]
toc = [("1", "Summary in one page"), ("2", "The problem, in plain words"), ("3", "Words you will see"),
       ("4", "Our data and how we checked it"), ("5", "How we solve it, step by step"), ("6", "How we keep the test honest"),
       ("7", "Results: what the gaps look like"), ("8", "Results: can the gaps be traded?"),
       ("9", "What the extra data showed"), ("10", "Limitations"), ("11", "References and files")]
s += [table([[a, b] for a, b in toc], [0.06, 0.94], head=False, zebra=False), Spacer(1, 10)]

s += [P("1. Summary in one page", "h1"),
      P("India's commodity exchange, MCX, lists four gold futures contracts that differ only in size and purity. "
        "Once their prices are converted to the same unit, rupees per gram of pure gold, they should be nearly identical. "
        "We measured every gap on 149 contracts of official exchange data (October 2023 to October 2026), and tested trading strategies "
        "after realistic costs on data they had never seen: a sealed holdout in 2025–26 and eight sealed years, 2016–2023, from "
        "710 contracts in all."),
      P("What we found", "h2")]
s += B(["<b>The conversion works.</b> In normal months the 100 g bar (GOLDM) and the 10 g bar (GOLDTEN) are priced the same "
        "per pure gram: +0.2 basis points, with a 95% range of −3.1 to +3.6. A mistake in our purity correction would show up as a 40-point gap.",
        "<b>The coin always costs more.</b> The 8 g coin (GOLDGUINEA) was about 72 bp (0.72%) dearer per gram than GOLDM in 2024 and "
        "about 61 bp in 2025–26. It was dearer in all 41 contract cycles we checked, so it is a lasting premium, not a passing mistake.",
        "<b>The 1 g contract changed sides.</b> GOLDPETAL traded about 137 bp (1.4%) <i>below</i> GOLDM through 2024, then about "
        "64 bp above it in 2025–26. A premium that can flip is not something to rely on.",
        "<b>In a crash the gap explodes.</b> During the gold sell-off of December 2025 to March 2026, the coin and 1 g contracts traded about "
        "2.6–2.7% above GOLDM on average (GOLDTEN about 1%), with a monthly peak of 3.8%. The most traded contract moved first and furthest; the small ones lagged.",
        "<b>The simple pairs rule fails.</b> Strategy A made +₹1.9 lakh in the 2025–26 sealed holdout at 5 bp slippage, but all of "
        "it came from January 2026; on eight older sealed years it lost in both windows (−₹1,11,508 over 246 trades).",
        "<b>The fair-price rule is positive, not proven.</b> Strategy B made money at 5 bp in all three sealed tests: +₹12,990 "
        "(2025–26), +₹35,873 (2016–2019) and +₹6,962 (2020–2023). Over 2016–2023 together, 80% of resamples are above zero, "
        "but the 95% range (−₹54,534 to +₹1,42,962) still includes zero, and at 10 bp it loses in two of the three tests.",
        "<b>Crashes pay sometimes, not always.</b> The 2026 crash paid; the March 2020 COVID crash did not pay a version retrained "
        "to trade only in stress (Strategy C), which did not beat B out of sample.",
        "<b>The answer is honest by design.</b> Every rule was fixed and time-stamped in Git before its test data was read, and "
        "each of the three sealed tests was run exactly once."])
s += [P("Why this matters", "h2"),
      P("Most backtests look profitable because they are tuned on the same data they are judged on, or they ignore costs. "
        "We did neither. The result is a map of when these gold contracts disagree, how large the disagreement is, and the conditions "
        "under which it can be traded: a small, positive edge that depends on good execution, not a money machine.")]

# ---------------------------------------------------------------- problem
s += [P("2. The problem, in plain words", "h1"),
      P("A <b>futures contract</b> is an agreement to buy or sell something at a fixed price on a future date. On MCX, people trade "
        "gold futures every day; the price moves with the gold price. Gold is sold in many sizes, so MCX offers four gold contracts "
        "for different budgets:"),
      table([["Contract", "Size of one lot", "Price is quoted per", "Purity", "Expires around", "Gold traded per day*"],
             ["GOLDM (Gold Mini)", "100 g", "10 g", "99.5%", "5th of the month", "441 kg"],
             ["GOLDTEN", "10 g", "10 g", "99.9%", "last day of month", "31 kg"],
             ["GOLDGUINEA", "8 g (coin)", "8 g", "99.9%", "last day of month", "7 kg"],
             ["GOLDPETAL", "1 g", "1 g", "99.9%", "last day of month", "12 kg"]],
            [0.2, 0.14, 0.17, 0.1, 0.2, 0.19]),
      P("* Median, October 2023 to October 2026. GOLDM trades about 14–60 times more gold than the others. Sizes, quotes, purities and "
        "expiry days are from the MCX contract specification of each contract. GOLDTEN only started in April 2025.", "cap"),
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
      P("The brief, point by point", "h2"),
      table([["The brief asks for", "Where this report answers it"],
             ["Normalize size, quote unit and purity; spot unusually cheap or dear contracts", "Sections 5 and 7; Strategy B in Section 8"],
             ["Analyze the futures curve; separate roll-down from genuine curve changes", "Section 7, roll-down vs curve move"],
             ["Walk-forward backtest with no look-ahead, costs and thin-day liquidity", "Sections 5, 6 and 8"],
             ["Dashboards or alerts that stay quiet without a signal; attribute performance to the strategy, not gold", "The dashboard (Section 11); Section 8, where the profit came from"],
             ["Track listing, liquidity, tender periods and expiry; keep every entry and exit inside the contract calendar", "Section 8, contract calendar check; Section 4"],
             ["Validate on unseen data; report after costs on the contracts held", "Sections 6 and 8 (three sealed tests)"]],
            [0.55, 0.45])]

# ---------------------------------------------------------------- glossary
s += [PageBreak(), P("3. Words you will see", "h1"),
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
            [0.24, 0.76], bold_first_col=True)]

# ---------------------------------------------------------------- data
s += [P("4. Our data and how we checked it", "h1"),
      P("<b>Source.</b> MCX Bhavcopy, downloaded in a web browser one contract at a time from mcxindia.com's commodity-wise "
        "Bhavcopy page (the site blocks scripted downloads from servers). We do not use stitched ‘continuous’ price series from charting sites, because joining different contracts "
        "together creates false jumps."),
      tiles([("710", "contracts"), ("55,457", "daily records"), ("20 Nov 2003", "first date"), ("1 Oct 2026", "last date")]),
      Spacer(1, 6),
      table([["File", "Dates", "Contracts / rows", "Used for"],
             ["clean/gold_futures.csv", "10 Oct 2023 – 1 Oct 2026", "149 / 12,021", "Every gap measurement, the dashboard, development and the 2025–26 holdout"],
             ["clean/gold_futures_history.csv", "Nov 2003 – Dec 2015", "273 / 21,511", "Training only (Strategy C)"],
             ["clean/sealed_rows.csv", "1 Jan 2016 – 9 Oct 2023", "288 / 21,925", "Sealed tests 2 and 3, read once"]],
            [0.3, 0.22, 0.16, 0.32]),
      Spacer(1, 8),
      P("Every file is identified by its contents (not its file name), duplicates are removed automatically, and each row is "
        "checked before it is used (figures below are for the 2023–2026 file):"),
      table([["Check", "What it catches", "Rows failing"],
             ["Duplicate rows", "Same contract and date twice", "0.00%"],
             ["Row after expiry", "Wrong dates", "0.00%"],
             ["Open or close outside the day's high–low", "Corrupt prices", "0.00% (older files: 261 rows, all on a contract's last trading day; see below)"],
             ["Zero or negative price", "Corrupt prices", "0.00%"],
             ["Missing trading day inside a contract's life", "Incomplete downloads", "0.00%"],
             ["Weekend date that is not a known special session", "Wrong date returned", "0.00% (3 special sessions found and expected)"],
             ["Previous close ≠ last row's close", "Broken history", "1.24% (147 rows), all right after a no-trade day; explained, flagged and excluded"],
             ["Price > 5% away from same-month peers", "Wrong units or lot sizes", "0.09% (11 rows): 10 GOLDM rows from 21 Jan to 1 Feb 2026, and GOLDGUINEA on its thin expiry day, 31 May 2024"]],
            [0.36, 0.26, 0.38]),
      Spacer(1, 6),
      P("The flagged prices are real. On 30 January 2026 gold fell about 10% in a day; GOLDM settled at its day's low (its lower "
        "price limit) while the smaller contracts settled higher. 1 February 2026 was a Sunday Budget-day special session. News reports "
        "confirm the crash (Section 11). We kept these rows and did not change any rule because of them."),
      P("<b>Expiry-day closes.</b> In the files before October 2023, 261 closes sit outside that day's traded high–low, every one "
        "on a contract's last trading day. The MCX contract specifications explain why: on expiry the final settlement price is the "
        "Due Date Rate, taken from the spot price polled that afternoon, not the futures closing price. We keep these rows as "
        "published; no strategy holds a position on that day."),
      P("<b>Sealed data is kept apart.</b> The loading script writes every row dated 1 January 2016 to 9 October 2023 to a separate "
        "file that no analysis reads. Those rows were read once, on 4 October 2026, in the single sealed run (Section 8)."),
      P("How far is the official close from a real trade?", "h2"),
      P("We compared each day's settlement close with that day's average traded price (VWAP). For a single contract the median "
        "gap is 17–26 bp. For the <i>gap between two contracts</i>, which is what we trade, the median is only 6.7–8.5 bp because the "
        "day's gold move cancels out. This is why we assume 5 bp of slippage per leg as the realistic case, and also show 0 and 10 bp.")]

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
        "(median about 11–14 bp) but without it GOLDM would look slightly too expensive."),
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
      P("<b>Strategy C</b> is Strategy B retrained in round 3 on 2003–2015 and 2024–2026: it was chosen by a pre-declared rule from "
        "72 settings and adds a stress filter, trading only when GOLDM's 5-day volatility is in the top 20% of the past year. It exits "
        "halfway back to the usual premium or after 10 days, and always 5 business days before expiry."),
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
      P("Each trade has four legs (buy and sell on entry and exit), so every cost is paid four times.", "cap")]

# ---------------------------------------------------------------- honesty
s += [P("6. How we keep the test honest", "h1"),
      P("The most common way to fool yourself in trading research is to tune a rule until it looks good on the past, and then report "
        "that same past as the result. We split the data <b>by calendar date</b> into periods with different jobs, and wrote down "
        "every rule, and the exact test dates, <b>before</b> the test data existed on our computers. Git commit timestamps prove the order."),
      table([["Period", "Dates", "Used for"],
             ["Train / Development", "up to 30 Apr 2025 (A); up to 5 Aug 2025 (B)", "Designing rules and choosing settings by a pre-declared rule"],
             ["Test 1 (Strategy A only)", "1 May – 31 Jul 2025", "First sealed test, run once"],
             ["Sealed holdout", "Aug 2025 – May 2026", "Final test of both strategies, run once"],
             ["Development, round 3 (C)", "before 2016, and 2024 onward", "Choosing Strategy C's setting from 72, by a rule written down first"],
             ["Sealed test 2", "1 Jan 2020 – 9 Oct 2023", "Declared before download; A and B as frozen in 2025, and C, run once on 4 Oct 2026"],
             ["Sealed test 3", "1 Jan 2016 – 31 Dec 2019", "Declared before download; run once with test 2"]],
            [0.24, 0.33, 0.43]),
      Spacer(1, 6),
      table([["Time (IST)", "Commit", "What happened"],
             ["1 Oct 2026, 21:45", "e5e0a21", "Holdout window declared, download list written"],
             ["1 Oct 2026, 22:15", "045ab2b", "Strategy B rules and setting (k = 1.5) frozen"],
             ["1 Oct 2026, 23:01", "7acf18e", "Holdout data (39 MCX files) uploaded"],
             ["1 Oct 2026, 23:05", "3e9e82d", "Holdout run once; results recorded as they came out"],
             ["2 Oct 2026, 03:28", "35d7e7b", "Sealed test 2 (2020–2023) declared before download"],
             ["3 Oct 2026, 01:13", "a8cda54", "Sealed test 3 (2016–2019) declared before download"],
             ["3 Oct 2026, 01:47", "8f16845", "Test 2 shortened to end 9 Oct 2023: the 2024 files included late-2023 days, now seen; sealed rows walled off in code"],
             ["3 Oct 2026, 02:43", "79129fc", "2020 files arrive and go straight to the sealed file, unread"],
             ["4 Oct 2026, 00:53", "391f24b", "Round 3 declared: all four contracts, pre-2016 joins training, sealed windows unchanged"],
             ["4 Oct 2026, 00:57", "dc055dc", "Strategy C's 72 settings, selection rule and sealed-run code committed"],
             ["4 Oct 2026, 01:05", "a24b828", "710 contracts arrive; 2016–2023 rows routed to the sealed file by the loader"],
             ["4 Oct 2026, 01:12", "a984901", "Strategy C's setting frozen from development data only"],
             ["4 Oct 2026, 01:13", "6df3bbd", "Sealed tests 2 and 3 run once; results recorded as they came out"]],
            [0.22, 0.13, 0.65]),
      Spacer(1, 6),
      P("Other safeguards", "h2")]
s += B(["Signals use only information available at that day's close; trades happen on the next day.",
        "One position per contract type at a time, so one market move is not counted as several independent wins.",
        "Positions close before MCX's compulsory delivery (tender) period, which the contract specifications set as the last 3 trading days.",
        "Unit tests (tests/test_strategies.py) check costs, that future prices cannot change past trades, the stress filter, "
        "the contract calendar, and that the sealed run refuses to run twice.",
        "We report results at three slippage levels, the 95% range, and how concentrated the profit is.",
        "Weekend dates must be known special sessions (Diwali Muhurat 2023, Budget days 2025 and 2026); dates are read in a fixed format so day and month cannot swap.",
        "A bug found during development (the 10-day average included the current day) was fixed <i>before</i> any test was run, and is logged.",
        "An earlier AI-generated draft from another tool produced statistics for contracts that were not in our data and references "
        "that did not exist. We discarded all of it and rebuilt every number from the raw files; every reference in Section 11 was checked."])

# ---------------------------------------------------------------- results: gaps
s += [PageBreak(), P("7. Results: what the gaps look like", "h1"),
      img("premium.png"),
      P("Monthly average price of each small contract above GOLDM, per pure gram, after the carry adjustment. GOLDTEN starts in "
        "April 2025, when MCX listed it.", "cap"),
      P("The chart shows three different worlds. In 2024 the coin sat above GOLDM while the 1 g contract sat well below it. Through "
        "the quiet months of 2025–26 GOLDTEN sits on GOLDM's line and the coin and 1 g contracts sit together about 20–130 bp above it. "
        "From December 2025 to March 2026, while gold crashed, every small contract became much dearer than GOLDM, then the gaps "
        "returned to normal by April–May 2026."),
      table([["Gap (A minus B, per pure gram)", "2024", "2025–26 quiet months", "Dec 2025 – Mar 2026"],
             *[[f"{x['a']} − {x['b']}", fmt(x["y2024"]), fmt(x["normal"]), fmt(x["crash"])] for x in DJ["pairs"]]],
            [0.28, 0.24, 0.24, 0.24]),
      P("Brackets show the 95% range. 2024: 65 weeks; 2025–26 quiet months: 62–75 weeks; crash period: 18 weeks. The crash "
        "period was chosen after looking at the chart, so that split describes the data rather than testing a prediction.", "cap"),
      P("Roll-down or a real move?", "h2"),
      P("A futures price drifts toward the spot price as expiry approaches, even if nothing in the market changes. This is "
        "<i>roll-down</i>, and it follows directly from the cost of carry. For each month we split the price change of the most-traded "
        "contract into roll-down (what that day's carry implies for the days that passed) and the curve move (everything else, mostly gold itself)."),
      table([["Contract", "Months", "Roll-down per month", "Curve move per month (average size)", "Roll-down share"],
             *[[x["symbol"], str(x["months"]), f"−{abs(x['avg_rolldown_pct']):.2f}%", f"±{x['avg_abs_curve_move_pct']:.2f}%",
                f"{x['rolldown_share_of_abs_change_pct']:.0f}%"] for x in sorted(DJ["rolldown"]["summary"], key=lambda y: ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"].index(y["symbol"]))]],
            [0.18, 0.12, 0.2, 0.32, 0.18]),
      P("We also fit a straight line through every listed expiry of each contract type every day; its slope is the annualised "
        "carry across the whole curve. Its monthly median was about 5% a year through 2024 (7% for GOLDPETAL), about 6–7% in 2025, "
        "about 15% from December 2025 to June 2026, and 8–10% from July 2026. All four contract types, fitted separately, moved together, so this is market-wide. "
        "A straight line fits each day's curve to within about 4–5 bp."),
      P("Roll-down is small and predictable; the curve move is large and is where the risk sits. Measured carry for GOLDM was about "
        "4% a year in 2023–24, 7% in 2025 and 13% in 2026; the 2026 level is what the data shows, and we have not found its cause.", "cap"),
      P("What this tells us", "h2")]
s += B(["<b>The purity correction is right.</b> If it were wrong, GOLDM and GOLDTEN would differ by about 40 bp in every month; in quiet months they differ by 0.2.",
        "<b>The coin premium is structural.</b> GOLDGUINEA was dearer than GOLDM in all 41 contract cycles from late 2023 to 2026, so the "
        "gap does not close and cannot be captured by holding to expiry. A likely reason, which we have not proved, is the higher cost "
        "of minting and delivering coins.",
        "<b>The 1 g premium is not.</b> GOLDPETAL was below GOLDM in 2024 and above it from early 2025; it agrees with GOLDM's sign in "
        "only 24 of 41 cycles. We checked the raw files: the units and lot values are right, so the flip is real. Its cause is not yet known.",
        "<b>Stress reveals who leads.</b> In a fast fall, GOLDM (where most gold trades) reprices first; the small contracts follow later. "
        "That delay is the only place we found real money (Section 8)."])

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
s += [P("Where the profit came from: the gap or gold?", "h2"),
      P("Both legs of every trade hold the same grams, so gold's own move mostly cancels. It does not cancel completely: a premium "
        "still open at exit, and GOLDM's 99.5% purity against 99.9%, leave a small exposure. We split every trade's profit exactly "
        "into a <b>gap part</b> (the gap changing, valued at the entry gold price) and a <b>gold part</b> (gold's move times the gap "
        "still open). The split reproduces every recorded trade profit to the rupee."),
      table([["Run", "Trades", "Gross profit", "From the gap", "From gold's move", "Correlation with gold's move"],
             ["A · test 1", "19", "₹14,624", "₹14,847", "−₹223", "−0.29"],
             ["A · sealed holdout", "156", "₹4,10,655", "₹4,04,944", "₹5,710 (1.4%)", "0.55"],
             ["B · development", "8", "₹1,13,653", "₹1,13,730", "−₹77", "0.57"],
             ["B · sealed holdout", "12", "₹86,572", "₹90,739", "−₹4,167 (−4.8%)", "−0.04"]],
            [0.2, 0.09, 0.15, 0.15, 0.18, 0.23]),
      P("Strategy A's correlation of 0.55 comes from January 2026: gold rose about 7.8% during those trades while the gaps widened "
        "and closed. That month the gap part made ₹3,08,106 and gold's move ₹9,997. Outside January the correlation is 0.02. "
        "The profit came from the gap, not from betting on gold's direction.", "cap"),
      P("Do the alerts mean anything?", "h2"),
      P("Using the same fair-price model, we listed every past alert (66 episodes since December 2023) and what the gap did next. "
        "An alert does <i>not</i> make the gap more likely to close: it halved within 10 trading days 51% of the time on alert days "
        "and 54% on ordinary days. But alerts mark the large gaps: the median gap was 188 bp and it closed by a median 51 bp within "
        "10 days, against 3 bp on ordinary days. A round trip costs about 24 bp at 5 bp slippage, so alerts clear costs at the "
        "median and only barely on average (33 bp). Most alerts during the crash did not close within 10 days."),
      P("Did every trade fit inside its contract?", "h2"),
      P("The MCX contract specifications for all four contracts set the staggered-delivery tender period as the last 3 trading days "
        "of a contract, expiry day included. Brokers close client positions earlier, for example by 29 January 2026 for the "
        "5 February 2026 expiry, so we treat the last 5 business days as off-limits, which is stricter than the exchange. We checked "
        "every trade: all started after their contract was trading, and every Strategy B trade closed before the cut-off. Strategy A's "
        "rule closed positions 3 calendar days before expiry, which is too late: 17 of its 156 holdout trades (and 3 of 19 in test 1) "
        "exited inside our 5-day cut-off, and 4 of those inside the exchange's own 3-day tender period. The dashboard leaves them out by default."),
      table([["Strategy A, net at 5 bp", "All trades", "Trades a broker would allow"],
             ["Sealed holdout", "+₹1,90,340 (156)", "+₹1,53,382 (139)"], ["Test 1", "−₹4,466 (19)", "−₹1,922 (16)"]],
            [0.4, 0.3, 0.3]),
      P("The sealed runs are not repeated; this is reported as a finding. Strategy C uses the 5-business-day exit; A and B were "
        "run on 2016–2023 exactly as frozen in 2025.", "cap"),
      P("Eight more years, sealed: 2016–2023 (run once, 4 October 2026)", "h2"),
      P("Every GOLDM, GOLDGUINEA and GOLDPETAL contract MCX lists for these years (GOLDTEN did not exist yet) was walled off "
        "until the rules were frozen in Git, then run once. A and B are the 2025 rules unchanged; C is B retrained on other years."),
      img("sealed.png"),
      table([["Strategy", "Window", "Trades", "Net at 0 bp", "Net at 5 bp", "Net at 10 bp"]] +
            [[{"A": "A: pairs, as frozen", "B": "B: fair price, as frozen", "C": "C: B retrained"}[k], w, str(r0["trades"]),
              inr(r0["net"]), inr(r5["net"]), inr(r10["net"])]
             for k in "ABC" for t, w in (("test3", "2016–2019"), ("test2", "2020 – Oct 2023"))
             for r0, r5, r10 in [[next(x for x in DJ["sealed"]["rows"] if x["strategy"] == k and x["test"] == t and x["slip"] == sl) for sl in (0, 5, 10)]]],
            [0.26, 0.18, 0.1, 0.15, 0.15, 0.16]),
      P("Both windows together at 5 bp, with the week-block bootstrap 95% range: A " + inr(DJ["sealed"]["boot5"]["A"]["net"]) +
        " (" + inr(DJ["sealed"]["boot5"]["A"]["lo"]) + " to " + inr(DJ["sealed"]["boot5"]["A"]["hi"]) + "); B " +
        inr(DJ["sealed"]["boot5"]["B"]["net"]) + " (" + inr(DJ["sealed"]["boot5"]["B"]["lo"]) + " to " + inr(DJ["sealed"]["boot5"]["B"]["hi"]) +
        ", 80% of resamples above zero); C " + inr(DJ["sealed"]["boot5"]["C"]["net"]) + " (" + inr(DJ["sealed"]["boot5"]["C"]["lo"]) +
        " to " + inr(DJ["sealed"]["boot5"]["C"]["hi"]) + ", 72%).", "cap")]
s += B(["<b>Strategy A is rejected.</b> It lost in both windows even with perfect fills (0 bp), and none of the bootstrap resamples "
        "of its 246 trades is above zero. Its 2025–26 profit was one crash, not an edge.",
        "<b>Strategy B held up, modestly.</b> Positive in all three sealed tests at 5 bp, mostly on GOLDPETAL in 2016–2019 "
        "(+₹31,018 of +₹35,873). It still loses at 10 bp in two of three tests, so the edge is about the size of execution costs.",
        "<b>Retraining did not help.</b> C was the best of 72 settings on its training years (+₹4,00,592 at 5 bp, ₹2,95,260 of it "
        "in Q1 2026, against +₹79,982 for B's rules on the same days). The best of many settings looks good on its own data partly "
        "by chance; a year-by-year walk-forward of the same choice made −₹70,866, an early warning. Out of sample, C made less than B.",
        "<b>2020 was not 2026.</b> Over February–June 2020, the COVID crash, B made +₹6,366 and C lost ₹9,166 at 5 bp. In March 2020 "
        "the two small contracts split: the 1 g contract fell to about 3% below GOLDM while the coin rose to almost 3% above it, and "
        "both gaps kept widening for a week after entry before snapping back. B held on for the snap-back; C's quicker exits took "
        "the same early losses but cut the recovery short. A crash is a condition for the trade, not a guarantee.",
        "<b>Older-year costs are approximate.</b> We charged today's fee, tax and stamp-duty rates on 2016–2023 trades; the real "
        "schedule differed in places (stamp duty was set state by state before July 2020). Fees and taxes are 18–35% of total costs "
        "at 5 bp in these years; the rest is slippage, which we vary from 0 to 10 bp."])
s += [Spacer(1, 2)]
s += [box(P("<b>Our verdict today.</b> The gaps between India's gold contracts are real, measurable and explainable. The simple "
            "pairs rule (A) does not survive costs. The GOLDM-anchored fair-price rule (B) made money in all three sealed tests at "
            "5 bp, +₹55,824 in total, but each test's 95% range includes zero and it loses at 10 bp in two of three. In a crash it "
            "pays sometimes: 2026 paid, 2020 did not. Parity's honest answer is a small, positive, unproven edge whose size is "
            "decided by execution, which is why the dashboard shows every result at 0, 5 and 10 bp.", "box"))]

# ---------------------------------------------------------------- future
s += [P("9. What the extra data showed", "h1"),
      P("The first version of this report projected what more data would add. Round 3 downloaded every GOLDM, GOLDTEN, GOLDGUINEA "
        "and GOLDPETAL contract MCX lists, 710 in all, from November 2003 to October 2026. Here is each projection against what happened.", "body"),
      table([["Batch", "Contracts", "Status", "What it added"],
             ["2024 and 2025–26 gaps", "All four, Oct 2023 – Oct 2026", "Done", "149 contracts for every gap measurement, including GOLDTEN Aug 2026"],
             ["Before 2016", "GOLDM from 2003, GOLDGUINEA from 2008, GOLDPETAL from 2011", "Done, training only", "Training years for Strategy C"],
             ["2016–2019", "Same three, every expiry", "Done, sealed, run once", "Sealed test 3"],
             ["2020 – Oct 2023", "Same three, every expiry", "Done, sealed, run once", "Sealed test 2, including the 2020 COVID crash"]],
            [0.2, 0.32, 0.18, 0.3]),
      Spacer(1, 6),
      table([["Projection (October 2026)", "What happened"],
             ["B's range per trade about 40% as wide, if 2016–2023 traded at the 2025–26 pace",
              "B traded far less often (38 trades in 8 years, against 12 in 10 months), so the range per trade narrowed only to about 90% of its width. The pace condition did not hold."],
             ["Several more crashes, judged on rules frozen beforehand",
              "The 2020 COVID crash: B +₹6,366, C −₹9,166 (Feb–Jun 2020, 5 bp). The ‘lag in a crash’ idea held in 2026, not in 2020."],
             ["Coin and 1 g premiums measured over up to 11 years", "Not yet measured. The sealed run is done, so these years can now be studied openly; this is the next step."],
             ["Quiet-month premium margin narrows only as new months arrive", "As projected: ±7.1 and ±9.5 bp (75 weeks), from ±7.7 and ±10.4"]],
            [0.42, 0.58]),
      P("Planned improvements: what was done", "h2")]
s += B(["<b>Exit before the tender period in every strategy:</b> done in Strategy C; A and B were run as frozen, and their late exits are flagged.",
        "<b>Stress detector:</b> done as Strategy C's filter, written down before 2016–2023 was read. It did not beat B out of sample.",
        "<b>Faster-adapting ‘usual premium’:</b> a one-year window was one of C's 72 settings; the rule chose the all-history average.",
        "<b>Drop GOLDTEN from Strategy B:</b> moot for 2016–2023, when GOLDTEN did not exist; still the plan for live use.",
        "<b>Price-limit filter</b> and <b>IBJA cross-check:</b> not done yet.",
        "<b>Next:</b> measure the coin and 1 g premiums back to 2008 and 2011, and test B live, day by day, on new MCX files from October 2026."])
# ---------------------------------------------------------------- limitations
s += [P("10. Limitations", "h1")]
s += B(["<b>Few crashes.</b> 23 years of data hold only a handful of sharp gold crashes; two (2020 and 2026) fall inside sealed tests, and they disagree.",
        "<b>Many settings tried for C.</b> Strategy C was the best of 72 on its training years; only its sealed result should be read.",
        "<b>Daily data only.</b> We see one official close and one average price per day, not every trade. Real fills could be "
        "better or worse than our 5 bp assumption, especially in a crash, when prices move fastest.",
        "<b>Some costs are assumptions.</b> Stamp duty, SEBI fee, brokerage and GST rates come from typical broker charge sheets, and today's rates are applied to 2016–2023.",
        "<b>Liquidity limits size.</b> GOLDGUINEA trades about 7 kg a day; larger positions than ours would move the price.",
        "<b>Why the premiums exist is a hypothesis.</b> Minting and delivery costs fit the coin premium, but we have not verified them "
        "from MCX's delivery records, and nothing we have explains why the 1 g premium flipped in early 2025.",
        "<b>Sealed results are final.</b> Section 8's numbers come from the single sealed runs of 1 and 4 October 2026 and are not re-run.",
        "<b>Holidays in the tender check.</b> The 5-business-day rule counts Monday to Friday and ignores exchange holidays; the exchange's own 3-day rule is checked against each contract's actual trading days."])
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
        "MCX contract specifications for GOLDM (Aug 2026 contract), GOLDTEN, GOLDGUINEA and GOLDPETAL (Jul 2026 contracts), mcxindia.com: "
        "lot size, quote, purity, last trading day, staggered-delivery tender period, Due Date Rate, price limits and margins.",
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
             ["strategy_c.py", "Strategy C: 72 settings on development years; the single sealed run of A, B and C on 2016–2023"],
             ["tests/", "Unit tests: costs, no look-ahead, stress filter, contract calendar, sealed-run guard"],
             ["uncertainty.py", "Week-block bootstrap for the profit ranges"],
             ["attribution.py", "Splits every trade's profit into the gap part and gold's own move"],
             ["rolldown.py", "Splits each month's price change into roll-down and curve move"],
             ["lifecycle.py", "Liquidity build-up, tender periods (5-day cut-off and the exchange's 3-day rule), every trade checked"],
             ["alerts.py", "Every past alert and what the gap did next, against ordinary days"],
             ["curve.py", "Daily slope of the whole futures curve per contract type"],
             ["dashboard/", "Interactive website built from the same results (export.py, build.py)"],
             ["report/", "This report: charts.py draws the charts from the dashboard data, build.py writes the PDF"]],
            [0.2, 0.8])]

doc.build(s)
print(OUT)

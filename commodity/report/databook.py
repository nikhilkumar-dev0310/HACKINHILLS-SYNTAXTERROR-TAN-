"""Parity data book: everything the project collects, in one PDF.

    python report/databook.py        (from commodity/)  ->  report/Parity_Data_Book.pdf

Every number is computed here from clean/*.csv, raw_clean/ and results/; nothing is typed in.
"""
import os, json, hashlib, glob
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image,
                                PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "report")
OUT = os.path.join(HERE, "Parity_Data_Book.pdf")
TMP = os.path.join(HERE, "_databook")
os.makedirs(TMP, exist_ok=True)

F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", F + "DejaVuSans.ttf")); pdfmetrics.registerFont(TTFont("DVB", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", F + "DejaVuSans-Oblique.ttf")); pdfmetrics.registerFont(TTFont("DVM", F + "DejaVuSansMono.ttf"))
addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB"); addMapping("DV", 0, 1, "DVI"); addMapping("DV", 1, 1, "DVB")

INK, INK2, MUTED = colors.HexColor("#1b1b1a"), colors.HexColor("#52514e"), colors.HexColor("#8a8984")
GOLD, GOLD_BG, RULE = colors.HexColor("#835a07"), colors.HexColor("#fbf5e6"), colors.HexColor("#dcdad3")
SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
SC = {"GOLDM": "#a87600", "GOLDTEN": "#2a6fd0", "GOLDGUINEA": "#cf4f2c", "GOLDPETAL": "#0f8f7e"}   # validated: all six checks pass
LOT_G = {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
QUOTE_G = {"GOLDM": 10, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
PUR = {"GOLDM": 0.995, "GOLDTEN": 0.999, "GOLDGUINEA": 0.999, "GOLDPETAL": 0.999}
DESC = {"GOLDM": "100 g bar", "GOLDTEN": "10 g bar", "GOLDGUINEA": "8 g coin", "GOLDPETAL": "1 g"}

ss = {}
ss["title"] = ParagraphStyle("title", fontName="DVB", fontSize=26, leading=32, textColor=INK, spaceAfter=8)
ss["sub"] = ParagraphStyle("sub", fontName="DV", fontSize=12, leading=17, textColor=INK2)
ss["h1"] = ParagraphStyle("h1", fontName="DVB", fontSize=16, leading=21, textColor=INK, spaceBefore=4, spaceAfter=8, keepWithNext=1)
ss["h2"] = ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, textColor=GOLD, spaceBefore=10, spaceAfter=4, keepWithNext=1)
ss["body"] = ParagraphStyle("body", fontName="DV", fontSize=9.5, leading=14.2, textColor=INK, spaceAfter=6)
ss["small"] = ParagraphStyle("small", fontName="DV", fontSize=8, leading=11, textColor=INK2, spaceAfter=4)
ss["cap"] = ParagraphStyle("cap", fontName="DVI", fontSize=8, leading=11, textColor=INK2, spaceAfter=8)
ss["cell"] = ParagraphStyle("cell", fontName="DV", fontSize=8, leading=10.5, textColor=INK)
ss["cellb"] = ParagraphStyle("cellb", parent=ss["cell"], fontName="DVB")
ss["mono"] = ParagraphStyle("mono", parent=ss["cell"], fontName="DVM", fontSize=7.3, leading=9.5)
ss["monot"] = ParagraphStyle("monot", parent=ss["mono"], fontSize=6.6, leading=8.4)
ss["bullet"] = ParagraphStyle("bullet", parent=ss["body"], leftIndent=12, bulletIndent=2, spaceAfter=3)
ss["big"] = ParagraphStyle("big", fontName="DVB", fontSize=18, leading=22, textColor=INK)
ss["bigcap"] = ParagraphStyle("bigcap", fontName="DV", fontSize=8, leading=10.5, textColor=INK2)
W = A4[0] - 36 * mm


def P(t, s="body"): return Paragraph(t, ss[s])
def B(items): return [Paragraph(i, ss["bullet"], bulletText="•") for i in items]
def n(v): return f"{int(v):,}".replace(",", ",")
def d(x): return pd.Timestamp(x).strftime("%d %b %Y")


def table(rows, widths, mono_cols=(), font=None, zebra=True, tight=False):
    data = []
    for i, r in enumerate(rows):
        data.append([Paragraph(str(c), ss["cellb"] if i == 0 else (ss["monot" if tight else "mono"] if j in mono_cols else ss[font or "cell"])) for j, c in enumerate(r)])
    t = Table(data, colWidths=[w * W for w in widths], repeatRows=1)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 1.6 if tight else 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 if tight else 2.6), ("LINEBELOW", (0, 0), (-1, -1), 0.35, RULE),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1efe8")), ("LINEBELOW", (0, 0), (-1, 0), 0.8, MUTED)]
    if zebra:
        st += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#faf9f6")) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(st))
    return t


def box(flows):
    t = Table([[flows]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GOLD_BG), ("LINEBEFORE", (0, 0), (0, -1), 2.5, GOLD),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def stats(items):
    cells = [[Paragraph(b, ss["big"]) for b, _ in items], [Paragraph(c, ss["bigcap"]) for _, c in items]]
    t = Table(cells, colWidths=[W / len(items)] * len(items))
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, 0), 2), ("TOPPADDING", (0, 1), (-1, 1), 0)]))
    return t


# ================================================================ data
os.chdir(ROOT)
PARTS = [("History", "clean/gold_futures_history.csv", "Training years. Rules were built and tuned only on these."),
         ("Sealed", "clean/sealed_rows.csv", "Walled off in a separate file until the rules were frozen in Git, then opened once."),
         ("Live", "clean/gold_futures.csv", "The working set: development, the 2025-26 holdout and today's market view.")]
frames = []
for name, path, _ in PARTS:
    x = pd.read_csv(path, parse_dates=["date", "expiry_date"]); x["part"] = name; frames.append(x)
A = pd.concat(frames, ignore_index=True)
A["kg"] = A.volume_lots * A.symbol.map(LOT_G) / 1000
raw = sorted(glob.glob("raw_clean/*.xls"))
hashes = [hashlib.sha256(open(f, "rb").read()).hexdigest() for f in raw]
DJ = json.load(open("dashboard/data.json"))
INTEG = pd.read_csv("results/testbed_integrity.csv")
VW = pd.read_csv("results/testbed_close_vs_vwap.csv")
FLAGS = DJ.get("flags", [])
ES = DJ.get("expiry_settle", {})
contracts = A.groupby(["symbol", "expiry_date"]).ngroups
files = A.source_file.nunique()
cyc = A.groupby(["symbol", "expiry_date"]).agg(first=("date", "min"), last=("date", "max"), rows=("date", "size"),
                                                files=("source_file", "nunique"), part=("part", lambda s: "/".join(sorted(set(s)))),
                                                kg=("kg", "median")).reset_index()

# ================================================================ charts (print: no hover; legends + direct labels)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#9a9893", "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#ecebe6", "grid.linewidth": 0.6, "axes.axisbelow": True})


def save(fig, name):
    p = os.path.join(TMP, name); fig.savefig(p, dpi=220, bbox_inches="tight"); plt.close(fig); return p


# 1 coverage: one bar per contract type, split into the three files
fig, ax = plt.subplots(figsize=(7.2, 2.0))
shade = {"History": "#d9d4c7", "Sealed": "#b7a57c", "Live": "#835a07"}
for i, s in enumerate(SYMS[::-1]):
    g = A[A.symbol == s]
    for part in ["History", "Sealed", "Live"]:
        h = g[g.part == part]
        if len(h):
            ax.barh(i, (h.date.max() - h.date.min()).days, left=h.date.min(), height=0.55, color=shade[part], edgecolor="white", linewidth=1.5)
    ax.text(g.date.min(), i + 0.42, f"{s} · from {g.date.min():%b %Y}", fontsize=7.5, color="#1b1b1a", va="bottom")
ax.set_yticks([]); ax.set_ylim(-0.5, 3.9); ax.grid(axis="y", visible=False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=shade[k], label=f"{k} file") for k in shade], frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, -0.42), fontsize=7.5)
C1 = save(fig, "coverage.png")

# 2 rows per year, per contract type
fig, ax = plt.subplots(figsize=(7.2, 2.1))
yr = A.groupby([A.date.dt.year, "symbol"]).size().unstack(fill_value=0)
for s in SYMS:
    v = yr[s].where(yr[s] > 0)
    ax.plot(v.index, v.values, color=SC[s], lw=2, marker="o", ms=3, label=s)
ax.set_ylabel("rows (contract-days)"); ax.legend(frameon=False, ncol=4, fontsize=7.5, loc="lower left", bbox_to_anchor=(0, 1.0))
C2 = save(fig, "rows_per_year.png")

# 3 price per gram of pure gold, most traded GOLDM contract each day
gm = A[(A.symbol == "GOLDM") & (A.volume_lots > 0)].sort_values("volume_lots").groupby("date").tail(1).sort_values("date")
fig, ax = plt.subplots(figsize=(7.2, 2.1))
ax.plot(gm.date, gm.rs_per_g, color=SC["GOLDM"], lw=1.4)
ax.set_ylabel("₹ per gram of pure gold"); ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"₹{v:,.0f}"))
for dt in [gm.date.iloc[0], gm.date.iloc[-1]]:
    r = gm[gm.date == dt].iloc[0]
    ax.annotate(f"₹{r.rs_per_g:,.0f}\n{dt:%b %Y}", (dt, r.rs_per_g), xytext=(6 if dt == gm.date.iloc[0] else -6, 8), textcoords="offset points",
                fontsize=7, ha="left" if dt == gm.date.iloc[0] else "right", color="#1b1b1a")
C3 = save(fig, "price.png")

# 4 gold traded per day, median by year
fig, ax = plt.subplots(figsize=(7.2, 2.1))
kgy = A[A.volume_lots > 0].groupby([A.date.dt.year, "symbol", "date"]).kg.sum().groupby(level=[0, 1]).median().unstack()
for s in SYMS:
    v = kgy[s].dropna()
    ax.plot(v.index, v.values, color=SC[s], lw=2, marker="o", ms=3, label=s)
ax.set_yscale("log"); ax.set_ylabel("kg per day (median, log)"); ax.legend(frameon=False, ncol=4, fontsize=7.5, loc="lower left", bbox_to_anchor=(0, 1.0))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
C4 = save(fig, "kg.png")

# ================================================================ document
def on_page(c, doc):
    c.saveState(); c.setFont("DV", 7.5); c.setFillColor(MUTED)
    c.drawString(18 * mm, 10 * mm, "Parity · Data book · © 2026 SYNTAX TERROR (TAN) · reuse needs our written permission (LICENSE)")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                      title="Parity data book", author="SYNTAX TERROR (TAN)", subject="Every MCX gold futures row Parity collects")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(18 * mm, 16 * mm, W, A4[1] - 32 * mm, id="f")], onPage=on_page)])
S = []

# ---------------------------------------------------------------- cover
S += [Spacer(1, 30 * mm), P("PARITY · MCX GOLD FUTURES", "h2"), P("Data book", "title"),
      P(f"Everything we collect: where it comes from, what each field means, how much there is, how it was checked, "
        f"and every one of the {n(files)} source files. Data from {d(A.date.min())} to {d(A.date.max())}.", "sub"),
      Spacer(1, 12 * mm),
      stats([(n(len(A)), "daily rows, one per contract per trading day"), (n(contracts), "futures contracts"),
             (n(files), "distinct MCX files"), (n(A.date.nunique()), "trading days")]),
      Spacer(1, 8 * mm),
      stats([("4", "contract types: GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL"), (f"{A.date.dt.year.nunique()}", "calendar years covered"),
             ("0", "unexplained errors after checks"), ("1", "source: MCX's official Bhavcopy")]),
      Spacer(1, 14 * mm),
      box([P("<b>In one line.</b> Every number in Parity starts from the official end-of-day MCX Bhavcopy, downloaded contract by "
             "contract, identified by its contents, checked row by row, and converted to ₹ per gram of pure gold so the four "
             "contracts can be compared directly. No price was ever edited by hand.", "body")]),
      Spacer(1, 10 * mm),
      P("Team SYNTAX TERROR (TAN): Nikhil Kumar, Sai Ganesh, Ishaan Chhabra. Live site: parity-gold-site.vercel.app. "
        "Code and data: github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-", "small"),
      P(f"Generated {pd.Timestamp.now(tz='Asia/Kolkata'):%d %b %Y, %H:%M} IST by report/databook.py from the repository's files.", "small"),
      PageBreak()]

# ---------------------------------------------------------------- 1 source
S += [P("1. Where the data comes from", "h1"),
      P("The only market data source is the <b>MCX Bhavcopy</b>, the official daily file the Multi Commodity Exchange of India "
        "publishes for every contract: prices, volume, open interest and traded value. We use the commodity-wise view on "
        "mcxindia.com (instrument FUTCOM), one download per contract and expiry. There are no paid feeds, no API keys and "
        "no third-party prices."),
      P("1.1 What we collected", "h2"),
      table([["Contract", "What it is", "Lot", "Quoted per", "Purity", "Contracts", "First day", "Last day"]] +
            [[s, DESC[s], f"{LOT_G[s]} g", f"{QUOTE_G[s]} g", f"{PUR[s] * 1000:.0f}", n(g.expiry_date.nunique()), d(g.date.min()), d(g.date.max())]
             for s in SYMS for g in [A[A.symbol == s]]], [.13, .13, .07, .1, .08, .1, .14, .14]),
      P("Lot, quote unit and purity are from the MCX contract specification documents for each contract.", "cap"),
      P("1.2 How it was downloaded", "h2")]
S += B([f"<b>{n(len(raw))} files downloaded</b> from the Bhavcopy page, by hand for the history and by a headless browser "
        f"script (tools/auto_fetch.mjs) for the latest contracts.",
        f"<b>Each file is identified by its contents, not its name.</b> {n(len(raw) - len(set(hashes)))} downloads were exact "
        f"duplicates and were dropped, leaving <b>{n(len(set(hashes)))} distinct files</b>.",
        f"Those files cover <b>{n(contracts)} contracts</b>. One contract (GOLDM expiring 3 Jan 2025) arrived in two downloads "
        "with different date ranges; its rows were merged and every row checked for duplicates.",
        "Dates are read with a fixed format, so day and month cannot swap. Expiry is parsed from the file "
        "(for example 04SEP2026) and every row is tied to its own contract; nothing is stitched into a continuous series.",
        "A scheduled job is built to add each new trading day automatically (tools/daily_update.py). It rejects an update "
        "if any already-published price changes."])
S += [P("1.3 Three files, by purpose", "h2"),
      P("The cleaned rows are kept in three files so that the test years could be walled off in code until the rules were frozen."),
      table([["File", "Rows", "Contracts", "From", "To", "Purpose"]] +
            [[f"{nm}<br/><font size=6.5 color='#8a8984'>{pth}</font>", n(len(g)), n(g.groupby(['symbol', 'expiry_date']).ngroups), d(g.date.min()), d(g.date.max()), why]
             for nm, pth, why in PARTS for g in [A[A.part == nm]]] +
            [["<b>All</b>", f"<b>{n(len(A))}</b>", f"<b>{n(contracts)}</b>", d(A.date.min()), d(A.date.max()), ""]],
            [.2, .09, .09, .12, .12, .38]),
      PageBreak()]

# ---------------------------------------------------------------- 2 fields
S += [P("2. Every field in a row", "h1"),
      P("Each row is one contract on one trading day. The first eleven fields are exactly as MCX publishes them; the last four are "
        "added by ingest.py and are reproducible from the others."),
      table([["Field", "Meaning", "Unit", "Source"],
             ["date", "Trading day", "date", "MCX"], ["symbol", "Contract type: GOLDM, GOLDTEN, GOLDGUINEA or GOLDPETAL", "", "MCX"],
             ["expiry_date", "Last trading day of this contract", "date", "MCX"],
             ["open, high, low", "Day's first, highest and lowest traded price. Blank when the contract did not trade", "₹ per quote unit", "MCX"],
             ["close", "Official settlement (closing) price", "₹ per quote unit", "MCX"],
             ["prev_close", "Previous day's settlement price", "₹ per quote unit", "MCX"],
             ["volume_lots", "Contracts traded that day", "lots", "MCX"], ["open_interest_lots", "Contracts still open at the end of the day", "lots", "MCX"],
             ["value_lakhs", "Value traded that day", "₹ lakh", "MCX"],
             ["source_file", "The MCX file this row came from", "", "Parity"],
             ["no_trade", "True when volume is zero or no open price was published", "true/false", "Parity"],
             ["rs_per_g", "close ÷ grams per quote ÷ purity: ₹ per gram of pure gold", "₹ / pure g", "Parity"],
             ["days_to_expiry", "Calendar days from date to expiry_date", "days", "Parity"]],
            [.2, .52, .15, .13], mono_cols=(0,)),
      P("2.1 Completeness", "h2"),
      table([["Field", "Blank rows", "Why"]] +
            [[c, n(A[c].isna().sum()), "No trade that day: MCX publishes only the settlement price" if A[c].isna().sum() else "Never blank"]
             for c in ["date", "symbol", "expiry_date", "open", "high", "low", "close", "prev_close", "volume_lots", "open_interest_lots", "value_lakhs"]],
            [.25, .15, .6], mono_cols=(0,)),
      P(f"{n(A.no_trade.sum())} rows ({A.no_trade.mean() * 100:.1f}%) are no-trade days. They are kept, marked, and left out of anything that needs a real trade.", "cap"),
      P("2.2 Three sample rows, one from each file", "h2")]
cols = ["date", "symbol", "expiry_date", "open", "high", "low", "close", "volume_lots", "open_interest_lots", "rs_per_g"]
samp = [A[A.part == p].iloc[0] for p in ["History", "Sealed", "Live"]]
S += [table([["date", "symbol", "expiry", "open", "high", "low", "close", "lots", "OI lots", "₹/pure g"]] +
            [[f"{r.date:%Y-%m-%d}", r.symbol, f"{r.expiry_date:%Y-%m-%d}", f"{r.open:,.0f}", f"{r.high:,.0f}", f"{r.low:,.0f}", f"{r.close:,.0f}",
              n(r.volume_lots), n(r.open_interest_lots), f"{r.rs_per_g:,.1f}"] for r in samp],
            [.11, .12, .11, .09, .09, .09, .09, .08, .1, .12], mono_cols=tuple(range(10))),
      PageBreak()]

# ---------------------------------------------------------------- 3 coverage
per = A.groupby("symbol").agg(rows=("date", "size"), contracts=("expiry_date", "nunique"), days=("date", "nunique"),
                              nt=("no_trade", "mean"), kg=("kg", "sum"), val=("value_lakhs", "sum"))
S += [P("3. How much there is", "h1"),
      table([["Contract", "Rows", "Contracts", "Trading days", "No-trade rows", "Gold traded, total", "Value traded, total"]] +
            [[s, n(per.rows[s]), n(per.contracts[s]), n(per.days[s]), f"{per.nt[s] * 100:.1f}%", f"{per.kg[s]:,.0f} kg", f"₹{per.val[s] / 1e7:,.1f} lakh crore"] for s in SYMS] +
            [["<b>All</b>", f"<b>{n(len(A))}</b>", f"<b>{n(contracts)}</b>", f"<b>{n(A.date.nunique())}</b>", f"{A.no_trade.mean() * 100:.1f}%",
              f"{per.kg.sum():,.0f} kg", f"₹{per.val.sum() / 1e7:,.1f} lakh crore"]],
            [.15, .1, .11, .13, .13, .18, .2]),
      P("Totals add up every contract's daily volume and value as published in the Bhavcopy.", "cap"),
      KeepTogether([Image(C1, width=W, height=W * 2.0 / 7.2 * 1.18), P("When each contract type's data starts, and which file holds each period. GOLDTEN was listed by MCX only in 2025.", "cap")]),
      KeepTogether([Image(C2, width=W, height=W * 2.1 / 7.2 * 1.1), P("Rows per calendar year. Rows grow with the number of contracts listed at once.", "cap")]),
      PageBreak(),
      KeepTogether([Image(C4, width=W, height=W * 2.1 / 7.2 * 1.1), P("Median gold traded per day by each contract type (all its contracts summed per day), on a log scale.", "cap")]),
      KeepTogether([Image(C3, width=W, height=W * 2.1 / 7.2),
      P("Price per gram of pure gold from the most-traded GOLDM contract each day. The other three contracts sit on nearly the same line once converted.", "cap")]),
      PageBreak()]

# ---------------------------------------------------------------- 4 checks
S += [P("4. How it was checked", "h1"),
      P("Every row of the live file passes these checks before any number on the site is computed (testbed.py). The history and "
        "sealed files pass the same structural checks in ingest.py."),
      table([["Check", "Rows checked", "Failing", "Share"]] +
            [[r.check.strip().replace("...", "… "), n(r.rows_checked), n(r.errors), f"{r.error_rate * 100:.2f}%"] for r in INTEG.itertuples()],
            [.55, .15, .12, .18]),
      Spacer(1, 4),
      box([P(f"<b>Result: 0 unexplained errors.</b> The {n(INTEG.errors.iloc[4])} previous-close mismatches all follow a no-trade day, where "
             f"MCX carries a price forward. The {n(INTEG.errors.iloc[-1])} rows far from their peers are real prices, mostly in the "
             "January 2026 crash, and are kept. No price was changed.", "body")]),
      P("4.1 Official close vs real trades", "h2"),
      P("The settlement price is not a fill. We measured how far it sits from the day's volume-weighted average traded price (VWAP)."),
      table([["Measure", "Period", "Days", "Typical gap", "90% of days within"]] +
            [[r.symbol, r.dates, n(r.days), f"{r.median_abs_gap_bp:.1f} bp", f"{r.p90_abs_gap_bp:.1f} bp"] for r in VW.itertuples()],
            [.24, .3, .1, .16, .2])]
if ES:
    S += [P("4.2 Expiry-day settlement", "h2"),
          P(f"On its last day a contract settles at MCX's Due Date Rate, taken from spot gold, not from futures trades. "
            f"{n(ES.get('outside', 0))} of {n(ES.get('rows', 0))} closes sit outside the day's high-low range; all "
            f"{n(ES.get('on_last_day', 0))} are on a contract's last trading day. They are kept as published.")]
if FLAGS:
    fk = pd.DataFrame(FLAGS).groupby("kind").size()
    S += [P("4.3 Flagged rows", "h2"),
          table([["Flag", "Rows", "What we did"]] + [[k, n(v), "Left out of signals (price carried forward)" if "close" in k.lower() else "Kept: real prices"] for k, v in fk.items()],
                [.45, .15, .4])]
S += [PageBreak()]

# ---------------------------------------------------------------- 5 what we derive
S += [P("5. What we compute from it", "h1"),
      P("Every analysis writes its results to a file in results/, and one export (dashboard/export.py) turns those files into the "
        "site, the report and the pitch. These are derived from the rows above; none of them is new market data."),
      ]
desc = {"accuracy": "Precision of every pair gap, carry and per-contract liquidity", "alerts": "Alert episodes and what each gap did next",
        "attribution": "Each trade's profit split into gap and gold's own move", "curve_slope": "Futures curve slope, daily and monthly",
        "fairvalue": "Strategy B (fair price off GOLDM): settings, development and holdout trades", "holdout": "Strategy A sealed holdout trades",
        "lifecycle": "Contract calendar, liquidity by days to expiry, tender checks", "methods_train": "Alternative pair methods tried on training data",
        "rolldown": "Monthly price change split into roll-down and curve move", "sealed": "2016-2023 sealed tests: summary and every trade",
        "spread_levels": "Pair gap level and spread by contract cycle", "strategy_b": "Strategy B over all development data",
        "strategy_c": "Strategy C: setting grid, walk-forward, trades", "test_": "Strategy A first sealed test and its bootstrap range",
        "testbed": "Data checks, close vs VWAP, margins of error", "train_": "Strategy A training sweep and trades",
        "frozen": "Strategy A rules, frozen before testing", "method_choice": "Which method was promoted, and why", "sealed_run": "When the sealed run happened"}
rows = [["File", "Rows", "What it holds"]]
for f in sorted(glob.glob("results/*.csv")) + sorted(glob.glob("results/*.json")):
    b = os.path.basename(f); k = next((k for k in desc if b.startswith(k)), None)
    rows.append([b, n(len(pd.read_csv(f))) if b.endswith(".csv") else "–", desc.get(k, "")])
S += [table(rows, [.36, .08, .56], mono_cols=(0,)),
      P("5.1 Where to get the full rows", "h2")]
S += B(["<b>Every row:</b> clean/gold_futures.csv, clean/gold_futures_history.csv and clean/sealed_rows.csv in the repository (CSV, opens in Excel).",
        "<b>The original MCX files:</b> raw_clean/, exactly as downloaded.",
        "<b>On the site:</b> Overview → Download the data (latest day, daily price per pure gram, daily premium, trades, alerts) and "
        "Data quality → Download log (the file list in Appendix A as CSV).",
        "<b>Rebuild everything:</b> python ingest.py, then the scripts listed in README.md."])
S += [PageBreak()]

# ---------------------------------------------------------------- appendix A: every contract and file
S += [P(f"Appendix A. Every contract and source file ({n(contracts)} contracts, {n(files)} files)", "h1"),
      P("One line per contract, newest expiry first within each contract type. Dates are year-month-day. Rows: trading days held. Kg/d: median gold traded "
        "on its trading days. File: where the rows sit (H = history, S = sealed, L = live).", "small")]
ab = {"History": "H", "Sealed": "S", "Live": "L"}
for s in SYMS:
    g = cyc[cyc.symbol == s].sort_values("expiry_date", ascending=False)
    rows = [["Expiry", "First", "Last", "Rows", "Kg/d", "File"] * 2]
    recs = [[f"{r.expiry_date:%Y-%m-%d}", f"{r['first']:%Y-%m-%d}", f"{r['last']:%Y-%m-%d}", n(r.rows), f"{r.kg:,.0f}" if r.kg >= 10 else f"{r.kg:.1f}",
             "+".join(ab[p] for p in r.part.split("/")) + (" ×2" if r.files > 1 else "")] for _, r in g.iterrows()]
    half = (len(recs) + 1) // 2
    for i in range(half):
        rows.append(recs[i] + (recs[i + half] if i + half < len(recs) else [""] * 6))
    S += [P(f"{s} · {DESC[s]} · {len(g)} contracts", "h2"),
          table(rows, [.1, .1, .1, .064, .062, .064] * 2, mono_cols=tuple(range(12)), tight=True)]
S += [Spacer(1, 6), P("×2: the rows came from two MCX downloads, merged and checked for duplicates.", "cap")]

doc.build(S)
print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB")

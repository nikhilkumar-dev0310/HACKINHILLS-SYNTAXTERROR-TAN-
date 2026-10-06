"""Every MCX gold futures row Parity holds, as one printable PDF ("data book").

    python tools/data_book.py            (from commodity/)  ->  report/Parity_MCX_Gold_Data_Book.pdf

Reads clean/gold_futures_history.csv, clean/sealed_rows.csv and clean/gold_futures.csv (built by ingest.py from the
official MCX Bhavcopy commodity-wise files). Values are printed exactly as published; nothing is filled in or changed.
Layout is planned first, then drawn, so the contents and contract index carry real page numbers.
"""
import os
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(HERE)
os.makedirs("report", exist_ok=True)
OUT = "report/Parity_MCX_Gold_Data_Book.pdf"
F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("S", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("SB", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("M", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("MB", F + "DejaVuSansMono-Bold.ttf"))

INK, INK2, INK3, GOLD, LINE, STRIPE, BAND = (HexColor(c) for c in ("#16181c", "#454a54", "#6b707a", "#835a07", "#d9d3c6", "#f6f3ec", "#efe7d6"))
SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
DESC = {"GOLDM": "100 g lot, quoted per 10 g, 995 fineness", "GOLDTEN": "10 g lot, quoted per 10 g, 999 fineness",
        "GOLDGUINEA": "8 g lot, quoted per 8 g, 999 fineness", "GOLDPETAL": "1 g lot, quoted per 1 g, 999 fineness"}
W, H = landscape(A4)
ML, MR, MT, MB = 28, 28, 34, 30
ROW = 9.2                                   # row height in points
TOP = H - MT - 30                           # first table row baseline area starts below the running header
BOTTOM = MB + 16
COLS = [("Date", 62, "l"), ("Open", 62, "r"), ("High", 62, "r"), ("Low", 62, "r"), ("Close", 62, "r"), ("Prev close", 62, "r"),
        ("Volume (lots)", 70, "r"), ("Open int. (lots)", 74, "r"), ("Value (₹ lakh)", 80, "r"), ("₹ / pure g", 66, "r"),
        ("Days left", 50, "r"), ("Traded", 46, "c")]

# ---------------------------------------------------------------- data
df = pd.concat([pd.read_csv(f, parse_dates=["date", "expiry_date"]) for f in
                ("clean/gold_futures_history.csv", "clean/sealed_rows.csv", "clean/gold_futures.csv")], ignore_index=True)
df = df.drop_duplicates(["symbol", "expiry_date", "date"]).sort_values(["symbol", "expiry_date", "date"])
df["symbol"] = pd.Categorical(df["symbol"], SYMS, ordered=True)
df = df.sort_values(["symbol", "expiry_date", "date"])
N, NC = len(df), df.groupby(["symbol", "expiry_date"], observed=True).ngroups
FIRST, LAST = df.date.min(), df.date.max()
FILES = df.source_file.nunique()
d = lambda t: t.strftime("%d %b %Y")
def num(v, dp=2):
    if pd.isna(v): return "—"
    return f"{v:,.{dp}f}"


# ---------------------------------------------------------------- plan pages (line accounting identical to drawing)
CONTRACT_HEAD = 2.4      # rows used by a contract heading
COLHEAD = 1.6
cap = (TOP - BOTTOM) / ROW
plan, page, used = [], 0, None   # plan: list of (page, kind, payload)
contracts = []
for sym in SYMS:
    page += 1; used = 4.0         # section heading block on a fresh page
    plan.append((page, "section", sym))
    for exp, g in df[df.symbol == sym].groupby("expiry_date"):
        rows = list(g.itertuples(index=False))
        need = CONTRACT_HEAD + COLHEAD + min(3, len(rows))
        if used + need > cap: page += 1; used = 0
        contracts.append((sym, exp, page, len(rows), rows[0].date, rows[-1].date, rows[0].source_file))
        plan.append((page, "contract", (sym, exp, len(rows), rows[0].source_file)))
        used += CONTRACT_HEAD
        plan.append((page, "colhead", None)); used += COLHEAD
        for i, r in enumerate(rows):
            if used + 1 > cap:
                page += 1; used = 0
                plan.append((page, "cont", (sym, exp))); used += 1.2
                plan.append((page, "colhead", None)); used += COLHEAD
            plan.append((page, "row", (r, i)))
            used += 1
BODY_PAGES = page
IDX_PER_PAGE = 3 * int((H - MT - 92 - MB - 20) / 11.5)
IDX_PAGES = -(-len(contracts) // IDX_PER_PAGE)
FRONT = 2 + IDX_PAGES                    # cover + guide, then the index
TOTAL = FRONT + BODY_PAGES

# ---------------------------------------------------------------- drawing helpers
c = canvas.Canvas(OUT, pagesize=(W, H))
c.setTitle("Parity · MCX gold futures data book"); c.setAuthor("SYNTAX TERROR (TAN): Nikhil Kumar, Sai Ganesh, Ishaan Chhabra")
c.setSubject(f"All {N:,} daily rows of {NC} MCX gold futures contracts, {d(FIRST)} – {d(LAST)}, from the official MCX Bhavcopy")
def T(x, y, s, f="S", z=9, col=INK, a="l"):
    c.setFont(f, z); c.setFillColor(col)
    (c.drawString if a == "l" else c.drawRightString if a == "r" else c.drawCentredString)(x, y, s)
def frame(pno, left_label):
    c.setStrokeColor(LINE); c.setLineWidth(.6); c.line(ML, H - MT + 6, W - MR, H - MT + 6); c.line(ML, MB + 4, W - MR, MB + 4)
    T(ML, H - MT + 12, "PARITY · MCX GOLD FUTURES DATA BOOK", "SB", 7.5, GOLD)
    T(W - MR, H - MT + 12, left_label, "S", 7.5, INK3, "r")
    T(ML, MB - 6, "Source: official MCX Bhavcopy, commodity-wise files (mcxindia.com). Values as published.", "S", 7, INK3)
    T(W - MR, MB - 6, f"{pno} / {TOTAL}", "M", 7.5, INK2, "r")
def colhead(y):
    x = ML
    c.setFillColor(BAND); c.rect(ML, y - 3, W - ML - MR, ROW * 1.35, stroke=0, fill=1)
    for name, w, a in COLS:
        T(x + 3 if a == "l" else x + w - 3 if a == "r" else x + w / 2, y, name, "SB", 6.8, INK2, a); x += w
def row(y, r, i):
    if i % 2: c.setFillColor(STRIPE); c.rect(ML, y - 2.6, W - ML - MR, ROW, stroke=0, fill=1)
    traded = not r.no_trade and r.volume_lots > 0
    vals = [d(r.date), num(r.open), num(r.high), num(r.low), num(r.close), num(r.prev_close), f"{int(r.volume_lots):,}",
            f"{int(r.open_interest_lots):,}" if not pd.isna(r.open_interest_lots) else "—", num(r.value_lakhs), num(r.rs_per_g, 1),
            f"{int(r.days_to_expiry)}", "yes" if traded else "no"]
    x = ML
    for (name, w, a), v in zip(COLS, vals):
        col = INK if traded else INK3
        T(x + 3 if a == "l" else x + w - 3 if a == "r" else x + w / 2, y, v, "M", 7, col, a); x += w

# ---------------------------------------------------------------- cover
T(ML + 20, H - 150, "PARITY · SYNTAX TERROR (TAN) · HACK IN HILLS '26 · PROBLEM 03", "SB", 10, GOLD)
T(ML + 20, H - 200, "MCX gold futures", "SB", 40, INK)
T(ML + 20, H - 246, "The complete data book", "S", 30, INK2)
y = H - 310
for k, v in [("Rows", f"{N:,} daily rows, one per contract per trading day"), ("Contracts", f"{NC} contracts across GOLDM, GOLDTEN, GOLDGUINEA and GOLDPETAL"),
             ("Period", f"{d(FIRST)} – {d(LAST)}"), ("Source", f"Official MCX Bhavcopy, commodity-wise files ({FILES} files), mcxindia.com"),
             ("Pages", f"{TOTAL}: guide, contract index with page numbers, then every row")]:
    T(ML + 20, y, k.upper(), "SB", 8.5, INK3); T(ML + 120, y, v, "S", 12, INK); y -= 24
T(ML + 20, 90, "Team: Nikhil Kumar · Sai Ganesh · Ishaan Chhabra", "S", 10, INK2)
T(ML + 20, 72, "Live site: parity-gold-site.vercel.app · Code: github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-", "S", 9, INK3)
c.showPage()

# ---------------------------------------------------------------- guide
frame(2, "How to read this book")
T(ML, H - MT - 30, "How to read this book", "SB", 20, INK)
y = H - MT - 62
T(ML, y, "CONTRACT TYPES", "SB", 8.5, GOLD); y -= 16
summ = df.groupby("symbol", observed=True).agg(rows=("date", "size"), first=("date", "min"), last=("date", "max"), contracts=("expiry_date", "nunique"))
for s in SYMS:
    r = summ.loc[s]
    T(ML, y, s, "MB", 9.5, INK); T(ML + 95, y, DESC[s], "S", 9.5, INK2)
    T(ML + 350, y, f"{r.contracts} contracts · {r.rows:,} rows · {d(r['first'])} – {d(r['last'])}", "S", 9.5, INK2); y -= 15
y -= 12; T(ML, y, "COLUMNS", "SB", 8.5, GOLD); y -= 16
guide = [("Date", "Trading day the row belongs to."), ("Open, High, Low, Close", "The day's prices in ₹, in the contract's own quote unit (per 10 g, 8 g or 1 g). Close is MCX's settlement price."),
         ("Prev close", "Previous day's settlement price, as MCX printed it."), ("Volume (lots)", "Lots traded that day. One lot: 100 g GOLDM, 10 g GOLDTEN, 8 g GOLDGUINEA, 1 g GOLDPETAL."),
         ("Open int. (lots)", "Lots still open at the end of the day."), ("Value (₹ lakh)", "Turnover that day in ₹ lakh (1 lakh = ₹1,00,000)."),
         ("₹ / pure g", "Derived by Parity: close converted to rupees per gram of pure gold, so the four contracts compare directly."),
         ("Days left", "Calendar days from the row's date to the contract's expiry."), ("Traded", "“no” (grey row) means no lots traded that day; MCX still prints a price.")]
for k, v in guide:
    T(ML, y, k, "SB", 9, INK); T(ML + 140, y, v, "S", 9, INK2); y -= 14.5
y -= 12; T(ML, y, "NOTES", "SB", 8.5, GOLD); y -= 16
for t in ["Each contract is listed separately under its own expiry date. Nothing is stitched into a continuous series.",
          "Rows are exactly as published in the MCX files after duplicate files were removed. No price has been changed or filled in.",
          "MCX settles a contract on its expiry day at the Due Date Rate (from spot gold), so an expiry-day close can sit outside that day's high–low range.",
          "Weekend dates are MCX special sessions (for example Diwali Muhurat trading and Union Budget days)."]:
    T(ML, y, "•  " + t, "S", 9, INK2); y -= 14
c.showPage()

# ---------------------------------------------------------------- index of contracts
for ip in range(IDX_PAGES):
    pno = 3 + ip
    frame(pno, "Contract index")
    T(ML, H - MT - 30, "Contract index" + (" (continued)" if ip else ""), "SB", 20, INK)
    T(ML, H - MT - 48, "Every contract, its expiry, trading days in this book and the page it starts on.", "S", 9, INK2)
    chunk = contracts[ip * IDX_PER_PAGE:(ip + 1) * IDX_PER_PAGE]
    per_col = IDX_PER_PAGE // 3; cw = (W - ML - MR) / 3
    for j, (sym, exp, pg, n, f0, f1, fn) in enumerate(chunk):
        col, k = divmod(j, per_col)
        x, yy = ML + col * cw, H - MT - 74 - k * 11.5
        if k == 0:
            T(x, yy + 12, "Contract", "SB", 6.8, INK3); T(x + 150, yy + 12, "Days", "SB", 6.8, INK3, "r"); T(x + cw - 18, yy + 12, "Page", "SB", 6.8, INK3, "r")
        T(x, yy, f"{sym} {exp.strftime('%d %b %Y')}", "M", 7.6, INK); T(x + 150, yy, f"{n}", "M", 7.6, INK2, "r")
        c.setStrokeColor(LINE); c.setDash(1, 2); c.line(x + 156, yy + 2, x + cw - 40, yy + 2); c.setDash()
        T(x + cw - 18, yy, f"{FRONT + pg}", "MB", 7.6, GOLD, "r")
        c.linkRect("", f"p{pg}", (x, yy - 2, x + cw - 14, yy + 8), relative=0)
    c.showPage()

# ---------------------------------------------------------------- body
cur, y, label = 0, None, ""
def new_page(p, lab):
    global y
    if p != 1: c.showPage()
    frame(FRONT + p, lab); c.bookmarkPage(f"p{p}"); y = TOP
for pg, kind, pay in plan:
    if pg != cur:
        lab = pay if kind == "section" else f"{pay[0]} · expiry {pay[1].strftime('%d %b %Y')}" if kind in ("contract", "cont") else label
        new_page(pg, lab); cur = pg; label = lab
    if kind == "section":
        s = pay; r = summ.loc[s]
        c.bookmarkPage(s); c.addOutlineEntry(s, s, level=0)
        T(ML, y - 10, s, "SB", 26, INK); T(ML + 6 + pdfmetrics.stringWidth(s, "SB", 26), y - 10, DESC[s], "S", 10, INK2)
        T(ML, y - 26, f"{r.contracts} contracts · {r.rows:,} daily rows · {d(r['first'])} – {d(r['last'])}", "S", 9, INK3)
        y -= 4.0 * ROW
    elif kind == "contract":
        sym, exp, n, fn = pay
        y -= 0.6 * ROW
        c.setFillColor(GOLD); c.rect(ML, y - 3, 2.2, 12, stroke=0, fill=1)
        T(ML + 8, y, f"{sym} · expiry {exp.strftime('%d %b %Y')}", "SB", 9.5, INK)
        T(W - MR, y, f"{n} trading days · file {fn}", "S", 7.5, INK3, "r")
        c.addOutlineEntry(f"{sym} {exp.strftime('%d %b %Y')}", f"p{pg}", level=1)
        y -= 1.8 * ROW
    elif kind == "cont":
        T(ML, y, f"{pay[0]} · expiry {pay[1].strftime('%d %b %Y')} (continued)", "SB", 7.5, INK3); y -= 1.2 * ROW
    elif kind == "colhead":
        colhead(y); y -= COLHEAD * ROW
    else:
        row(y, *pay); y -= ROW
c.showPage(); c.save()
print(f"wrote {OUT}: {TOTAL} pages, {N:,} rows, {NC} contracts")

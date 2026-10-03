"""Charts for the report, drawn from dashboard/data.json so they always match the site.

    python report/charts.py      (then python report/build.py)
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "..", "dashboard", "data.json")))
COL = {"GOLDGUINEA": "#e8643a", "GOLDPETAL": "#1aae7a", "GOLDTEN": "#2a78d6"}
LAB = {"GOLDGUINEA": "GOLDGUINEA (8 g)", "GOLDPETAL": "GOLDPETAL (1 g)", "GOLDTEN": "GOLDTEN (10 g)"}
plt.rcParams.update({"axes.axisbelow": True, "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#999", "axes.labelcolor": "#555",
                     "xtick.color": "#555", "ytick.color": "#555", "axes.spines.top": False, "axes.spines.right": False})


def k_(v):
    t = f"{abs(v) / 1000:.1f}" if abs(v) < 1000 else f"{abs(v) / 1000:.0f}"
    return ("+" if v >= 0 else "−") + t + "k"


def premium():
    pm = D["premium_monthly"]
    x = pd.to_datetime(pm["months"]) + pd.Timedelta(days=14)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    a, b = pd.to_datetime(D["crash_window"])
    ax.axvspan(a, b + pd.Timedelta(days=1), color="#efede8", zorder=0)
    ax.axvline(pd.Timestamp("2024-07-23"), color="#999", lw=1, ls=":")
    ax.text(pd.Timestamp("2024-07-28"), 395, "23 Jul 2024\nduty cut 15% → 6%", fontsize=9.5, color="#555", va="top")
    ax.axhline(0, color="#555", lw=1.4)
    last = {}
    for s in ("GOLDGUINEA", "GOLDPETAL", "GOLDTEN"):
        y = pd.Series(pm[s], index=x, dtype=float)
        ax.plot(y.index, y.values, color=COL[s], lw=2.6, marker="o", ms=4, mec="white", mew=.8)
        last[s] = y.dropna().iloc[-1]
    order = sorted(last, key=lambda s: -last[s])
    for i, s in enumerate(order):
        ax.text(x[-1] + pd.Timedelta(days=25), 105 - 65 * i, LAB[s], fontsize=10.5, va="center", color="#111")
    ax.text(pd.Timestamp("2025-04-15"), -50, "GOLDM (100 g bar) = 0 line", fontsize=10.5, color="#555")
    ax.set_ylim(-260, 400)
    ax.text(a + (b - a) / 2, -250, "crash period", ha="center", fontsize=10.5, color="#555")
    ax.set_ylabel("Price above GOLDM, basis points\n(100 bp = 1%)")
    ax.grid(axis="y", color="#e5e5e5")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 5, 9)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    ax.set_xlim(x[0] - pd.Timedelta(days=40), x[-1] + pd.Timedelta(days=140))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "premium.png"))
    plt.close(fig)


def months():
    m = pd.DataFrame(D["A_hold_monthly"])
    fig, ax = plt.subplots(figsize=(10, 4), dpi=140)
    lab = pd.to_datetime(m.month).dt.strftime("%b %y")
    ax.bar(lab, m.net / 1000, color=["#1aae7a" if v >= 0 else "#d6453a" for v in m.net], width=.65)
    for i, (v, n) in enumerate(zip(m.net, m.trades)):
        ax.text(i, v / 1000 + (6 if v >= 0 else -6), f"{k_(v)}\n{n} trades", ha="center", va="bottom" if v >= 0 else "top", fontsize=9, color="#333")
    ax.axhline(0, color="#555", lw=1)
    ax.set_ylabel("Net profit, ₹ thousand")
    ax.set_ylim(min(-60, m.net.min() / 1000 - 30), m.net.max() / 1000 + 50)
    ax.grid(axis="y", color="#e5e5e5")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "zscore_months.png"))
    plt.close(fig)


def sealed():
    rows = pd.DataFrame(D["sealed"]["rows"])
    r5 = rows[rows.slip == 5]
    tests = [("test3", "2016–2019"), ("test2", "2020 – Oct 2023")]
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=140)
    strat = [("A", "Strategy A (pairs)", "#9a9a9a"), ("B", "Strategy B (fair price)", "#835a07"), ("C", "Strategy C (B retrained)", "#c9a24a")]
    w = .26
    for j, (k, name, c) in enumerate(strat):
        vals = [r5[(r5.strategy == k) & (r5.test == t)].net.iloc[0] / 1000 for t, _ in tests]
        xs = [i + (j - 1) * w for i in range(len(tests))]
        ax.bar(xs, vals, w * .92, color=c, label=name)
        for xv, v in zip(xs, vals):
            ax.text(xv, v + (2 if v >= 0 else -2), k_(v * 1000), ha="center", va="bottom" if v >= 0 else "top", fontsize=9.5)
    ax.set_xticks(range(len(tests)), [t[1] for t in tests])
    ax.axhline(0, color="#555", lw=1)
    ax.set_ylabel("Net at 5 bp, ₹ thousand")
    ax.set_ylim(-80, 55)
    ax.grid(axis="y", color="#e5e5e5")
    ax.legend(frameon=False, fontsize=9.5, loc="lower left", ncol=3, bbox_to_anchor=(0, 1.0))
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "sealed.png"))
    plt.close(fig)


if __name__ == "__main__":
    premium(); months(); sealed()
    print("wrote premium.png, zscore_months.png, sealed.png")

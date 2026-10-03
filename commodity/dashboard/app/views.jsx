import { useEffect, useMemo, useState } from "react";
import { D, P, CRASH, SYM, SYMS, SHORT, MON, T, inr, sgn, fdate, fmon, pname, r2, slug, NAME, reducedMotion } from "./lib.js";
import { lineChart, barChart, scatter, groupBars, curveChart, alertStrip, calendarChart, liquidityChart } from "./charts.js";
import { Chart, Card, Kpi, Num, Seg, Pill, Legend, Term, Hero, Reveal, Pager, Icon, CsvButton, downloadCSV, useApp, Takeaway, More } from "./ui.jsx";

const roll = (a, n) => a.map((_, i) => { const w = a.slice(Math.max(0, i - n + 1), i + 1).filter(v => v != null); return a[i] == null || !w.length ? null : w.reduce((x, y) => x + y, 0) / w.length; });
const kfmt = v => v === 0 ? "0" : (Math.abs(v) >= 1e5 ? (v / 1e5).toFixed(1) + "L" : (v / 1e3).toFixed(0) + "k");
const Go = ({ to, children }) => <a className="go" href={"#" + to}>{children} <Icon name="arrow" size={15} /></a>;

/* ================================================================ DOWNLOADS (shared by the front page, Backtest and Signals) */
const TRADE_HEAD = ["strategy", "contract", "expiry", "entry", "exit", "position", "days_held", "grams_per_leg", "gold_move_pct", "from_gap_rs", "from_gold_rs", "gross_rs", "costs_rs", "net_rs", "slippage_bp", "tender", "last_safe_exit"];
function csvTrades(key, s, rows, tonly = false, f = "All") {
  downloadCSV(`parity_trades_${slug(BT[key].name)}_${s.toFixed(1)}bp${tonly ? "_broker-allowed" : ""}${f !== "All" ? "_" + slug(f) : ""}.csv`, TRADE_HEAD,
    rows.map(t => [BT[key].name.replace(" · ", " "), t.what, t.expiry, t.entry, t.exit, posText(t), t.days, D.backtests[key].grams, r2(t.gold_move), r2(t.gap_part), r2(t.gold_part), r2(t.gross), r2(t.gross - t.net), r2(t.net), s, t.ok_tender ? "clear" : "in tender", t.safe_exit]));
}
function csvAlerts(list, f = "All") {
  downloadCSV(`parity_alerts_${f === "All" ? "all" : slug(f)}.csv`,
    ["start", "end", "contract", "expiry", "signal", "alert_days", "z", "premium_bp", "usual_premium_bp", "premium_5d_bp", "premium_10d_bp", "premium_20d_bp", "closed_halfway_10d", "days_to_half"],
    list.map(a => [a.start, a.end, a.symbol, a.expiry, a.direction, a.alert_days, r2(a.z), r2(a.premium_bp), r2(a.usual_bp), r2(a.prem_5d), r2(a.prem_10d), r2(a.prem_20d),
      a.closed_half_10d === true ? "yes" : a.closed_half_10d === false ? "no" : "too recent", a.days_to_half == null || !isFinite(a.days_to_half) ? null : a.days_to_half]));
}
const allTrades = (key, s = 5) => D.trades[key].map(t => ({ ...t, net: netAt(t, s) }));

/* The latest end-of-day snapshot: for each contract type, the contract the fair-price signal watches (GOLDM: the most traded). */
function latest() {
  const day = D.curves.today, pts = day.points;
  const m = pts.filter(p => p.symbol === "GOLDM").reduce((a, b) => b.kg > a.kg ? b : a);
  const rows = [{ symbol: "GOLDM", expiry: m.expiry, rs: m.rs_per_g, kg: m.kg, ref: true }];
  D.signals.rows.forEach(r => { const p = pts.find(x => x.symbol === r.symbol && x.expiry === r.expiry);
    rows.push({ symbol: r.symbol, expiry: r.expiry, rs: p ? p.rs_per_g : null, kg: p ? p.kg : null, prem: r.premium_bp, usual: r.usual_bp, z: r.z }); });
  return { date: day.date, rows, all: pts };
}

function Snapshot() {
  const k = D.signals.threshold, L = latest(), hot = L.rows.filter(r => r.z != null && Math.abs(r.z) >= k);
  const csv = () => downloadCSV(`parity_latest_${L.date}.csv`, ["date", "contract", "expiry", "rs_per_pure_gram", "traded_kg", "days_to_expiry"],
    L.all.map(p => [L.date, p.symbol, p.expiry, p.rs_per_g, p.kg, p.dte]));
  return <Card id="latest" title="Latest market data" sub={<>End of day {fdate(L.date)}, the last complete MCX Bhavcopy in our files. Prices are ₹ per gram of pure gold, so the four can be compared directly.</>}
    actions={<CsvButton text="Download" label={`Download every contract traded on ${fdate(L.date)} (${L.all.length} rows, CSV)`} onClick={csv} />}>
    <div className={"status inset" + (hot.length ? " hot" : "")}><span className="dot" />
      <div><b>{hot.length ? `Signal today: ${hot.length} contract${hot.length > 1 ? "s" : ""} off fair price` : "Signal today: quiet. Every contract is close to its fair price."}</b>
        <div className="muted">Our model's output. An alert fires when a contract sits more than {k}σ from its fair price.</div></div>
      <Go to="signals">How the signal works</Go></div>
    <div className="tw"><table className="snap"><thead><tr><th>Contract</th><th className="ph-x">Expiry</th><th className="n">₹ / pure g</th><th className="n ph-x">Traded</th><th className="n">Premium<span className="ph-x"> vs GOLDM</span></th><th className="n ph-x">Usual</th><th>Signal</th></tr></thead>
      <tbody>{L.rows.map(r => <tr key={r.symbol}><td className="nowrap"><span className="sw" style={{ background: SYM[r.symbol].c }} /><b>{r.symbol}</b><div className="dim sm">{SYM[r.symbol].d}<span className="ph-o"> · {fdate(r.expiry)}</span></div></td>
        <td className="mono nowrap ph-x">{fdate(r.expiry)}</td><td className="n" data-l="₹ / pure g">{r.rs == null ? "—" : r.rs.toLocaleString("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</td><td className="n dim ph-x">{r.kg == null ? "—" : r.kg + " kg"}</td>
        {r.ref ? <><td className="n dim" data-l="Premium">reference</td><td className="n dim ph-x">—</td><td data-l="Signal"><Pill>Benchmark</Pill></td></>
          : <><td className="n" data-l="Premium">{sgn(r.prem)} bp</td><td className="n dim ph-x">{sgn(r.usual)} bp</td>
            <td data-l="Signal">{Math.abs(r.z) >= k ? <Pill tone="warn">{r.z > 0 ? "Rich" : "Cheap"} · {sgn(r.z, 2, "σ")}</Pill> : <Pill tone="good">Normal · {sgn(r.z, 2, "σ")}</Pill>}</td></>}</tr>)}</tbody></table></div>
    <p className="note">Premium is measured after moving GOLDM to the same expiry, so different expiry dates compare fairly. Parity does not forecast gold's price; the brief asks for a signal, a test on unseen data and results after costs. The MCX files are end-of-day, so “current” means the latest file: add newer Bhavcopy files and rebuild to move this table forward.</p>
  </Card>;
}

function BriefQA() {
  const mt = P["M-TEN"].normal, mg = P["M-GUINEA"].normal, mp = P["M-PETAL"].normal, rs = Object.fromEntries(D.rolldown.summary.map(a => [a.symbol, a]));
  const A5 = D.backtests.A_hold.rows.find(r => r.slip === 5), B5 = D.backtests.B_hold.rows.find(r => r.slip === 5);
  const lc = Object.fromEntries(D.lifecycle_summary.map(a => [a.run, a])), att = Object.fromEntries(D.attribution.map(a => [a.run, a]));
  const k = D.signals.threshold, hot = D.signals.rows.filter(r => Math.abs(r.z) >= k).length;
  const dirs = [
    ["Relative value", "Once size, quote and purity are normalised, is one contract cheap or expensive against another?",
      <>GOLDM and GOLDTEN match ({sgn(mt[0])} bp). The 8 g coin and 1 g contract carry a steady {Math.round(-mg[0])}–{Math.round(-mp[0])} bp premium.</>, "relative"],
    ["Term structure and carry", "How much of a price change is mechanical roll-down, and how much is the curve itself moving?",
      <>Roll-down is about {Math.abs(rs.GOLDM.avg_rolldown_pct).toFixed(1)}% a month for GOLDM; curve moves average {rs.GOLDM.avg_abs_curve_move_pct.toFixed(1)}%, so most change is the curve.</>, "term"],
    ["Walk-forward backtest", "Replayed day by day with no look-ahead, after costs and thin days, does a strategy make money?",
      <>Strategy A {inr(A5.net)}, Strategy B {inr(B5.net)} net at 5 bp on a sealed holdout. A's profit came almost all from January 2026.</>, "backtest"],
    ["Trader alerts", "Do alerts flag real opportunities and stay quiet when there is nothing to act on?",
      <>{hot ? `${hot} alert${hot > 1 ? "s" : ""} today.` : "Quiet today."} {D.alerts.history.length} alerts in the record; one fires only beyond ±{k}σ from fair price.</>, "signals"],
    ["Contract lifecycle", "Does every entry and exit sit inside the contract calendar, including the tender period?",
      <>Every trade starts after listing. B always exits before tender; A's {lc.A_hold.trades - lc.A_hold.outside_tender} tender trades are shown and can be left out.</>, "calendar"]
  ];
  const fin = [
    ["Validated on unseen history?", "Yes. Three sealed tests, each run once after the rules were frozen in Git: Aug 2025 – May 2026, 2016–2019 and 2020–2023.", "backtest"],
    ["Reported after costs, on the contracts actually held?", "Yes. MCX fees, taxes, brokerage, GST and 0–10 bp slippage on every leg of the exact contract.", "backtest"],
    ["Strategy separated from gold's own move?", `Yes. Each trade is split exactly; gold's move is ${Math.abs(att.A_hold.gold_share_of_gross_pct).toFixed(1)}% of Strategy A's gross profit.`, "backtest"],
    ["Is there a persistent edge after costs?", "No. The best rule stays slightly positive over 2016–2023 but within the range of luck; the 2026 crash paid, the 2020 crash did not. The brief accepts a rigorous “no edge”.", "backtest"]
  ];
  const Row = ({ n, h, q, a, to }) => <li className="qa-r"><span className="qa-n">{String(n).padStart(2, "0")}</span>
    <div className="qa-b">{h && <div className="qa-h">{h}</div>}<div className="qa-q">{q}</div><div className="qa-a">{a}</div></div><Go to={to}>See it</Go></li>;
  return <Card id="asks" title="What the problem statement asks, and our answer" sub="Problem 03 sets five analysis directions and a final challenge. Each one, answered in a line.">
    <div className="qa-g"><div className="lab">Five analysis directions</div>
      <ol className="qa">{dirs.map(([h, q, a, to], i) => <Row key={h} n={i + 1} h={h} q={q} a={a} to={to} />)}</ol></div>
    <div className="qa-g"><div className="lab">Final challenge</div>
      <ol className="qa">{fin.map(([q, a, to], i) => <Row key={q} n={i + 6} q={q} a={a} to={to} />)}</ol></div>
    <Go to="brief">The full brief, quoted line by line</Go>
  </Card>;
}

function Downloads() {
  const L = latest(), pr = D.prices, pd = D.premium_daily, h = D.alerts.history;
  const items = [
    ["Latest day, every contract", `${L.all.length} contracts on ${fdate(L.date)}`, () => downloadCSV(`parity_latest_${L.date}.csv`, ["date", "contract", "expiry", "rs_per_pure_gram", "traded_kg", "days_to_expiry"], L.all.map(p => [L.date, p.symbol, p.expiry, p.rs_per_g, p.kg, p.dte]))],
    ["Daily price per pure gram", `${pr.dates.length} days, most traded contract of each type`, () => downloadCSV("parity_daily_price_per_pure_gram.csv", ["date", ...SYMS], pr.dates.map((d, i) => [d, ...SYMS.map(s => pr[s][i])]))],
    ["Daily premium over GOLDM", `${pd.dates.length} days, in bp, same expiry`, () => { const ss = ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"].filter(s => pd[s]); downloadCSV("parity_daily_premium_bp.csv", ["date", ...ss], pd.dates.map((d, i) => [d, ...ss.map(s => pd[s][i])])); }],
    ["Strategy A trades", `${D.trades.A_hold.length} trades, sealed holdout, net at 5 bp`, () => csvTrades("A_hold", 5, allTrades("A_hold"))],
    ["Strategy B trades", `${D.trades.B_hold.length} trades, sealed holdout, net at 5 bp`, () => csvTrades("B_hold", 5, allTrades("B_hold"))],
    ["Alert history", `${h.length} alert episodes and what each gap did next`, () => csvAlerts(h.slice().reverse())]
  ];
  return <Card id="downloads" title="Download the data" sub="Everything on this site comes from these tables. CSV files open in Excel or Google Sheets.">
    <div className="dl">{items.map(([t, d, fn]) => <button key={t} type="button" className="dl-i" onClick={fn} aria-label={`Download ${t} as CSV: ${d}`}>
      <Icon name="download" size={18} /><span><b>{t}</b><small>{d}</small></span><span className="dl-x">CSV</span></button>)}</div>
  </Card>;
}

/* ================================================================ OVERVIEW */
export function Overview() {
  const [range, setRange] = useState(0);
  const pd = D.premium_daily, cut = range ? T(pd.dates[pd.dates.length - 1]) - range * 30.44 * 864e5 : -Infinity;
  const pr = D.prices;
  return <>
    <Hero n={1} eyebrow="MCX gold futures · Problem 03" title={<>One metal, <span className="hl">four prices.</span></>}>
      <b>The problem:</b> MCX lists four gold futures that differ only in size and <Term k="purity">purity</Term>. Per gram of pure gold they should cost the same. Parity checks whether they do, whether any gap can be traded after real costs, and tells a trader when one is worth a look.
    </Hero>
    <Takeaway>They mostly match. Where they don't, the gap is usually too small to pay for the costs of trading it. It paid in the January 2026 crash, and not reliably in eight more years of sealed tests.</Takeaway>
    <nav className="jump" aria-label="On this page"><a href="#latest" onClick={jump}>Latest data</a><a href="#asks" onClick={jump}>What the brief asks</a><a href="#downloads" onClick={jump}>Downloads</a></nav>
    <Snapshot />
    <BriefQA />
    <Downloads />
    <div className="more-list">
      <More title="How the premium moved, 2023 – 2026" hint="How much more the small contracts cost than GOLDM, with market events marked">
        <div className="toolbar"><Legend items={["GOLDGUINEA", "GOLDPETAL", "GOLDTEN"].map(s => [SYM[s].c, `${s} (${SYM[s].d})`])} band />
          <Seg label="Range" value={range} onChange={setRange} options={[[6, "6M"], [12, "1Y"], [0, "All"]]} small /></div>
        <Chart deps={[range]} draw={host => { const ix = pd.dates.map((d, i) => T(d) >= cut ? i : -1).filter(i => i >= 0);
          const ser = ["GOLDGUINEA", "GOLDPETAL", "GOLDTEN"].map(s => { const sm = roll(pd[s], 5); return { label: s, color: SYM[s].c, values: ix.map(i => sm[i]) }; });
          lineChart(host, { dates: ix.map(i => pd.dates[i]), series: ser, band: CRASH, zero: true, endLabels: true, yfmt: v => v + " bp", tfmt: v => sgn(v, 0, " bp"), aria: "Premium of small gold contracts over GOLDM" }); }} />
      </More>
      <More title="All four contracts on one price chart" hint="₹ per gram of pure gold. The lines overlap; that is the point.">
        <Legend items={SYMS.map(s => [SYM[s].c, s])} band />
        <Chart deps={[range]} draw={host => { const pidx = pr.dates.map((d, i) => T(d) >= cut ? i : -1).filter(i => i >= 0);
          const ps = SYMS.map(s => ({ label: s, color: SYM[s].c, values: pidx.map(i => pr[s][i]) }));
          lineChart(host, { dates: pidx.map(i => pr.dates[i]), series: ps, band: CRASH, yfmt: v => "₹" + v.toLocaleString("en-IN"), tfmt: v => "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 0 }), aria: "Price per gram of pure gold, four contracts",
            extra: i => { const vv = ps.map(s => s.values[i]).filter(v => v != null); if (vv.length < 2) return ""; return `<div class="r sep"><span>Widest gap</span><b>${((Math.max(...vv) / Math.min(...vv) - 1) * 1e4).toFixed(0)} bp</b></div>`; } }); }} />
      </More>
    </div>
  </>;
}
/* In-page jumps without touching the hash router */
function jump(e) { e.preventDefault(); const el = document.getElementById(e.currentTarget.getAttribute("href").slice(1)); if (el) { el.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" }); } }

/* ================================================================ BRIEF */
export function Brief() {
  const P5 = P["M-TEN"].normal, att = Object.fromEntries(D.attribution.map(a => [a.run, a])), lc = Object.fromEntries(D.lifecycle_summary.map(a => [a.run, a]));
  const rs = Object.fromEntries(D.rolldown.summary.map(a => [a.symbol, a]));
  const A5 = D.backtests.A_hold.rows.find(r => r.slip === 5), B5 = D.backtests.B_hold.rows.find(r => r.slip === 5);
  const dirs = [
    ["Cross-contract relative value", "Normalize contract size, quotation base, and purity. Identify when one contract appears unusually cheap or expensive relative to another.",
      [`All four contracts in ₹ per gram of pure gold; GOLDM vs GOLDTEN ${sgn(P5[0])} bp in quiet months proves the conversion`, "All six pairs measured for 2024, quiet 2025–26 months and the crash", "Strategy B flags a contract that strays from its fair price"], "relative"],
    ["Term structure & carry", "Analyze the futures curve. Separate mechanical roll-down toward expiry from genuine changes in the curve.",
      ["Futures curve on any of three dates; carry measured from the data", "The curve's slope tracked month by month across all listed expiries, for every contract type", `Each month's price change split: roll-down about ${Math.abs(rs.GOLDM.avg_rolldown_pct).toFixed(1)}% vs curve moves of about ${rs.GOLDM.avg_abs_curve_move_pct.toFixed(1)}% a month for GOLDM`], "term"],
    ["Walk-forward backtesting", "Replay historical contracts day by day without look-ahead bias. Account for transaction costs and thin-day liquidity.",
      ["Signals at today's close, trades at the next day's price", "MCX fees, taxes and 0–10 bp slippage on every leg", "Days with under 1 kg traded are skipped; rules frozen in Git before each sealed test"], "backtest"],
    ["Trader-facing intelligence", "Build dashboards or alerts that highlight meaningful opportunities. Keep alerts quiet when there is no meaningful signal. Attribute performance to the strategy rather than simply to gold-price movement.",
      ["This site; the Signals page stays “Quiet” unless a contract is ±1.5σ from fair", `A full alert history: ${D.alerts.history.length} past alerts and what each gap did next, against ordinary days and the cost of a round trip`, `Every trade's profit split into gap and gold parts: gold's own move is ${Math.abs(att.A_hold.gold_share_of_gross_pct).toFixed(1)}% of Strategy A's and ${Math.abs(att.B_hold.gold_share_of_gross_pct).toFixed(1)}% of Strategy B's holdout gross profit`], "backtest"],
    ["Contract lifecycle planning", "Track listing dates, liquidity development, tender periods, and expiry. Place every intended entry and exit inside the relevant contract calendar.",
      ["Every contract's first and last day, its tender period, and how liquidity builds", `All trades start after listing. Strategy B exits before the tender period every time; Strategy A held ${lc.A_hold.trades - lc.A_hold.outside_tender} of ${lc.A_hold.trades} holdout trades into it, shown and excluded on request`], "calendar"]
  ];
  const fin = [
    ["Create a functional prototype that transforms exchange settlement data into a defensible analytical signal or intelligence product", "This site, rebuilt by two scripts from the official MCX files"],
    ["…and validates the approach using unseen historical data", `Three sealed tests, each run once: Aug 2025 – May 2026, then ${D.meta.sealed_contracts} contracts from 2016–2023, walled off in code until the rules were frozen`],
    ["Report performance after relevant costs using the prices of the contracts actually held", `Every trade priced on the exact contracts held. Strategy A ${inr(A5.net)}, Strategy B ${inr(B5.net)} at 5 bp`],
    ["Clearly separate strategy performance from the impact of the underlying gold price", "Exact per-trade split into gap and gold parts, plus each trade plotted against gold's move"],
    ["A rigorous demonstration that no persistent edge survives costs is also a valid analytical outcome", `Our verdict: no dependable edge after costs. The fair-price model is ${inr(D.sealed.boot5.B.net)} over 2016–2023 at 5 bp, but its 95% range includes zero`]
  ];
  const warn = [
    ["Validate the returned Date against the requested date", "Every file identified by its contents; no row after its contract's expiry; every weekend date must be a known special session (Diwali Muhurat 2023, Budget days 2025 and 2026)"],
    ["Requests use DD/MM/YYYY, responses MM/DD/YYYY; compact expiry format; space-padded symbols", "Downloaded files carry dates as “29 Aug 2025”, parsed with a fixed format, so day and month cannot swap; expiry parsed as 04SEP2026; symbols stripped"],
    ["Track contracts by expiry date, not a continuous near-month series", "Every price, pair and trade is tied to one contract's expiry; nothing is stitched"],
    ["Settlement prices are not automatically executable fills", "Measured: the official close sits 17–26 bp from the day's average traded price. Strategy B fills at that average; all results shown at 0, 5 and 10 bp slippage"],
    ["Volume is not market depth", "We only have daily volume, so we skip days under 1 kg traded and keep positions small (40–200 g). Depth cannot be measured from end-of-day files; stated as a limitation"],
    ["GOLDTEN only exists from 2025", "GOLDTEN pairs start April 2025 and are marked “not listed yet” for 2024"]
  ];
  return <>
    <Hero n={2} eyebrow="Problem 03 · Commodity Derivatives Intelligence" title={<>What the brief asks, <span className="hl">and our answer.</span></>}>
      Build a data product from MCX's public futures data that finds and analyses price differences between gold contracts, validates it on unseen history, reports results after costs, and separates strategy performance from gold's own move. A rigorous “no edge after costs” is an accepted outcome.
    </Hero>
    <Takeaway>All five directions in the brief are covered and every line of the final challenge is answered. Our honest result: after costs there is no dependable edge. The gap paid in the January 2026 crash; tested once on 2016–2023, that did not repeat reliably.</Takeaway>
    <div className="grid g2">{dirs.map(([h, q, items, link], i) => <Reveal key={h} className={"dir" + (i === dirs.length - 1 ? " span2" : "")}>
      <div className="dir-h"><span className="fn">{String(i + 1).padStart(2, "0")}</span><h3>{h}</h3><Pill tone="good">Done</Pill></div>
      <q>{q}</q><ul>{items.map(t => <li key={t}>{t}</li>)}</ul><Go to={link}>See it</Go></Reveal>)}</div>
    <Card title="The final challenge, line by line" sub="Quoted from the problem statement.">
      <div className="tw"><table><thead><tr><th>The brief says</th><th>What we did</th><th>Status</th></tr></thead>
        <tbody>{fin.map(r => <tr key={r[0]}><td className="quote">{r[0]}</td><td>{r[1]}</td><td><Pill tone="good">Done</Pill></td></tr>)}</tbody></table></div>
    </Card>
    <div className="more-list"><More title="Data warnings in the brief" hint="Six warnings, and what we did about each">
      <div className="tw"><table><thead><tr><th>Warning in the brief</th><th>How we handled it</th></tr></thead>
        <tbody>{warn.map(r => <tr key={r[0]}><td style={{ maxWidth: 360 }}><b>{r[0]}</b></td><td>{r[1]}</td></tr>)}</tbody></table></div>
    </More></div>
  </>;
}

/* ================================================================ RELATIVE VALUE */
const Stat = ({ lab, v, rng, tone = "" }) => <div className={"kpi sm " + tone}><div className="lab">{lab}</div><div className="val">{v}</div><div className="note">{rng}</div></div>;
export function Relative() {
  const { rvPair: pair, setRvPair: setPair } = useApp();
  const p = P[pair], s = D.pair_series[pair];
  return <>
    <Hero n={3} eyebrow="Relative value" title={<>Six pairs, <span className="hl">two worlds.</span></>}>
      Every pair of contracts compared per pure gram. 2024, the quiet months of 2025–26 and the Dec 2025 – Mar 2026 crash behave differently enough that we report them separately. GOLDTEN only started in April 2025.
    </Hero>
    <Takeaway>GOLDM and GOLDTEN trade at the same price. GOLDGUINEA and GOLDPETAL sit steadily above GOLDM. All the gaps blew out only in the December 2025 – March 2026 crash. Pick a pair to see it.</Takeaway>
    <Card title={pname(pair)} sub={<>Daily gap per pure gram, in <Term k="bp">bp</Term>. Above zero: {SHORT[pair.split("-")[0]]} is dearer.</>}
      actions={<Seg label="Pair" value={pair} onChange={setPair} options={D.pairs.map(q => [q.pair, q.pair.replace("M-", "GOLDM-")])} small />}>
      <div className="grid g-main">
        <div style={{ minWidth: 0 }}><Legend items={[["var(--teal)", "Daily gap"], ["var(--gold)", "2025–26 quiet-month average"]]} band />
          <Chart deps={[pair]} draw={host => lineChart(host, { dates: s.dates, series: [{ label: "Gap", color: "var(--teal)", values: s.bp }], band: CRASH, zero: true, area: true, hline: p.normal[0], yfmt: v => v + " bp", tfmt: v => sgn(v, 1, " bp"), aria: "Daily gap for " + pname(pair) })} /></div>
        <div className="stack">
          {p.y2024 && <Stat lab="2024" v={`${sgn(p.y2024[0])} bp`} rng={`95% range ${sgn(p.y2024[1])} to ${sgn(p.y2024[2])} · ${p.y2024[3]} weeks`} />}
          <Stat tone="accent" lab="2025–26 quiet months" v={`${sgn(p.normal[0])} bp`} rng={`95% range ${sgn(p.normal[1])} to ${sgn(p.normal[2])} · ${p.normal[3]} weeks`} />
          <Stat lab="Crash period" v={`${sgn(p.crash[0])} bp`} rng={`95% range ${sgn(p.crash[1])} to ${sgn(p.crash[2])} · ${p.crash[3]} weeks`} />
          <Stat lab="Same sign in" v={p.cycles_same_sign} rng={`contract cycles · typical daily swing ${p.daily_sd} bp`} />
        </div>
      </div>
    </Card>
    <div className="more-list"><More title="All six pairs in one table" hint="Mean gap by period, with its 95% range. Click a row to chart it.">
      <div className="tw"><table><thead><tr><th>Pair</th><th className="n">2024</th><th className="n">2025–26 quiet</th><th className="n">95% range</th><th className="n">Crash period</th><th className="n">All days</th><th className="n">Cycles</th></tr></thead>
        <tbody>{D.pairs.map(q => { const zero = q.normal[1] <= 0 && q.normal[2] >= 0;
          return <tr key={q.pair} className={"click" + (q.pair === pair ? " sel" : "")} tabIndex={0} onClick={() => setPair(q.pair)} onKeyDown={e => e.key === "Enter" && setPair(q.pair)}>
            <td><b>{pname(q.pair)}</b> {zero && <Pill tone="good">same price</Pill>}</td><td className="n">{q.y2024 ? sgn(q.y2024[0]) + " bp" : <span className="dim">not listed</span>}</td>
            <td className="n">{sgn(q.normal[0])} bp</td><td className="n dim">{sgn(q.normal[1])} to {sgn(q.normal[2])}</td><td className="n">{sgn(q.crash[0])} bp</td><td className="n">{sgn(q.all[0])} bp</td><td className="n">{q.cycles_same_sign}</td></tr>; })}</tbody></table></div>
    </More></div>
  </>;
}

/* ================================================================ TERM STRUCTURE */
export function Term_() {
  const [day, setDay] = useState("today");
  const c = D.curves[day], cs = D.curve_slope, ssy = SYMS.filter(x => cs[x]), rd = D.rolldown.goldm;
  return <>
    <Hero n={4} eyebrow="Term structure" title={<>Later expiries <span className="hl">cost more.</span></>}>
      Holding gold for longer ties up money, so contracts that expire later trade higher. We measure that <Term k="carry">cost of carry</Term> from the data itself and use it to line GOLDM up with the others.
    </Hero>
    <Takeaway>Contracts that expire later cost more, because holding gold ties up money. That carry was about 4–6% a year until 2025 and 10–18% in 2026. Time alone moves GOLDM only about {Math.abs(D.rolldown.summary.find(r => r.symbol === "GOLDM").avg_rolldown_pct).toFixed(1)}% a month; gold's own moves are far bigger.</Takeaway>
    <Card title="Futures curve" sub={`₹ per gram of pure gold against days to expiry, ${fdate(c.date)}.`}
      actions={<Seg label="Date" value={day} onChange={setDay} options={[["today", "Latest"], ["t30", "30 days earlier"], ["t90", "90 days earlier"]]} />}>
      <Legend items={SYMS.map(s => [SYM[s].c, s]).concat([["transparent", "Dot size: gold traded that day"]])} />
      <Chart deps={[day]} draw={host => curveChart(host, c)} />
    </Card>
    <div className="more-list">
    <More title="Roll-down vs curve move, month by month" hint="What time alone does to GOLDM's price, against everything else">
      <p className="prose sm"><Term k="rolldown">Roll-down</Term>: what time alone does to a futures price on an unchanged curve, from that day's carry. Curve move: everything else, mostly gold itself.</p>
      <Legend items={[["var(--gold)", "Roll-down"], ["var(--teal)", "Curve move"]]} />
      <Chart className="bars" draw={host => groupBars(host, { labels: rd.map(r => r.month), a: rd.map(r => r.rolldown_pct), b: rd.map(r => r.curve_move_pct), yfmt: v => v + "%", short: i => fmon(rd[i].month + "-01").split(" ")[0], aria: "GOLDM monthly roll-down and curve move",
        tip: i => `<div class="t">${fmon(rd[i].month + "-01")} · GOLDM ${fdate(rd[i].expiry)}</div><div class="r"><span>Total change</span><b>${sgn(rd[i].total_pct, 2, "%")}</b></div><div class="r"><span><i style="background:var(--gold)"></i>Roll-down</span><b>${sgn(rd[i].rolldown_pct, 2, "%")}</b></div><div class="r"><span><i style="background:var(--teal)"></i>Curve move</span><b>${sgn(rd[i].curve_move_pct, 2, "%")}</b></div><div class="r"><span>Carry that day</span><b>${rd[i].carry_pa_pct.toFixed(1)}% a year</b></div>` })} />
      <div className="tw mt"><table><thead><tr><th>Contract</th><th className="n">Months</th><th className="n">Roll-down / month</th><th className="n">Curve move / month</th><th className="n">Roll-down share</th></tr></thead>
        <tbody>{D.rolldown.summary.map(r => <tr key={r.symbol}><td><span className="sw" style={{ background: SYM[r.symbol].c }} />{r.symbol}</td><td className="n">{r.months}</td><td className="n">{sgn(r.avg_rolldown_pct, 2, "%")}</td><td className="n">±{r.avg_abs_curve_move_pct.toFixed(2)}%</td><td className="n">{r.rolldown_share_of_abs_change_pct.toFixed(0)}%</td></tr>)}</tbody></table></div>
    </More>
    <More title="How steep the curve has been" hint="Annualised carry across every listed expiry, monthly median">
      <Legend items={ssy.map(x => [SYM[x].c, x])} band />
      <Chart draw={host => lineChart(host, { dates: cs.months.map(m => m + "-15"), series: ssy.map(x => ({ label: x, color: SYM[x].c, values: cs[x] })), band: CRASH, zero: true, endLabels: true, events: false, yfmt: v => v + "%", tfmt: v => v.toFixed(1) + "% a year", aria: "Futures curve slope by month", h: 270 })} />
      <p className="note">All four contract types, fitted separately, steepen together from December 2025 and flatten from July 2026, so this is a market-wide change, not a data quirk. A straight line fits each day's curve to within about 4–5 bp. We have not found the cause of the 2026 steepening.</p>
    </More>
      <More title="Cost of carry by year" hint="Median annualised gap between neighbouring expiries">
        <div className="tw"><table><thead><tr><th>Year</th>{SYMS.map(s => <th key={s} className="n">{s}</th>)}</tr></thead>
          <tbody>{D.carry.map(r => <tr key={r.date}><td className="mono">{r.date}</td>{SYMS.map(s => <td key={s} className="n">{r[s] != null && !isNaN(r[s]) ? r[s].toFixed(2) + "%" : <span className="dim">—</span>}</td>)}</tr>)}</tbody></table></div>
        <p className="note">Measured carry rose from about 4–6% a year (2024–25) to about 10–18% in 2026. The 2026 level is what the data shows; we have not found its cause, and the crash months distort the small contracts most.</p>
      </More>
      <More title="Contracts on the latest curve" hint="Price per pure gram and days to expiry">
        <div className="tw"><table><thead><tr><th>Contract</th><th>Expiry</th><th className="n">Days</th><th className="n">₹ / pure g</th><th className="n">Traded</th></tr></thead>
          <tbody>{D.curves.today.points.slice().sort((a, b) => a.dte - b.dte || a.symbol.localeCompare(b.symbol)).map(p => <tr key={p.symbol + p.expiry}><td><span className="sw" style={{ background: SYM[p.symbol].c }} />{p.symbol}</td><td className="mono">{fdate(p.expiry)}</td><td className="n">{p.dte}</td><td className="n">{p.rs_per_g.toLocaleString("en-IN", { minimumFractionDigits: 1 })}</td><td className="n">{p.kg} kg</td></tr>)}</tbody></table></div>
      </More>
    </div>
  </>;
}

/* ================================================================ BACKTEST */
const BT = {
  A_hold: { name: "A · sealed holdout", desc: "Strategy A: when the gap between two same-expiry small contracts is more than 2 standard deviations from its 10-day average, bet that it returns. 40 g per leg, filled at the next day's settlement price. Sealed holdout, Aug 2025 – May 2026, run once." },
  B_hold: { name: "B · sealed holdout", desc: "Strategy B: fair price of a small contract = GOLDM moved to the same expiry + that contract's usual premium. Trade when it strays more than 1.5 standard deviations. 200 g per leg, filled at the next day's average traded price. Sealed holdout, 6 Aug 2025 – 29 May 2026, run once." },
  A_test: { name: "A · test 1", desc: "Strategy A on its first sealed test, 1 May – 31 Jul 2025. Training before this lost money even before costs (9 trades, gross −₹3,939)." },
  B_dev: { name: "B · development", desc: "Strategy B on the development window, up to 5 Aug 2025. Its setting (k = 1.5) was chosen here, so this is in-sample and flattering by design." }
};
const netAt = (t, s) => t.net0 + (t.net5 - t.net0) * s / 5;
const posText = t => { const [a, b] = t.what.split("-"); return t.side === "long a/short b" ? `buy ${a}, sell ${b}` : t.side === "short a/long b" ? `sell ${a}, buy ${b}` : t.side.replace("X", t.what).replace(" / ", ", "); };

/* Feature: how a typical backtest is reported, against our sealed test. Every figure is from data.json. */
function HonestyGap() {
  const [mode, setMode] = useState("ours");
  const ag = D.backtests.A_hold.rows.find(r => r.slip === 0).gross, a5 = D.backtests.A_hold.rows.find(r => r.slip === 5).net;
  const bg = D.backtests.B_dev.rows.find(r => r.slip === 0).gross, b5 = D.backtests.B_hold.rows.find(r => r.slip === 5).net;
  const typ = mode === "typical", max = Math.max(ag, bg);
  const rows = [
    ["Costs", "Left out", "MCX fee, CTT, stamp duty, SEBI fee, brokerage and GST on all four legs"],
    ["Fills", "Settlement price, no slippage", "5 bp worse on every leg, each side"],
    ["Data", "The window the settings were chosen on", "A sealed window, run once after the rules were frozen in Git"],
    ["Tender period", "Ignored", `Checked: Strategy A's ${D.trades.A_hold.filter(t => !t.ok_tender).length} trades held into it are shown`]
  ];
  const S = [["A", "Strategy A", ag, a5, "sealed holdout before costs (its tuning window lost money)", "sealed holdout, all costs, 5 bp"],
    ["B", "Strategy B", bg, b5, "development window it was tuned on, before costs", "sealed holdout, all costs, 5 bp"]];
  return <Card className={"honest " + mode} title="A typical backtest vs our test" sub="Most reports leave out costs, assume perfect fills and score a strategy on the data it was tuned on. Flip the switch to see what that does to the same two strategies."
    actions={<Seg label="Reporting style" value={mode} onChange={setMode} options={[["typical", "How most teams report"], ["ours", "Our sealed test"]]} />}>
    <div className="hg">
      {S.map(([k, name, g, n, lt, lo]) => { const v = typ ? g : n; return <div key={k} className="hg-s">
        <div className="lab">{name}</div>
        <div className={"hg-v " + (v >= 0 ? "pos" : "neg")}><Num v={v} f="inr" k={"hg" + k} dur={700} /></div>
        <div className="hg-bar"><i style={{ width: (100 * Math.max(0, v) / max).toFixed(1) + "%" }} /></div>
        <div className="note">{typ ? lt : lo}</div>
        {!typ && <div className="hg-cut">{Math.round(100 * (1 - n / g))}% of the typical headline disappears</div>}
      </div>; })}
    </div>
    <div className="tw"><table className="hg-t"><thead><tr><th></th><th className={typ ? "on" : ""}>How most teams report</th><th className={!typ ? "on" : ""}>Our sealed test</th></tr></thead>
      <tbody>{rows.map(r => <tr key={r[0]}><td><b>{r[0]}</b></td><td className={typ ? "on" : "dim"}>{r[1]}</td><td className={!typ ? "on" : "dim"}>{r[2]}</td></tr>)}</tbody></table></div>
  </Card>;
}

/* Round 3: eight more years, sealed and run once (strategy_c.py). Net is linear in slippage, so the slider is exact. */
function SealedTests({ s }) {
  const S = D.sealed; if (!S) return null;
  const at = (st, test) => { const g = sl => S.rows.find(r => r.strategy === st && r.test === test && r.slip === sl), a = g(0), b = g(5), c = g(10);
    if (!a) return null; return { trades: a.trades, net: s <= 5 ? a.net + (b.net - a.net) * s / 5 : b.net + (c.net - b.net) * (s - 5) / 5 }; };
  const ST = [["A", "Strategy A", "pairs, as frozen in 2025"], ["B", "Strategy B", "fair price, as frozen in 2025"], ["C", "Strategy C", "fair price retrained on 2008–15 and 2024–26"]];
  const C = S.c, cell = v => v ? <td className={"n " + (v.net >= 0 ? "pos" : "neg")}>{inr(v.net)}<div className="dim sm">{v.trades} trades</div></td> : <td className="n dim">—</td>;
  return <Card title="Eight more years, sealed" sub={<>Every contract MCX lists for 2016–2023, walled off until the rules were frozen in Git, then run once. Net after all costs at {s.toFixed(1)} bp slippage (use the slider above).</>}>
    <div className="tw"><table className="sealed-t"><thead><tr><th>Strategy</th><th className="n">2016 – 2019</th><th className="n">2020 – 2023</th><th className="n">Both</th><th className="n">95% range at 5 bp</th></tr></thead>
      <tbody>{ST.map(([k, n, d]) => { const a = at(k, "test3"), b = at(k, "test2"), bo = S.boot5[k];
        const both = a && b ? { net: a.net + b.net, trades: a.trades + b.trades } : null;
        return <tr key={k}><td><b>{n}</b><div className="dim sm">{d}</div></td>{cell(a)}{cell(b)}{cell(both)}
          <td className="n dim">{inr(bo.lo)} to {inr(bo.hi)}<div className="sm">{bo.p_pos}% of resamples above zero</div></td></tr>; })}</tbody></table></div>
    <p className="note">Retraining (C) chose a stress filter on {C.years} training years: {inr(C.dev_net5)} at 5 bp, {inr(C.q1_2026)} of it in Q1 2026, against {inr(C.b_dev_net5)} for B's rules on the same days.
      Out of sample it did not beat B. In the March 2020 crash the small contracts moved the other way and the gap widened after entry (Feb–Jun 2020 at 5 bp: B {inr(S.covid.B)}, C {inr(S.covid.C)}).
      Choosing the setting year by year with only earlier years would have made {inr(C.wf_total)} on training data, an early warning that the edge comes in bursts.</p>
  </Card>;
}

export function Backtest() {
  const [key, setKey] = useState("A_hold"), [s, setS] = useState(5), [tonly, setTonly] = useState(false), [filter, setFilter] = useState("All"), [sort, setSort] = useState({ k: "entry", dir: "asc" }), [page, setPage] = useState(0);
  const all = D.trades[key], tr = tonly ? all.filter(t => t.ok_tender) : all, info = D.backtests[key];
  const near = info.rows.reduce((a, r) => Math.abs(r.slip - s) < Math.abs(a.slip - s) ? r : a);
  const inTender = all.length - all.filter(t => t.ok_tender).length;
  const nets = tr.map(t => netAt(t, s)), tot = nets.reduce((a, b) => a + b, 0), hit = nets.filter(v => v > 0).length / nets.length * 100, gross = tr.reduce((a, t) => a + t.gross, 0);
  const gp = tr.reduce((a, t) => a + t.gap_part, 0), gd = tr.reduce((a, t) => a + t.gold_part, 0), ab = Math.abs(gp) + Math.abs(gd) || 1;
  const xs2 = tr.map(t => t.gold_move), mx = xs2.reduce((a, b) => a + b, 0) / xs2.length, my = tot / nets.length;
  const corr = xs2.reduce((a, x, i) => a + (x - mx) * (nets[i] - my), 0) / Math.sqrt(xs2.reduce((a, x) => a + (x - mx) ** 2, 0) * nets.reduce((a, y) => a + (y - my) ** 2, 0) || 1);
  const jan = tr.map((t, i) => t.entry.startsWith("2026-01") ? nets[i] : null).filter(v => v != null), rest = tot - jan.reduce((a, b) => a + b, 0);
  const V = {
    A_hold: <><b>One event.</b> January 2026 alone made {inr(jan.reduce((a, b) => a + b, 0))} from {jan.length} trades; the other {tr.length - jan.length} trades made {inr(rest)}. Outside the crash, this rule loses after costs. {inTender} trades were held 1–3 business days into the <Term k="tender">tender period</Term>, which a broker would not allow; tick “Only trades a broker would allow” below to leave them out.</>,
    B_hold: <><b>Positive, not proven.</b> It earned on GUINEA and PETAL, where a real premium exists, and lost on GOLDTEN, where there is none. With {info.rows[0].weeks} independent weeks the 95% range still includes zero at 5 bp.</>,
    A_test: <><b>Break-even near 3.5 bp.</b> Profitable only with near-perfect fills. Move the slider below 3.5 to see it turn positive.</>,
    B_dev: <><b><Term k="insample">In-sample</Term>.</b> These are the numbers the setting was chosen on, so they overstate. About 80% of the profit came from the swings of 1–15 April 2025.</>
  };
  const cons = ["All", ...new Set(tr.map(t => t.what))], f = cons.includes(filter) ? filter : "All";
  const rows = tr.map((t, i) => ({ ...t, net: nets[i] })).filter(t => f === "All" || t.what === f)
    .sort((a, b) => { const d = sort.dir === "asc" ? 1 : -1; return (typeof a[sort.k] === "number" ? a[sort.k] - b[sort.k] : String(a[sort.k]).localeCompare(String(b[sort.k]))) * d; });
  const PER = 12, pages = Math.max(1, Math.ceil(rows.length / PER)), pg = Math.min(page, pages - 1), shown = rows.slice(pg * PER, pg * PER + PER);
  const sortBy = k => setSort(o => ({ k, dir: o.k === k && o.dir === "asc" ? "desc" : "asc" }));
  const Th = ({ k, l, n }) => <th className={"sort" + (n ? " n" : "")} tabIndex={0} aria-sort={sort.k === k ? (sort.dir === "asc" ? "ascending" : "descending") : "none"} data-dir={sort.k === k ? sort.dir : undefined}
    onClick={() => sortBy(k)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sortBy(k); } }}>{l}</th>;
  const ord = tr.map((t, i) => ({ t, v: nets[i] })).sort((a, b) => a.t.exit.localeCompare(b.t.exit));
  const byDay = {}; ord.forEach(o => byDay[o.t.exit] = (byDay[o.t.exit] || 0) + o.v);
  const days = Object.keys(byDay).sort(); let c = 0; const cum = days.map(d => (c += byDay[d]));
  const bm = {}; tr.forEach((t, i) => { const k = t.entry.slice(0, 7); bm[k] = bm[k] || { v: 0, n: 0 }; bm[k].v += nets[i]; bm[k].n++; }); const mk = Object.keys(bm).sort();
  const csv = () => csvTrades(key, s, rows, tonly, f);
  const pickKey = k => { setKey(k); setFilter("All"); setPage(0); };
  return <>
    <Hero n={5} eyebrow="Backtest" title={<>Can the gaps <span className="hl">be traded?</span></>}>
      Two strategies, tested once on data they never saw, after MCX fees, taxes and <Term k="slippage">slippage</Term>. Move the slider to see how much execution quality decides the result.
    </Hero>
    <Takeaway>{V[key]}</Takeaway>
    <Reveal className="card controls-card">
      <div className="controls">
        <div className="ctl"><div className="lab">Strategy and period</div><Seg label="Strategy and period" value={key} onChange={pickKey} options={Object.entries(BT).map(([k, v]) => [k, v.name])} /></div>
        <label className="toggle"><input type="checkbox" checked={tonly} onChange={e => { setTonly(e.target.checked); setPage(0); }} /><span>Only trades a broker would allow<br /><small>exit before the 5-day <Term k="tender">tender period</Term></small></span></label>
        <div className="slider"><div className="row"><label htmlFor="slip">Slippage per leg, each side</label><b><span>{s.toFixed(1)}</span> bp</b></div>
          <input id="slip" className="range" type="range" min="0" max="10" step="0.5" value={s} onChange={e => setS(+e.target.value)} />
          <div className="row ticks"><span>0 · perfect fills</span><span>5 · realistic</span><span>10 · poor</span></div></div>
      </div>
      <p className="note">{BT[key].desc}</p>
    </Reveal>
    <div className="grid g4">
      <Kpi label="Net profit" note={<>{info.grams} g per leg · <Term k="gross">gross</Term> {inr(gross)}</>}><span className={tot >= 0 ? "pos" : "neg"}><Num v={tot} f="inr" k="bt-net" /></span></Kpi>
      <Kpi label="Trades" note={tonly ? `${inTender} trade${inTender === 1 ? "" : "s"} held into the tender period left out` : `from ${info.rows[0].weeks} independent entry weeks · ${inTender} held into the tender period`}><Num v={tr.length} k="bt-n" /></Kpi>
      <Kpi label="Won after costs" note={`of trades at ${s.toFixed(1)} bp slippage`}><Num v={hit} f="pct" k="bt-hit" /><small>%</small></Kpi>
      <Kpi label={<><Term k="range95">95% range</Term> at {near.slip} bp</>} note={`${near.p_pos}% of resamples above zero${tonly ? " (all trades)" : ""}`}><span className="val-sm"><Num v={near.ci[0]} f="inr" k="bt-lo" /> to <Num v={near.ci[1]} f="inr" k="bt-hi" /></span></Kpi>
    </div>
    <Card title="Cumulative profit" sub="After all costs, at the selected slippage, by exit date."
      actions={<CsvButton text="Download trades" label={`Download all ${rows.length} trade${rows.length === 1 ? "" : "s"} in this view as CSV`} onClick={csv} />}>
        <Chart deps={[key, s, tonly]} draw={host => lineChart(host, { dates: days, series: [{ label: "Cumulative", color: tot >= 0 ? "var(--good)" : "var(--bad)", values: cum }], band: CRASH, zero: true, area: true, yfmt: kfmt, tfmt: v => inr(v), aria: "Cumulative profit", h: 270 })} />
    </Card>
    <HonestyGap />
    <SealedTests s={s} />
    <div className="more-list">
      <More title="Profit by month of entry" hint="Net at the selected slippage">
        <Chart className="bars" deps={[key, s, tonly]} draw={host => barChart(host, { labels: mk.map(fmon), values: mk.map(k => bm[k].v), yfmt: kfmt, tfmt: v => inr(v), short: i => MON[+mk[i].slice(5) - 1], extra: i => `<div class="r"><span>Trades</span><b>${bm[mk[i]].n}</b></div>`, aria: "Profit by month" })} />
      </More>
      <More title="Is it just a bet on gold's direction?" hint="Each trade's profit split exactly into the gap and gold's own move">
        <div className="grid g-main">
          <div style={{ minWidth: 0 }}><p className="prose sm">Each dot is one trade: net profit at the selected slippage against how much gold moved while it was open.</p>
        <Chart deps={[key, s, tonly]} draw={host => scatter(host, { x: xs2, y: nets, color: i => nets[i] >= 0 ? "var(--good)" : "var(--bad)", xfmt: v => v + "%", yfmt: kfmt, xlabel: "gold's move while the trade was open", aria: "Profit per trade against gold's move",
          tip: i => `<div class="t">${tr[i].what.replace(/GOLD/g, "")} · ${fdate(tr[i].entry)} → ${fdate(tr[i].exit)}</div><div class="r"><span>Gold moved</span><b>${sgn(tr[i].gold_move, 2, "%")}</b></div><div class="r"><span>Net</span><b>${inr(nets[i])}</b></div><div class="r"><span>From the gap</span><b>${inr(tr[i].gap_part)}</b></div><div class="r"><span>From gold's move</span><b>${inr(tr[i].gold_part)}</b></div>` })} />
          </div>
          <div>
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div><div className="lab">From the gap</div><div className="bignum" style={{ color: "var(--teal)" }}><Num v={gp} f="inr" k="bt-gp" /></div></div>
          <div><div className="lab">From gold's move</div><div className="bignum" style={{ color: "var(--gold)" }}><Num v={gd} f="inr" k="bt-gd" /></div></div></div>
        <div className="split" aria-hidden="true"><i style={{ width: (100 * Math.abs(gp) / ab).toFixed(1) + "%", background: "var(--teal)" }} /><i style={{ width: (100 * Math.abs(gd) / ab).toFixed(1) + "%", background: "var(--gold)" }} /></div>
        <p className="note">Gold's own move is <b>{(100 * Math.abs(gd) / ab).toFixed(1)}%</b> of the profit swing. Both legs hold the same grams, so gold's move cancels except for the gap still open and GOLDM's 99.5% purity.</p>
        <dl className="kv"><dt>Correlation of net profit with gold's move</dt><dd>{corr.toFixed(2)}</dd><dt>Gross before costs</dt><dd>{inr(gp + gd)}</dd></dl>
        <p className="note">{key === "A_hold" ? "The correlation comes from January 2026, when gold rose about 8% while the gaps widened and closed; outside January it is close to zero. The money came from the gap, not from gold's direction." : "A correlation near zero, or driven by a few large moves, means the strategy is not a disguised bet on gold."}</p>
          </div>
        </div>
      </More>
      <More title={`Trade log · ${rows.length} trade${rows.length === 1 ? "" : "s"}`} hint={`Net at ${s.toFixed(1)} bp. Sort by any column; download as CSV.`}>
        <div className="toolbar"><Seg label="Contract filter" value={f} onChange={v => { setFilter(v); setPage(0); }} options={cons.map(x => [x, x.replace(/GOLD/g, "")])} small /><CsvButton label={`CSV: download all ${rows.length} trade${rows.length === 1 ? "" : "s"} in this view`} onClick={csv} /></div>
      <div className="tw"><table id="bt-log"><thead><tr><Th k="what" l="Contract" /><Th k="expiry" l="Expiry" /><Th k="entry" l="Entry" /><Th k="exit" l="Exit" /><Th k="side" l="Position" /><Th k="days" l="Days" n /><Th k="gold_part" l="Gold part" n /><Th k="gross" l="Gross" n /><Th k="net" l="Net" n /><th>Tender</th></tr></thead>
        <tbody>{shown.map((t, i) => <tr key={t.what + t.entry + i}><td><b>{t.what.replace(/GOLD/g, "")}</b></td><td className="mono">{fdate(t.expiry)}</td><td className="mono">{fdate(t.entry)}</td><td className="mono">{fdate(t.exit)}</td>
          <td className="dim">{t.side.replace("long a/short b", "buy A, sell B").replace("short a/long b", "sell A, buy B")}</td><td className="n">{t.days}</td><td className="n dim">{inr(t.gold_part)}</td><td className="n">{inr(t.gross)}</td>
          <td className={"n " + (t.net >= 0 ? "pos" : "neg")}>{inr(t.net)}</td><td>{t.ok_tender ? <Pill tone="good">Clear</Pill> : <Pill tone="bad" title={`Last safe exit ${fdate(t.safe_exit)}`}>In tender</Pill>}</td></tr>)}</tbody></table></div>
      <Pager page={pg} pages={pages} set={setPage} />
      </More>
      <More title="How we kept the test honest" hint="Rules were committed to Git before the test data existed">
        <ul className="tl">{D.timeline.map(t => <li key={t.commit}><span className="b" /><div><div className="w">{t.when}<span className="c">{t.commit}</span></div><div>{t.what}</div></div></li>)}</ul>
      </More>
      <More title="Costs charged on every leg" hint="Fees, taxes, brokerage and slippage on all four legs">
        <div className="tw"><table><thead><tr><th>Item</th><th>Rate</th><th>Basis</th></tr></thead><tbody>
          {[["MCX transaction fee", "₹2.10 / lakh", "MCX filing, from 1 Oct 2024"], ["Commodity transaction tax", "0.01% sell", "Non-agri futures"], ["Stamp duty", "0.002% buy", "Broker charge sheets"], ["SEBI fee", "₹10 / crore", "Assumption"],
            ["Brokerage", "₹20, max 0.03%", "Discount broker"], ["GST", "18%", "On brokerage and fees"], ["Slippage", "0–10 bp", "Slider above"]].map(r => <tr key={r[0]}><td>{r[0]}</td><td className="mono">{r[1]}</td><td>{r[2]}</td></tr>)}</tbody></table></div>
      </More>
    </div>
  </>;
}

/* ================================================================ SIGNALS */
function Gauge({ z, k }) {
  const pos = Math.max(0, Math.min(100, (z + 3) / 6 * 100));
  const [p, setP] = useState(50);
  useEffect(() => { let b; const a = requestAnimationFrame(() => { b = requestAnimationFrame(() => setP(pos)); }); return () => { cancelAnimationFrame(a); cancelAnimationFrame(b); }; }, [pos]);
  return <div className="gauge" role="img" aria-label={`Distance from usual ${sgn(z, 2)} sigma`}><div className="track" /><div className="thr" style={{ left: (3 - k) / 6 * 100 + "%" }} /><div className="thr" style={{ left: (3 + k) / 6 * 100 + "%" }} /><div className="mid" />
    <div className="needle" style={{ left: p + "%" }} /><div className="ticks"><span>−3σ</span><span>−{k}</span><span>0</span><span>+{k}</span><span>+3σ</span></div></div>;
}
export function Signals() {
  const k = D.signals.threshold, rows = D.signals.rows, hot = rows.filter(r => Math.abs(r.z) >= k);
  const A = D.alerts, h = A.history, base = Object.fromEntries(A.baseline.map(b => [String(b.alert_day), b])), on = base["true"] || base["True"], off = base["false"] || base["False"];
  const all = A.summary.find(x => x.symbol === "All");
  const [f, setF] = useState("All"), [page, setPage] = useState(0);
  const list = h.filter(a => f === "All" || a.symbol === f).slice().reverse(), PER = 10, pages = Math.max(1, Math.ceil(list.length / PER)), pg = Math.min(page, pages - 1);
  const csv = () => csvAlerts(list, f);
  return <>
    <Hero n={6} eyebrow="Signals" title={hot.length ? <>{hot.length} contract{hot.length > 1 ? "s" : ""} <span className="hl">off fair price.</span></> : <>Quiet. <span className="hl">No signal today.</span></>}>
      Each small contract is compared with its fair price: GOLDM moved to the same expiry, plus that contract's usual <Term k="premium">premium</Term>. A signal needs the gap to sit more than {k} <Term k="sigma">standard deviations</Term> from usual, using only past days.
    </Hero>
    <Takeaway>{hot.length ? `${hot.length} contract${hot.length > 1 ? "s are" : " is"} more than ${k}σ from fair price.` : "Every contract is within its normal range, so there is nothing to act on."} When alerts do fire they mark big gaps: a median {on.median_closed_bp_10d.toFixed(0)} bp closes within 10 trading days, against a {on.round_trip_cost_bp_at_5bp.toFixed(0)} bp round-trip cost. Most days the right answer is to wait.</Takeaway>
    <div className="grid g3">{rows.map((r, i) => { const onS = Math.abs(r.z) >= k; return <Reveal key={r.symbol} className="card sig">
      <div className="card-h"><div className="card-t"><h2><span className="sw" style={{ background: SYM[r.symbol].c }} />{r.symbol}</h2><p className="sub">{SYM[r.symbol].d} · expiry {fdate(r.expiry)}</p></div>
        <Pill tone={onS ? "warn" : "good"}>{onS ? (r.z > 0 ? "Rich vs GOLDM" : "Cheap vs GOLDM") : "Normal"}</Pill></div>
      <Gauge z={r.z} k={k} />
      <dl className="kv"><dt>Premium today</dt><dd>{sgn(r.premium_bp)} bp</dd><dt>Usual premium</dt><dd>{sgn(r.usual_bp)} bp</dd><dt>Typical swing (1σ)</dt><dd>{r.sd_bp.toFixed(1)} bp</dd><dt>Distance from usual</dt><dd><b>{sgn(r.z, 2, "σ")}</b></dd></dl>
      <Chart style={{ minHeight: 90, marginTop: 16 }} draw={host => lineChart(host, { dates: r.z_hist.dates, series: [{ label: "Distance", color: SYM[r.symbol].c, values: r.z_hist.z }], zero: true, h: 110, events: false, yfmt: v => v + "σ", tfmt: v => sgn(v, 2, "σ"), aria: "Recent distance from usual premium" })} />
      <p className="note">Last 90 market days to {fdate(r.date)}.</p></Reveal>; })}</div>
    <div className="grid g4">
      <Kpi label="Alert episodes" note={`${fdate(h[0].start)} – ${fdate(h[h.length - 1].start)}`}><Num v={h.length} intro /></Kpi>
      <Kpi label="Closed halfway in 10 days" note={`vs ${off.closed_half_10d.toFixed(0)}% of ordinary days: alerts are not more likely to close`}><Num v={all.closed_half_10d_pct} f="pct" intro /><small>%</small></Kpi>
      <Kpi tone="accent" label="Gap closed in 10 days" note={`median after an alert, vs ${off.median_closed_bp_10d.toFixed(0)} bp on ordinary days`}><Num v={on.median_closed_bp_10d} intro /><small>bp</small></Kpi>
      <Kpi label="Round-trip cost" note={`at 5 bp slippage. Alerts clear it at the median (${on.median_closed_bp_10d.toFixed(0)} bp), barely on average (${on.mean_closed_bp_10d.toFixed(0)} bp)`}><Num v={on.round_trip_cost_bp_at_5bp} intro /><small>bp</small></Kpi>
    </div>
    <Reveal className="dlbar"><div><b>Alert history</b><span className="muted">{h.length} alert episodes since {fdate(h[0].start)}, with what each gap did over the next 20 trading days.</span></div>
      <CsvButton text="Download alerts" label={`Download all ${h.length} alert episodes as CSV`} onClick={() => csvAlerts(h.slice().reverse())} /></Reveal>
    <div className="more-list">
    <More title={`Every alert so far · ${h.length} episodes`} hint="Each dot is one alert, sized by its gap. Green: closed at least halfway within 10 trading days.">
      <div className="legend"><span><i style={{ background: "var(--good)" }} />Closed halfway in 10 days</span><span><i style={{ background: "var(--bad)" }} />Did not</span><span><i style={{ background: "var(--ink-3)" }} />Too recent to judge</span><span><i className="box" />Crash period</span></div>
      <Chart draw={host => alertStrip(host, h)} />
    </More>
    <More title="Alert log" hint="Newest first, premiums in bp above GOLDM per pure gram. Download as CSV.">
      <div className="toolbar"><Seg label="Contract filter" value={f} onChange={v => { setF(v); setPage(0); }} options={["All", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"].map(o => [o, o === "All" ? "All" : o.replace("GOLD", "")])} small />
        <CsvButton label={`CSV: download all ${list.length} alert episode${list.length === 1 ? "" : "s"} in this view`} onClick={csv} /></div>
      <div className="tw"><table id="sg-log"><thead><tr><th>Started</th><th>Contract</th><th>Signal</th><th className="n">Days</th><th className="n">Distance</th><th className="n">Premium</th><th className="n">Usual</th><th className="n">After 10 days</th><th>Outcome</th></tr></thead>
        <tbody>{list.slice(pg * PER, pg * PER + PER).map(a => <tr key={a.symbol + a.start}><td className="mono">{fdate(a.start)}</td><td className="nowrap"><span className="sw" style={{ background: SYM[a.symbol].c }} />{a.symbol}</td><td>{a.direction}</td><td className="n">{a.alert_days}</td><td className="n">{sgn(a.z, 2, "σ")}</td>
          <td className="n">{sgn(a.premium_bp, 0)}</td><td className="n">{sgn(a.usual_bp, 0)}</td><td className="n">{a.prem_10d == null || !isFinite(a.prem_10d) ? "—" : sgn(a.prem_10d, 0)}</td>
          <td>{a.closed_half_10d === true ? <Pill tone="good">Closed halfway, day {a.days_to_half}</Pill> : a.closed_half_10d === false ? <Pill tone="bad">Did not close</Pill> : <Pill>Too recent</Pill>}</td></tr>)}</tbody></table></div>
      <Pager page={pg} pages={pages} set={setPage} prev="← Newer" next="Older →" />
    </More>
    <More title="Why quiet is the right answer most days" hint="What the alert record and the sealed test show">
      <p className="prose"><b>What the alert record shows.</b> An alert does not make the gap more likely to close, but it marks the large gaps: after an alert the gap closed a median of about {on.median_closed_bp_10d.toFixed(0)} bp in 10 trading days, against {off.median_closed_bp_10d.toFixed(0)} bp on ordinary days, and a round trip costs about {on.round_trip_cost_bp_at_5bp.toFixed(0)} bp. So alerts are worth a look, and quiet days are rightly quiet. <b>Why quiet is the right answer most days.</b> In our sealed test, quiet-month signals lost money after costs. The gap paid only during sharp gold sell-offs, when GOLDM moved first and the small contracts lagged. We then trained a stress filter for exactly that case on 2008–2015 and 2024–26. On the sealed 2016–2023 data it did not beat the plain rule: in the March 2020 crash the gap kept widening after entry.</p>
    </More>
    </div>
  </>;
}

/* ================================================================ CONTRACTS */
export function Calendar() {
  const { calF, setCalF } = useApp(); const [calT, setCalT] = useState("A_hold");
  const cs = D.contracts.filter(c => calF === "All" || c.symbol === calF).sort((a, b) => SYMS.indexOf(a.symbol) - SYMS.indexOf(b.symbol) || a.expiry.localeCompare(b.expiry));
  const L = Object.fromEntries(D.lifecycle_summary.map(a => [a.run, a])), nm = { A_test: "A · test 1", A_hold: "A · sealed holdout", B_dev: "B · development", B_hold: "B · sealed holdout" };
  return <>
    <Hero n={7} eyebrow="Contract calendar" title={<>Every contract <span className="hl">we hold.</span></>}>
      Each bar is one contract from the first to the last day in our files. GOLDM expires around the 5th; the others at month end. Hover a bar for its liquidity.
    </Hero>
    <Takeaway>{D.meta.contracts} contracts, each tracked from listing to expiry. Strategy B always closed before the delivery (tender) period; Strategy A held {L.A_hold.trades - L.A_hold.outside_tender} of {L.A_hold.trades} holdout trades into it, which a broker would not allow. Leaving those out, A still made {inr(L.A_hold.net_outside_tender_only)} at 5 bp.</Takeaway>
    <Card title={`${cs.length} contracts`} sub={<>The darker end of each bar is the 5-business-day <Term k="tender">tender period</Term>, when positions must already be closed. Shaded band: Dec 2025 – Mar 2026 crash.</>}
      actions={<div className="stack-r"><Seg label="Contract type" value={calF} onChange={setCalF} options={["All", ...SYMS].map(s => [s, s === "All" ? "All" : s.replace("GOLD", "") || "M"])} small />
        <Seg label="Trades shown" value={calT} onChange={setCalT} options={[["none", "No trades"], ["A_hold", "Strategy A trades"], ["B_hold", "Strategy B trades"]]} small /></div>}>
      <div className="legend"><span><i style={{ background: "var(--ink)", opacity: .55 }} />Tender period</span>{calT !== "none" && <><span><i style={{ background: "var(--good)" }} />Trade, profit</span><span><i style={{ background: "var(--bad)" }} />Trade, loss</span><span><i className="ring" />Exit inside tender period</span></>}<span><i className="box" />Crash period</span></div>
      <Chart deps={[calF, calT]} draw={host => calendarChart(host, cs, calF, calT)} />
    </Card>
    <div className="more-list">
      <More title="How liquidity builds over a contract's life" hint="Median gold traded per day, by business days left to expiry">
        <Legend items={SYMS.map(sy => [SYM[sy].c, sy]).concat([["var(--line-2)", "Shaded: tender period"]])} />
        <Chart draw={host => liquidityChart(host)} />
      </More>
      <More title="Every trade checked against its contract" hint="Entry after listing, exit before the tender period">
        <div className="tw"><table><thead><tr><th>Run</th><th className="n">Trades</th><th className="n">After listing</th><th className="n">Clear of tender</th><th className="n">Net, all</th><th className="n">Net, allowed</th></tr></thead>
          <tbody>{["A_test", "A_hold", "B_dev", "B_hold"].map(k => { const a = L[k]; return <tr key={k}><td><b>{nm[k]}</b></td><td className="n">{a.trades}</td><td className="n">{a.inside_life}</td><td className={"n " + (a.outside_tender < a.trades ? "neg" : "pos")}>{a.outside_tender}</td><td className="n">{inr(a.net_all)}</td><td className="n">{inr(a.net_outside_tender_only)}</td></tr>; })}</tbody></table></div>
        <p className="note">Strategy A's force-exit was 3 calendar days before expiry, which can fall inside MCX's 5-business-day tender period. Strategy B exits 5 business days before expiry and is always clear. Net at 5 bp slippage.</p>
      </More>
    </div>
  </>;
}

/* ================================================================ DATA QUALITY */
export function Quality() {
  const [f, setF] = useState("All"); const integ = D.integrity, kinds = ["All", ...new Set(D.flags.map(x => x.kind))];
  return <>
    <Hero n={8} eyebrow="Data quality" title={<>Checked before <span className="hl">it is trusted.</span></>}>
      Every MCX <Term k="bhavcopy">Bhavcopy</Term> file is identified by its contents, duplicates are dropped, and every row passes these checks before any number on this site is computed.
    </Hero>
    <Takeaway>Every row passed the checks: 0 unexplained errors in {D.meta.rows.toLocaleString("en-IN")} rows. Of the {D.flags.length} flagged rows, {D.flags.filter(x => x.kind === "Previous close mismatch").length} follow a no-trade day and are left out; {D.flags.filter(x => x.kind === "Far from peers").length} are real prices far from their peers, mostly in the January 2026 crash, and are kept. No price was changed.</Takeaway>
    <div className="grid g4">
      <Kpi label="Files read" note={`MCX Bhavcopy downloads, deduplicated. ${D.meta.sealed_contracts} sealed-test contracts, read only in the one sealed run.`}><Num v={D.meta.files} intro /></Kpi>
      <Kpi label="Contracts" note={`${fdate(D.meta.first)} – ${fdate(D.meta.last)}`}><Num v={D.meta.contracts} intro /></Kpi>
      <Kpi label="Rows checked" note="One row per contract per trading day"><Num v={D.meta.rows} intro /></Kpi>
      <Kpi tone="accent" label="Unexplained errors" note={`${D.flags.length} rows flagged, each explained below`}>0</Kpi>
    </div>
    <div className="more-list">
      <More title="Integrity checks" hint="Share of rows failing each check">
        <div className="tw"><table><thead><tr><th>Check</th><th className="n">Failing</th><th>Status</th></tr></thead>
          <tbody>{integ.map(r => { const sub = r.check.trim().startsWith("..."), ok = r.errors === 0;
            return <tr key={r.check}><td style={sub ? { paddingLeft: 28, color: "var(--ink-2)" } : undefined}>{r.check.replace(/^\s*\.\.\./, "")}</td><td className="n">{r.error_rate.toFixed(2)}% <span className="dim">({r.errors})</span></td>
              <td>{ok ? <Pill tone="good">Pass</Pill> : r.check.includes("peers") || r.check.includes("median") ? <Pill tone="warn">Real prices</Pill> : <Pill>Explained</Pill>}</td></tr>; })}</tbody></table></div>
      </More>
      <More title="Official close vs real trades" hint="Gap between the settlement price and the day's average traded price (VWAP)">
        <div className="tw"><table><thead><tr><th>Measure</th><th className="n">Typical</th><th className="n">90% of days</th></tr></thead>
          <tbody>{D.close_vs_vwap.map(r => <tr key={r.symbol}><td>{r.symbol.startsWith("spread") ? <b>Gap {r.symbol.replace("spread ", "").replace("-", " − ")}</b> : r.symbol}</td><td className="n">{r.median_abs_gap_bp.toFixed(1)} bp</td><td className="n">{r.p90_abs_gap_bp.toFixed(1)} bp</td></tr>)}</tbody></table></div>
        <p className="note">The gap between two contracts is what a spread trade pays. A typical 7–8 bp there is why 5 bp per leg is our realistic slippage.</p>
      </More>
      <More title="Each contract type" hint="Liquidity decides how far a price can be trusted">
      <div className="tw"><table><thead><tr><th>Contract</th><th className="n">Contracts</th><th className="n">Days</th><th className="n">No-trade days</th><th className="n">Gold traded / day</th><th className="n">Close vs trades</th></tr></thead>
        <tbody>{D.per_contract.map(r => <tr key={r.symbol}><td><span className="sw" style={{ background: SYM[r.symbol].c }} /><b>{r.symbol}</b> <span className="dim">{SYM[r.symbol].d}</span></td><td className="n">{r.contracts}</td><td className="n">{r.rows.toLocaleString("en-IN")}</td><td className="n">{r.no_trade_pct.toFixed(2)}%</td><td className="n">{r.median_kg_traded_per_day.toLocaleString("en-IN")} kg</td><td className="n">{r.close_vs_vwap_median_bp.toFixed(1)} bp</td></tr>)}</tbody></table></div>
      </More>
      <More title={`Flagged rows · ${D.flags.length}`} hint="Every row a check flagged, and what we did with it">
      <div className="toolbar"><Seg label="Flag type" value={f} onChange={setF} options={kinds.map(x => [x, `${x} ${x === "All" ? D.flags.length : D.flags.filter(y => y.kind === x).length}`])} small /></div>
      <div className="tw"><table><thead><tr><th>Date</th><th>Contract</th><th>Check</th><th>Detail</th><th>What we did</th></tr></thead>
        <tbody>{D.flags.filter(x => f === "All" || x.kind === f).map((x, i) => <tr key={i}><td className="mono">{fdate(x.date)}</td><td className="nowrap"><span className="sw" style={{ background: SYM[x.symbol].c }} />{x.symbol} <span className="dim">{fmon(x.expiry)}</span></td>
          <td><Pill tone={x.kind.startsWith("Far") ? "warn" : "neutral"}>{x.kind}</Pill></td><td className="dim">{x.detail}</td><td>{x.action}</td></tr>)}</tbody></table></div>
      </More>
    </div>
  </>;
}

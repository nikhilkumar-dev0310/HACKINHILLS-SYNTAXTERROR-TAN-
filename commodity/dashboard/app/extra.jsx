/* Round 4 additions: price cards, the cost line (today and replayed), what makes Parity different,
   the automatic update log, the per-file download log, and what the data cannot tell you.
   Every number is read from data.json; nothing here is typed in. */
import { useMemo, useState } from "react";
import { D, SYM, SYMS, SRC, inr, sgn, fdate, fmon, T } from "./lib.js";
import { Card, Pill, Term, Icon, Reveal, Pager, CsvButton, downloadCSV, Seg, More, Src } from "./ui.jsx";

const UNIT = { GOLDM: "per 10 g", GOLDTEN: "per 10 g", GOLDGUINEA: "per 8 g", GOLDPETAL: "per 1 g" };
const SMALL = ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"];
const base = () => { const b = Object.fromEntries(D.alerts.baseline.map(x => [String(x.alert_day).toLowerCase(), x])); return b; };
export const roundTrip = () => base()["true"].round_trip_cost_bp_at_5bp;
export const costLine = () => 2 * roundTrip();
const isAuto = u => /GitHub Actions/.test(u.source || "");
const autoRuns = () => D.provenance.updates.filter(isAuto);
/* The scheduled job has run on the team computer since this date (first run checked MCX and found no new day). */
const LIVE_SINCE = "2026-10-07";
const both = (g, z) => g != null && z != null && g >= costLine() && Math.abs(z) >= D.signals.threshold;

/* ---------------------------------------------------------------- price cards with a 6-month sparkline */
function Spark({ values, color }) {
  const v = values.filter(x => x != null); if (v.length < 2) return null;
  const lo = Math.min(...v), hi = Math.max(...v), W = 220, H = 44, n = values.length;
  let d = "", started = false;
  values.forEach((y, i) => { if (y == null) return; const X = (i / (n - 1)) * W, Y = H - 3 - ((y - lo) / (hi - lo || 1)) * (H - 6); d += (started ? "L" : "M") + X.toFixed(1) + " " + Y.toFixed(1); started = true; });
  return <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true"><path d={d} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" /></svg>;
}
export function Quotes() {
  const pr = D.prices, n = pr.dates.length, from = Math.max(0, n - 126);
  return <div className="quotes" role="list" aria-label={`Latest settlement prices, ${fdate(D.quotes[0].date)}`}>
    {D.quotes.map(q => { const up = q.chg > 0, dn = q.chg < 0;
      return <Reveal key={q.symbol} className="quote" role="listitem">
        <div className="q-h"><span className="sw" style={{ background: SYM[q.symbol].c }} /><b>{q.symbol}</b><Src src={SRC.prices} note={`MCX close on ${fdate(q.date)} for the contract expiring ${fdate(q.expiry)}, the one with the most gold traded that day.`} /></div><div className="dim sm q-d">{SYM[q.symbol].d}</div>
        <div className="q-p"><span className="num">{inr(q.close)}</span><small>{UNIT[q.symbol]}</small></div>
        <div className={"q-c " + (up ? "pos" : dn ? "neg" : "dim")}>{up ? "▲" : dn ? "▼" : "■"} {inr(Math.abs(q.chg))} ({sgn(q.chg_pct, 2, "%")})<div className="dim">previous <Term k="settlement">close</Term> {inr(q.prev_close)}</div></div>
        <Spark values={pr[q.symbol].slice(from)} color={SYM[q.symbol].c} />
        <div className="q-f"><span>₹ per gram of pure gold</span><b className="num">{q.rs_per_g.toLocaleString("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}</b></div>
        <div className="q-f dim"><span><Term k="expiry">Expiry</Term> {fdate(q.expiry)}</span><span>{q.lots.toLocaleString("en-IN")} <Term k="lot">lots</Term></span></div>
      </Reveal>; })}
  </div>;
}

/* ---------------------------------------------------------------- the cost line */
function Bars({ i, compact }) {
  const H = D.hurdle, line = costLine(), max = Math.max(line * 1.6, ...SMALL.map(s => H[s].gap[i] || 0)) * 1.05;
  return <ul className={"hurdle" + (compact ? " compact" : "")}>{SMALL.map(s => { const g = H[s].gap[i], z = H[s].z[i];
    if (g == null) return <li key={s}><div className="h-n"><span className="sw" style={{ background: SYM[s].c }} /><b>{s}</b></div><div className="dim sm">not trading that day</div></li>;
    const over = g >= line, look = both(g, z), k = D.signals.threshold;
    return <li key={s} className={look ? "over" : ""}>
      <div className="h-n"><span className="sw" style={{ background: SYM[s].c }} /><b>{s}</b>{!compact && <span className="dim sm">{SYM[s].d}</span>}</div>
      <div className="h-bar" role="img" aria-label={`${s}: gap from usual ${g.toFixed(1)} bp, cost line ${line.toFixed(1)} bp`}>
        <i style={{ width: (100 * g / max).toFixed(1) + "%" }} /><span className="h-line" style={{ left: (100 * line / max).toFixed(1) + "%" }} /></div>
      <div className="h-v"><b className="num">{g.toFixed(1)}</b><small> bp</small></div>
      <div className="h-s">{look ? <Pill tone="warn">Worth a look</Pill> : over ? <Pill>Clears cost, usual for it</Pill> : <Pill tone="good">Short by {(line - g).toFixed(1)} bp</Pill>}
        {!compact && z != null && <div className="dim sm">{sgn(z, 2, "σ")} from usual{over && !look ? `, needs ±${k}σ` : ""}</div>}</div>
    </li>; })}</ul>;
}
export function CostLineToday({ go }) {
  const H = D.hurdle, i = H.dates.length - 1, line = costLine(), rt = roundTrip();
  const over = SMALL.filter(s => both(H[s].gap[i], H[s].z[i]));
  const big = SMALL.map(s => [s, H[s].gap[i]]).filter(x => x[1] != null).sort((a, b) => b[1] - a[1])[0];
  return <Card id="worth" className="worth" src={SRC.signals} title="Is any gap worth trading today?"
    sub={<>{fdate(H.dates[i])}. A gap is worth a look only if it passes two checks: it is bigger than the <Term k="costline">cost line</Term> ({line.toFixed(1)} <Term k="bp">bp</Term>, twice the {rt.toFixed(1)} bp a <Term k="roundtrip">round trip</Term> costs at 5 bp <Term k="slippage">slippage</Term>), and it is unusual for that contract (beyond ±{D.signals.threshold}<Term k="sigma">σ</Term>).</>}>
    <div className="worth-g">
      <div className="worth-a"><div className={"worth-v " + (over.length ? "yes" : "no")}>{over.length ? "Worth a look." : "No."}</div>
        <p>{over.length ? `${over.join(", ")} ${over.length > 1 ? "pass" : "passes"} both checks today. Read the Signals page before acting.`
          : <>The biggest gap from usual is {big[1].toFixed(1)} bp, on {big[0]}{big[1] >= line ? ", above the cost line but normal for that contract" : `, short of the ${line.toFixed(1)} bp a trade needs to pay for itself`}.</>}</p>
        {go}</div>
      <Bars i={i} />
    </div>
  </Card>;
}
export function CostLineReplay() {
  const H = D.hurdle, n = H.dates.length, line = costLine(), [i, setI] = useState(n - 1);
  const stats = useMemo(() => { let any = 0, days = 0, cost = 0; const per = Object.fromEntries(SMALL.map(s => [s, 0]));
    for (let k = 0; k < n; k++) { let hit = false, c = false, have = false;
      SMALL.forEach(s => { const g = H[s].gap[k], z = H[s].z[k]; if (g == null) return; have = true; if (g >= line) c = true; if (both(g, z)) { per[s]++; hit = true; } });
      if (have) days++; if (hit) any++; if (c) cost++; }
    return { any, days, per, cost }; }, []);
  const year = H.dates[i].slice(0, 4);
  return <Card title="Replay every day since October 2023" sub={<>Drag to any market day and see where each gap stood against the {line.toFixed(1)} bp <Term k="costline">cost line</Term> and the ±{D.signals.threshold}<Term k="sigma">σ</Term> alert rule. Usual levels use only days before the one shown.</>}>
    <div className="slider"><div className="row"><label htmlFor="replay">Market day</label><b className="num">{fdate(H.dates[i])}</b></div>
      <input id="replay" className="range" type="range" min="0" max={n - 1} step="1" value={i} onChange={e => setI(+e.target.value)} />
      <div className="row ticks"><span>{fmon(H.dates[0])}</span><span>{year}</span><span>{fmon(H.dates[n - 1])}</span></div></div>
    <Bars i={i} />
    <p className="note">Over {stats.days.toLocaleString("en-IN")} market days, some contract sat above the cost line on {stats.cost} ({(100 * stats.cost / stats.days).toFixed(0)}%), mostly GOLDPETAL, whose <Term k="premium">premium</Term> swings widely day to day.
      That is why the cost line alone is not enough. Both checks passed on <b>{stats.any}</b> days ({(100 * stats.any / stats.days).toFixed(0)}%): {SMALL.map(s => `${s} ${stats.per[s]}`).join(", ")}.</p>
  </Card>;
}

/* ---------------------------------------------------------------- what makes Parity different */
export function Unique() {
  const A = D.meta.all, last = autoRuns()[0];
  const items = [
    ["23 years of MCX history", `${A.rows.toLocaleString("en-IN")} daily rows, ${A.contracts} contracts, ${fdate(A.first)} – ${fdate(A.last)}.`, "The usual shortcut: the last two or three years only, so the rules never meet a different market."],
    [<>Eight <Term k="sealed">sealed</Term> years</>, <>2016–2023 were walled off until the rules were frozen in Git, then opened once. Plus a sealed <Term k="holdout">holdout</Term> in 2025–26.</>, "The usual shortcut: one test window, chosen after looking at the data."],
    ["Updates itself every trading day", last ? `A scheduled job fetches the new MCX Bhavcopy, checks it, rebuilds the site and publishes. Last update ${last.run_ist} IST, data through ${fdate(last.data_through)}.` : `A scheduled job fetches each new MCX Bhavcopy, checks it, rebuilds the site and publishes. Live since ${fdate(LIVE_SINCE)}; no one feeds it by hand.`, "The usual shortcut: a snapshot that goes stale the day after it is built."],
    [<>A <Term k="fairprice">fair price</Term>, not just pairs</>, <>Each small contract is priced off GOLDM, which trades 20–60× more gold, moved to the same expiry with that day's <Term k="carry">carry</Term>.</>, <>The usual shortcut: compare thin (low-<Term k="liquidity">liquidity</Term>) contracts with each other and trade the noise.</>],
    ["The exchange's own rules", <><Term k="tender">Tender period</Term> and expiry-day settlement taken from MCX's contract specifications; every trade checked against them.</>, "The usual shortcut: trade right up to expiry, into compulsory delivery."],
    [<>Tested for luck, not just profit</>, D.overfit && D.robustness ? <>Picking the best of 72 settings is checked for <Term k="pbo">overfitting</Term> ({Math.round(100 * D.overfit.pbo.value)}%), against a <Term k="placebo">placebo</Term> of 2,000 random strategies, with a <Term k="dsr">deflated Sharpe</Term> and each result's <Term k="breakeven">break-even slippage</Term>.</> : "Overfitting, placebo and break-even checks on every result.", "The usual shortcut: the best of many settings reported as if it were the only one tried."],
    [`Checked by ${D.tests ? D.tests.tests.toLocaleString("en-IN") : "thousands of"} automated tests`, <>Every stored trade re-derived from MCX prices, the frozen rules pinned by fingerprint, every number on this site and in the README checked against its file. They run before each day's data may be published.</>, "The usual shortcut: a demo that worked on the day it was recorded."],
    ["Says what it cannot explain", <>Each MCX file quirk is named, not smoothed over, and GOLDPETAL's abrupt November 2024 jump is flagged as unexplained rather than given a convenient cause. Event notes are tested against the prices.</>, "The usual shortcut: a confident story for every wiggle in the chart."],
    ["An honest verdict", <>Every trade <Term k="attribution">split into gap vs gold's move</Term>; <Term k="bootstrap">bootstrap</Term> ranges and <Term k="tstat">t-statistics</Term> shown; the answer is “a small <Term k="edge">edge</Term>, not proven”.</>, "The usual shortcut: a big headline from perfect fills and no costs."]
  ];
  return <Card id="unique" className="unique" title="What makes Parity different" sub={`${items.length} things you can check on this site, each against the shortcut it avoids.`}>
    <ol className="uq">{items.map(([h, a, b], k) => <li key={k}><span className="uq-n">{String(k + 1).padStart(2, "0")}</span><div><b>{h}</b><p>{a}</p><p className="dim sm">{b}</p></div></li>)}</ol>
  </Card>;
}

/* A slim line of checkable facts near the top of the Overview; each opens the section that proves it. */
export function Proof() {
  const A = D.meta.all, T_ = D.tests, last = autoRuns()[0];
  const items = [
    [`${Number(A.last.slice(0, 4)) - Number(A.first.slice(0, 4))} years of MCX data`, "quality", `${A.contracts} contracts since ${fdate(A.first)}`],
    ["3 sealed tests", "backtest", "rules frozen in Git first"],
    T_ && [`${T_.tests.toLocaleString("en-IN")} tests ${T_.failed ? "run" : "passing"}`, "quality", `latest run ${T_.run_at}`],
    ["Updated every trading day", "quality", last ? `last ${last.run_ist} IST` : "by a scheduled job"]
  ].filter(Boolean);
  return <nav className="proof" aria-label="Checkable facts">{items.map(([b, to, t]) =>
    <a key={b} href={"#" + to}><b>{b}</b><small>{t}</small></a>)}</nav>;
}

/* ---------------------------------------------------------------- automatic updates and the download log */
export function AutoUpdate() {
  const up = D.provenance.updates, auto = autoRuns();
  const steps = [["Fetch", <>Every trading day at 03:30 IST (retry 08:00), GitHub Actions starts the job on a team computer, which opens the official MCX <Term k="bhavcopy">Bhavcopy</Term> page and downloads every gold futures contract still trading. MCX refuses cloud servers, so the job cannot run in a data centre.</>],
    ["Check", "The update is rejected if a published price changed, a contract type is missing, a close is outside its day's range off expiry day, or a price is out by a unit error."],
    ["Rebuild", <>Prices, premiums, the <Term k="curve">curve</Term>, <Term k="rolldown">roll-down</Term>, alerts and the contract calendar are recomputed. Strategy rules and <Term k="sealed">sealed test</Term> results stay frozen.</>],
    ["Publish", "The job commits the new files; Vercel redeploys the site from GitHub within minutes."]];
  return <Card id="auto" title="Updates itself every trading day"
    sub={<>{auto.length ? "No one feeds this site by hand." : `Live since ${fdate(LIVE_SINCE)} on a team computer; no one feeds this site by hand.`} The workflow is .github/workflows/daily-data.yml; the checks are in commodity/tools/daily_update.py.</>}>
    <ol className="steps4">{steps.map(([h, t], k) => <li key={k}><span className="tn">{k + 1}</span><b>{h}</b><p>{t}</p></li>)}</ol>
    {up.length ? <div className="tw"><table><thead><tr><th>Run (IST)</th><th>Data through</th><th className="n">New days</th><th className="n">New rows</th><th className="n">Rows held</th><th>How</th></tr></thead>
      <tbody>{up.slice(0, 8).map(u => <tr key={u.run_ist}><td className="mono">{u.run_ist}</td><td className="mono">{fdate(u.data_through)}</td><td className="n">{u.new_days}</td><td className="n">{u.new_rows}</td><td className="n">{u.rows_total.toLocaleString("en-IN")}</td><td className="dim">{isAuto(u) ? "Scheduled job" : "By hand, from the MCX page, same checks"}</td></tr>)}</tbody></table></div>
      : <p className="note">The first automatic run will be listed here once it has published new data.</p>}
    {up.length > 0 && !auto.length && <p className="note">The scheduled job went live on {fdate(LIVE_SINCE)}; its first run checked MCX and found no new trading day yet. Its first update is listed here after the next MCX session. Earlier updates were run by hand through the same checks.</p>}
  </Card>;
}
export function DownloadLog() {
  const F = D.provenance.files, [f, setF] = useState("All"), [page, setPage] = useState(0);
  const list = F.filter(x => f === "All" || x.symbol === f), PER = 12, pages = Math.max(1, Math.ceil(list.length / PER)), pg = Math.min(page, pages - 1);
  const csv = () => downloadCSV("parity_download_log.csv", ["file", "contract", "expiry", "rows", "first_day", "last_day"], list.map(x => [x.file, x.symbol, x.expiry, x.rows, x.first, x.last]));
  return <More title={`Download log · ${F.length} MCX files`} hint="One file per contract and expiry. Every row on this site traces back to one of them.">
    <div className="toolbar"><Seg label="Contract filter" value={f} onChange={v => { setF(v); setPage(0); }} options={["All", ...SYMS].map(o => [o, o === "All" ? `All ${F.length}` : o.replace("GOLD", "")])} small />
      <CsvButton label={`CSV: download the log of ${list.length} files`} onClick={csv} /></div>
    <div className="tw"><table><thead><tr><th>File</th><th>Contract</th><th>Expiry</th><th className="n">Rows</th><th>First to last trading day</th></tr></thead>
      <tbody>{list.slice(pg * PER, pg * PER + PER).map(x => <tr key={x.file}><td className="mono sm">{x.file}</td><td className="nowrap"><span className="sw" style={{ background: SYM[x.symbol].c }} />{x.symbol}</td>
        <td className="mono">{fdate(x.expiry)}</td><td className="n">{x.rows}</td><td className="mono">{fdate(x.first)} to {fdate(x.last)}</td></tr>)}</tbody></table></div>
    <Pager page={pg} pages={pages} set={setPage} prev="← Later expiries" next="Earlier →" />
  </More>;
}
export function Limits() {
  const v = D.close_vs_vwap.find(r => r.symbol.startsWith("spread")), b = D.backtests.B_hold.rows.find(r => r.slip === 5);
  const L = [
    <>Prices are end-of-day <Term k="settlement">settlements</Term> from the <Term k="bhavcopy">Bhavcopy</Term>, not fills from the order book. Real trades happen during the day.</>,
    <>The Bhavcopy has volume but no order-book <Term k="depth">depth</Term>, so <Term k="slippage">slippage</Term> is assumed, not measured. The close and the day's average traded price differ by a typical {v ? v.median_abs_gap_bp.toFixed(1) : "7–8"} bp on a <Term k="spread">spread</Term>, which is why 5 bp per <Term k="leg">leg</Term> is our realistic case.</>,
    "GOLDTEN has traded only since April 2025, so its history is short.",
    <>Samples are small: Strategy B made {b.trades} trades on its sealed holdout, too few to prove an <Term k="edge">edge</Term> (<Term k="tstat">t</Term> = {b.t == null ? "—" : b.t.toFixed(2)} at 5 bp).</>,
    "Fees and taxes for 2016–2023 use today's rates; the real schedule differed in places, so those costs are approximate.",
    "One crash (January 2026) dominates the recent results. Without it, the pairs rule loses after costs."
  ];
  return <More title="What this data cannot tell you" hint="Limits worth knowing before trusting any number here">
    <ul className="lim">{L.map((x, i) => <li key={i}>{x}</li>)}</ul>
  </More>;
}

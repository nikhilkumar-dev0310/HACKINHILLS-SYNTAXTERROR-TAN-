import { Component, useEffect, useLayoutEffect, useMemo, useRef, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import { D, NAME, VIEWS, SYMS, SYM, EVENTS, GLOSSARY, fdate, pname, reducedMotion } from "./lib.js";
import { AppCtx, Icon } from "./ui.jsx";
import { useSmoothScroll, useMagnetic } from "./motion.js";

/* The Equal Ingot: two gold bars as an equals sign. When a contract is off fair price today, the lower bar steps right. */
const HOT = D.signals.rows.filter(r => Math.abs(r.z) >= D.signals.threshold).length;
function Mark() {
  return <span className={"mark" + (HOT ? " hot" : "")} title={HOT ? `${HOT} contract${HOT > 1 ? "s" : ""} off fair price today` : undefined}>
    <svg viewBox="9 11 32 26" width="30" height="24" aria-hidden="true">
      <path className="bar" d="M14 13h20l3.2 8.6H10.8z" />
      <path className="bar lo" d="M14 26.4h20l3.2 8.6H10.8z" />
    </svg></span>;
}
import { Overview, Brief, Relative, Term_, Backtest, Signals, Calendar, Quality } from "./views.jsx";

const PAGES = { overview: Overview, brief: Brief, relative: Relative, term: Term_, backtest: Backtest, signals: Signals, calendar: Calendar, quality: Quality };
const TABS = ["overview", "brief", "backtest", "signals"];
const store = { get: (k, d) => { try { return localStorage.getItem(k) ?? d; } catch (e) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} } };
const label = id => (VIEWS.find(v => v[0] === id) || VIEWS[0])[1];
const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

/* ---------- theme */
function useTheme() {
  const [t, setT] = useState(() => store.get("parity-theme", store.get("gsl-theme", "system")));
  useLayoutEffect(() => { const r = document.documentElement; t === "system" ? r.removeAttribute("data-theme") : r.setAttribute("data-theme", t); store.set("parity-theme", t); }, [t]);
  // like the macOS appearance change: the whole page cross-fades to the new theme (where the browser supports it)
  const setSmooth = v => {
    const go = () => flushSync(() => setT(v));
    if (document.startViewTransition && !matchMedia("(prefers-reduced-motion: reduce)").matches) document.startViewTransition(go); else go();
  };
  return [t, setSmooth];
}
function ThemeSwitch({ theme, setTheme }) {
  return <div className="theme" role="group" aria-label="Colour theme">
    {[["light", "sun", "Light theme"], ["system", "auto", "Auto theme, follows your device"], ["dark", "moon", "Dark theme"]].map(([v, ic, l]) =>
      <button key={v} type="button" aria-pressed={theme === v} aria-label={l} title={l} onClick={() => setTheme(v)}><Icon name={ic} size={15} sw={1.8} /></button>)}
  </div>;
}

/* ---------- command menu (⌘K / Ctrl+K) */
function buildItems(go, ctx) {
  const it = [];
  const KW = { overview: "summary home start answer premium prices", brief: "problem statement requirements checklist judges", relative: "pairs gap spread cheap expensive premium",
    term: "curve carry expiry roll-down slope", backtest: "profit strategy trades costs slippage csv results honest typical", signals: "alerts alert today fair price signal z sigma",
    calendar: "contracts expiry listing tender liquidity calendar", quality: "data checks errors flags integrity vwap files" };
  VIEWS.forEach(([id, l], i) => it.push({ id: "v" + id, group: "Sections", title: l, hint: String(i + 1), keys: "page section " + id + " " + KW[id], icon: id, run: () => go(id) }));
  D.pairs.forEach(p => it.push({ id: "p" + p.pair, group: "Pairs", title: pname(p.pair), hint: "Relative value", keys: "pair gap spread " + p.pair.replace("M-", "GOLDM "), icon: "relative", run: () => { ctx.setRvPair(p.pair); go("relative"); } }));
  SYMS.forEach(s => it.push({ id: "c" + s, group: "Contracts", title: `${s} contracts`, hint: SYM[s].d, keys: "contract calendar expiry " + s.replace("GOLD", ""), icon: "calendar", run: () => { ctx.setCalF(s); go("calendar"); } }));
  EVENTS.slice().reverse().forEach(e => it.push({ id: "e" + e.date, group: "Events", title: `${fdate(e.date)} · ${e.tag}`, hint: "Overview chart", keys: e.text + " " + e.date, icon: "overview", run: () => go("overview") }));
  Object.entries(GLOSSARY).forEach(([k, [t, d]]) => it.push({ id: "g" + k, group: "Terms", title: t, hint: "Definition", keys: d, icon: "book", def: d }));
  [["light", "Light theme", "sun"], ["dark", "Dark theme", "moon"], ["system", "Auto theme", "auto"]].forEach(([v, t, ic]) => it.push({ id: "t" + v, group: "Actions", title: t, keys: "theme mode colour color", icon: ic, run: () => ctx.setTheme(v) }));
  it.push({ id: "anews", group: "Actions", title: "What's new: data and test log", keys: "changelog updates uploads", icon: "news", run: () => ctx.setNews(true) });
  it.push({ id: "ahelp", group: "Actions", title: "Keyboard shortcuts", hint: "?", keys: "help keys keyboard shortcuts hotkeys", icon: "keys", run: () => ctx.setKeysSheet(true) });
  it.push({ id: "aprint", group: "Actions", title: "Print or save this page as PDF", keys: "print pdf save paper export", icon: "print", run: () => setTimeout(() => print(), 120) });
  it.push({ id: "akeys", group: "Actions", title: ctx.keysOn ? "Turn off number-key shortcuts" : "Turn on number-key shortcuts", keys: "keyboard shortcuts keys", icon: "more", run: () => ctx.setKeysOn(!ctx.keysOn) });
  return it;
}
function Palette({ open, onClose, go, ctx }) {
  const [q, setQ] = useState(""), [act, setAct] = useState(0), [def, setDef] = useState(null), input = useRef(null), list = useRef(null), back = useRef(null);
  const items = useMemo(() => buildItems(go, ctx), [ctx.keysOn]);
  const res = useMemo(() => { const toks = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (!toks.length) return items.filter(i => i.group !== "Terms" && i.group !== "Events").concat(items.filter(i => i.group === "Events").slice(0, 3));
    return items.filter(i => { const hay = (i.title + " " + i.keys + " " + i.group).toLowerCase(); return toks.every(t => hay.includes(t)); })
      .sort((a, b) => (b.title.toLowerCase().startsWith(toks[0]) ? 1 : 0) - (a.title.toLowerCase().startsWith(toks[0]) ? 1 : 0)).slice(0, 40); }, [q, items]);
  useEffect(() => { if (open) { back.current = document.activeElement; setQ(""); setAct(0); setDef(null); setTimeout(() => input.current && input.current.focus(), 0); } else if (back.current && back.current.focus) back.current.focus(); }, [open]);
  useEffect(() => { setAct(0); setDef(null); }, [q]);
  useEffect(() => { const el = list.current && list.current.querySelector('[aria-selected="true"]'); if (el) el.scrollIntoView({ block: "nearest" }); }, [act]);
  if (!open) return null;
  const choose = i => { if (!i) return; if (i.def) { setDef(i); return; } onClose(); i.run(); };
  const key = e => { if (e.key === "ArrowDown") { e.preventDefault(); setAct(a => Math.min(res.length - 1, a + 1)); } else if (e.key === "ArrowUp") { e.preventDefault(); setAct(a => Math.max(0, a - 1)); }
    else if (e.key === "Enter") { e.preventDefault(); choose(res[act]); } else if (e.key === "Escape") { e.preventDefault(); def ? setDef(null) : onClose(); } else if (e.key === "Tab") e.preventDefault(); };
  let lastG = null;
  return <div className="overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}>
    <div className="palette" role="dialog" aria-modal="true" aria-label="Search Parity">
      <div className="pal-in"><Icon name="search" size={18} />
        <input ref={input} autoFocus value={q} onChange={e => setQ(e.target.value)} onKeyDown={key} placeholder="Search sections, pairs, contracts, events, terms…" role="combobox" aria-expanded="true" aria-controls="pal-list" aria-activedescendant={res[act] ? "pi-" + res[act].id : undefined} aria-autocomplete="list" />
        <kbd>esc</kbd></div>
      {def ? <div className="pal-def"><div className="lab">Definition</div><h3>{def.title}</h3><p>{def.def}</p><button type="button" className="linkbtn" onClick={() => { setDef(null); input.current.focus(); }}>Back to results</button></div> :
        <ul className="pal-list" id="pal-list" role="listbox" ref={list} aria-label="Results">
          {res.length ? res.map((i, n) => { const head = i.group !== lastG; lastG = i.group;
            return [head && <li key={"h" + i.group} className="pal-g" role="presentation">{i.group}</li>,
              <li key={i.id} id={"pi-" + i.id} role="option" aria-selected={n === act} className="pal-i" onMouseMove={() => setAct(n)} onClick={() => choose(i)}>
                <Icon name={i.icon} size={16} /><span className="pt">{i.title}</span>{i.hint && <span className="ph">{i.hint}</span>}</li>]; })
            : <li className="pal-empty" role="presentation">Nothing matches “{q}”. Try PETAL, Jan 2026, carry or backtest.</li>}
        </ul>}
      <div className="pal-f"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>↵</kbd> open</span><span><kbd>{isMac ? "⌘" : "Ctrl"}</kbd><kbd>K</kbd> toggle</span></div>
    </div>
  </div>;
}

/* ---------- what's new: every data upload, test run and build, from the Git history */
function News({ open, onClose }) {
  const ref = useRef(null), back = useRef(null);
  useEffect(() => { if (open) { back.current = document.activeElement; setTimeout(() => ref.current && ref.current.focus(), 0); } else if (back.current && back.current.focus) back.current.focus(); }, [open]);
  if (!open) return null;
  const log = D.changelog || [], days = []; log.forEach(c => { const d = c.date; if (!days.length || days[days.length - 1][0] !== d) days.push([d, []]); days[days.length - 1][1].push(c); });
  const files = log.reduce((a, c) => a + (c.files || 0), 0), uploads = log.filter(c => c.files).length;
  return <div className="overlay" onMouseDown={e => e.target === e.currentTarget && onClose()} onKeyDown={e => e.key === "Escape" && onClose()}>
    <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="news-h" tabIndex={-1} ref={ref}>
      <header><div><div className="lab">From the Git history</div><h2 id="news-h">What's new</h2>
        <p className="sub">{uploads} data uploads ({files} MCX files) and {log.length - uploads} analysis, test and site changes. Times in IST.</p></div>
        <button type="button" className="iconbtn" aria-label="Close" onClick={onClose}><Icon name="close" /></button></header>
      <div className="news">{days.map(([d, cs]) => <section key={d}><h3>{fdate(d)}</h3><ul>{cs.map(c => <li key={c.hash}>
        <span className={"kind " + c.kind}>{c.kindLabel}</span><div><div className="nt">{c.title}</div><div className="nm"><span className="num">{c.time}</span> · <span className="num">{c.hash}</span>{c.files ? ` · ${c.files} files` : ""}</div></div></li>)}</ul></section>)}</div>
    </aside>
  </div>;
}

/* ---------- a single indicator per nav that glides to whichever item is current */
function useIndicator(view) {
  const host = useRef(null), ind = useRef(null), snap = useRef(true);
  const place = useCallback(() => { const h = host.current, i = ind.current; if (!h || !i) return;
    const a = h.querySelector(':scope > [aria-current="page"]');
    if (!a || !h.offsetParent && getComputedStyle(h).position !== "fixed") { i.classList.remove("ready"); snap.current = true; return; }
    if (snap.current) i.classList.add("no-anim");
    i.style.width = a.offsetWidth + "px"; i.style.height = a.offsetHeight + "px"; i.style.transform = `translate3d(${a.offsetLeft}px,${a.offsetTop}px,0)`;
    i.classList.add("ready");
    if (snap.current) { i.getBoundingClientRect(); requestAnimationFrame(() => i.classList.remove("no-anim")); snap.current = false; }
    if (h.scrollWidth > h.clientWidth + 2) { const l = a.offsetLeft - (h.clientWidth - a.offsetWidth) / 2; h.scrollTo({ left: l, behavior: reducedMotion() ? "auto" : "smooth" }); }
  }, []);
  useLayoutEffect(place, [view, place]);
  useEffect(() => { const h = host.current; if (!h) return; const ro = new ResizeObserver(() => { snap.current = true; place(); }); ro.observe(h); return () => ro.disconnect(); }, [place]);
  return [host, ind];
}
const vIdx = id => VIEWS.findIndex(v => v[0] === id);

/* ---------- freshness: how current the data is, and when the scheduled job next looks for a new MCX file.
   The job runs at 03:30 IST Tuesday to Saturday (after each Monday-Friday session), with a retry at 08:00 IST. */
const DAY = 864e5, IST = 5.5 * 36e5, WD = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const istNow = () => Date.now() + IST;                                    // read with getUTC* to get IST fields
const ymd = t => new Date(t).toISOString().slice(0, 10);
function freshness(now = istNow()) {
  const last = D.meta.last_full || D.meta.last, base = Math.floor(now / DAY) * DAY;
  let next = null;
  for (let d = 0; d < 9 && !next; d++) for (const [h, m] of [[3, 30], [8, 0]]) {
    const t = base + d * DAY + (h * 60 + m) * 6e4, w = new Date(t).getUTCDay();
    if (w >= 2 && w <= 6 && t > now) { next = t; break; } }
  // the newest weekday session whose 08:00 retry has already passed
  let exp = base - DAY; while (true) { const w = new Date(exp).getUTCDay(); if (w >= 1 && w <= 5 && exp + DAY + 8.5 * 36e5 <= now) break; exp -= DAY; }
  let lag = 0; for (let t = Date.parse(last + "T00:00:00Z") + DAY; t <= exp; t += DAY) { const w = new Date(t).getUTCDay(); if (w >= 1 && w <= 5) lag++; }
  const nd = new Date(next), today = Math.floor(next / DAY) * DAY === base;
  const nextTxt = `${today ? "today" : WD[nd.getUTCDay()] + " " + nd.getUTCDate() + " " + ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][nd.getUTCMonth()]}, ${String(nd.getUTCHours()).padStart(2, "0")}:${String(nd.getUTCMinutes()).padStart(2, "0")} IST`;
  const nextShort = `${today ? "today" : WD[nd.getUTCDay()]} ${String(nd.getUTCHours()).padStart(2, "0")}:${String(nd.getUTCMinutes()).padStart(2, "0")} IST`;
  return { last, lag, stale: lag >= 2, expected: ymd(exp), nextTxt, nextShort };
}
function Fresh({ compact }) {
  const [f, setF] = useState(freshness);
  useEffect(() => { const t = setInterval(() => setF(freshness()), 6e4); return () => clearInterval(t); }, []);
  const tip = f.stale
    ? `Behind by ${f.lag} trading days: MCX's file for ${fdate(f.expected)} should be in by now. A market holiday can also cause this; the next check is ${f.nextTxt}.`
    : `Up to date. New sessions are added after MCX publishes its end-of-day file; the next check is ${f.nextTxt}.`;
  if (compact) return <span className={"fresh-c" + (f.stale ? " stale" : "")} title={tip}>Data {fdate(f.last)} · next check {f.nextTxt}</span>;
  return <div className={"live" + (f.stale ? " stale" : "")} title={tip}>
    <span className="pulse" />{f.stale ? "Data may be behind · " : "Data through "}<b className="num">{fdate(f.last)}</b>
    <span className="next">Next check {f.nextShort}</span></div>;
}

/* ---------- build stamp, written by dashboard/build.py */
const BUILD = window.__PARITY_BUILD__ || {};

/* ---------- keyboard shortcuts sheet ("?") */
function Keys({ open, onClose }) {
  const ref = useRef(null), back = useRef(null);
  useEffect(() => { if (open) { back.current = document.activeElement; setTimeout(() => ref.current && ref.current.focus(), 0); } else if (back.current && back.current.focus) back.current.focus(); }, [open]);
  if (!open) return null;
  const mod = isMac ? "⌘" : "Ctrl";
  const rows = [[[mod, "K"], "Search sections, pairs, contracts and terms"], [["/"], "Search, too"], [["1", "–", "8"], "Jump to a section"],
    [["?"], "This list"], [["Esc"], "Close any panel or definition"], [["Tab"], "Move between controls; dotted terms and sources are focusable"],
    [["Enter"], "Open a dotted term's definition or a number's source"], [[mod, "P"], "Print or save the page as a PDF"]];
  return <div className="overlay" onMouseDown={e => e.target === e.currentTarget && onClose()} onKeyDown={e => { if (e.key === "Escape" || e.key === "?") { e.preventDefault(); onClose(); } }}>
    <div className="palette keysheet" role="dialog" aria-modal="true" aria-labelledby="keys-h" tabIndex={-1} ref={ref}>
      <header><h2 id="keys-h">Keyboard shortcuts</h2><button type="button" className="iconbtn" aria-label="Close" onClick={onClose}><Icon name="close" /></button></header>
      <dl>{rows.map(([k, d], i) => <div key={i}><dt>{k.map((x, j) => x === "–" ? <span key={j} className="dim"> – </span> : <kbd key={j}>{x}</kbd>)}</dt><dd>{d}</dd></div>)}</dl>
      <p className="sub">Number keys can be turned off in the side menu if they get in your way.</p>
    </div>
  </div>;
}

/* ---------- when a page fails to draw, say so plainly instead of showing a blank screen */
class Guard extends Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  componentDidCatch(err) { try { console.error("Parity page error:", err); } catch (e) {} }
  render() {
    if (!this.state.err) return this.props.children;
    return <section className="card oops" role="alert">
      <div className="lab">Something went wrong</div>
      <h2>This page could not be drawn.</h2>
      <p className="sub">The rest of the site still works. Reloading usually fixes it; if it does not, the message below helps us find the cause.</p>
      <code className="oops-m">{String(this.state.err && this.state.err.message || this.state.err).slice(0, 240)}</code>
      <div className="oops-a"><button type="button" className="btn" onClick={() => location.reload()}><Icon name="reload" size={16} />Reload</button>
        <a className="btn ghost" href="#overview" onClick={() => this.setState({ err: null })}>Go to the overview</a></div>
    </section>;
  }
}

/* ---------- an address that is not one of the eight sections */
function NotFound({ hash, go, openSearch }) {
  return <section className="card oops nf">
    <div className="lab">404 · page not found</div>
    <h1 tabIndex={-1}>No page called “#{hash}”.</h1>
    <p className="sub">Parity has eight sections. Pick one, or search for a contract, pair or term.</p>
    <ol className="nf-l">{VIEWS.map(([id, l], i) => <li key={id}><a href={"#" + id} onClick={e => { e.preventDefault(); go(id); }}><span className="num">{String(i + 1).padStart(2, "0")}</span>{l}</a></li>)}</ol>
    <div className="oops-a"><button type="button" className="btn" onClick={openSearch}><Icon name="search" size={16} />Search the site</button></div>
  </section>;
}

/* ---------- app */
/* ---------- Dock magnification (macOS) and press ripple (iOS)
   Pointer: the tile under the pointer grows most, its neighbours a little less, falling off with distance.
   Touch: pressing a tile sinks it and its neighbours ripple a little, then spring back.
   One rAF loop drives every tile with its own critically damped spring, so there are no CSS transitions to
   re-target on each frame (the cause of the old shimmer). Rects are layout boxes, measured without the
   transforms we apply, and re-measured on scroll instead of resetting. Only transform changes (composited),
   so it runs at the display's refresh rate. In the sidebar only the label grows, so the highlight stays inside. */
const DOCK_TILE = ".quote,.kpi,.dir,.dl-i,.jump a,.find,.hg-s,.status,.proof a,.qa-r,.uq li,.unique li,.rail nav a,.strip a,.more:not([open])";
const PRESS_TILE = ".quote,.kpi,.dir,.dl-i,.jump a,.find,.hg-s,.proof a,.qa-r,.strip a,.sheet a,.sheet button,.nf-l a";
function useDock() {
  useEffect(() => {
    if (reducedMotion()) return;
    const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
    const live = new Map();                 // element -> {tgt, s, y, x, ts, ty, tx, side}
    let group = null, tiles = [], rects = [], raf = 0, last = 0, px = 0, py = 0, quiet = 0, dirty = false, mode = "hover", pressed = null;
    const TAU = 0.075;                      // seconds; spring time constant (snappy like the Dock, never overshoots)
    const st = (tile) => {
      let o = live.get(tile);
      if (!o) {
        const side = !!tile.closest(".rail");
        const tgt = side ? tile.querySelector(".rl") : tile;
        o = { tgt, side, s: 1, y: 0, ts: 1, ty: 0 };
        tgt.style.willChange = "transform"; tgt.classList.add("dk");
        if (side) tgt.style.transformOrigin = "left center";
        live.set(tile, o);
      }
      return o;
    };
    const measure = () => {                 // layout boxes: transforms on tiles are undone, side tiles are never transformed
      rects = tiles.map(t => { const r = t.getBoundingClientRect(), o = live.get(t); const w = t.offsetWidth || r.width, h = t.offsetHeight || r.height;
        if (o && !o.side) { const cx = r.left + r.width / 2, cy = r.top + r.height / 2 - o.y; return { cx, cy, w, h }; }
        return { cx: r.left + r.width / 2, cy: r.top + r.height / 2, w, h }; });
      dirty = false;
    };
    const targets = () => {
      if (!group || !rects.length) return;
      if (dirty) measure();
      const n = rects.length, w = rects.reduce((a, r) => a + r.w, 0) / n, h = rects.reduce((a, r) => a + r.h, 0) / n;
      const vertical = n > 1 ? Math.abs(rects[1].cy - rects[0].cy) > Math.abs(rects[1].cx - rects[0].cx) : w >= 520;
      const side = tiles[0].closest(".rail") != null, wide = w >= 520;
      if (mode === "press") {               // iOS: the pressed tile sinks, neighbours answer a little
        const pi = tiles.indexOf(pressed), pr = rects[pi]; if (!pr) return;
        tiles.forEach((t, i) => { const r = rects[i], d = Math.hypot(r.cx - pr.cx, r.cy - pr.cy), k = i === pi ? 1 : Math.exp(-(d * d) / (2 * 140 * 140)) * 0.35;
          const o = st(t); o.ts = 1 - (wide ? 0.015 : 0.04) * k; o.ty = 0; });
        return;
      }
      if (wide && !vertical) return;
      const amp = wide ? Math.min(0.03, 22 / w) : side ? 0.07 : 0.08;
      const sig = vertical ? Math.max(28, h * 0.9) : Math.max(90, w * 0.6);
      tiles.forEach((t, i) => {
        const r = rects[i];
        const d = vertical ? Math.max(0, Math.abs(py - r.cy) - r.h * 0.2)
                           : Math.hypot(Math.max(0, Math.abs(px - r.cx) - r.w * 0.2), Math.max(0, Math.abs(py - r.cy) - r.h * 0.2));
        const k = Math.exp(-(d * d) / (2 * sig * sig)), o = st(t);
        o.ts = 1 + amp * k; o.ty = side || vertical ? 0 : -6 * k;
        t.style.zIndex = k > 0.6 ? "3" : k > 0.2 ? "2" : "";
      });
    };
    const frame = now => {
      raf = 0;
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 1 / 60; last = now;
      targets();
      const a = 1 - Math.exp(-dt / TAU);
      let moving = false;
      live.forEach((o, t) => {
        o.s += (o.ts - o.s) * a; o.y += (o.ty - o.y) * a;
        const done = Math.abs(o.ts - o.s) < 5e-4 && Math.abs(o.ty - o.y) < 0.05;
        if (done) { o.s = o.ts; o.y = o.ty; }
        if (done && o.ts === 1 && o.ty === 0 && !tiles.includes(t)) {   // back at rest and no longer in play: clean up
          o.tgt.style.transform = ""; o.tgt.style.willChange = ""; o.tgt.style.transformOrigin = ""; o.tgt.classList.remove("dk"); t.style.zIndex = ""; live.delete(t); return;
        }
        o.tgt.style.transform = (o.y ? `translate3d(0,${o.y.toFixed(2)}px,0) ` : "") + `scale(${o.s.toFixed(4)})`;
        if (!done) moving = true;
      });
      if (moving || group) raf = requestAnimationFrame(frame); else last = 0;
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
    const release = () => {
      live.forEach(o => { o.ts = 1; o.ty = 0; });
      tiles.forEach(t => { t.style.zIndex = ""; });
      group = null; tiles = []; rects = []; pressed = null; kick();
    };
    const enter = (g, sel) => { release(); group = g; tiles = [...g.children].filter(c => c.matches(sel)); measure(); };
    const onMove = e => {
      if (e.pointerType !== "mouse" || !fine) return;
      px = e.clientX; py = e.clientY;
      if (e.timeStamp < quiet) return;                                   // a panel is still unfolding: rows below are moving
      const tile = e.target.closest && e.target.closest(DOCK_TILE), g = tile && tile.parentElement;
      if (g && g !== group) { mode = "hover"; enter(g, DOCK_TILE); }
      else if (!g && group) {
        const r0 = group.getBoundingClientRect();
        if (!(px >= r0.left - 12 && px <= r0.right + 12 && py >= r0.top - 12 && py <= r0.bottom + 12)) { release(); return; }
      }
      if (group) kick();
    };
    const onDown = e => {
      if (e.pointerType === "mouse") return;
      const tile = e.target.closest && e.target.closest(PRESS_TILE); if (!tile || !tile.parentElement) return;
      mode = "press"; enter(tile.parentElement, PRESS_TILE); pressed = tile; kick();
    };
    const onUp = () => { if (mode === "press" && group) release(); };
    const onScroll = () => { if (mode === "press") { if (group) release(); return; } if (group) { dirty = true; kick(); } };
    const onClick = e => { quiet = e.timeStamp + 560; if (group && mode === "hover") release(); };
    const onLeave = () => { if (group) release(); };
    const opt = { passive: true };
    document.addEventListener("pointermove", onMove, opt);
    document.addEventListener("pointerdown", onDown, opt);
    document.addEventListener("pointerup", onUp, opt);
    document.addEventListener("pointercancel", onUp, opt);
    document.documentElement.addEventListener("mouseleave", onLeave, opt);
    addEventListener("scroll", onScroll, opt);
    document.addEventListener("click", onClick, { passive: true, capture: true });
    return () => {
      document.removeEventListener("pointermove", onMove); document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("pointerup", onUp); document.removeEventListener("pointercancel", onUp);
      document.documentElement.removeEventListener("mouseleave", onLeave); removeEventListener("scroll", onScroll);
      document.removeEventListener("click", onClick, { capture: true }); cancelAnimationFrame(raf);
      live.forEach((o, t) => { o.tgt.style.transform = ""; o.tgt.style.willChange = ""; t.style.zIndex = ""; });
    };
  }, []);
}

/* ---------- glass sheen: a soft reflection follows the pointer across the panel under it (mouse only) */
function useSheen() {
  useEffect(() => {
    if (!matchMedia("(hover: hover) and (pointer: fine)").matches || reducedMotion()) return;
    let el = null, raf = 0, x = 0, y = 0, tgt = null;
    const paint = () => { raf = 0;
      if (tgt !== el) { if (el) el.classList.remove("lit"); el = tgt; if (el) el.classList.add("lit"); }
      if (el) { const r = el.getBoundingClientRect(); el.style.setProperty("--mx", (x - r.left).toFixed(0) + "px"); el.style.setProperty("--my", (y - r.top).toFixed(0) + "px"); } };
    const move = e => { if (e.pointerType !== "mouse") return; x = e.clientX; y = e.clientY;
      tgt = e.target.closest ? e.target.closest(".card,.take,.more") : null; if (!raf) raf = requestAnimationFrame(paint); };
    const leave = () => { tgt = null; if (!raf) raf = requestAnimationFrame(paint); };
    document.addEventListener("pointermove", move, { passive: true });
    document.documentElement.addEventListener("mouseleave", leave, { passive: true });
    return () => { document.removeEventListener("pointermove", move); document.documentElement.removeEventListener("mouseleave", leave); cancelAnimationFrame(raf); if (el) el.classList.remove("lit"); };
  }, []);
}

/* ---------- phone chrome (iOS): reading down hides the header and minimises the tab bar; the first flick up
   brings both back. Once the page title scrolls away, the header shows it in place of the wordmark. */
function usePhoneChrome(view) {
  useEffect(() => {
    const mq = matchMedia("(max-width: 760px)"), root = document.documentElement;
    let y0 = scrollY, acc = 0, raf = 0, io = null;
    const set = (c, on) => root.classList.toggle(c, on);
    const tick = () => { raf = 0; const y = scrollY, dy = y - y0; y0 = y;
      if (!mq.matches || y < 72) { acc = 0; set("sd", false); return; }
      acc = Math.sign(dy) === Math.sign(acc) ? acc + dy : dy;          // direction must hold for a few px: no flicker
      if (acc > 14) set("sd", true); else if (acc < -10) set("sd", false); };
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(tick); };
    addEventListener("scroll", onScroll, { passive: true });
    const watch = () => { if (io) io.disconnect(); const h = document.querySelector("main h1"); set("ph", false);
      if (h && "IntersectionObserver" in window) { io = new IntersectionObserver(([e]) => set("ph", !e.isIntersecting && e.boundingClientRect.top < 0), { rootMargin: "-60px 0px 0px 0px" }); io.observe(h); } };
    const t = setTimeout(watch, 80);
    set("sd", false);
    return () => { removeEventListener("scroll", onScroll); cancelAnimationFrame(raf); clearTimeout(t); if (io) io.disconnect(); };
  }, [view]);
}

/* ---------- the More sheet follows the finger and is flicked away, like an iOS sheet */
function useSheetDrag(ref, open, close) {
  useEffect(() => {
    const el = ref.current; if (!open || !el) return;
    let y0 = 0, t0 = 0, dy = 0, on = false, id = null;
    const down = e => { if (e.pointerType === "mouse") return; on = true; id = e.pointerId; y0 = e.clientY; t0 = e.timeStamp; dy = 0; };
    const move = e => { if (!on || e.pointerId !== id) return; dy = Math.max(0, e.clientY - y0) ;
      const d = e.clientY - y0 < 0 ? -Math.sqrt(-(e.clientY - y0)) * 1.5 : dy;      // rubber-band upwards
      if (Math.abs(e.clientY - y0) > 4) { el.classList.add("drag"); el.style.transform = `translate3d(0,${d.toFixed(1)}px,0)`; } };
    const up = e => { if (!on) return; on = false; const v = dy / Math.max(1, e.timeStamp - t0);
      el.classList.remove("drag");
      if (dy > 90 || (dy > 24 && v > 0.45)) {
        const a = el.animate([{ transform: el.style.transform || "none" }, { transform: "translate3d(0,100%,0)" }], { duration: 260, easing: "cubic-bezier(.32,.72,0,1)", fill: "forwards" });
        a.onfinish = () => close();
      } else if (el.style.transform) {
        el.animate([{ transform: el.style.transform }, { transform: "none" }], { duration: 420, easing: "cubic-bezier(.32,.72,0,1)" });
        el.style.transform = "";
      } };
    el.addEventListener("pointerdown", down, { passive: true }); el.addEventListener("pointermove", move, { passive: true });
    el.addEventListener("pointerup", up, { passive: true }); el.addEventListener("pointercancel", up, { passive: true });
    return () => { el.removeEventListener("pointerdown", down); el.removeEventListener("pointermove", move); el.removeEventListener("pointerup", up); el.removeEventListener("pointercancel", up); };
  }, [open]);
}

function App() {
  useDock(); useSheen(); useSmoothScroll(); useMagnetic();
  const bad = h => h && h !== "main" && !PAGES[h];
  const init = () => { const h = location.hash.slice(1); return PAGES[h] ? h : bad(h) ? "404" : store.get("gsl-view", "overview"); };
  const [view, setView] = useState(init), [theme, setTheme] = useTheme(), [phase, setPhase] = useState("in"), [navN, setNavN] = useState(0);
  const viewRef = useRef(view); viewRef.current = view;
  const pend = useRef(null), tmr = useRef(0), lost = useRef(location.hash.slice(1));
  const [pal, setPal] = useState(false), [news, setNews] = useState(false), [more, setMore] = useState(false), [keysSheet, setKeysSheet] = useState(false);
  usePhoneChrome(view);
  const sheetRef = useRef(null); useSheetDrag(sheetRef, more, () => setMore(false));
  const [keysOn, setKeysOnS] = useState(() => store.get("gsl-keys", "on") !== "off");
  const [rvPair, setRvPair] = useState("M-GUINEA"), [calF, setCalF] = useState("All");
  const userNav = useRef(false);
  const setKeysOn = v => { setKeysOnS(v); store.set("gsl-keys", v ? "on" : "off"); };
  const focusHead = () => requestAnimationFrame(() => { const h = document.querySelector("main h1"); if (h) h.focus({ preventScroll: true }); });
  /* Page change: the old page leaves (160 ms), the jump to the top happens while nothing is on screen, then the new
     page arrives. A second click mid-way just retargets; nothing queues up, so rapid switching never lags behind. */
  const commit = () => { tmr.current = 0; const id = pend.current; pend.current = null; if (!id) return;
    scrollTo({ top: 0, behavior: "instant" }); setView(id); setPhase("in"); };
  const navigate = useCallback(id => {
    if (!PAGES[id]) { if (bad(id)) { lost.current = id; pend.current = "404"; commit(); } return; }
    const cur = viewRef.current;
    if (id === cur && !pend.current) { scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" }); focusHead(); return; }
    document.documentElement.classList.toggle("nav-back", vIdx(id) < vIdx(cur));
    pend.current = id; userNav.current = true; setNavN(n => n + 1);
    if (reducedMotion()) { commit(); return; }
    if (!tmr.current) { setPhase("out"); tmr.current = setTimeout(commit, 160); }
  }, []);
  const go = useCallback(id => { setMore(false); if (location.hash.slice(1) !== id) location.hash = id; else navigate(id); }, []);
  useEffect(() => { const on = () => navigate(location.hash.slice(1)); addEventListener("hashchange", on); return () => { removeEventListener("hashchange", on); clearTimeout(tmr.current); }; }, []);
  useEffect(() => { document.title = view === "overview" ? `${NAME} · MCX gold futures` : view === "404" ? `Page not found · ${NAME}` : `${label(view)} · ${NAME}`; if (PAGES[view]) store.set("gsl-view", view);
    if (userNav.current) { focusHead(); userNav.current = false; } }, [view]);
  const [railH, railI] = useIndicator(view), [stripH, stripI] = useIndicator(view), [tabH, tabI] = useIndicator(view + more);
  useEffect(() => { const k = e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setNews(false); setKeysSheet(false); setPal(p => !p); return; }
    if (pal || news || keysSheet || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
    if (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "?") { e.preventDefault(); setKeysSheet(true); return; }
    if (!keysOn || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
    if (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "/") { e.preventDefault(); setPal(true); return; }
    const n = "12345678".indexOf(e.key); if (n < 0 || e.key.length !== 1) return; e.preventDefault(); go(VIEWS[n][0]); };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, [pal, news, keysOn, keysSheet]);
  useEffect(() => { document.documentElement.classList.toggle("nokeys", !keysOn); }, [keysOn]);
  const ctx = { view, go, rvPair, setRvPair, calF, setCalF, theme, setTheme, keysOn, setKeysOn, setNews, setPal, setKeysSheet };
  const Page = PAGES[view], idx = VIEWS.findIndex(v => v[0] === view);
  /* the loading screen leaves once the first page has painted */
  /* after "Enter Parity" on the intro it is the logo reveal instead (template.html): it plays for 3 s, then the doors
     part and the page's own entrance (paused until now by html.reveal) runs as the site comes into view */
  useEffect(() => { const b = document.getElementById("boot"); if (!b) return;
    const rvl = b.classList.contains("rvl"), t0 = (rvl ? window.__PARITY_RVL_T0 : window.__PARITY_T0) || 0, wait = Math.max(0, (rvl ? 3000 : 650) - (performance.now() - t0));   // the reveal is timed from when it first appeared
    const t = setTimeout(() => { b.classList.add("done"); setTimeout(() => document.documentElement.classList.remove("reveal"), rvl ? 260 : 0);
      setTimeout(() => b.remove(), rvl ? 1300 : 520); }, reducedMotion() ? 0 : wait); return () => clearTimeout(t); }, []);
  /* printing: always the light theme, every "more" panel opened, then put back */
  useEffect(() => { let opened = [], prev = null, on = false;
    const before = () => { if (on) return; on = true; prev = document.documentElement.getAttribute("data-theme"); document.documentElement.setAttribute("data-theme", "light");
      opened = [...document.querySelectorAll("main details:not([open])")]; opened.forEach(d => d.open = true);
      document.querySelectorAll("main .rv").forEach(e => e.classList.add("in")); };
    const after = () => { if (!on) return; on = false; prev ? document.documentElement.setAttribute("data-theme", prev) : document.documentElement.removeAttribute("data-theme"); opened.forEach(d => d.open = false); opened = []; };
    addEventListener("beforeprint", before); addEventListener("afterprint", after);
    return () => { removeEventListener("beforeprint", before); removeEventListener("afterprint", after); }; }, []);
  const newest = D.changelog && D.changelog[0];
  return <AppCtx.Provider value={ctx}>
    <a className="skip" href="#main" onClick={e => { e.preventDefault(); focusHead(); }}>Skip to content</a>
    <div className="bgfx" aria-hidden="true"><i /><i /></div>
    <header className="top">
      <a className="brand" href="#overview" aria-label={`${NAME}, overview`} onClick={e => { e.preventDefault(); go("overview"); }}><Mark /><span className="wm">{NAME}<small>MCX gold futures</small></span><span className="top-t" aria-hidden="true">{view === "404" ? "Not found" : label(view)}</span></a>
      <div className="crumb" aria-hidden="true"><span key={view} className="roll"><span className="num">{idx < 0 ? "—" : String(idx + 1).padStart(2, "0")} / 08</span>{view === "404" ? "Not found" : label(view)}</span></div>
      <div className="top-r">
        <button type="button" className="search" onClick={() => setPal(true)} aria-label="Search (Ctrl+K)"><Icon name="search" size={16} /><span className="sl">Search</span><kbd>{isMac ? "⌘" : "Ctrl"} K</kbd></button>
        <button type="button" className="iconbtn" onClick={() => setNews(true)} aria-label="What's new" title={newest ? `What's new · latest ${fdate(newest.date)}` : "What's new"}><Icon name="news" size={18} /></button>
        <ThemeSwitch theme={theme} setTheme={setTheme} />
      </div>
    </header>
    <nav className="strip ind-host" aria-label="Sections" ref={stripH}><span className="ind" ref={stripI} aria-hidden="true" />{VIEWS.map(([id, l], i) => <a key={id} href={"#" + id} aria-current={id === view ? "page" : undefined}><span className="num">{String(i + 1).padStart(2, "0")}</span>{l}</a>)}</nav>
    <div className="shell">
      <aside className="rail">
        <nav aria-label="Sections" className="ind-host" ref={railH}><span className="ind" ref={railI} aria-hidden="true" />{VIEWS.map(([id, l], i) => <a key={id} href={"#" + id} aria-current={id === view ? "page" : undefined} aria-keyshortcuts={keysOn ? String(i + 1) : undefined}>
          <span className="num">{String(i + 1).padStart(2, "0")}</span><span className="rl"><span className="rr" data-t={l}>{l}</span></span><kbd className="key" aria-hidden="true">{i + 1}</kbd></a>)}</nav>
        <div className="rail-f">
          <Fresh />
          <div>Official MCX Bhavcopy · end of day</div>
          <div className="keys">{keysOn ? <><span className="kh"><kbd>1</kbd>–<kbd>8</kbd> sections · <kbd>/</kbd> search · <button type="button" className="linkbtn kq" onClick={() => setKeysSheet(true)} aria-label="All keyboard shortcuts" title="All keyboard shortcuts"><kbd>?</kbd></button></span><button type="button" className="linkbtn" onClick={() => setKeysOn(false)}>Turn off shortcuts</button></>
            : <button type="button" className="linkbtn" onClick={() => setKeysOn(true)}>Turn on number-key shortcuts</button>}</div>
        </div>
      </aside>
      <main id="main" key={view} className={"page " + (phase === "out" ? "p-out" : "p-in")}>
        <div className="print-h" aria-hidden="true"><b>{NAME}</b> · {view === "404" ? "Page not found" : label(view)} · data through {fdate(D.meta.last_full || D.meta.last)} · parity-gold-site.vercel.app/#{view}</div>
        <Guard key={view}>{Page ? <Page /> : <NotFound hash={lost.current} go={go} openSearch={() => setPal(true)} />}</Guard>
        <footer className="foot">
          <div className="foot-a"><span className="foot-b"><span className="num">v{BUILD.version || "dev"}</span>{BUILD.built && <> · built <span className="num">{BUILD.built}</span></>}{BUILD.commit && <> · after commit <a className="num" href={`https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-/commit/${BUILD.commit}`} target="_blank" rel="noopener">{BUILD.commit}</a></>}</span>
            <Fresh compact /></div>
          <div className="foot-a"><span>SYNTAX TERROR (TAN) · Nikhil Kumar, Sai Ganesh, Ishaan Chhabra · Hack in Hills ’26</span>
            <span>Prices: official MCX Bhavcopy, mcxindia.com · <a href="https://github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-" target="_blank" rel="noopener">Code and data on GitHub</a> · <a href="#quality" onClick={e => { e.preventDefault(); go("quality"); }}>Known limits</a> · <a href="/intro">Replay intro</a> · <button type="button" className="linkbtn" onClick={() => setKeysSheet(true)}>Shortcuts</button></span></div>
        </footer>
      </main>
    </div>
    <nav className="tabbar ind-host" aria-label="Sections" ref={tabH}><span className="ind" ref={tabI} aria-hidden="true" />
      {TABS.map(id => <a key={id} href={"#" + id} aria-current={id === view ? "page" : undefined}><Icon name={id} size={20} /><span>{id === "brief" ? "Brief" : label(id)}</span></a>)}
      <button type="button" aria-expanded={more} aria-current={!TABS.includes(view) ? "page" : undefined} onClick={() => setMore(m => !m)}><Icon name="more" size={20} /><span>More</span></button>
    </nav>
    {more && <div className="overlay sheet-o" onMouseDown={e => e.target === e.currentTarget && setMore(false)} onKeyDown={e => e.key === "Escape" && setMore(false)}>
      <div className="sheet" ref={sheetRef} role="dialog" aria-modal="true" aria-label="More sections">
        <div className="grab" aria-hidden="true" />
        {VIEWS.filter(v => !TABS.includes(v[0])).map(([id, l]) => <a key={id} href={"#" + id} onClick={() => setMore(false)} aria-current={id === view ? "page" : undefined}><Icon name={id} size={20} />{l}</a>)}
        <button type="button" onClick={() => { setMore(false); setPal(true); }}><Icon name="search" size={20} />Search</button>
        <button type="button" onClick={() => { setMore(false); setNews(true); }}><Icon name="news" size={20} />What's new</button>
      </div></div>}
    {navN > 0 && <div key={navN} className="navbar-p" aria-hidden="true" />}
    <Palette open={pal} onClose={() => setPal(false)} go={go} ctx={ctx} />
    <News open={news} onClose={() => setNews(false)} />
    <Keys open={keysSheet} onClose={() => setKeysSheet(false)} />
  </AppCtx.Provider>;
}

createRoot(document.getElementById("root")).render(<App />);

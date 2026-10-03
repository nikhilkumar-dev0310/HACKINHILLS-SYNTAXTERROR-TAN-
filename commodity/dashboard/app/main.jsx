import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { createRoot } from "react-dom/client";
import { D, NAME, VIEWS, SYMS, SYM, EVENTS, GLOSSARY, fdate, pname, reducedMotion } from "./lib.js";
import { AppCtx, Icon } from "./ui.jsx";

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
  useEffect(() => { const r = document.documentElement; t === "system" ? r.removeAttribute("data-theme") : r.setAttribute("data-theme", t); store.set("parity-theme", t); }, [t]);
  return [t, setT];
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

/* ---------- app */
function App() {
  const init = () => { const h = location.hash.slice(1); return PAGES[h] ? h : store.get("gsl-view", "overview"); };
  const [view, setView] = useState(init), [theme, setTheme] = useTheme();
  const [pal, setPal] = useState(false), [news, setNews] = useState(false), [more, setMore] = useState(false);
  const [keysOn, setKeysOnS] = useState(() => store.get("gsl-keys", "on") !== "off");
  const [rvPair, setRvPair] = useState("M-GUINEA"), [calF, setCalF] = useState("All");
  const userNav = useRef(false);
  const setKeysOn = v => { setKeysOnS(v); store.set("gsl-keys", v ? "on" : "off"); };
  const go = useCallback(id => { userNav.current = true; setMore(false); if (location.hash.slice(1) !== id) location.hash = id; else { setView(id); focusHead(); } }, []);
  const focusHead = () => requestAnimationFrame(() => { const h = document.querySelector("main h1"); if (h) h.focus({ preventScroll: true }); });
  useEffect(() => { const on = () => { const h = location.hash.slice(1); if (PAGES[h]) { userNav.current = true; setView(h); } }; addEventListener("hashchange", on); return () => removeEventListener("hashchange", on); }, []);
  useEffect(() => { document.title = view === "overview" ? `${NAME} · MCX gold futures` : `${label(view)} · ${NAME}`; store.set("gsl-view", view);
    if (userNav.current) { scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" }); focusHead(); userNav.current = false; } }, [view]);
  useEffect(() => { const k = e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setNews(false); setPal(p => !p); return; }
    if (pal || news || !keysOn || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return;
    if (e.target.closest && e.target.closest("input, textarea, select, [contenteditable]")) return;
    if (e.key === "/") { e.preventDefault(); setPal(true); return; }
    const n = "12345678".indexOf(e.key); if (n < 0 || e.key.length !== 1) return; e.preventDefault(); go(VIEWS[n][0]); };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k); }, [pal, news, keysOn]);
  useEffect(() => { document.documentElement.classList.toggle("nokeys", !keysOn); }, [keysOn]);
  const ctx = { view, go, rvPair, setRvPair, calF, setCalF, theme, setTheme, keysOn, setKeysOn, setNews, setPal };
  const Page = PAGES[view], idx = VIEWS.findIndex(v => v[0] === view);
  const newest = D.changelog && D.changelog[0];
  return <AppCtx.Provider value={ctx}>
    <a className="skip" href="#main" onClick={e => { e.preventDefault(); focusHead(); }}>Skip to content</a>
    <div className="bgfx" aria-hidden="true"><i /><i /></div>
    <header className="top">
      <a className="brand" href="#overview" aria-label={`${NAME}, overview`} onClick={e => { e.preventDefault(); go("overview"); }}><Mark /><span className="wm">{NAME}<small>MCX gold futures</small></span></a>
      <div className="crumb" aria-hidden="true"><span className="num">{String(idx + 1).padStart(2, "0")} / 08</span>{label(view)}</div>
      <div className="top-r">
        <button type="button" className="search" onClick={() => setPal(true)} aria-label="Search (Ctrl+K)"><Icon name="search" size={16} /><span className="sl">Search</span><kbd>{isMac ? "⌘" : "Ctrl"} K</kbd></button>
        <button type="button" className="iconbtn" onClick={() => setNews(true)} aria-label="What's new" title={newest ? `What's new · latest ${fdate(newest.date)}` : "What's new"}><Icon name="news" size={18} /></button>
        <ThemeSwitch theme={theme} setTheme={setTheme} />
      </div>
    </header>
    <nav className="strip" aria-label="Sections">{VIEWS.map(([id, l], i) => <a key={id} href={"#" + id} aria-current={id === view ? "page" : undefined}><span className="num">{String(i + 1).padStart(2, "0")}</span>{l}</a>)}</nav>
    <div className="shell">
      <aside className="rail">
        <nav aria-label="Sections">{VIEWS.map(([id, l], i) => <a key={id} href={"#" + id} aria-current={id === view ? "page" : undefined} aria-keyshortcuts={keysOn ? String(i + 1) : undefined}>
          <span className="num">{String(i + 1).padStart(2, "0")}</span><span className="rl">{l}</span><kbd className="key" aria-hidden="true">{i + 1}</kbd></a>)}</nav>
        <div className="rail-f">
          <div className="live" title={D.meta.last_full !== D.meta.last ? `Full futures curve to ${fdate(D.meta.last_full)}. Later rows, to ${fdate(D.meta.last)}, cover only contracts running into their expiry.` : undefined}><span className="pulse" />Data through <b className="num">{fdate(D.meta.last_full || D.meta.last)}</b></div>
          <div>Official MCX Bhavcopy · end of day</div>
          <div className="keys">{keysOn ? <><span className="kh"><kbd>1</kbd>–<kbd>8</kbd> sections · <kbd>/</kbd> search</span><button type="button" className="linkbtn" onClick={() => setKeysOn(false)}>Turn off shortcuts</button></>
            : <button type="button" className="linkbtn" onClick={() => setKeysOn(true)}>Turn on number-key shortcuts</button>}</div>
        </div>
      </aside>
      <main id="main" key={view} className="page">
        <Page />
        <footer className="foot"><span>Source: MCX Bhavcopy (mcxindia.com). Code and data: github.com/nikhilkumar-dev0310/HACKINHILLS-SYNTAXTERROR-TAN-</span><span>Exported <span className="num">{D.meta.exported}</span></span></footer>
      </main>
    </div>
    <nav className="tabbar" aria-label="Sections">
      {TABS.map(id => <a key={id} href={"#" + id} aria-current={id === view ? "page" : undefined}><Icon name={id} size={20} /><span>{id === "brief" ? "Brief" : label(id)}</span></a>)}
      <button type="button" aria-expanded={more} aria-current={!TABS.includes(view) ? "page" : undefined} onClick={() => setMore(m => !m)}><Icon name="more" size={20} /><span>More</span></button>
    </nav>
    {more && <div className="overlay sheet-o" onMouseDown={e => e.target === e.currentTarget && setMore(false)} onKeyDown={e => e.key === "Escape" && setMore(false)}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label="More sections">
        <div className="grab" aria-hidden="true" />
        {VIEWS.filter(v => !TABS.includes(v[0])).map(([id, l]) => <a key={id} href={"#" + id} onClick={() => setMore(false)} aria-current={id === view ? "page" : undefined}><Icon name={id} size={20} />{l}</a>)}
        <button type="button" onClick={() => { setMore(false); setPal(true); }}><Icon name="search" size={20} />Search</button>
        <button type="button" onClick={() => { setMore(false); setNews(true); }}><Icon name="news" size={20} />What's new</button>
      </div></div>}
    <Palette open={pal} onClose={() => setPal(false)} go={go} ctx={ctx} />
    <News open={news} onClose={() => setNews(false)} />
  </AppCtx.Provider>;
}

createRoot(document.getElementById("root")).render(<App />);

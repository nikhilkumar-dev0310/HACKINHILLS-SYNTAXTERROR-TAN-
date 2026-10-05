import { useEffect, useLayoutEffect, useRef, useState, useId, createContext, useContext } from "react";
import { createPortal } from "react-dom";
import { ICON, GLOSSARY, inr, reducedMotion } from "./lib.js";

export const AppCtx = createContext(null);
export const useApp = () => useContext(AppCtx);

export function Icon({ name, size = 18, sw = 1.7 }) {
  return <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" dangerouslySetInnerHTML={{ __html: ICON[name] }} />;
}

/* An imperative SVG chart, redrawn when its inputs change or its width changes by more than 30 px. */
export function Chart({ draw, deps = [], className = "", style }) {
  const ref = useRef(null), last = useRef(0), fn = useRef(draw); fn.current = draw;
  useLayoutEffect(() => { const el = ref.current; if (!el) return; last.current = el.clientWidth; fn.current(el); }, deps);
  useEffect(() => { const el = ref.current; if (!el) return;
    const ro = new ResizeObserver(() => { const w = el.clientWidth; if (Math.abs(w - last.current) > 30) { last.current = w; fn.current(el); } });
    ro.observe(el); return () => ro.disconnect(); }, []);
  return <div ref={ref} className={"chart " + className} style={style} />;
}

/* Scroll reveal: children fade and rise once when they enter the viewport.
   "in" lives in React state, so a later className change (e.g. a mode switch) cannot strip it and hide the element. */
export function useReveal() {
  const ref = useRef(null), [shown, setShown] = useState(() => reducedMotion() || !("IntersectionObserver" in window));
  useEffect(() => { const el = ref.current; if (!el || shown) return;
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { setShown(true); io.disconnect(); } }), { rootMargin: "0px 0px -8% 0px" });
    io.observe(el); return () => io.disconnect(); }, [shown]);
  return [ref, shown];
}
export function Reveal({ as: Tag = "div", className = "", children, ...rest }) {
  const [ref, shown] = useReveal(); return <Tag ref={ref} className={"rv " + className + (shown ? " in" : "")} {...rest}>{children}</Tag>;
}

export function Card({ fig, title, sub, actions, children, className = "", id }) {
  return <Reveal as="section" className={"card " + className} id={id} aria-label={typeof title === "string" ? title : undefined}>
    {(title || actions) && <header className="card-h">
      <div className="card-t">{title && <h2>{title}</h2>}{sub && <p className="sub">{sub}</p>}</div>
      {actions && <div className="acts">{actions}</div>}
    </header>}
    {children}
  </Reveal>;
}

/* Numbers that count to their new value: 400 ms on cubic-bezier(.2,0,0,1). The value on screen is kept per key, so a
   change mid-way starts from what the reader sees. intro: count up from zero the first time it scrolls into view. */
const easeStd = x => { let lo = 0, hi = 1, t = x; for (let i = 0; i < 24; i++) { t = (lo + hi) / 2; const xt = .6 * t * (1 - t) ** 2 + t ** 3; if (xt < x) lo = t; else hi = t; } return 3 * (1 - t) * t * t + t ** 3; };
const SHOWN = {};
export const FMT = { inr: v => inr(Math.round(v) || 0), int: v => Math.round(v).toLocaleString("en-IN"), pct: v => v.toFixed(0), d1: v => v.toFixed(1), sgn1: v => (v > 0.05 ? "+" : v < -0.05 ? "−" : "") + Math.abs(v).toFixed(1) };
export function Num({ v, f = "int", k, intro = false, dur = 400 }) {
  const key = useRef(k || "n" + Math.random().toString(36).slice(2)).current;
  const span = useRef(null), raf = useRef(0), seen = useRef(!intro);
  const paint = x => { SHOWN[key] = x; if (span.current) span.current.textContent = FMT[f](x); };
  const run = (from, to, d) => { cancelAnimationFrame(raf.current);
    if (from == null || from === to || reducedMotion()) { paint(to); return; }
    const t0 = performance.now(); const step = now => { const p = Math.min(1, (now - t0) / d); paint(from + (to - from) * easeStd(p)); if (p < 1) raf.current = requestAnimationFrame(step); };
    raf.current = requestAnimationFrame(step); };
  const target = useRef(v); target.current = v;
  useLayoutEffect(() => { if (!seen.current) return; run(SHOWN[key], v, dur); }, [v]);
  useLayoutEffect(() => { if (!intro) return; const el = span.current;
    if (reducedMotion() || !("IntersectionObserver" in window)) { seen.current = true; paint(target.current); return; }
    paint(0); const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { seen.current = true; run(0, target.current, 1100); io.disconnect(); } }, { threshold: .4 });
    io.observe(el); return () => io.disconnect(); }, []);
  useEffect(() => () => cancelAnimationFrame(raf.current), []);
  return <span ref={span} className="numv" />;
}

export function Kpi({ label, children, note, tone = "", big }) {
  return <Reveal className={"kpi " + tone + (big ? " big" : "")}><div className="lab">{label}</div><div className="val">{children}</div>{note && <div className="note">{note}</div>}</Reveal>;
}

export function Seg({ options, value, onChange, label, small }) {
  return <div className={"seg" + (small ? " sm" : "")} role="group" aria-label={label}>
    {options.map(([v, l]) => <button key={v} type="button" aria-pressed={v === value} onClick={() => onChange(v)}>{l}</button>)}
  </div>;
}
export const Pill = ({ tone = "neutral", children, title }) => <span className={"pill " + tone} title={title}>{children}</span>;
export const Legend = ({ items, band }) => <div className="legend">{items.map(([c, l]) => <span key={l}><i style={{ background: c }} />{l}</span>)}{band && <span><i className="box" />Crash period</span>}</div>;

/* Jargon with a plain-English definition on hover, keyboard focus or tap. */
/* Hover (mouse) opens after a short intent delay so sweeping the cursor across text does not flash cards; tap or
   keyboard focus opens at once. The card grows out of the word it explains, with a small arrow pointing back to it. */
export function Term({ k, children }) {
  const [open, setOpen] = useState(false), [pos, setPos] = useState(null), ref = useRef(null), tm = useRef(0), id = useId(), g = GLOSSARY[k];
  const place = () => { const r = ref.current.getBoundingClientRect(), w = Math.min(320, innerWidth - 24), cx = r.left + r.width / 2;
    const left = Math.max(12, Math.min(innerWidth - w - 12, cx - w / 2)), up = r.bottom + 150 > innerHeight && r.top > 160;
    setPos({ left, w, up, top: r.bottom + 10, bottom: innerHeight - r.top + 10, ax: Math.max(14, Math.min(w - 14, cx - left)) }); };
  const show = () => { clearTimeout(tm.current); place(); setOpen(true); };
  const hide = () => { clearTimeout(tm.current); setOpen(false); };
  useEffect(() => { if (!open) return; const off = () => setOpen(false);
    const out = e => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    addEventListener("scroll", off, true); addEventListener("pointerdown", out, true);
    return () => { removeEventListener("scroll", off, true); removeEventListener("pointerdown", out, true); }; }, [open]);
  useEffect(() => () => clearTimeout(tm.current), []);
  if (!g) return children;
  return <>
    <span role="button" tabIndex={0} ref={ref} className={"term" + (open ? " on" : "")} aria-describedby={open ? id : undefined} aria-expanded={open}
      onPointerEnter={e => { if (e.pointerType === "mouse") { clearTimeout(tm.current); tm.current = setTimeout(show, 90); } }}
      onPointerLeave={e => { if (e.pointerType === "mouse") hide(); }}
      onFocus={e => { if (e.target.matches(":focus-visible")) show(); }} onBlur={hide}
      onClick={e => { e.stopPropagation(); e.preventDefault(); open ? hide() : show(); }}
      onKeyDown={e => { if (e.key === "Escape") hide(); else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open ? hide() : show(); } }}>{children}</span>
    {open && pos && createPortal(<div id={id} role="tooltip" className={"gloss" + (pos.up ? " up" : "")} style={{ left: pos.left, width: pos.w, "--ax": pos.ax + "px", ...(pos.up ? { bottom: pos.bottom } : { top: pos.top }) }}>
      <b>{g[0]}</b>{g[1]}</div>, document.body)}
  </>;
}

/* Every definition on the site in one place, A to Z. */
export function Glossary() {
  const [q, setQ] = useState("");
  const all = Object.entries(GLOSSARY).sort((a, b) => a[1][0].localeCompare(b[1][0], "en", { sensitivity: "base" }));
  const list = all.filter(([, [t, d]]) => !q || (t + " " + d).toLowerCase().includes(q.toLowerCase()));
  return <div className="glossary">
    <label className="gl-s"><Icon name="search" size={16} /><input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder={`Filter ${all.length} terms…`} aria-label="Filter the glossary" /></label>
    <dl className="gl">{list.map(([key, [t, d]]) => <div key={key}><dt>{t}</dt><dd>{d}</dd></div>)}</dl>
    {!list.length && <p className="note">No term matches “{q}”.</p>}
  </div>;
}

export function Hero({ n, eyebrow, title, children, aside }) {
  return <header className="hero">
    <Reveal className="hero-t">
      <div className="eyebrow"><span className="idx">{String(n).padStart(2, "0")}</span>{eyebrow}</div>
      <h1 tabIndex={-1}>{title}</h1>
      {children && <p className="lead">{children}</p>}
    </Reveal>
    {aside}
  </header>;
}

/* Pager for long tables */
export function Pager({ page, pages, set, prev = "← Previous", next = "Next →" }) {
  if (pages <= 1) return null;
  return <div className="pager"><button type="button" disabled={page === 0} onClick={() => set(page - 1)}>{prev}</button><span className="num">{page + 1} / {pages}</span><button type="button" disabled={page === pages - 1} onClick={() => set(page + 1)}>{next}</button></div>;
}

export function downloadCSV(name, header, rows) {
  const esc = v => { if (v == null || (typeof v === "number" && !isFinite(v))) return ""; const s = String(v); return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const url = URL.createObjectURL(new Blob([[header, ...rows].map(r => r.map(esc).join(",")).join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 4000);
}
export function CsvButton({ label, onClick, text = "Download CSV" }) {
  return <button type="button" className="btn dlb" aria-label={label} title={label} onClick={onClick}><Icon name="download" size={16} />{text}</button>;
}

/* "In short": the one thing to take from a page, said first. */
export function Takeaway({ children, points }) {
  return <Reveal className="take" role="note" aria-label="In short">
    <div className="take-l">In short</div>
    <div className="take-b"><p className="take-p">{children}</p>
      {points && <ol className="take-pts">{points.map((p, i) => <li key={i}><span className="tn">{i + 1}</span><span>{p}</span></li>)}</ol>}</div>
  </Reveal>;
}

/* Detail on demand: a native disclosure, closed by default, so a page shows its answer first. */
export function More({ title, hint, children, open = false }) {
  return <details className="more" open={open}>
    <summary><span className="mt-t">{title}</span>{hint && <span className="mt-h">{hint}</span>}<span className="chev" aria-hidden="true" /></summary>
    <div className="more-b">{children}</div>
  </details>;
}

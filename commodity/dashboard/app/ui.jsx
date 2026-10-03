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

/* Scroll reveal: children fade and rise once when they enter the viewport. */
export function useReveal() {
  const ref = useRef(null);
  useEffect(() => { const el = ref.current; if (!el) return;
    if (reducedMotion() || !("IntersectionObserver" in window)) { el.classList.add("in"); return; }
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px" });
    io.observe(el); return () => io.disconnect(); }, []);
  return ref;
}
export function Reveal({ as: Tag = "div", className = "", children, ...rest }) {
  const ref = useReveal(); return <Tag ref={ref} className={"rv " + className} {...rest}>{children}</Tag>;
}

export function Card({ fig, title, sub, actions, children, className = "", id }) {
  return <Reveal as="section" className={"card " + className} id={id} aria-label={typeof title === "string" ? title : undefined}>
    {(title || actions) && <header className="card-h">
      <div className="card-t">{fig && <span className="fig">{fig}</span>}{title && <h2>{title}</h2>}{sub && <p className="sub">{sub}</p>}</div>
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
export function Term({ k, children }) {
  const [open, setOpen] = useState(false), [pos, setPos] = useState(null), ref = useRef(null), id = useId(), g = GLOSSARY[k];
  if (!g) return children;
  const show = () => { const r = ref.current.getBoundingClientRect(); const w = Math.min(300, innerWidth - 24);
    setPos({ left: Math.max(12, Math.min(innerWidth - w - 12, r.left + r.width / 2 - w / 2)), top: r.bottom + 8, w, up: r.bottom + 120 > innerHeight, bottom: innerHeight - r.top + 8 }); setOpen(true); };
  useEffect(() => { if (!open) return; const off = () => setOpen(false); addEventListener("scroll", off, true); return () => removeEventListener("scroll", off, true); }, [open]);
  return <>
    <button type="button" ref={ref} className="term" aria-describedby={open ? id : undefined} onMouseEnter={show} onMouseLeave={() => setOpen(false)}
      onFocus={show} onBlur={() => setOpen(false)} onClick={() => open ? setOpen(false) : show()} onKeyDown={e => e.key === "Escape" && setOpen(false)}>{children}</button>
    {open && pos && createPortal(<div id={id} role="tooltip" className="gloss" style={{ left: pos.left, width: pos.w, ...(pos.up ? { bottom: pos.bottom } : { top: pos.top }) }}><b>{g[0]}</b>{g[1]}</div>, document.body)}
  </>;
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
export function CsvButton({ label, onClick }) {
  return <button type="button" className="btn" aria-label={label} title={label} onClick={onClick}><Icon name="download" size={16} />CSV</button>;
}

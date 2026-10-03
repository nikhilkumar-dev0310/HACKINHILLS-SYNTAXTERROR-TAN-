/* Imperative SVG charts, carried over from the earlier dashboard (crosshair, axis badges, true minus signs),
   plus event notes on time charts. React calls these from <Chart draw={...}/>. */
import { MON, T, fdate, mm, EVENTS, SYM, CRASH, inr, sgn, fmon, D } from "./lib.js";

const NS = "http://www.w3.org/2000/svg";
export const sv = (t, a = {}) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function tipFor(host) { let t = host.querySelector(".tip"); if (!t) { t = document.createElement("div"); t.className = "tip"; t.setAttribute("role", "status"); host.appendChild(t); } return t; }
export function placeTip(host, tip, x, y) {
  const w = host.clientWidth, tw = tip.offsetWidth, th = tip.offsetHeight;
  let left = x + 16; if (left + tw > w) left = x - tw - 16; if (left < 0) left = 0;
  let top = y - th - 12; if (top < 0) top = y + 16;
  tip.style.left = left + "px"; tip.style.top = top + "px"; tip.classList.add("show");
}
export function nice(lo, hi, n = 5) {
  if (lo === hi) { lo -= 1; hi += 1; }
  const raw = (hi - lo) / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
  const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
  const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, ticks = [];
  for (let v = a; v <= b + step / 2; v += step) ticks.push(+v.toFixed(10));
  return { lo: a, hi: b, ticks };
}
export function monthTicks(t0, t1, maxN) {
  const out = []; const d = new Date(t0); d.setUTCDate(1); d.setUTCMonth(d.getUTCMonth() + 1);
  while (d.getTime() <= t1) { out.push(d.getTime()); d.setUTCMonth(d.getUTCMonth() + 1); }
  const step = Math.max(1, Math.ceil(out.length / maxN)); return out.filter((_, i) => i % step === 0);
}
const monthLabel = tt => { const d = new Date(tt); return MON[d.getUTCMonth()] + " " + String(d.getUTCFullYear()).slice(2); };
function crashBand(svg, X, t0, t1, y, h, label, H, m) {
  const a = Math.max(T(CRASH[0]), t0), b = Math.min(T(CRASH[1]), t1); if (b <= a) return;
  svg.appendChild(sv("rect", { x: X(a), y, width: X(b) - X(a), height: h, fill: "var(--band)" }));
  if (label) { const tx = sv("text", { x: (X(a) + X(b)) / 2, y: H - m.b - 8, "text-anchor": "middle", class: "bandlbl" }); tx.textContent = "crash period"; svg.appendChild(tx); }
}

/* event notes: dashed rule + marker + short label (wide charts), full note on hover or focus */
function drawEvents(svg, host, X, t0, t1, m, H, W) {
  const evs = EVENTS.filter(e => T(e.date) >= t0 && T(e.date) <= t1); if (!evs.length) return [];
  const g = sv("g", { class: "evts" }), lastRight = [-1e9, -1e9], wide = W >= 640, tip = tipFor(host);
  svg.appendChild(g);                                         // in the document, so label widths can be measured
  evs.forEach(e => {
    const x = X(T(e.date)), y0 = m.t;
    g.appendChild(sv("line", { x1: x, x2: x, y1: y0, y2: H - m.b, class: "evline" }));
    const mk = sv("g", { class: "evmark", tabindex: 0, role: "img", "aria-label": `${fdate(e.date)}: ${e.text}` });
    mk.appendChild(sv("circle", { cx: x, cy: y0, r: 10, fill: "transparent" }));
    mk.appendChild(sv("circle", { cx: x, cy: y0, r: 3.5, class: "evdot" }));
    g.appendChild(mk);
    if (wide) {
      const t = sv("text", { class: "evtag" }); t.textContent = e.tag; mk.appendChild(t);
      const w = t.getComputedTextLength(), lx = Math.min(x + 7, W - m.r - w);
      const row = [0, 1].find(r => lx >= lastRight[r] + 8);
      if (row == null) t.remove(); else { t.setAttribute("x", lx); t.setAttribute("y", y0 - 20 + row * 12); lastRight[row] = lx + w; }
    }
    const showTip = () => { tip.innerHTML = `<div class="t">${fdate(e.date)}</div><div class="evtxt">${esc(e.text)}</div><div class="evsrc">${esc(e.src)}</div>`; placeTip(host, tip, x, y0); };
    mk.addEventListener("mouseenter", showTip); mk.addEventListener("focus", showTip);
    mk.addEventListener("mouseleave", () => tip.classList.remove("show")); mk.addEventListener("blur", () => tip.classList.remove("show"));
  });
  return [g, evs];
}

export function lineChart(host, o) {
  host.innerHTML = ""; const W = Math.max(host.clientWidth, 280), H = o.h || (W < 560 ? 240 : 310);
  const narrow = W < 560, endL = o.endLabels && !narrow, ev = o.events !== false && o.dates.length > 30;
  const m = { l: 62, r: endL ? 96 : 16, t: ev ? (W >= 640 ? 44 : 20) : 14, b: 30 };
  const xs = o.dates.map(T); const t0 = xs[0], t1 = xs[xs.length - 1];
  let vals = []; o.series.forEach(s => s.values.forEach(v => v != null && vals.push(v)));
  if (o.zero) vals.push(0);
  const sc = nice(Math.min(...vals), Math.max(...vals), H < 150 ? 2 : 5);
  const X = t => m.l + (t - t0) / (t1 - t0 || 1) * (W - m.l - m.r), Y = v => m.t + (sc.hi - v) / (sc.hi - sc.lo) * (H - m.t - m.b);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.aria || "" });
  if (o.band) crashBand(svg, X, t0, t1, m.t, H - m.t - m.b, true, H, m);
  sc.ticks.forEach(v => { svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0 && o.zero ? "zero" : "gridl" }));
    const t = sv("text", { x: m.l - 10, y: Y(v) + 4, "text-anchor": "end" }); t.textContent = mm((o.yfmt || (x => x))(v)); svg.appendChild(t); });
  monthTicks(t0, t1, W < 420 ? 3 : W < 560 ? 4 : 8).forEach(tt => { svg.appendChild(sv("line", { x1: X(tt), x2: X(tt), y1: m.t, y2: H - m.b, class: "gridl" }));
    const t = sv("text", { x: X(tt), y: H - 8, "text-anchor": "middle" }); t.textContent = monthLabel(tt); svg.appendChild(t); });
  const G = sv("g", { class: "reveal" });
  if (o.hline != null) svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: Y(o.hline), y2: Y(o.hline), stroke: "var(--gold)", "stroke-dasharray": "5 4", "stroke-width": 1.2, opacity: .8 }));
  o.series.forEach((s, si) => {
    let d = "", pen = false;
    s.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + X(xs[i]).toFixed(1) + " " + Y(v).toFixed(1); pen = true; });
    if (o.area && si === 0) { const pts = s.values.map((v, i) => v == null ? null : [X(xs[i]), Y(v)]).filter(Boolean);
      if (pts.length) { const id = "g" + Math.random().toString(36).slice(2, 7); const g = sv("linearGradient", { id, x1: 0, x2: 0, y1: 0, y2: 1 });
        g.appendChild(sv("stop", { offset: "0", style: `stop-color:${s.color};stop-opacity:.24` })); g.appendChild(sv("stop", { offset: "1", style: `stop-color:${s.color};stop-opacity:0` }));
        const defs = sv("defs"); defs.appendChild(g); svg.appendChild(defs);
        const base = Y(Math.max(sc.lo, Math.min(0, sc.hi)));
        G.appendChild(sv("path", { d: `M${pts[0][0]} ${base}` + pts.map(p => `L${p[0]} ${p[1]}`).join("") + `L${pts[pts.length - 1][0]} ${base}Z`, fill: `url(#${id})` })); } }
    const p = sv("path", { d, class: "line", style: `stroke:${s.color}` }); if (s.dash) p.setAttribute("stroke-dasharray", "4 4"); G.appendChild(p);
    if (endL) { let li = s.values.length - 1; while (li > 0 && s.values[li] == null) li--; s._ly = Y(s.values[li]); }
  });
  svg.appendChild(G);
  if (endL) { const ls = o.series.filter(s => s._ly != null).sort((a, b) => a._ly - b._ly);
    for (let i = 1; i < ls.length; i++) if (ls[i]._ly - ls[i - 1]._ly < 15) ls[i]._ly = ls[i - 1]._ly + 15;
    ls.forEach(s => { const t = sv("text", { x: W - m.r + 10, y: s._ly + 4, class: "lbl", style: `fill:${s.color}` }); t.textContent = s.label; svg.appendChild(t); }); }
  const cross = sv("line", { class: "cross", y1: m.t, y2: H - m.b, opacity: 0 }); svg.appendChild(cross);
  const crossY = sv("line", { class: "cross", x1: m.l, x2: W - m.r, opacity: 0 }); svg.appendChild(crossY);
  const badge = () => { const g = sv("g", { class: "axbadge", opacity: 0 }); const r = sv("rect", { rx: 4, height: 18 }); const t = sv("text", {}); g.append(r, t); svg.appendChild(g); return { g, r, t }; };
  const bx = badge(), by = badge();
  const dots = o.series.map(s => { const c = sv("circle", { r: 4.5, style: `fill:${s.color};stroke:var(--panel);stroke-width:2`, opacity: 0 }); svg.appendChild(c); return c; });
  const hit = sv("rect", { x: m.l, y: m.t, width: W - m.l - m.r, height: H - m.t - m.b, fill: "transparent", style: "cursor:crosshair" }); svg.appendChild(hit);
  host.appendChild(svg);
  let evs = []; if (ev) { const r = drawEvents(svg, host, X, t0, t1, m, H, W); if (r.length) evs = r[1]; }
  const tip = tipFor(host);
  const move = e => { const r = svg.getBoundingClientRect(); const px = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
    const tt = t0 + (px - m.l) / (W - m.l - m.r) * (t1 - t0); let i = 0, best = Infinity; xs.forEach((x, j) => { const dd = Math.abs(x - tt); if (dd < best) { best = dd; i = j; } });
    const x = X(xs[i]); cross.setAttribute("x1", x); cross.setAttribute("x2", x); cross.setAttribute("opacity", 1);
    const py = Math.max(m.t, Math.min(H - m.b, (e.touches ? e.touches[0].clientY : e.clientY) - r.top));
    const yv = sc.hi - (py - m.t) / (H - m.t - m.b) * (sc.hi - sc.lo);
    crossY.setAttribute("y1", py); crossY.setAttribute("y2", py); crossY.setAttribute("opacity", 1);
    bx.t.textContent = fdate(o.dates[i]); const bw = bx.t.getComputedTextLength() + 14, bxl = Math.max(m.l, Math.min(W - m.r - bw, x - bw / 2));
    bx.r.setAttribute("x", bxl); bx.r.setAttribute("y", H - m.b + 4); bx.r.setAttribute("width", bw);
    bx.t.setAttribute("x", bxl + 7); bx.t.setAttribute("y", H - m.b + 17); bx.g.setAttribute("opacity", 1);
    by.t.textContent = mm((o.yfmt || (z => z))(+yv.toFixed(Math.abs(sc.hi - sc.lo) < 10 ? 2 : 0)));
    by.r.setAttribute("x", 0); by.r.setAttribute("y", py - 9); by.r.setAttribute("width", m.l - 4);
    by.t.setAttribute("x", m.l - 9); by.t.setAttribute("text-anchor", "end"); by.t.setAttribute("y", py + 4); by.g.setAttribute("opacity", 1);
    let rows = ""; o.series.forEach((s, k) => { const v = s.values[i]; if (v == null) { dots[k].setAttribute("opacity", 0); return; }
      dots[k].setAttribute("cx", x); dots[k].setAttribute("cy", Y(v)); dots[k].setAttribute("opacity", 1);
      rows += `<div class="r"><span><i style="background:${s.color}"></i>${s.label}</span><b>${(o.tfmt || o.yfmt || (z => z))(v)}</b></div>`; });
    const evHere = evs.find(e2 => e2.date === o.dates[i]);
    tip.innerHTML = `<div class="t">${fdate(o.dates[i])}</div>${rows}${o.extra ? o.extra(i) : ""}${evHere ? `<div class="evtxt sep">${esc(evHere.text)}</div>` : ""}`;
    placeTip(host, tip, x, Y(o.series.map(s => s.values[i]).find(v => v != null) ?? 0)); };
  const leave = () => { [cross, crossY].forEach(c => c.setAttribute("opacity", 0)); bx.g.setAttribute("opacity", 0); by.g.setAttribute("opacity", 0); dots.forEach(d => d.setAttribute("opacity", 0)); tip.classList.remove("show"); };
  hit.addEventListener("mousemove", move); hit.addEventListener("touchmove", move, { passive: true }); hit.addEventListener("mouseleave", leave); hit.addEventListener("touchend", leave);
}

export function barChart(host, o) {
  host.innerHTML = ""; const W = Math.max(host.clientWidth, 260), H = o.h || 260, m = { l: 56, r: 8, t: 22, b: 30 };
  const vals = o.values.concat([0]); const sc = nice(Math.min(...vals), Math.max(...vals), 4);
  const n = o.values.length, bw = (W - m.l - m.r) / n, Y = v => m.t + (sc.hi - v) / (sc.hi - sc.lo) * (H - m.t - m.b);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.aria || "" });
  sc.ticks.forEach(v => { svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0 ? "zero" : "gridl" }));
    const t = sv("text", { x: m.l - 10, y: Y(v) + 4, "text-anchor": "end" }); t.textContent = mm(o.yfmt(v)); svg.appendChild(t); });
  const step = Math.ceil(n / (W < 480 ? 5 : 10)); const tip = tipFor(host);
  o.values.forEach((v, i) => { const x = m.l + i * bw + bw * .18, w = bw * .64, y0 = Y(0), y1 = Y(v);
    const r = sv("rect", { x, width: w, y: Math.min(y0, y1), height: Math.max(1, Math.abs(y1 - y0)), rx: 2, class: "bar", style: `fill:${v >= 0 ? "var(--good)" : "var(--bad)"}` });
    r.style.transformOrigin = `${x + w / 2}px ${y0}px`; r.animate([{ transform: "scaleY(0)" }, { transform: "scaleY(1)" }], { duration: 700, delay: i * 35, easing: "cubic-bezier(.2,.8,.2,1)", fill: "backwards" });
    r.addEventListener("mouseenter", () => { tip.innerHTML = `<div class="t">${o.labels[i]}</div><div class="r"><span>Net</span><b>${o.tfmt(v)}</b></div>${o.extra ? o.extra(i) : ""}`; placeTip(host, tip, x + w / 2, Math.min(y0, y1)); });
    r.addEventListener("mouseleave", () => tip.classList.remove("show")); svg.appendChild(r);
    if (i % step === 0) { const t = sv("text", { x: x + w / 2, y: H - 8, "text-anchor": "middle" }); t.textContent = o.short ? o.short(i) : o.labels[i]; svg.appendChild(t); } });
  host.appendChild(svg);
}

export function scatter(host, o) {
  host.innerHTML = ""; const W = Math.max(host.clientWidth, 260), H = o.h || 290, m = { l: 62, r: 14, t: 12, b: 44 };
  const sx = nice(Math.min(...o.x, 0), Math.max(...o.x, 0), 6), sy = nice(Math.min(...o.y, 0), Math.max(...o.y, 0), 5);
  const X = v => m.l + (v - sx.lo) / (sx.hi - sx.lo) * (W - m.l - m.r), Y = v => m.t + (sy.hi - v) / (sy.hi - sy.lo) * (H - m.t - m.b);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.aria || "" });
  sy.ticks.forEach(v => { svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0 ? "zero" : "gridl" })); const t = sv("text", { x: m.l - 10, y: Y(v) + 4, "text-anchor": "end" }); t.textContent = mm(o.yfmt(v)); svg.appendChild(t); });
  sx.ticks.forEach(v => { svg.appendChild(sv("line", { x1: X(v), x2: X(v), y1: m.t, y2: H - m.b, class: v === 0 ? "zero" : "gridl" })); const t = sv("text", { x: X(v), y: H - 24, "text-anchor": "middle" }); t.textContent = mm(o.xfmt(v)); svg.appendChild(t); });
  const xl = sv("text", { x: W - m.r, y: H - 1, "text-anchor": "end" }); xl.textContent = o.xlabel; svg.appendChild(xl);
  const tip = tipFor(host);
  o.x.forEach((xv, i) => { const c = sv("circle", { cx: X(xv), cy: Y(o.y[i]), r: 5.5, style: `fill:${o.color(i)};fill-opacity:.75;stroke:var(--panel);stroke-width:1.5;cursor:pointer` });
    c.style.transformOrigin = `${X(xv)}px ${Y(o.y[i])}px`; c.animate([{ transform: "scale(0)" }, { transform: "scale(1)" }], { duration: 450, delay: Math.min(i * 6, 600), fill: "backwards", easing: "cubic-bezier(.2,.8,.2,1)" });
    c.addEventListener("mouseenter", () => { c.setAttribute("r", 8); tip.innerHTML = o.tip(i); placeTip(host, tip, X(xv), Y(o.y[i])); });
    c.addEventListener("mouseleave", () => { c.setAttribute("r", 5.5); tip.classList.remove("show"); }); svg.appendChild(c); });
  host.appendChild(svg);
}

export function groupBars(host, o) {
  host.innerHTML = ""; const W = Math.max(host.clientWidth, 260), H = o.h || 260, m = { l: 56, r: 8, t: 14, b: 30 };
  const all = o.a.concat(o.b, [0]); const sc = nice(Math.min(...all), Math.max(...all), 5);
  const n = o.labels.length, bw = (W - m.l - m.r) / n, Y = v => m.t + (sc.hi - v) / (sc.hi - sc.lo) * (H - m.t - m.b);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": o.aria || "" });
  sc.ticks.forEach(v => { svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: v === 0 ? "zero" : "gridl" })); const t = sv("text", { x: m.l - 10, y: Y(v) + 4, "text-anchor": "end" }); t.textContent = mm(o.yfmt(v)); svg.appendChild(t); });
  const step = Math.ceil(n / (W < 480 ? 5 : 12)); const tip = tipFor(host);
  o.labels.forEach((lab, i) => { const g = sv("g", { class: "bar" }); [[o.a[i], "var(--gold)", 0], [o.b[i], "var(--teal)", 1]].forEach(([v, col, k]) => {
      const w = bw * .34, x = m.l + i * bw + bw * .14 + k * (w + bw * .04), y0 = Y(0), y1 = Y(v);
      const r = sv("rect", { x, width: w, y: Math.min(y0, y1), height: Math.max(1, Math.abs(y1 - y0)), rx: 1.5, style: `fill:${col}` });
      r.style.transformOrigin = `${x}px ${y0}px`; r.animate([{ transform: "scaleY(0)" }, { transform: "scaleY(1)" }], { duration: 650, delay: i * 25, fill: "backwards", easing: "cubic-bezier(.2,.8,.2,1)" }); g.appendChild(r); });
    const hit = sv("rect", { x: m.l + i * bw, y: m.t, width: bw, height: H - m.t - m.b, fill: "transparent" }); g.appendChild(hit);
    g.addEventListener("mouseenter", () => { tip.innerHTML = o.tip(i); placeTip(host, tip, m.l + i * bw + bw / 2, Y(Math.max(o.a[i], o.b[i], 0))); });
    g.addEventListener("mouseleave", () => tip.classList.remove("show")); svg.appendChild(g);
    if (i % step === 0) { const t = sv("text", { x: m.l + i * bw + bw / 2, y: H - 8, "text-anchor": "middle" }); t.textContent = o.short(i); svg.appendChild(t); } });
  host.appendChild(svg);
}

/* futures curve: price per pure gram against days to expiry, dot size = gold traded */
export function curveChart(host, c) {
  host.innerHTML = ""; const W = Math.max(host.clientWidth, 280), H = W < 560 ? 250 : 310, m = { l: 64, r: 16, t: 14, b: 34 };
  const pts = c.points, xs = pts.map(p => p.dte), ys = pts.map(p => p.rs_per_g);
  const sx = nice(0, Math.max(...xs), 6), sy = nice(Math.min(...ys), Math.max(...ys), 5);
  const X = v => m.l + (v - sx.lo) / (sx.hi - sx.lo) * (W - m.l - m.r), Y = v => m.t + (sy.hi - v) / (sy.hi - sy.lo) * (H - m.t - m.b);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": "Futures curve" });
  sy.ticks.forEach(v => { svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: Y(v), y2: Y(v), class: "gridl" })); const t = sv("text", { x: m.l - 10, y: Y(v) + 4, "text-anchor": "end" }); t.textContent = "₹" + v.toLocaleString("en-IN"); svg.appendChild(t); });
  sx.ticks.forEach(v => { const t = sv("text", { x: X(v), y: H - 10, "text-anchor": "middle" }); t.textContent = v + "d"; svg.appendChild(t); });
  const tip = tipFor(host);
  ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"].forEach((s, si) => { const q = pts.filter(p => p.symbol === s).sort((a, b) => a.dte - b.dte); if (!q.length) return;
    svg.appendChild(sv("path", { d: q.map((p, i) => (i ? "L" : "M") + X(p.dte) + " " + Y(p.rs_per_g)).join(""), class: "line", style: `stroke:${SYM[s].c};opacity:.7` }));
    q.forEach((p, i) => { const r = Math.max(5, Math.min(11, 4 + Math.sqrt(p.kg)));
      const cc = sv("circle", { cx: X(p.dte), cy: Y(p.rs_per_g), r, style: `fill:${SYM[s].c};stroke:var(--panel);stroke-width:2;cursor:pointer` });
      cc.style.transformOrigin = `${X(p.dte)}px ${Y(p.rs_per_g)}px`;
      cc.animate([{ opacity: 0, transform: "scale(.4)" }, { opacity: 1, transform: "scale(1)" }], { duration: 500, delay: 300 + si * 120 + i * 60, fill: "backwards", easing: "cubic-bezier(.2,.8,.2,1)" });
      cc.addEventListener("mouseenter", () => { cc.setAttribute("r", r + 3); tip.innerHTML = `<div class="t">${s} · expires ${fdate(p.expiry)}</div><div class="r"><span>Price</span><b>₹${p.rs_per_g.toLocaleString("en-IN")}/g</b></div><div class="r"><span>Days to expiry</span><b>${p.dte}</b></div><div class="r"><span>Traded</span><b>${p.kg} kg</b></div>`; placeTip(host, tip, X(p.dte), Y(p.rs_per_g)); });
      cc.addEventListener("mouseleave", () => { cc.setAttribute("r", r); tip.classList.remove("show"); }); svg.appendChild(cc); }); });
  host.appendChild(svg);
}

/* every alert episode as a dot on a timeline, one row per contract */
export function alertStrip(host, h) {
  host.innerHTML = ""; const syms = ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"];
  const W = Math.max(host.clientWidth, 280), rowH = 54, m = { l: W < 560 ? 76 : 104, r: 16, t: 10, b: 30 }, H = m.t + syms.length * rowH + m.b;
  const t0 = T(h[0].start) - 20 * 864e5, t1 = T(D.meta.last), X = t => m.l + (t - t0) / (t1 - t0) * (W - m.l - m.r);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": "Alert history" });
  crashBand(svg, X, t0, t1, m.t, H - m.t - m.b, false, H, m);
  monthTicks(t0, t1, W < 560 ? 4 : 10).forEach(tt => { svg.appendChild(sv("line", { x1: X(tt), x2: X(tt), y1: m.t, y2: H - m.b, class: "gridl" }));
    const t = sv("text", { x: X(tt), y: H - 10, "text-anchor": "middle" }); t.textContent = monthLabel(tt); svg.appendChild(t); });
  const tip = tipFor(host);
  syms.forEach((sy, k) => { const cy = m.t + k * rowH + rowH / 2;
    svg.appendChild(sv("line", { x1: m.l, x2: W - m.r, y1: cy, y2: cy, class: "gridl" }));
    const lb = sv("text", { x: 0, y: cy + 4, class: "lbl", style: `fill:${SYM[sy].c}` }); lb.textContent = sy; svg.appendChild(lb);
    h.filter(a => a.symbol === sy).forEach((a, i) => { const gap = Math.abs(a.premium_bp - a.usual_bp), r = Math.max(4, Math.min(16, 3 + Math.sqrt(gap) * .7));
      const col = a.closed_half_10d === true ? "var(--good)" : a.closed_half_10d === false ? "var(--bad)" : "var(--ink-3)";
      const c = sv("circle", { cx: X(T(a.start)), cy, r, style: `fill:${col};fill-opacity:.5;stroke:${col};stroke-width:1.5;cursor:pointer` });
      c.style.transformOrigin = `${X(T(a.start))}px ${cy}px`; c.animate([{ transform: "scale(0)" }, { transform: "scale(1)" }], { duration: 500, delay: i * 25, fill: "backwards", easing: "cubic-bezier(.2,.8,.2,1)" });
      c.addEventListener("mouseenter", () => { tip.innerHTML = `<div class="t">${sy} · ${fdate(a.start)}${a.alert_days > 1 ? " – " + fdate(a.end) : ""}</div><div class="r"><span>Signal</span><b>${a.direction}</b></div><div class="r"><span>Premium / usual</span><b>${sgn(a.premium_bp, 0)} / ${sgn(a.usual_bp, 0)} bp</b></div><div class="r"><span>10 days later</span><b>${a.prem_10d == null || !isFinite(a.prem_10d) ? "—" : sgn(a.prem_10d, 0) + " bp"}</b></div><div class="r"><span>Halfway closed</span><b>${a.days_to_half ? "after " + a.days_to_half + " days" : a.closed_half_10d === false ? "not within 10 days" : "—"}</b></div>`; placeTip(host, tip, X(T(a.start)), cy - r); });
      c.addEventListener("mouseleave", () => tip.classList.remove("show")); svg.appendChild(c); }); });
  host.appendChild(svg);
}

/* contract calendar: one bar per contract, tender period marked, trades overlaid */
export function calendarChart(host, cs, calF, calT) {
  const syms = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"], rowY = {};
  host.innerHTML = ""; const W = Math.max(host.clientWidth, 300), rowH = calF === "All" ? 9 : 18, gap = calF === "All" ? 3 : 6, m = { l: W < 560 ? 72 : 100, r: 12, t: 8, b: 30 };
  let groups = [], y = m.t; syms.forEach(s => { const g = cs.filter(c => c.symbol === s); if (!g.length) return; groups.push({ s, y0: y, n: g.length }); y += g.length * (rowH + gap) + 14; });
  const H = y + m.b - 14; const t0 = Math.min(...cs.map(c => T(c.first))), t1 = Math.max(...cs.map(c => T(c.last)));
  const X = t => m.l + (t - t0) / (t1 - t0) * (W - m.l - m.r);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, height: H, role: "img", "aria-label": "Contract calendar" });
  crashBand(svg, X, t0, t1, m.t - 4, H - m.b - m.t + 4, false, H, m);
  monthTicks(t0, t1, W < 560 ? 5 : 10).forEach(tt => { svg.appendChild(sv("line", { x1: X(tt), x2: X(tt), y1: m.t - 4, y2: H - m.b, class: "gridl" }));
    const t = sv("text", { x: X(tt), y: H - 10, "text-anchor": "middle" }); t.textContent = monthLabel(tt); svg.appendChild(t); });
  const tip = tipFor(host); const maxKg = Math.max(...cs.map(c => c.kg_median || 0.01));
  groups.forEach(g => { const t = sv("text", { x: 0, y: g.y0 + Math.min(g.n * (rowH + gap), 40) / 2 + 4, class: "lbl", style: `fill:${SYM[g.s].c}` }); t.textContent = g.s; svg.appendChild(t);
    cs.filter(c => c.symbol === g.s).forEach((c, i) => { const x = X(T(c.first)), w = Math.max(2, X(T(c.last)) - x), yy = g.y0 + i * (rowH + gap);
      const op = .35 + .65 * Math.sqrt((c.kg_median || 0) / maxKg);
      const r = sv("rect", { x, y: yy, width: w, height: rowH, rx: rowH / 2.5, style: `fill:${SYM[c.symbol].c};opacity:${op.toFixed(2)};cursor:pointer` });
      r.style.transformOrigin = `${x}px ${yy}px`; r.animate([{ transform: "scaleX(0)" }, { transform: "scaleX(1)" }], { duration: 600, delay: i * 18, fill: "backwards", easing: "cubic-bezier(.2,.8,.2,1)" });
      r.addEventListener("mouseenter", () => { r.style.opacity = 1; tip.innerHTML = `<div class="t">${c.symbol} · expires ${fdate(c.expiry)}</div><div class="r"><span>In our files</span><b>${fdate(c.first)} – ${fdate(c.last)}</b></div><div class="r"><span>Trading days</span><b>${c.days}</b></div><div class="r"><span>No-trade days</span><b>${c.no_trade}</b></div><div class="r"><span>Median traded</span><b>${c.kg_median} kg/day</b></div>`; placeTip(host, tip, x + w / 2, yy); });
      r.addEventListener("mouseleave", () => { r.style.opacity = op; tip.classList.remove("show"); }); svg.appendChild(r);
      rowY[c.symbol + "|" + c.expiry] = yy + rowH / 2;
      if (c.safe_exit && T(c.last) > T(c.safe_exit)) { const tx = X(T(c.safe_exit));
        svg.appendChild(sv("rect", { x: tx, y: yy, width: Math.max(2, X(T(c.last)) - tx), height: rowH, rx: rowH / 2.5, style: "fill:var(--ink);opacity:.5;pointer-events:none" })); } }); });
  if (calT !== "none") {
    D.trades[calT].forEach(t => { const legs = calT.startsWith("A") ? t.what.split("-").map(sy => sy + "|" + t.expiry) : [t.what + "|" + t.expiry, "GOLDM|" + t.m_exp];
      legs.forEach(k => { const yy = rowY[k]; if (yy == null) return; const x0 = X(T(t.entry)), x1 = Math.max(X(T(t.exit)), x0 + 3), col = t.net5 >= 0 ? "var(--good)" : "var(--bad)";
        const ln = sv("line", { x1: x0, x2: x1, y1: yy, y2: yy, style: `stroke:${col};stroke-width:${calF === "All" ? 4 : 6};stroke-linecap:round;cursor:pointer` });
        ln.addEventListener("mouseenter", () => { tip.innerHTML = `<div class="t">${t.what.replace(/GOLD/g, "")} · ${fdate(t.entry)} → ${fdate(t.exit)}</div><div class="r"><span>Net at 5 bp</span><b>${inr(t.net5)}</b></div><div class="r"><span>Last safe exit</span><b>${fdate(t.safe_exit)}</b></div><div class="r"><span>Tender check</span><b>${t.ok_tender ? "clear" : "exit inside tender"}</b></div>`; placeTip(host, tip, x1, yy); });
        ln.addEventListener("mouseleave", () => tip.classList.remove("show")); svg.appendChild(ln);
        if (!t.ok_tender) svg.appendChild(sv("circle", { cx: x1, cy: yy, r: calF === "All" ? 5 : 7, style: "fill:none;stroke:var(--bad);stroke-width:2;pointer-events:none" })); }); }); }
  host.appendChild(svg);
}

/* how liquidity builds by business days left to expiry, each type scaled to its busiest stretch */
export function liquidityChart(host) {
  const syms = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"];
  const order = ["(100.0, 130.0]", "(80.0, 100.0]", "(60.0, 80.0]", "(40.0, 60.0]", "(20.0, 40.0]", "(10.0, 20.0]", "(5.0, 10.0]", "(-0.001, 5.0]"];
  const labs = ["130–100", "100–80", "80–60", "60–40", "40–20", "20–10", "10–5", "5–0"];
  host.innerHTML = ""; const LW = Math.max(host.clientWidth, 260), LH = 250, lm = { l: 48, r: 12, t: 12, b: 40 };
  const lx = i => lm.l + i / (order.length - 1) * (LW - lm.l - lm.r), ly = v => lm.t + (1 - v) * (LH - lm.t - lm.b);
  const svg = sv("svg", { viewBox: `0 0 ${LW} ${LH}`, height: LH, role: "img", "aria-label": "Liquidity by business days to expiry" });
  svg.appendChild(sv("rect", { x: lx(6.5), y: lm.t, width: lx(7) - lx(6.5) + 6, height: LH - lm.t - lm.b, style: "fill:var(--ink);opacity:.08" }));
  [0, .25, .5, .75, 1].forEach(v => { svg.appendChild(sv("line", { x1: lm.l, x2: LW - lm.r, y1: ly(v), y2: ly(v), class: v === 0 ? "zero" : "gridl" })); const t = sv("text", { x: lm.l - 8, y: ly(v) + 4, "text-anchor": "end" }); t.textContent = v * 100 + "%"; svg.appendChild(t); });
  const lstep = LW < 420 ? 2 : 1;
  labs.forEach((l, i) => { if (i % lstep) return; const t = sv("text", { x: lx(i), y: LH - 22, "text-anchor": "middle" }); t.textContent = l; svg.appendChild(t); });
  const xt = sv("text", { x: LW - lm.r, y: LH - 4, "text-anchor": "end" }); xt.textContent = "business days left to expiry →"; svg.appendChild(xt);
  const tip = tipFor(host); const G = sv("g", { class: "reveal" });
  syms.forEach(sy => { const rows = order.map(o => D.liquidity.find(q => q.symbol === sy && q.bucket === o)); const mxk = Math.max(...rows.map(q => q ? q.kg_median : 0)) || 1;
    const vals = rows.map(q => q ? q.kg_median / mxk : null);
    G.appendChild(sv("path", { d: vals.map((v, i) => v == null ? "" : (i ? "L" : "M") + lx(i) + " " + ly(v)).join(""), class: "line", style: `stroke:${SYM[sy].c}` }));
    vals.forEach((v, i) => { if (v == null) return; const c = sv("circle", { cx: lx(i), cy: ly(v), r: 4.5, style: `fill:${SYM[sy].c};stroke:var(--panel);stroke-width:1.5;cursor:pointer` });
      c.addEventListener("mouseenter", () => { tip.innerHTML = `<div class="t">${sy} · ${labs[i]} business days left</div><div class="r"><span>Median traded</span><b>${rows[i].kg_median.toLocaleString("en-IN")} kg/day</b></div><div class="r"><span>Open interest</span><b>${Math.round(rows[i].oi_lots_median).toLocaleString("en-IN")} lots</b></div><div class="r"><span>No-trade days</span><b>${rows[i].no_trade_pct.toFixed(1)}%</b></div>`; placeTip(host, tip, lx(i), ly(v)); });
      c.addEventListener("mouseleave", () => tip.classList.remove("show")); G.appendChild(c); }); });
  svg.appendChild(G); host.appendChild(svg);
}
export { fmon };

/* Gold cursor: a gold arrow pointer that leaves a short trail of gold flecks (small bars, coins and glints).
   Self-contained and switchable. setGoldCursor(false) restores the normal cursor and stops all drawing.
   To remove it from the site completely: delete this file and its import and call in main.jsx.

   Kept light: the trail canvas only animates while flecks are visible, at most 48 at a time.
   Off automatically on touch screens; no trail when the system asks for reduced motion, or when printing. */

const svg = s => `url("data:image/svg+xml,${encodeURIComponent(s)}")`;
const GRAD = `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffe7a3"/><stop offset=".45" stop-color="#f5b83d"/><stop offset="1" stop-color="#b9780f"/></linearGradient></defs>`;
const ARROW = `<path d="M3 2.2 L3 19.6 L7.7 15.4 L10.6 22 L13.6 20.7 L10.8 14.2 L17.2 14.2 Z" fill="url(#g)" stroke="#4a2f02" stroke-width="1.4" stroke-linejoin="round"/><path d="M5 6 L5 13.5" stroke="#fff6d6" stroke-width="1.1" stroke-linecap="round" opacity=".8"/>`;
const C_DEFAULT = svg(`<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">${GRAD}${ARROW}</svg>`);
/* links and buttons: the arrow carries a small gold bar, the Parity mark */
const C_LINK = svg(`<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">${GRAD}${ARROW}<path d="M17.6 18.4h6.2l1.4 3.6h-9z" fill="url(#g)" stroke="#4a2f02" stroke-width="1.1" stroke-linejoin="round"/></svg>`);
/* dotted terms and sources: the arrow carries a small "?" coin */
const C_HELP = svg(`<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">${GRAD}${ARROW}<circle cx="21" cy="20.5" r="5" fill="url(#g)" stroke="#4a2f02" stroke-width="1.1"/><text x="21" y="23.2" font-family="Arial,sans-serif" font-size="7.5" font-weight="700" text-anchor="middle" fill="#4a2f02">?</text></svg>`);

const LINKS = `a[href],button:not(:disabled),[role=button],[role=tab],[role=option],summary,label,select,input[type=checkbox],input[type=radio],input[type=range],
.search,.iconbtn,.theme button,.linkbtn,.seg button,.btn,tr.click,th.sort,.pager button,.toggle,.pal-i,.tabbar a,.tabbar button,.more summary,.dl-i,[style*="cursor:pointer"]`;
const HELP = `.term,.src,.chart .evmark`;
const pick = s => s.split(",").map(x => "html.gold-cursor " + x.trim()).join(",");
const CSS = `@media (hover:hover) and (pointer:fine){
html.gold-cursor,html.gold-cursor body{cursor:${C_DEFAULT} 3 2,auto}
${pick(LINKS)}{cursor:${C_LINK} 3 2,pointer!important}
${pick(HELP)}{cursor:${C_HELP} 3 2,help!important}
html.gold-cursor input:not([type=checkbox]):not([type=radio]):not([type=range]),html.gold-cursor textarea,html.gold-cursor [contenteditable]{cursor:text}}
#gold-trail{position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:2147483000}
@media print{#gold-trail{display:none}}`;

const COLS = ["#ffe39a", "#f5b83d", "#e0a020", "#c98a14", "#fff3c4"];
const COLS_LIGHT = ["#c98a14", "#b5780c", "#e0a020", "#9a6608", "#d99a1e"];   // deeper golds that read on the cream light theme
const light = () => { const t = document.documentElement.getAttribute("data-theme"); return t ? t === "light" : matchMedia("(prefers-color-scheme: light)").matches; };
let style, cvs, ctx, on = false, parts = [], raf = 0, last = null, dpr = 1;
const fine = () => matchMedia("(hover:hover) and (pointer:fine)").matches;
const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

function size() { dpr = Math.min(2, devicePixelRatio || 1); cvs.width = innerWidth * dpr; cvs.height = innerHeight * dpr; }

function spawn(x, y, vx, vy) {
  if (parts.length >= 48) parts.shift();
  const r = Math.random(), kind = r < .45 ? "glint" : r < .75 ? "bar" : "coin";
  parts.push({ x, y, kind, vx: vx * .06 + (Math.random() - .5) * .5, vy: vy * .06 + Math.random() * .3 - .2,
    rot: Math.random() * 6.28, vr: (Math.random() - .5) * .14, s: kind === "glint" ? 2.4 + Math.random() * 2 : 2.6 + Math.random() * 1.8,
    c: (light() ? COLS_LIGHT : COLS)[(Math.random() * 5) | 0], t: 0, life: 520 + Math.random() * 380 });
}

function draw(p, a) {
  ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot); ctx.globalAlpha = a; ctx.fillStyle = p.c;
  const s = p.s;
  if (p.kind === "bar") {                       // a tiny ingot: the Parity mark's trapezoid
    ctx.beginPath(); ctx.moveTo(-s, -s * .45); ctx.lineTo(s, -s * .45); ctx.lineTo(s * 1.35, s * .45); ctx.lineTo(-s * 1.35, s * .45); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "rgba(255,248,220,.7)"; ctx.fillRect(-s * .7, -s * .4, s * 1.2, s * .22);
  } else if (p.kind === "coin") {               // a tiny coin with a rim
    ctx.beginPath(); ctx.arc(0, 0, s, 0, 6.283); ctx.fill();
    ctx.strokeStyle = "rgba(120,78,6,.55)"; ctx.lineWidth = .8; ctx.beginPath(); ctx.arc(0, 0, s * .62, 0, 6.283); ctx.stroke();
  } else {                                      // a four-point glint
    ctx.beginPath();
    for (let i = 0; i < 8; i++) { const ang = i * Math.PI / 4, rr = i % 2 ? s * .28 : s; ctx.lineTo(Math.cos(ang) * rr, Math.sin(ang) * rr); }
    ctx.closePath(); ctx.fill();
  }
  ctx.restore();
}

let prevT = 0;
function tick(now) {
  const dt = Math.min(40, now - (prevT || now)); prevT = now;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, innerWidth, innerHeight);
  parts = parts.filter(p => (p.t += dt) < p.life);
  for (const p of parts) {
    p.vy += .0016 * dt; p.x += p.vx * dt * .06; p.y += p.vy * dt * .06; p.rot += p.vr * dt * .06;
    const k = p.t / p.life; draw(p, (1 - k) * (k < .12 ? k / .12 : 1) * .9);
  }
  raf = parts.length ? requestAnimationFrame(tick) : (prevT = 0, 0);
}

function move(e) {
  if (e.pointerType !== "mouse") return;
  if (!last) { last = { x: e.clientX, y: e.clientY }; return; }
  const dx = e.clientX - last.x, dy = e.clientY - last.y, d = Math.hypot(dx, dy);
  if (d < 16) return;                           // one fleck per ~16 px of travel: a trace, not a spray
  const n = Math.min(3, Math.floor(d / 16));
  for (let i = 1; i <= n; i++) spawn(last.x + dx * i / n, last.y + dy * i / n, dx, dy);
  last = { x: e.clientX, y: e.clientY };
  if (!raf) raf = requestAnimationFrame(tick);
}
const leave = () => { last = null; };

export function setGoldCursor(want) {
  if (!style) { style = document.createElement("style"); style.id = "gold-cursor-css"; style.textContent = CSS; document.head.appendChild(style); }
  document.documentElement.classList.toggle("gold-cursor", !!want);
  const trail = !!want && fine() && !calm();
  if (trail === on) return; on = trail;
  if (on) {
    cvs = document.createElement("canvas"); cvs.id = "gold-trail"; cvs.setAttribute("aria-hidden", "true");
    document.body.appendChild(cvs); ctx = cvs.getContext("2d"); size();
    addEventListener("resize", size); addEventListener("pointermove", move, { passive: true });
    document.addEventListener("pointerleave", leave); addEventListener("blur", leave);
  } else {
    removeEventListener("resize", size); removeEventListener("pointermove", move);
    document.removeEventListener("pointerleave", leave); removeEventListener("blur", leave);
    cancelAnimationFrame(raf); raf = 0; parts = []; last = null; if (cvs) cvs.remove(); cvs = ctx = null;
  }
}

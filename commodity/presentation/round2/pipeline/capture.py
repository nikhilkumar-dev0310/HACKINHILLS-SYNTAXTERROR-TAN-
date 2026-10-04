"""Director: drives the Parity dashboard frame by frame and records a timeline for the compositor.

Time is virtual: the page clock is paused and advanced 1/30 s per frame, CSS animations are stepped by hand,
so every frame is captured at exactly the right moment however slow the machine is.

    python capture.py [--only N]      frames -> frames/NNNNN.jpg, timeline -> timeline.json
"""
import asyncio, base64, json, math, os, sys
from playwright.async_api import async_playwright

URL = "file:///home/claude/hackinhills-syntaxterror-tan-/commodity/dashboard/index.html"
FPS, VW, VH, DSF = 30, 1600, 900, 1.5
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
CARD_FRAMES = 66
DRY = os.environ.get("DRY") == "1"
SNAP = set()
STOP = int(os.environ.get("STOP", "99"))
FROM = int(os.environ.get("FROM", "0"))
KEEP = os.environ.get("KEEP") == "1"                     # chapter card length (2.6 s); the compositor draws the card itself

INJECT = r"""
(() => {
  if (window.__dir) return;
  const css = `#__cur{position:fixed;left:0;top:0;width:30px;height:30px;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px);
      filter:drop-shadow(0 3px 6px rgba(0,0,0,.35));transition:none}
    #__rip{position:fixed;left:0;top:0;width:56px;height:56px;margin:-28px 0 0 -28px;border-radius:50%;border:3px solid #e2a227;z-index:2147483646;
      pointer-events:none;opacity:0;background:rgba(245,184,61,.18)}
    #__ring{position:absolute;left:0;top:0;border-radius:16px;z-index:2147483645;pointer-events:none;opacity:0;
      box-shadow:0 0 0 3px #e2a227,0 0 0 9px rgba(226,162,39,.22),0 10px 40px rgba(226,162,39,.25)}`;
  const st = document.createElement('style'); st.textContent = css; document.documentElement.appendChild(st);
  const cur = document.createElement('div'); cur.id = '__cur';
  cur.innerHTML = '<svg width="30" height="30" viewBox="0 0 30 30"><path d="M4 2.5l20 11.2-8.6 2.3 5 9.3-4 2.1-5-9.3-6.4 6.1z" fill="#1d1d1f" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>';
  const rip = document.createElement('div'); rip.id = '__rip';
  const ring = document.createElement('div'); ring.id = '__ring';
  document.documentElement.appendChild(cur); document.documentElement.appendChild(rip); document.body.appendChild(ring);
  window.__dir = s => {
    if (s.scroll != null) window.scrollTo({ top: s.scroll, behavior: 'instant' });
    if (s.cur) { cur.style.transform = `translate(${s.cur[0] - 4}px,${s.cur[1] - 2}px)`; cur.style.opacity = s.cur[2]; }
    if (s.rip) { rip.style.left = s.rip[0] + 'px'; rip.style.top = s.rip[1] + 'px'; const p = s.rip[2];
      rip.style.opacity = p >= 1 ? 0 : (1 - p) * .95; rip.style.transform = `scale(${.35 + p * 1.15})`; }
    if (s.ring) { const r = s.ring; let ringEl = document.getElementById('__ring'); if (!ringEl.isConnected) document.body.appendChild(ringEl);
      ringEl.style.left = r[0] + 'px'; ringEl.style.top = r[1] + 'px'; ringEl.style.width = r[2] + 'px'; ringEl.style.height = r[3] + 'px'; ringEl.style.opacity = r[4]; }
    for (const a of document.getAnimations()) { if (a.__v === undefined) { a.__v = a.currentTime || 0; a.pause(); } a.__v += s.dt; a.currentTime = a.__v; }
    return [scrollX, scrollY];
  };
  window.__find = (sel, txt, nth) => {
    let els = [...document.querySelectorAll(sel)].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
    if (txt) { const t = txt.toLowerCase(); els = els.filter(e => (e.innerText || e.textContent || '').toLowerCase().includes(t)); }
    if (!els.length) return null;
    if (nth == null) els.sort((a, b) => { const A = a.getBoundingClientRect(), B = b.getBoundingClientRect(); return A.width * A.height - B.width * B.height; });
    const e = els[nth || 0], r = e.getBoundingClientRect();
    return [r.left, r.top, r.width, r.height, scrollY, document.documentElement.scrollHeight];
  };
})();
"""

ease = lambda p: 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, p)))


class Director:
    def __init__(self, pg, cdp):
        self.pg, self.cdp, self.n = pg, cdp, 0
        self.events, self.scroll, self.cur, self.cur_a = [], 0.0, [VW * 0.62, VH * 0.55], 0.0
        self.rip, self.ring, self.ring_a, self.ring_target = None, None, 0.0, 0.0
        self.anim = []                      # per-frame generators
        self.cap_at, self.cap_need = 0, 0
        self.clock_ms = 0.0

    def log(self, **e):
        e["f"] = self.n; self.events.append(e)

    async def frame(self):
        self.clock_ms += 1000 / FPS
        step = int(self.clock_ms); self.clock_ms -= step
        await self.pg.clock.run_for(step)
        for g in list(self.anim):
            try: next(g)
            except StopIteration: self.anim.remove(g)
        if self.ring is not None:
            self.ring_a += (self.ring_target - self.ring_a) * 0.25
        s = {"dt": 1000 / FPS, "scroll": self.scroll, "cur": [self.cur[0], self.cur[1], self.cur_a]}
        if self.rip: s["rip"] = self.rip
        if self.ring is not None: s["ring"] = self.ring + [round(self.ring_a, 3)]
        sx, sy = await self.pg.evaluate("s => window.__dir(s)", s)
        if (not DRY or self.n in SNAP) and self.n >= FROM:
            shot = await self.cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 92, "optimizeForSpeed": True, "clip": {"x": sx, "y": sy, "width": VW, "height": VH, "scale": DSF}})
            with open(os.path.join(OUT, f"{self.n:05d}.jpg"), "wb") as fh:
                fh.write(base64.b64decode(shot["data"]))
        self.n += 1

    async def wait(self, sec):
        for _ in range(max(1, round(sec * FPS))): await self.frame()

    async def until_read(self):
        left = self.cap_need - (self.n - self.cap_at)
        if left > 0:
            for _ in range(left): await self.frame()

    # ---------------------------------------------------------------- narration and camera (drawn by the compositor)
    async def say(self, text, extra=0.0):
        await self.until_read()
        plain = text.replace("**", "")
        self.cap_at, self.cap_need = self.n, round((max(2.7, len(plain) / 16 + 0.85) + extra) * FPS)
        self.log(cap=text)

    def cam(self, rect=None, sec=0.9, zmax=1.45):
        self.log(cam=rect, dur=round(sec * FPS), zmax=zmax)

    # ---------------------------------------------------------------- page geometry
    async def rect(self, sel, txt=None, nth=None):
        r = await self.pg.evaluate("([s,t,n]) => window.__find(s,t,n)", [sel, txt, nth])
        if r is None: raise RuntimeError(f"not found: {sel} {txt}")
        return r

    async def focus(self, sel, txt=None, nth=None, pad=24, sec=0.9, zmax=1.45, grow=None):
        x, y, w, h, *_ = await self.rect(sel, txt, nth)
        if grow: x, y, w, h = x - grow[0], y - grow[1], w + grow[0] + grow[2], h + grow[1] + grow[3]
        self.cam([x - pad, y - pad, w + 2 * pad, h + 2 * pad], sec, zmax)

    # ---------------------------------------------------------------- motion
    def _tween(self, sec, fn):
        n = max(1, round(sec * FPS))
        def g():
            for i in range(1, n + 1):
                fn(ease(i / n)); yield
        self.anim.append(g())
        return n

    async def scroll_to(self, y, sec=1.1, block=True):
        maxs = await self.pg.evaluate("document.documentElement.scrollHeight - innerHeight")
        y = max(0, min(maxs, y)); y0 = self.scroll
        n = self._tween(sec, lambda p: setattr(self, "scroll", y0 + (y - y0) * p))
        if block:
            for _ in range(n): await self.frame()

    async def scroll_el(self, sel, txt=None, top=96, sec=1.1, nth=None):
        x, y, w, h, sy, H = await self.rect(sel, txt, nth)
        await self.scroll_to(sy + y - top, sec)

    async def show_cursor(self, on=True, sec=0.3):
        a0, a1 = self.cur_a, 1.0 if on else 0.0
        n = self._tween(sec, lambda p: setattr(self, "cur_a", a0 + (a1 - a0) * p))
        for _ in range(n): await self.frame()

    async def move(self, x, y, sec=0.85, hover=True):
        x0, y0 = self.cur
        # a gentle arc feels like a hand, not a robot
        bend = 0.12 * math.hypot(x - x0, y - y0)
        def f(p):
            self.cur = [x0 + (x - x0) * p, y0 + (y - y0) * p - bend * math.sin(math.pi * p) * 0.35]
        n = self._tween(sec, f)
        for i in range(n):
            await self.frame()
            if hover and (i % 2 == 1 or i == n - 1): await self.pg.mouse.move(self.cur[0], self.cur[1])

    async def point(self, sel, txt=None, nth=None, fx=0.5, fy=0.5, sec=0.85, dx=0, dy=0):
        x, y, w, h, *_ = await self.rect(sel, txt, nth)
        await self.move(x + w * fx + dx, y + h * fy + dy, sec)

    async def click(self, settle=0.25):
        x, y = self.cur
        await self.pg.mouse.click(x, y)
        self.log(sfx="click")
        def g():
            for i in range(1, 15):
                self.rip = [x, y, i / 14]; yield
            self.rip = None
        self.anim.append(g())
        await self.wait(settle)

    async def ring_on(self, sel, txt=None, nth=None, pad=8):
        x, y, w, h, sy, H = await self.rect(sel, txt, nth)
        self.ring = [x - pad, y + sy - pad, w + 2 * pad, h + 2 * pad]; self.ring_target = 1.0

    async def ring_off(self):
        self.ring_target = 0.0

    async def drag_slider(self, sel, v0, v1, vmax=10, sec=2.0):
        x, y, w, h, *_ = await self.rect(sel)
        pos = lambda v: x + 9 + (w - 18) * v / vmax
        await self.move(pos(v0), y + h / 2, 0.7)
        await self.pg.mouse.down(); self.log(sfx="click")
        n = round(sec * FPS)
        for i in range(1, n + 1):
            p = ease(i / n); self.cur = [pos(v0 + (v1 - v0) * p), y + h / 2]
            await self.pg.mouse.move(self.cur[0], self.cur[1])
            await self.frame()
        await self.pg.mouse.up()

    async def type(self, text, every=3):
        for ch in text:
            await self.pg.keyboard.type(ch); self.log(sfx="key")
            await self.wait(every / FPS)

    async def chapter(self, i, hash_):
        await self.until_read()
        if i > STOP: raise EOFError
        self.log(card=i, dur=CARD_FRAMES); self.log(cap=None); self.log(cam=None, dur=1, zmax=1)
        await self.wait(0.45)                                          # card now fully covers the page
        self.ring, self.ring_a = None, 0.0
        await self.pg.evaluate("h => { location.hash = h; }", hash_)
        self.scroll = 0.0; self.cur = [VW * 0.62, VH * 0.6]; self.cur_a = 0.0
        await self.wait(0.6)
        await self.pg.evaluate("document.querySelectorAll('.rv').forEach(e => e.classList.add('in'))")
        await self.wait(CARD_FRAMES / FPS - 1.05)
        self.cap_at, self.cap_need = self.n, 0


# ==================================================================== the storyboard
async def story(d: Director):
    pg = d.pg

    # ---------------------------------------------------------------- 1 overview
    await d.chapter(1, "overview")
    await d.say("This is **Parity**. Each page answers one simple question about MCX gold futures.")
    await d.wait(0.5); await d.focus("h1", "One metal", grow=(0, 40, 520, 110), zmax=1.3)
    await d.until_read()
    await d.show_cursor(True)
    await d.point("button.term", "purity", sec=0.9)
    await d.say("Any dotted word explains itself. Just **hover** over it.")
    d.log(sfx="pop")
    await d.focus("button.term", "purity", grow=(260, 40, 160, 120), zmax=1.4)
    await d.until_read()
    await d.move(1180, 470, 0.6)
    await d.say("Every page opens with the answer first, in the **In short** box.")
    await d.focus(".take", zmax=1.35); await d.ring_on(".take")
    await d.until_read(); await d.ring_off()
    d.cam(None, 0.8)
    await d.scroll_el("h2", "Latest market data", top=80, sec=1.1)
    await d.say("The latest closing prices, all four turned into **₹ per gram of pure gold**.")
    await d.focus("table", None, nth=0, zmax=1.3)
    await d.point("th", "/ pure g", sec=0.9)
    await d.until_read()
    await d.say("**Premium** = how much dearer than GOLDM. **Usual** = its normal level.")
    await d.point("th", "premium vs goldm", sec=0.7); await d.wait(0.5)
    await d.point("th", "usual", sec=0.5)
    await d.until_read()
    await d.say("Today all sit near their usual level, so the signal is **quiet**. No noise.")
    await d.focus(".status", "Signal today", zmax=1.4)
    await d.point(".status b", "Signal today", fx=0.15, sec=0.8)
    await d.until_read()
    d.cam(None, 0.7)
    await d.scroll_el("h2", "Download the data", top=110, sec=1.3)
    await d.say("Every table **downloads** as a spreadsheet, ready for Excel.")
    await d.focus(".card", "Download the data", zmax=1.3)
    await d.point("button.dl-i", "Daily price per pure gram", sec=0.9)
    await d.until_read()
    d.cam(None, 0.6)
    await d.move(1310, 31, 0.9)
    await d.say("Lost? Press **Ctrl + K** and search the whole site.")
    await d.click(0.1)
    await d.wait(0.4)
    d.cam([440, 90, 720, 300], 0.8, zmax=1.45)
    await d.type("tender", every=2)
    await d.until_read()
    await pg.keyboard.press("Escape"); await d.wait(0.2)

    # ---------------------------------------------------------------- 2 brief
    await d.chapter(2, "brief")
    await d.say("The organisers asked for **five things**. Each card: the ask, what we built, a link to the proof.")
    await d.show_cursor(True)
    await d.scroll_el("h3", "Cross-contract relative value", top=120, sec=1.0)
    await d.focus(".dir", "Cross-contract relative value", zmax=1.35)
    await d.point(".dir-h .pill, .dir-h span", "Done", nth=0, sec=0.9)
    await d.until_read()
    d.cam(None, 0.7)
    await d.scroll_el("h2", "The final challenge", top=90, sec=1.6)
    await d.say("All five are **done**, and every line of the final challenge is answered.")
    await d.focus(".card", "The final challenge", zmax=1.2)
    await d.move(1450, 400, 0.9)
    await d.until_read()

    # ---------------------------------------------------------------- 3 relative value
    await d.chapter(3, "relative")
    await d.say("Here we compare contracts **two at a time**, per gram of pure gold.")
    await d.show_cursor(True)
    await d.scroll_to(400, 1.0)
    await d.focus(".card", "Daily gap per pure gram", zmax=1.2)
    await d.point("button", "GOLDM-TEN", sec=0.9); await d.click()
    await d.until_read()
    await d.say("GOLDM vs GOLDTEN: the line hugs **zero**. Same gold, same price. Our maths checks out.")
    d.cam([290, 100, 760, 520], 0.9)
    await d.until_read()
    await d.point("button", "GOLDM-GUINEA", sec=0.7); await d.click()
    await d.say("GOLDM vs the 8 g coin: the coin is **always dearer**, about 60 bp (0.6%) per gram.")
    await d.move(640, 405, 0.9)
    await d.until_read()
    await d.say("In the **Dec 2025 – Mar 2026 crash** that gap blew out past 2.6%.")
    d.cam([700, 140, 480, 400], 0.9, zmax=1.45)
    await d.move(860, 420, 1.0); await d.move(905, 470, 0.6)
    await d.until_read()
    d.cam(None, 0.7)
    await d.say("Dearer in **all 41 contract months**: a lasting premium, not a mistake.")
    await d.focus(".kpi", "Same sign in", zmax=1.45)
    await d.point(".kpi", "41/41", sec=0.9)
    await d.until_read()

    # ---------------------------------------------------------------- 4 term structure
    await d.chapter(4, "term")
    await d.say("Each dot is **one contract**. Further right = it expires later.")
    await d.show_cursor(True)
    await d.scroll_to(400, 1.0)
    await d.focus(".card", "Futures curve", zmax=1.25)
    await d.move(980, 400, 0.9)
    await d.until_read()
    await d.say("Later costs more, like **rent** for holding gold until then. That's the **cost of carry**.")
    await d.until_read()
    await d.point("button", "90 days earlier", sec=0.8); await d.click()
    await d.say("90 days back the whole line sat elsewhere: **gold itself moved**, not just time.")
    await d.until_read()
    await d.point("button", "Latest", sec=0.6); await d.click(0.1)
    d.cam(None, 0.7)
    await d.scroll_el("summary", "Roll-down vs curve move", top=170, sec=0.9)
    await d.point("summary", "Roll-down vs curve move", fx=0.2, sec=0.7); await d.click(0.3)
    await d.say("Time alone moves GOLDM only about **0.6% a month**. Gold's own moves are far bigger.")
    await d.scroll_el("summary", "Roll-down vs curve move", top=90, sec=0.9)
    await d.focus("details", "Roll-down vs curve move", zmax=1.25)
    await d.move(1250, 460, 0.8)
    await d.until_read()

    # ---------------------------------------------------------------- 5 backtest
    await d.chapter(5, "backtest")
    await d.say("The big question: buy the cheap one, sell the dear one. **Do you make money?**")
    await d.show_cursor(True)
    await d.scroll_to(230, 1.0)
    await d.focus(".controls-card", zmax=1.3, grow=(0, 0, 0, 260))
    await d.until_read()
    await d.say("**Slippage** is the bit you lose each time an order fills. With perfect fills…")
    await d.drag_slider("#slip", 5, 0, sec=1.3)
    await d.focus(".kpi", "Net profit", zmax=1.45)
    await d.until_read()
    d.cam([300, 160, 1250, 560], 0.6)
    await d.say("…profit looks big. At **10 bp** most of it vanishes. Costs decide everything.")
    await d.drag_slider("#slip", 0, 10, sec=2.0)
    await d.until_read()
    await d.say("So every result is shown at **5 bp**, the realistic middle.")
    await d.drag_slider("#slip", 10, 5, sec=1.0)
    await d.until_read()
    d.cam(None, 0.7)
    await d.scroll_el("h2", "Cumulative profit", top=80, sec=1.0)
    await d.say("Strategy A's profit came almost all from **one crash month**: January 2026.")
    await d.focus(".card", "Cumulative profit", zmax=1.25)
    await d.move(1000, 260, 1.0)
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_to(230, 0.9)
    await d.point("button", "B · sealed holdout", sec=0.8); await d.click()
    await d.say("Strategy B, the **fair-price** rule: fewer trades, steadier, still positive.")
    await d.focus(".grid.g4", "Net profit", zmax=1.35)
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_el("h2", "A typical backtest vs our test", top=80, sec=1.1)
    await d.say("Most backtests skip costs and grade a rule on the data it was tuned on…")
    await d.focus(".card", "A typical backtest vs our test", zmax=1.2)
    await d.point("button", "How most teams report", sec=0.8); await d.click(0.3)
    d.log(sfx="pop")
    await d.until_read()
    await d.say("…so the numbers look **huge**. That is not real money.")
    await d.until_read()
    await d.point("button", "Our sealed test", sec=0.7); await d.click(0.3)
    await d.say("Ours: **real costs**, on data the rules had never seen.")
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_el("h2", "Eight more years, sealed", top=80, sec=1.2)
    await d.say("The hardest exam: **8 more years** (2016–2023), locked away until the rules were frozen.")
    await d.focus(".card", "Eight more years, sealed", zmax=1.2, grow=(0, 0, 0, -150))
    await d.until_read()
    await d.say("Strategy A **failed**. Strategy B made money in **both** windows. Small, but real.")
    await d.point("td, b", "Strategy B", sec=0.8); await d.ring_on("tr", "fair price, as frozen")
    await d.until_read(); await d.ring_off()
    d.cam(None, 0.6)
    await d.scroll_el("summary", "Is it just a bet on gold", top=200, sec=0.9)
    await d.point("summary", "Is it just a bet on gold", fx=0.2, sec=0.7); await d.click(0.3)
    await d.say("A bet on gold going up? **No.** Every trade's profit is split into gap and gold.")
    await d.scroll_el("summary", "Is it just a bet on gold", top=90, sec=0.9)
    await d.focus("details", "Is it just a bet on gold", zmax=1.2)
    await d.until_read()

    # ---------------------------------------------------------------- 6 signals
    await d.chapter(6, "signals")
    await d.say("Is any contract **far from its fair price** right now? The black marker is today.")
    await d.show_cursor(True)
    await d.scroll_to(380, 1.0)
    await d.focus(".card.sig", "GOLDGUINEA", zmax=1.45)
    await d.point(".card.sig", "GOLDGUINEA", fy=0.3, sec=0.9)
    await d.until_read()
    await d.say("Past the **red ticks** an alert fires. Today every contract is **normal**.")
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_to(820, 1.0)
    await d.say("**66 alerts** since 2023. A typical one saw the gap close **51 bp** within 10 trading days.")
    await d.focus(".grid.g4", "Alert episodes", zmax=1.3)
    await d.move(980, 260, 0.9)
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_el("summary", "Every alert so far", top=220, sec=0.9)
    await d.point("summary", "Every alert so far", fx=0.2, sec=0.7); await d.click(0.3)
    await d.scroll_el("summary", "Every alert so far", top=90, sec=0.9)
    await d.say("Every alert is on record with **what happened next**. Most days, the honest answer is: wait.")
    await d.focus("details", "Every alert so far", zmax=1.2)
    await d.until_read()

    # ---------------------------------------------------------------- 7 contracts
    await d.chapter(7, "calendar")
    await pg.evaluate("() => { const s = document.createElement('style'); s.id = '__notip'; s.textContent = '.tip{display:none!important}'; document.head.appendChild(s); }")
    await d.say("Each bar is **one contract**, from its first trading day to expiry.")
    await d.show_cursor(True)
    await d.scroll_to(340, 1.0)
    await d.move(700, 520, 0.9)
    await d.until_read()
    await d.scroll_to(1050, 1.2)
    await d.say("Each dash is a **trade**: green made money, red lost. The pink band is the 2026 crash.")
    d.cam([1040, 100, 420, 260], 0.9)
    await d.move(1230, 180, 0.9)
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_to(0, 0.9)
    await d.point("button", "Strategy B trades", sec=0.8); await d.click(0.3)
    await d.scroll_to(790, 1.1)
    await d.say("The dark end of each bar is the run-up to **delivery**. Strategy B always exits before it.")
    d.cam([1060, 70, 440, 290], 0.9)
    await d.move(1290, 190, 0.9)
    await d.until_read()
    d.cam(None, 0.6)

    # ---------------------------------------------------------------- 8 data quality
    await d.chapter(8, "quality")
    await pg.evaluate("() => { const s = document.getElementById('__notip'); if (s) s.remove(); }")
    await d.say("Built on **723 official MCX files**: 12,021 rows checked, **0 unexplained errors**.")
    await d.show_cursor(True)
    await d.focus(".grid.g4", "Files read", zmax=1.3)
    await d.point(".kpi", "Unexplained errors", sec=0.9)
    await d.until_read()
    d.cam(None, 0.6)
    await d.point("summary", "Rules taken from the MCX contract", fx=0.2, sec=0.8); await d.click(0.3)
    await d.scroll_el("summary", "Rules taken from the MCX contract", top=100, sec=0.9)
    await d.say("Rules like the delivery period come straight from **MCX's own documents**.")
    await d.focus("details", "Rules taken from the MCX contract", zmax=1.2)
    await d.until_read()
    d.cam(None, 0.6)
    await d.scroll_to(0, 0.7)
    await d.point("button[aria-label='Dark theme']", sec=0.9); await d.click(0.5)
    await d.say("And for late nights, a **dark mode**.")
    await d.until_read()
    await d.point("button[aria-label='Light theme']", sec=0.7); await d.click(0.3)
    await d.show_cursor(False)
    d.log(cap=None)
    await d.wait(0.4)


async def main():
    os.makedirs(OUT, exist_ok=True)
    if not KEEP:
        for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": VW, "height": VH}, device_scale_factor=DSF, color_scheme="light", reduced_motion="no-preference")
        await ctx.add_init_script("try{localStorage.clear()}catch(e){}")
        pg = await ctx.new_page()
        await pg.clock.install(time=1790000000000)
        await pg.goto(URL + "#overview")
        await pg.wait_for_timeout(1200)
        await pg.clock.pause_at(1790000005000)
        await pg.evaluate(INJECT)
        cdp = await ctx.new_cdp_session(pg)
        d = Director(pg, cdp)
        try:
            await story(d)
        except EOFError:
            pass
        finally:
            json.dump({"fps": FPS, "frames": d.n, "vw": VW, "vh": VH, "dsf": DSF, "events": d.events}, open("timeline.json", "w"), indent=0)
            print("frames", d.n, "seconds", d.n / FPS)
        await b.close()

asyncio.run(main())

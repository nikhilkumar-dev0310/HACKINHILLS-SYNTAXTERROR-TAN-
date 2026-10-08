"""Storyboard for the v3 demo (about 2:10): a story, not a tour.

Built from the attention research in ../ENGAGEMENT.md: open on a surprising true number and a question
(curiosity gap), ask the viewer to predict before each reveal, change the picture every few seconds, one
peak (the profit, then the honest twist), and an ending that leaves a true, open question that only the
live site answers. Every number is read from dashboard/data.json or from the page itself.

    python capture3.py        -> frames3/NNNNN.jpg, timeline3.json   (about 25 min on 2 CPUs)

Events logged for the compositor and the sound designer:
    cap    caption (short, **gold** words)         beat   full-screen statement card {beat, dur}
    sfx    a sound on a meaningful moment          mus    music intensity 0-3 (or "drop")
    rise   riser that lands at frame f + dur      tick   counter ticks for dur frames
    predict "your guess" countdown for dur frames  cam    camera move
"""
import asyncio, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capture as C
from capture import Director, FPS, VW, VH, DSF, URL, DATA, INJECT
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
C.OUT = os.path.join(HERE, "frames3")

# ---------------------------------------------------------------- numbers, all from the exported data
def inr_in(v):                      # Indian grouping: 1,53,382
    s = str(abs(round(v))); h, t = s[:-3], s[-3:]
    while len(h) > 2: t = h[-2:] + "," + t; h = h[:-2]
    return ("−" if v < 0 else "") + "₹" + (h + "," + t if h else t)

A = [t for t in DATA["trades"]["A_hold"] if t["ok_tender"]]
NET5 = sum(t["net5"] for t in A)
JAN = [t["net5"] for t in A if t["entry"].startswith("2026-01")]
REST = NET5 - sum(JAN)
OF = DATA["overfit"]; PBO = round(100 * OF["pbo"]["value"]); SETTINGS = OF["pbo"]["settings"]
TESTS = DATA["tests"]["tests"]
ALLM = DATA["meta"]["all"]; YEARS = int(ALLM["last"][:4]) - int(ALLM["first"][:4])
LAST = DATA["meta"]["last"]
MON = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
LAST_TXT = f"{int(LAST[8:])} {MON[int(LAST[5:7]) - 1]}"
CRASH_I = DATA["hurdle"]["dates"].index("2026-01-30")
N_DAYS = len(DATA["hurdle"]["dates"])
BE_MAX = max(r["breakeven_bp"] for r in DATA["robustness"]["breakeven"]["rows"] if r["breakeven_bp"] is not None)
assert len(A) - len(JAN) > 0


class D3(Director):
    async def say(self, text, extra=0.0, need=None):
        """A caption; it stays up for its reading time (or `need` seconds) before the next one may start."""
        await self.until_read()
        plain = text.replace("**", "")
        self.cap_at = self.n
        floor = len(plain) / 15 + 0.6                                  # never faster than 15 characters a second
        self.cap_need = round((max(need or 0, floor, 2.0) + extra) * FPS)
        self.log(cap=text)

    async def beat(self, name, sec, hash_=None, setup=None):
        """A full-screen statement card; while it covers the page the next scene is set up."""
        await self.until_read()
        start, plan = self.n, round(sec * FPS)
        self.log(beat=name, dur=plan); self.log(cap=None)
        await self.wait(0.12)
        self.ring, self.ring_a = None, 0.0
        self.log(cam=None, dur=1, zmax=1)
        if hash_:
            await self.pg.evaluate("h => { location.hash = h; }", hash_)
            self.scroll = 0.0; self.cur_a = 0.0
            await self.wait(0.4)
            await self.pg.evaluate("document.querySelectorAll('.rv').forEach(e => e.classList.add('in'))")
        if setup: await setup()
        await self.wait(1 / FPS)
        used = self.n - start
        if used < plan:
            await self.wait((plan - used) / FPS)
        elif used > plan:                                          # setup ran long: the edit drops the extra frames,
            self.log_at(start + plan, skip=used - plan)            # so the card is on screen exactly `sec`
        self.cap_at, self.cap_need = self.n, 0

    def log_at(self, f, **e):
        e["f"] = f; self.events.append(e)

    def sfx(self, name, **k): self.log(sfx=name, **k)
    def mus(self, level): self.log(mus=level)
    def rise(self, sec): self.log(rise=round(sec * FPS))         # lands sec seconds from now

    async def set_slider(self, sel, value):
        """Set a range input instantly (off camera)."""
        await self.pg.evaluate("""([s, v]) => { const el = document.querySelector(s);
            const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            set.call(el, String(v)); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }""", [sel, value])

    async def fade_el(self, sel, to, sec=0.35):
        await self.pg.evaluate("""([s, o, ms]) => { const e = document.querySelector(s); const from = getComputedStyle(e).opacity;
            e.animate([{ opacity: from }, { opacity: o }], { duration: ms, fill: 'forwards', easing: 'ease-out' }); }""", [sel, to, sec * 1000])


async def story(d: D3):
    pg = d.pg

    # ================================================================ 0:00  HOOK: a surprising true number, and a question
    async def setup_hook():
        x, y, w, h, sy, H = await d.rect(".kpi", "Net profit")
        d.scroll = max(0, sy + y - 320); await d.wait(0.1)
        await d.set_slider("#slip", 5); await d.wait(0.2)
        await d.focus(".kpi", "Net profit", sec=0.05, zmax=1.9, pad=70)
    d.mus(0)
    await d.beat("black", 0.6, None, setup_hook)
    d.sfx("impact")                                                # the number appears out of silence
    d.mus(1)
    await d.focus(".kpi", "Net profit", sec=6.0, zmax=2.35, pad=40)       # slow push-in while the question lands
    await d.say(f"**{inr_in(NET5)}** profit, on a year our rules never saw.", need=3.6)
    await d.say("So why aren't we trading it?", need=2.6)

    # ================================================================ 0:08  THE PROBLEM, in one picture
    d.sfx("whoosh")
    async def setup_same():
        await pg.evaluate("() => { const g = document.querySelector('#worth .worth-g'); if (g) g.style.opacity = '0'; }")
        x, y, w, h, sy, H = await d.rect(".quotes")
        d.scroll = max(0, sy + y - 260); await d.wait(0.1)
        await d.focus(".quotes", zmax=1.5, sec=0.05, pad=30)
    await d.beat("same", 2.4, "overview", setup_same)
    d.mus(2)
    await d.say("Per gram of pure gold, they should cost **exactly the same**.", need=3.2)
    d.sfx("whoosh_soft")
    await d.focus(".quotes", zmax=1.3, sec=1.4, pad=60, grow=(0, 110, 0, 0))       # widen to the facts strip above
    await d.say("Parity measures every gap, **every trading day**, after every cost.", need=3.0)

    # ================================================================ 0:20  PREDICTION, then the reveal
    await d.until_read()
    d.sfx("whoosh_soft")
    await d.scroll_el("#worth", top=130, sec=0.9)
    await d.focus("#worth h2", zmax=1.7, pad=60, sec=0.8)
    d.mus(0.4)                                                     # the music thins: room to think
    await d.say("Your guess: is any gap worth trading **today**?", need=3.3)
    d.log(predict=round(2.4 * FPS))
    await d.wait(2.6)
    await d.until_read()
    d.sfx("reveal"); d.mus(1)
    await d.fade_el("#worth .worth-g", 1, 0.3)
    await d.focus("#worth .worth-a", zmax=1.6, pad=40, sec=0.6)
    txt = await pg.evaluate("() => document.querySelector('#worth .worth-a p').innerText")
    gap, line = re.search(r"([\d.]+) bp", txt).group(1), re.findall(r"([\d.]+) bp", txt)[-1]
    await d.say(f"**No.** The biggest gap is {gap} bp. A trade needs {line}.", need=3.4)
    await d.say("Most days, the honest answer is **wait**.", need=2.4)

    # ================================================================ 0:33  EXCEPT ONCE
    d.sfx("whoosh")
    async def setup_replay():
        x, y, w, h, sy, H = await d.rect("#replay")
        d.scroll = max(0, sy + y - 210); await d.wait(0.1)
        await d.focus(".card", "Replay every day", zmax=1.25, sec=0.05)
    await d.beat("cut", 0.3, "signals", setup_replay)
    d.mus(2)
    await d.say("Rewind to **January 2026**…", need=2.2)
    await d.show_cursor(True, 0.2)
    x, y, w, h, *_ = await d.rect("#replay")
    pos = lambda i: x + 9 + (w - 18) * i / (N_DAYS - 1)
    await d.move(pos(N_DAYS - 1), y + h / 2, 0.5)
    await pg.mouse.down(); d.sfx("click")
    d.log(tick=round(1.5 * FPS))
    n = round(1.5 * FPS)
    for k in range(1, n + 1):
        p = C.ease(k / n); i = (N_DAYS - 1) + (CRASH_I - (N_DAYS - 1)) * p
        d.cur = [pos(i), y + h / 2]; await pg.mouse.move(d.cur[0], d.cur[1]); await d.frame()
    await pg.mouse.up()
    d.sfx("alert")
    await d.say("…the gold crash. Every gap blew through the **cost line**.", need=3.2)
    await d.show_cursor(False, 0.2)

    # ================================================================ 0:42  HOW WE KNOW: four fast proofs
    async def setup_proof():
        x, y, w, h, sy, H = await d.rect(".proof")
        d.scroll = max(0, sy + y - 300); await d.wait(0.1)
        await d.focus(".proof", zmax=1.7, pad=30, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, "overview", setup_proof)
    d.mus(2)
    await d.say(f"**{YEARS} years** of official MCX data. **{ALLM['contracts']}** contracts.", need=3.0)
    d.sfx("shimmer")

    async def setup_slip():
        x, y, w, h, sy, H = await d.rect(".kpi", "Net profit")
        d.scroll = max(0, sy + y - 470); await d.wait(0.1)
        await d.set_slider("#slip", 5); await d.wait(0.15)
        x, y, w, h, *_ = await d.rect(".kpi", "Net profit"); xs, ys, ws, hs, *_ = await d.rect("#slip")
        d.cam([x - 30, ys - 70, (xs + ws) - x + 60, (y + h) - ys + 100], 0.05, zmax=1.7)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, "backtest", setup_slip)
    await d.say("Every fee. Every tax. And slippage **you control**.", need=2.0)
    await d.show_cursor(True, 0.2)
    d.log(tick=round(1.0 * FPS)); await d.drag_slider("#slip", 5, 0, sec=1.0)
    d.log(tick=round(1.6 * FPS)); d.sfx("cost", d=1.6); await d.drag_slider("#slip", 0, 10, sec=1.6)
    await d.say(f"Past **{BE_MAX:.0f} bp** of slippage, no result survives.", need=2.6)
    await d.until_read()                                           # hold at 10 bp, the loss in red, while it is read
    await d.drag_slider("#slip", 10, 5, sec=0.7)
    await d.show_cursor(False, 0.2)

    async def setup_honest():
        x, y, w, h, sy, H = await d.rect(".card", "A typical backtest vs our test")
        d.scroll = max(0, sy + y - 60); await d.wait(0.1)
        await d.focus(".card", "A typical backtest vs our test", zmax=1.3, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, None, setup_honest)
    await d.show_cursor(True, 0.2)
    await d.point("button", "How most teams report", sec=0.6); await d.click(0.15)
    d.sfx("land")
    await d.say("Most teams would report **this**…", need=2.4)
    await d.until_read()
    await d.point("button", "Our sealed test", sec=0.5); await d.click(0.15)
    d.sfx("cost")
    lost = await pg.evaluate("() => [...document.querySelectorAll('.card.honest *')].map(e => e.innerText).join(' ')")
    pct = re.findall(r"(\d+)% of the typical headline disappears", lost)
    await d.say(f"…we report **this**. Up to **{max(map(int, pct))}%** of the headline disappears." if pct else "…we report **this**.", need=3.2)
    await d.show_cursor(False, 0.2)

    async def setup_cal():
        d.scroll = 380; await d.wait(0.1)
        d.cam([140, 60, 1320, 760], 0.05, zmax=1.2)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, "calendar", setup_cal)
    await d.say("Every trade placed inside its contract's calendar. **None held into delivery.**", need=3.2)

    async def setup_sealed():
        x, y, w, h, sy, H = await d.rect(".card", "Eight more years")
        d.scroll = max(0, sy + y - 70); await d.wait(0.1)
        await d.focus(".card", "Eight more years", zmax=1.45, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, "backtest", setup_sealed)
    await d.say("Rules frozen in Git. **Eight years kept sealed**, then opened once.", need=3.3)
    d.sfx("shimmer"); await d.ring_on("tr", "fair price, as frozen")
    await d.until_read(); await d.ring_off()

    # ================================================================ 1:05  PEAK: too good to be true? then the honest twist
    d.rise(2.6)                                                    # lands as the card's question appears
    d.mus("drop")
    async def setup_twist():
        x, y, w, h, sy, H = await d.rect(".take")
        d.scroll = max(0, sy + y - 160); await d.wait(0.1)
        await d.focus(".take", zmax=1.45, pad=36, sec=0.05)
    await d.beat("toogood", 3.0, "backtest", setup_twist)
    d.sfx("impact_big"); d.mus(3)
    await d.say(f"January 2026 alone made **{inr_in(sum(JAN))}**.", need=2.6)
    d.sfx("cost")
    await d.say(f"The other {len(A) - len(JAN)} trades lost **{inr_in(-REST) if REST < 0 else inr_in(REST)}**.", need=2.8)
    await d.say("Outside the crash, the rule **loses money**.", need=2.4)

    async def setup_luck():
        x, y, w, h, sy, H = await d.rect(".card", "Skill, tuning or luck?")
        d.scroll = max(0, sy + y - 80); await d.wait(0.1)
        await d.focus(".card", "Skill, tuning or luck?", zmax=1.45, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, None, setup_luck)
    await d.say(f"Best of {SETTINGS} settings? A **{PBO}%** chance that's noise.", need=3.0)
    d.sfx("shimmer"); await d.ring_on(".kpi", "Overfitting (PBO)")
    await d.until_read(); await d.ring_off()
    await d.say("A small edge. Not proven. **We say so.**", need=2.8)

    # ================================================================ 1:30  TRUST, quietly
    async def setup_tests():
        x, y, w, h, sy, H = await d.rect("#tests")
        d.scroll = max(0, sy + y - 90); await d.wait(0.1)
        await d.focus("#tests", zmax=1.5, sec=0.05, pad=20)
    d.sfx("whoosh_soft")
    await d.beat("cut", 0.3, "quality", setup_tests)
    d.mus(1)
    await d.say(f"Checked by **{TESTS:,}** automated tests, before every update.", need=3.2)
    async def setup_auto():
        x, y, w, h, sy, H = await d.rect("#auto")
        d.scroll = max(0, sy + y - 90); await d.wait(0.1)
        await d.focus("#auto", zmax=1.2, sec=0.05, pad=20)
    d.sfx("whoosh_soft")
    await d.beat("cut", 0.3, None, setup_auto)
    await d.say("And it updates **itself**, every trading day.", need=2.6)

    # ================================================================ 1:40  THE OPEN ENDING
    async def setup_end():
        await pg.evaluate("() => { const g = document.querySelector('#worth .worth-g'); if (g) { g.getAnimations().forEach(a => a.cancel()); g.style.opacity = '1'; } }")
        x, y, w, h, sy, H = await d.rect("#worth")
        d.scroll = max(0, sy + y - 130); await d.wait(0.1)
        await d.focus("#worth", zmax=1.3, sec=0.05, pad=30)
    d.sfx("whoosh_soft")
    await d.beat("cut", 0.3, "overview", setup_end)
    await d.say(f"That was **{LAST_TXT}**.", need=2.2)
    d.mus("resolve")
    await d.beat("tomorrow", 3.2)
    d.sfx("end_chime")
    await d.beat("end", 5.0)
    d.log(end=1)


async def main():
    os.makedirs(C.OUT, exist_ok=True)
    for f in os.listdir(C.OUT): os.remove(os.path.join(C.OUT, f))
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": VW, "height": VH}, device_scale_factor=DSF, color_scheme="light", reduced_motion="no-preference")
        await ctx.add_init_script("try{localStorage.clear()}catch(e){}")
        pg = await ctx.new_page()
        await pg.clock.install(time=1790000000000)
        await pg.goto(URL + "#backtest")
        await pg.wait_for_timeout(1500)
        await pg.clock.pause_at(1790000005000)
        await pg.evaluate(INJECT)
        cdp = await ctx.new_cdp_session(pg)
        d = D3(pg, cdp)
        try:
            await story(d)
        finally:
            json.dump({"fps": FPS, "frames": d.n, "vw": VW, "vh": VH, "dsf": DSF, "events": d.events}, open(os.path.join(HERE, "timeline3.json"), "w"), indent=0)
            print("frames", d.n, "seconds", round(d.n / FPS, 1))
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())

"""Storyboard for the v4 demo (about 85 s after the edit). Built from the research in ../ENGAGEMENT.md (v4 section).

Changes from v3: Pari, the mascot, carries the questions and asides in speech bubbles while captions carry the facts
(never both at once); a labelled "What we do differently, 1 of 4" run; a "How close are we?" card from the site's
brief page; slower, eased camera moves that hold; no outlines or rings drawn on the page.

    python capture4.py        -> frames4/NNNNN.jpg, timeline4.json

Extra events (besides those of capture3.py):
    pari   pose for Pari {pari, dur}            bubble  Pari's speech bubble text (with pari, dur)
    chip   "What we do differently" counter (0 hides it)
"""
import asyncio, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capture as C
from capture import FPS, VW, VH, DSF, URL, DATA, INJECT
from capture3 import D3, inr_in, A, NET5, JAN, REST, PBO, SETTINGS, TESTS, ALLM, YEARS, CRASH_I, N_DAYS, BE_MAX
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
C.OUT = os.path.join(HERE, "frames4")

# "How close are we?" card: when each line ticks in (seconds from the card's start); shared with overlays4.html
BRIEF_T = [0.95, 1.30, 1.65, 2.00, 2.35, 3.15, 3.75, 4.45]


def worth_caption():
    """Today's answer, built from the same data and rule as the site's "Is any gap worth trading today?" card."""
    H = DATA["hurdle"]; i = len(H["dates"]) - 1; k = DATA["signals"]["threshold"]
    line = 2 * next(x for x in DATA["alerts"]["baseline"] if str(x["alert_day"]).lower() == "true")["round_trip_cost_bp_at_5bp"]
    return _worth(H, i, k, line)

def _worth(H, i, k, line):
    small = ["GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
    look = [s for s in small if H[s]["gap"][i] is not None and H[s]["gap"][i] >= line and abs(H[s]["z"][i]) >= k]
    if look: return f"**Worth a look:** {', '.join(look)} passes both checks today."
    s, g = max(((s, H[s]["gap"][i]) for s in small if H[s]["gap"][i] is not None), key=lambda x: x[1])
    if g >= line: return f"**No.** The biggest gap, {g:.1f} bp, clears costs but is normal for {s}."
    return f"**No.** The biggest gap is {g:.1f} bp. A trade needs {line:.1f}."


class D4(D3):
    async def pari(self, pose, text=None, sec=None):
        """Pari reacts (pose) and, with text, speaks in a bubble that takes the reading slot (no caption meanwhile).
        Bubble time: 1.5 s + 0.3 s a word (at least 2 s); a pose alone holds `sec` (default 1.5 s)."""
        if text:
            await self.until_read()
            n = len(text.split())
            dur = round(max(2.0, 1.5 + 0.3 * n) * FPS)
            self.log(cap=None); self.log(pari=pose, bubble=text, dur=dur)
            self.cap_at, self.cap_need = self.n, dur + round(0.25 * FPS)
        else:
            self.log(pari=pose, dur=round((sec or 1.5) * FPS))

    def chip(self, n): self.log(chip=n)


async def story(d: D4):
    pg = d.pg

    # ================================================================ HOOK: a true number, and a question (Pari asks it)
    async def setup_hook():
        x, y, w, h, sy, H = await d.rect(".kpi", "Net profit")
        d.scroll = max(0, sy + y - 320); await d.wait(0.1)
        await d.set_slider("#slip", 5); await d.wait(0.2)
        await d.focus(".kpi", "Net profit", sec=0.05, zmax=1.9, pad=70)
    d.mus(0)
    await d.beat("black", 0.6, None, setup_hook)
    d.sfx("impact"); d.mus(1)
    await d.pari("wow", sec=1.2)
    await d.focus(".kpi", "Net profit", sec=6.0, zmax=2.3, pad=40)          # slow push-in while it lands
    await d.say(f"**{inr_in(NET5)}** profit, on a year our rules never saw.", need=3.6)
    await d.pari("think", "So why aren't we trading it?")

    # ================================================================ THE PROBLEM, in one picture
    d.sfx("whoosh")
    async def setup_same():
        await pg.evaluate("() => { const g = document.querySelector('#worth .worth-g'); if (g) g.style.opacity = '0'; }")
        x, y, w, h, sy, H = await d.rect(".quotes")
        d.scroll = max(0, sy + y - 260); await d.wait(0.1)
        await d.focus(".quotes", zmax=1.5, sec=0.05, pad=30)
    await d.beat("same", 2.6, "overview", setup_same)
    d.mus(2)
    await d.say("Per gram of pure gold, they should cost **exactly the same**.", need=3.2)
    await d.focus(".quotes", zmax=1.3, sec=0.9, pad=60, grow=(0, 110, 0, 0))
    await d.say("Parity measures every gap, **every trading day**, after every cost.", need=3.1)

    # ================================================================ PREDICTION, then the reveal
    await d.until_read()
    await d.scroll_el("#worth", top=130, sec=0.9)
    await d.focus("#worth h2", zmax=1.7, pad=60, sec=0.8)
    d.mus(0.4)                                                       # the music thins: room to think
    await d.say("Is any gap worth trading **today**?", need=2.4)
    await d.pari("think", sec=3.0)
    d.log(predict=round(2.4 * FPS))
    d.rise(2.6)
    await d.wait(2.6)
    await d.until_read()
    d.sfx("reveal"); d.mus(1)
    await d.fade_el("#worth .worth-g", 1, 0.3)
    await d.focus("#worth .worth-a", zmax=1.6, pad=40, sec=0.8)
    await d.pari("no", sec=2.0)
    await d.say(worth_caption(), need=3.6)
    await d.pari("idle", "Most days, the honest answer: wait.")

    # ================================================================ EXCEPT ONCE
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
    n = round(1.5 * FPS)
    for k in range(1, n + 1):
        p = C.ease(k / n); i = (N_DAYS - 1) + (CRASH_I - (N_DAYS - 1)) * p
        d.cur = [pos(i), y + h / 2]; await pg.mouse.move(d.cur[0], d.cur[1]); await d.frame()
    await pg.mouse.up()
    d.sfx("alert"); await d.pari("wow", sec=1.4)
    await d.say("…the gold crash. Every gap blew through the **cost line**.", need=3.2)
    await d.show_cursor(False, 0.2)

    # ================================================================ WHAT WE DO DIFFERENTLY: 1 of 4, every cost
    async def setup_slip():
        x, y, w, h, sy, H = await d.rect(".kpi", "Net profit")
        d.scroll = max(0, sy + y - 470); await d.wait(0.1)
        await d.set_slider("#slip", 5); await d.wait(0.15)
        x, y, w, h, *_ = await d.rect(".kpi", "Net profit"); xs, ys, ws, hs, *_ = await d.rect("#slip")
        d.cam([x - 30, ys - 70, (xs + ws) - x + 60, (y + h) - ys + 100], 0.05, zmax=1.7)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, "backtest", setup_slip)
    await d.pari("point_r", "Here's what we do differently.")
    d.chip(1); d.sfx("step", step=1)
    await d.say("Every fee. Every tax. And slippage **you control**.", need=2.4)
    await d.show_cursor(True, 0.2)
    d.log(tick=round(1.6 * FPS)); d.sfx("cost", d=1.6); await d.drag_slider("#slip", 5, 10, sec=1.6)
    await d.say(f"Past **{BE_MAX:.0f} bp** of slippage, no result survives.", need=2.8)
    await d.until_read()                                             # hold at 10 bp, the loss in red, while it is read
    await d.drag_slider("#slip", 10, 5, sec=0.7)
    await d.show_cursor(False, 0.2)

    # ---------------------------------------------------------------- 2 of 4: sealed tests
    async def setup_sealed():
        x, y, w, h, sy, H = await d.rect(".card", "Eight more years")
        d.scroll = max(0, sy + y - 70); await d.wait(0.1)
        await d.focus(".card", "Eight more years", zmax=1.45, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, "backtest", setup_sealed)
    d.chip(2); d.sfx("step", step=2)
    await d.say("Rules frozen in Git. **Eight years kept sealed**, then opened once.", need=3.3)
    await d.wait(0.4)
    await d.focus("tr", "fair price, as frozen", zmax=1.9, pad=28, sec=0.8)
    await d.pari("point_r", sec=1.6)
    await d.until_read()

    # ---------------------------------------------------------------- 3 of 4: honest reporting
    async def setup_honest():
        x, y, w, h, sy, H = await d.rect(".card", "A typical backtest vs our test")
        d.scroll = max(0, sy + y - 60); await d.wait(0.1)
        await d.focus(".card", "A typical backtest vs our test", zmax=1.3, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, None, setup_honest)
    d.chip(3); d.sfx("step", step=3)
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

    # ================================================================ PEAK: too good to be true? then the honest twist
    d.chip(0)
    d.rise(2.6)
    d.mus("drop")
    async def setup_twist():
        x, y, w, h, sy, H = await d.rect(".take")
        d.scroll = max(0, sy + y - 160); await d.wait(0.1)
        await d.focus(".take", zmax=1.45, pad=36, sec=0.05)
    await d.beat("toogood", 3.0, "backtest", setup_twist)
    d.sfx("impact_big"); d.mus(3)
    await d.say(f"January 2026 alone made **{inr_in(sum(JAN))}**.", need=2.6)
    d.sfx("cost"); await d.pari("sad", sec=2.6)
    await d.say(f"The other {len(A) - len(JAN)} trades lost **{inr_in(-REST) if REST < 0 else inr_in(REST)}**.", need=2.8)

    # ---------------------------------------------------------------- 4 of 4: tested for luck, and we say so
    async def setup_luck():
        x, y, w, h, sy, H = await d.rect(".card", "Skill, tuning or luck?")
        d.scroll = max(0, sy + y - 80); await d.wait(0.1)
        await d.focus(".card", "Skill, tuning or luck?", zmax=1.45, sec=0.05)
    d.sfx("whoosh")
    await d.beat("cut", 0.3, None, setup_luck)
    d.chip(4); d.sfx("step", step=4); d.mus(2)
    await d.say(f"Best of {SETTINGS} settings? A **{PBO}%** chance that's noise.", need=3.0)
    await d.wait(0.3)
    await d.focus(".kpi", "Overfitting (PBO)", zmax=2.0, pad=30, sec=0.8)
    await d.pari("proud", "Not proven. We say so.")
    d.chip(0)

    # ================================================================ HOW CLOSE ARE WE? the brief, line by line
    await d.until_read()
    d.mus(1)
    s0 = d.n
    for i, t in enumerate(BRIEF_T):
        d.log_at(s0 + round(t * FPS), sfx="tick_up", step=i)
    await d.beat("brief", 5.6)
    d.log_at(d.n - round(1.4 * FPS), pari="cheer", dur=round(1.4 * FPS))

    # ================================================================ THE OPEN ENDING
    d.mus("resolve")
    await d.beat("tomorrow", 3.0)
    d.sfx("end_chime")
    d.log(pari="wave", dur=round(2.4 * FPS))                       # no bubble: the end card carries the words
    await d.beat("end", 4.2)
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
        d = D4(pg, cdp)
        try:
            await story(d)
        finally:
            json.dump({"fps": FPS, "frames": d.n, "vw": VW, "vh": VH, "dsf": DSF, "events": d.events, "brief_t": BRIEF_T},
                      open(os.path.join(HERE, "timeline4.json"), "w"), indent=0)
            print("frames", d.n, "seconds", round(d.n / FPS, 1))
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())

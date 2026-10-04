import asyncio, os, glob
from playwright.async_api import async_playwright
URL = "file:///home/claude/hackinhills-syntaxterror-tan-/commodity/dashboard/index.html"
CAP = r"""(t) => { let c = document.getElementById('__cap');
  if (!c) { c = document.createElement('div'); c.id='__cap';
    c.style.cssText='position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;max-width:1180px;padding:16px 26px;border-radius:14px;background:rgba(20,18,14,.88);color:#fff;font:500 22px/1.4 system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.25);transition:opacity .35s;text-align:center';
    document.body.appendChild(c); }
  c.style.opacity = t ? 1 : 0; if (t) c.innerHTML = t; }"""
SLIDE = r"""(v) => { const el = document.getElementById('slip'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  set.call(el, String(v)); el.dispatchEvent(new Event('input', {bubbles:true})); }"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1600, "height": 900}, record_video_dir=".", record_video_size={"width": 1600, "height": 900}, color_scheme="light")
        pg = await ctx.new_page()
        cap = lambda t: pg.evaluate(CAP, t)
        async def go(v):
            await pg.goto(URL + "#" + v); await pg.wait_for_timeout(700)
            await pg.evaluate("document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))")
        async def scroll(px, ms=2600, steps=40):
            for _ in range(steps):
                await pg.mouse.wheel(0, px / steps); await pg.wait_for_timeout(ms // steps)
        w = pg.wait_for_timeout

        await go("overview"); await w(400)
        await cap("<b>Parity</b> · MCX gold futures intelligence · Team SYNTAX TERROR (TAN) · Problem 03"); await w(4000)
        await cap("Four MCX gold contracts, one metal. Parity puts all four in ₹ per gram of pure gold."); await w(3500)
        await scroll(520); await cap("Latest close: every contract against its fair price. Today the signal is quiet, so Parity says so."); await w(5000)
        await scroll(700); await w(3000)

        await go("relative"); await cap("Relative value: GOLDM and GOLDTEN match to 0.2 bp. The 8 g coin is 61–72 bp dearer, in all 41 cycles."); await w(5500)
        await scroll(650); await w(3500)
        await cap("In the Dec 2025 – Mar 2026 crash the small contracts sat about 2.7% above GOLDM."); await w(4000)

        await go("term"); await cap("Term structure: how much of a price move is roll-down, and how much is the curve itself moving."); await w(5000)
        await scroll(600); await w(2500)

        await go("backtest"); await cap("Backtest: rules frozen in Git, tested once on data they never saw, after MCX fees, taxes and slippage."); await w(5000)
        await cap("Slippage decides the result. Watch the net profit as fills get worse…"); await w(1500)
        for v in [5.5, 6.5, 7.5, 8.5, 10, 8, 6, 4, 2, 0, 2, 3.5, 5]:
            await pg.evaluate(SLIDE, v); await w(330)
        await w(1500)
        await pg.locator("text=\"B · sealed holdout\"").first.click(); await w(600); await cap("Strategy B, the fair-price rule: positive in every sealed test, but its 95% range still includes zero."); await w(4500)
        await scroll(900, 3000); await cap("Eight more years, 2016–2023, sealed and run once: A fails; B holds up modestly."); await w(5500)
        await scroll(900, 3000); await w(2500)

        await go("signals"); await cap("Signals: an alert fires only beyond ±1.5σ from fair price. Every past alert is listed with what happened next."); await w(5000)
        await scroll(800, 3000); await w(3000)

        await go("calendar"); await cap("Contract calendar: every trade checked against listing, expiry and the MCX tender period."); await w(5000)
        await scroll(500); await w(2500)

        await go("quality"); await cap("Data quality: 710 MCX contracts, 55,457 rows, 0 unexplained errors. Rules cited from the MCX contract specifications."); await w(5000)
        await go("overview"); await cap("Parity: a small, positive, honestly tested edge, decided by execution. Built by Nikhil Kumar, Sai Ganesh and Ishaan Chhabra."); await w(5000)
        await cap(""); await w(800)
        path = await pg.video.path()
        await ctx.close(); await b.close()
        os.replace(path, "raw.webm")
asyncio.run(main())

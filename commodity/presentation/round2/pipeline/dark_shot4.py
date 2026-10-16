"""Dark-mode frames for the theme switch in the v4 demo (v4.3).

Replays capture4.py's storyboard on the same paused clock up to the "Parity measures..." shot, switches the site to
its dark theme as that caption starts, and saves only those frames (framesdark4/), so dark frame N matches light
frame N in frames4/ except for the colours. Also records where the theme buttons are (theme_buttons4.json).

    FROM=440 python3 dark_shot4.py
"""
import asyncio, json, os, sys
os.environ.setdefault("FROM", "440")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capture as C
import capture4 as C4
HERE = os.path.dirname(os.path.abspath(__file__))
C.OUT = os.path.join(HERE, "framesdark4")
C.FROM = int(os.environ["FROM"])


class Stop(Exception): pass


class Dark(C4.D4):
    async def say(self, text, extra=0.0, need=None):
        if text.startswith("Is any gap"):
            raise Stop()
        if text.startswith("Parity measures"):
            await self.pg.evaluate("() => document.documentElement.setAttribute('data-theme', 'dark')")
            btn = {}
            for lab in ("Dark theme", "Light theme"):
                btn[lab] = await self.pg.evaluate("l => { const b = document.querySelector(`button[aria-label='${l}']`); const r = b.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }", lab)
            json.dump({"frame": self.n, "buttons": btn}, open(os.path.join(HERE, "theme_buttons4.json"), "w"))
        await super().say(text, extra, need)


async def main():
    os.makedirs(C.OUT, exist_ok=True)
    for f in os.listdir(C.OUT): os.remove(os.path.join(C.OUT, f))
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": C.VW, "height": C.VH}, device_scale_factor=C.DSF, color_scheme="light", reduced_motion="no-preference")
        await ctx.add_init_script("try{localStorage.clear()}catch(e){}")
        pg = await ctx.new_page()
        await pg.clock.install(time=1790000000000)
        await pg.goto(C.URL + "#backtest")
        await pg.wait_for_timeout(1500)
        await pg.clock.pause_at(1790000005000)
        await pg.evaluate(C.INJECT)
        cdp = await ctx.new_cdp_session(pg)
        d = Dark(pg, cdp)
        try:
            await C4.story(d)
        except Stop:
            print("stopped at frame", d.n)
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())

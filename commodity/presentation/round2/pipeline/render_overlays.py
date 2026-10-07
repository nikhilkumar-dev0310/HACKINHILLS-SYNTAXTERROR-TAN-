"""Render intro, chapter cards, outro (frame sequences) and every caption / Pari sprite (transparent PNGs)."""
import asyncio, json, os, sys, hashlib
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "overlays.html")
QR = "file://" + os.path.abspath(os.path.join(HERE, "..", "..", "round1", "assets", "qr-site.png"))   # the live site
FPS = 30
LABELS = ["The front page", "The brief", "Relative value", "Term structure", "Backtest", "Signals", "Contracts", "Data quality"]

def cap_key(text, label): return hashlib.md5((label + "|" + text).encode()).hexdigest()[:12]

async def main(which):
    os.makedirs("ov/intro", exist_ok=True); os.makedirs("ov/outro", exist_ok=True); os.makedirs("ov/cards", exist_ok=True); os.makedirs("ov/caps", exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        await pg.goto(URL); await pg.wait_for_timeout(500)
        await pg.evaluate("document.fonts.ready")
        # the intro's four price cards show the latest closes the site shows (dashboard/data.json)
        D = json.load(open(os.path.join(HERE, "..", "..", "..", "dashboard", "data.json")))
        Q = {q["symbol"]: q for q in D["quotes"]}
        await pg.evaluate("q => { C4 = C4.map(c => [c[0], c[1], q[c[0]].close, c[3], Math.round(q[c[0]].rs_per_g), c[5]]); }", Q)
        if "caps" in which:
            tl = json.load(open(os.environ.get("TLF", "timeline.json")))
            ch, meta = 0, {}
            for e in tl["events"]:
                if "card" in e: ch = e["card"]
                if e.get("cap"):
                    label = f"{ch:02d} · {LABELS[ch - 1]}"; k = cap_key(e["cap"], label)
                    if k in meta: continue
                    r = await pg.evaluate("([h,l]) => caption(h,l)", [e["cap"], label])
                    await pg.screenshot(path=f"ov/caps/{k}.png", omit_background=True, clip={"x": r[0] - 2, "y": r[1] - 2, "width": r[2] + 4, "height": r[3] + 4})
                    meta[k] = {"w": r[2] + 4, "h": r[3] + 4}
            old = json.load(open("ov/caps/meta.json")) if os.path.exists("ov/caps/meta.json") else {}
            old.update(meta); json.dump(old, open("ov/caps/meta.json", "w"))
            print("captions", len(meta))
        if "pari" in which:
            for mood in ("happy", "talk", "wow"):
                for blink in (0, 1):
                    await pg.evaluate("([m,b]) => pari(m,b,0)", [mood, blink])
                    await pg.screenshot(path=f"ov/pari_{mood}_{blink}.png", omit_background=True, clip={"x": 0, "y": 0, "width": 180, "height": 186})
        if "intro" in which:
            n = round(15.0 * FPS)
            for i in range(n):
                await pg.evaluate("t => intro(t)", i / FPS); await pg.screenshot(path=f"ov/intro/{i:04d}.jpg", type="jpeg", quality=93)
            print("intro", n)
        if "intro_fast" in which:
            os.makedirs("ov/intro_fast", exist_ok=True); n = round(15.0 / 1.6 * FPS)
            for i in range(n):
                await pg.evaluate("t => intro(t)", min(15.0, i / FPS * 1.6)); await pg.screenshot(path=f"ov/intro_fast/{i:04d}.jpg", type="jpeg", quality=93)
            print("intro_fast", n)
        if "outro_fast" in which:
            os.makedirs("ov/outro_fast", exist_ok=True)
            warp = lambda s: s * 1.6 if s * 1.6 < 11.1 else 11.1 + (s - 11.1 / 1.6)
            n = round((11.1 / 1.6 + 3.9) * FPS)
            for i in range(n):
                await pg.evaluate("([t,q]) => outro(t,q)", [warp(i / FPS), QR]); await pg.screenshot(path=f"ov/outro_fast/{i:04d}.jpg", type="jpeg", quality=93)
            print("outro_fast", n)
        if "cards" in which:
            for c in range(1, 9):
                for i in range(66):
                    await pg.evaluate("([c,t]) => card(c,t)", [c, i / FPS]); await pg.screenshot(path=f"ov/cards/{c}_{i:03d}.jpg", type="jpeg", quality=93)
            print("cards")
        if "outro" in which:
            n = round(15.0 * FPS)
            for i in range(n):
                await pg.evaluate("([t,q]) => outro(t,q)", [i / FPS, QR]); await pg.screenshot(path=f"ov/outro/{i:04d}.jpg", type="jpeg", quality=93)
            print("outro", n)
        await b.close()

asyncio.run(main(sys.argv[1:] or ["pari", "intro", "cards", "outro"]))

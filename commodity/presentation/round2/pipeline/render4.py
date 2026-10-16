"""Render the v4 overlays from overlays4.html (plus Pari's bubbles and the "what we do differently" chip): captions (transparent PNGs), statement cards and the
"your guess" countdown (frame sequences), sized from timeline3.json.

    python render3.py
"""
import asyncio, hashlib, json, os
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "overlays4.html")
QR = "file://" + os.path.abspath(os.path.join(HERE, "..", "..", "round1", "assets", "qr-site.png"))
FPS = 30
OV = os.path.join(HERE, "ov4")


def key(text): return hashlib.md5(text.encode()).hexdigest()[:12]


def inr_in(v):
    s = str(abs(round(v))); h, t = s[:-3], s[-3:]
    while len(h) > 2: t = h[-2:] + "," + t; h = h[:-2]
    return ("−" if v < 0 else "") + "₹" + (h + "," + t if h else t)


async def main():
    tl = json.load(open(os.path.join(HERE, "timeline4.json")))
    D = json.load(open(os.path.join(HERE, "..", "..", "..", "dashboard", "data.json")))
    A = [t for t in D["trades"]["A_hold"] if t["ok_tender"]]
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last = D["meta"]["last"]
    V = {"net": inr_in(sum(t["net5"] for t in A)), "last": f"{int(last[8:])} {mon[int(last[5:7]) - 1]} {last[:4]}",
         "tests": f"{D['tests']['tests']:,}", "qr": QR, "brief_t": tl.get("brief_t", []),
         "years": int(D["meta"]["all"]["last"][:4]) - int(D["meta"]["all"]["first"][:4]), "contracts": D["meta"]["all"]["contracts"]}
    for sub in ("caps", "beats", "predict", "bubbles", "chips"): os.makedirs(os.path.join(OV, sub), exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1920, "height": 1080})
        await pg.goto(URL); await pg.wait_for_timeout(400); await pg.evaluate("document.fonts.ready")
        await pg.evaluate("v => { V = v; }", V)
        meta = {}
        for e in tl["events"]:
            if e.get("cap"):
                k = key(e["cap"])
                if k in meta: continue
                r = await pg.evaluate("h => caption(h)", e["cap"])
                await pg.screenshot(path=os.path.join(OV, "caps", k + ".png"), omit_background=True,
                                    clip={"x": r[0] - 2, "y": r[1] - 2, "width": r[2] + 4, "height": r[3] + 4})
                meta[k] = {"w": r[2] + 4, "h": r[3] + 4, "text": e["cap"]}
        json.dump(meta, open(os.path.join(OV, "caps", "meta.json"), "w"))
        for e in tl["events"]:
            if e.get("bubble"):
                k = key(e["bubble"]); r = await pg.evaluate("t => bubble(t)", e["bubble"])
                await pg.screenshot(path=os.path.join(OV, "bubbles", k + ".png"), omit_background=True,
                                    clip={"x": r[0] - 46, "y": r[1] - 46, "width": r[2] + 92, "height": r[3] + 92})   # room for the soft shadow
        B = json.load(open(os.path.join(HERE, "banter4.json")))
        for txt in [x[1] for x in B["after_caption"]] + [x[2] for x in B["on_card"]]:
            k = key(txt); r = await pg.evaluate("t => bubble(t)", txt)
            await pg.screenshot(path=os.path.join(OV, "bubbles", k + ".png"), omit_background=True,
                                clip={"x": r[0] - 46, "y": r[1] - 46, "width": r[2] + 92, "height": r[3] + 92})
        r = await pg.evaluate("t => titlev(t)", B["title"])
        await pg.screenshot(path=os.path.join(OV, "chips", "title.png"), omit_background=True,
                            clip={"x": 0, "y": 0, "width": r[0] + r[2] + 30, "height": r[1] + r[3] + 30})
        for n in range(1, 5):
            r = await pg.evaluate("n => chipv(n)", n)
            await pg.screenshot(path=os.path.join(OV, "chips", f"{n}.png"), omit_background=True,
                                clip={"x": 0, "y": 0, "width": r[0] + r[2] + 30, "height": r[1] + r[3] + 30})
        done = set()
        for e in tl["events"]:
            if "beat" in e and e["beat"] not in ("cut",) and e["beat"] not in done:
                done.add(e["beat"]); d = os.path.join(OV, "beats", e["beat"]); os.makedirs(d, exist_ok=True)
                for i in range(e["dur"]):
                    await pg.evaluate("([n, t]) => beat(n, t)", [e["beat"], i / FPS])
                    if e["beat"] == "end": await pg.wait_for_timeout(30 if i else 300)    # let the QR image load
                    await pg.screenshot(path=os.path.join(d, f"{i:04d}.jpg"), type="jpeg", quality=93)
            if "predict" in e:
                for i in range(e["predict"]):
                    await pg.evaluate("([t, d]) => predict(t, d)", [i / FPS, e["predict"] / FPS])
                    await pg.screenshot(path=os.path.join(OV, "predict", f"{i:04d}.png"), omit_background=True)
        await b.close()
    print("captions", len(meta), "cards", sorted(done))


asyncio.run(main())

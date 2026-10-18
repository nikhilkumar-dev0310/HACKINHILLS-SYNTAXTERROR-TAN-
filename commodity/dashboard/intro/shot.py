import asyncio, sys, pathlib, time
from playwright.async_api import async_playwright
H=pathlib.Path(__file__).parent; NM=H/"node_modules/three"
mode=sys.argv[1]  # desktop | phone
async def route(r):
    u=r.request.url
    if "cdn.jsdelivr.net/npm/three@0.170.0/" in u:
        rel=u.split("three@0.170.0/")[1]; f=NM/rel
        return await r.fulfill(path=str(f), headers={"content-type":"application/javascript","access-control-allow-origin":"*"})
    if "fonts.g" in u: return await r.abort()
    await r.continue_()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=["--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader","--ignore-gpu-blocklist"])
        if mode=="phone":
            dev=p.devices["iPhone 13"]; ctx=await b.new_context(**{k:v for k,v in dev.items() if k!="default_browser_type"}, reduced_motion="reduce")
        else: ctx=await b.new_context(viewport={"width":1440,"height":900}, reduced_motion="reduce")
        pg=await ctx.new_page(); errs=[]; logs=[]
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: logs.append(m.text) if m.type in ("error","warning") else None)
        await pg.route("**/*", route)
        await pg.goto("file://"+str(H/"index.html")); await pg.wait_for_timeout(2500)
        n=await pg.evaluate("document.querySelectorAll('.beat').length")
        for i in range(n):
            top=await pg.evaluate(f"document.querySelectorAll('.beat')[{i}].offsetTop")
            span=await pg.evaluate(f"(document.querySelectorAll('.beat')[{i+1}]||{{offsetTop:document.documentElement.scrollHeight}}).offsetTop - {top}") if i<n-1 else 0
            await pg.evaluate(f"scrollTo(0,{top + (span*0.1 if i<n-1 else 0)})"); await pg.wait_for_timeout(1600)
            await pg.screenshot(path=str(H/f"{mode}_{i}.png"))
        # a mid-transition frame
        print(mode, "errors:", errs, "console:", logs[:5])
        await b.close()
asyncio.run(main())

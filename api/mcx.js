// Read-only relay to MCX's public Bhavcopy, run from Vercel's Mumbai region (vercel.json: bom1).
// MCX refuses requests from GitHub's US servers; the daily GitHub Action calls this instead.
// Fixed to one host and two pages, gold futures only, every parameter validated: it cannot fetch anything else.
const BASE = "https://www.mcxindia.com";
const PAGE = "/market-data/bhavcopy";
const SYMS = new Set(["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]);
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36";
const H = { "User-Agent": UA, "Accept-Language": "en-IN,en;q=0.9" };

function cookiesOf(res) {
  const raw = typeof res.headers.getSetCookie === "function" ? res.headers.getSetCookie() : [];
  return raw.map(c => c.split(";")[0]).join("; ");
}
async function openPage() {
  const r = await fetch(BASE + PAGE, { headers: { ...H, Accept: "text/html,application/xhtml+xml" }, redirect: "follow" });
  return { r, html: await r.text(), cookie: cookiesOf(r) };
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  const q = req.query || {};
  try {
    if (q.mode === "probe") {
      const { r, html } = await openPage();
      const title = (html.match(/<title>([^<]*)/i) || [])[1] || "";
      return res.status(200).json({ status: r.status, title: title.trim(), hasList: html.includes('id="symbol-data"'), bytes: html.length, region: process.env.VERCEL_REGION || null });
    }
    if (q.mode === "list") {
      const { r, html } = await openPage();
      const m = html.match(/id="symbol-data"[^>]*>([\s\S]*?)<\/script>/i);
      if (r.status !== 200 || !m) return res.status(502).json({ error: "MCX page not available", status: r.status });
      const list = JSON.parse(m[1]).filter(x => /FUTCOM/i.test(x.InstrumentName || "") && SYMS.has((x.SymbolValue || "").trim()))
        .map(x => ({ symbol: x.SymbolValue.trim(), expiry: x.ExpiryDate.trim() }));
      return res.status(200).json({ list });
    }
    if (q.mode === "data") {
      const { symbol, expiry, from, to } = q;
      if (!SYMS.has(symbol) || !/^\d{2}[A-Z]{3}\d{4}$/.test(expiry || "") || !/^\d{2}\/\d{2}\/\d{4}$/.test(from || "") || !/^\d{2}\/\d{2}\/\d{4}$/.test(to || ""))
        return res.status(400).json({ error: "bad parameters" });
      const { cookie } = await openPage();
      const u = BASE + PAGE + "/GetCommoditywiseBhavCopy?" + new URLSearchParams({ InstrumentName: "FUTCOM", Symbol: symbol, Expiry: expiry, fromDate: from, toDate: to });
      const r = await fetch(u, { headers: { ...H, Accept: "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest", Referer: BASE + PAGE, ...(cookie ? { Cookie: cookie } : {}) } });
      const text = await r.text();
      if (r.status !== 200) return res.status(502).json({ error: "MCX refused", status: r.status, body: text.slice(0, 200) });
      return res.status(200).json({ data: (JSON.parse(text).Data) || [] });
    }
    return res.status(400).json({ error: "mode must be probe, list or data" });
  } catch (e) {
    return res.status(502).json({ error: String(e && e.message || e) });
  }
}

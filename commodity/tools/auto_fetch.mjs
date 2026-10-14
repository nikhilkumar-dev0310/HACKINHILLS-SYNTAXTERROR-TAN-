// Daily, unattended version of tools/mcx_fetch.js (runs in GitHub Actions, no person needed).
//
//   node tools/auto_fetch.mjs <since YYYY-MM-DD> <out.json.gz>
//
// Opens the official MCX Bhavcopy page in headless Chromium and, from inside that page, calls the
// page's own commodity-wise Bhavcopy endpoint for every GOLDM / GOLDTEN / GOLDGUINEA / GOLDPETAL
// futures contract that expires on or after <since> (the contracts still trading, plus any newly
// listed). Each file is built with the page's own XLS export (ExportManager), so it is byte-for-byte
// what the page's Download button gives a person. 400 ms pause between requests.
import { chromium } from "playwright";
import { writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";

const [since, out] = process.argv.slice(2);
if (!since || !out) { console.error("usage: node tools/auto_fetch.mjs YYYY-MM-DD out.json.gz"); process.exit(2); }

// PARITY_CHROME=chrome uses the computer's installed Google Chrome instead of Playwright's bundled Chromium.
// MCX's firewall turns away Playwright's old-style headless browser (403 Access Denied) even from a home
// connection. So with the real Chrome the job runs quietly in the background:
//   1. "hidden": Chrome's modern headless mode (the full browser, no window at all);
//   2. if MCX refuses that, "offscreen": a normal Chrome window placed off the screen, small, muted.
// Either way it is one tab, images/fonts/video are not downloaded, and Chrome quits as soon as the files are in
// (about a minute a day, a few hundred MB of memory while it runs, nothing afterwards).
const LEAN = ["--disable-blink-features=AutomationControlled", "--no-first-run", "--no-default-browser-check",
  "--disable-extensions", "--disable-sync", "--disable-background-networking", "--disable-component-update",
  "--mute-audio", "--renderer-process-limit=2", "--js-flags=--max-old-space-size=256"];
const CHROME = process.env.PARITY_CHROME;
const MODES = CHROME ? ["hidden", "offscreen"] : ["bundled"];
const SY = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"];

// Never ask for a day that is still trading: a Bhavcopy row is final only after the evening session (23:30 IST).
// Before 23:55 IST the last day requested is yesterday, so a job that runs late (a computer that slept through
// 03:30) cannot pick up a partial day that would later "change its close" and block every following update.
const ist = new Date(Date.now() + 5.5 * 3600e3);
const istMin = ist.getUTCHours() * 60 + ist.getUTCMinutes();
const capD = new Date(Date.UTC(ist.getUTCFullYear(), ist.getUTCMonth(), ist.getUTCDate() - (istMin < 23 * 60 + 55 ? 1 : 0)));
const CAP = capD.toISOString().slice(0, 10);

async function openMcx(mode) {
  const args = [...LEAN];
  if (mode === "hidden") args.push("--headless=new", "--window-size=1366,900");
  if (mode === "offscreen") args.push("--window-position=-2400,-2400", "--window-size=900,700");
  const browser = await chromium.launch({ args, ...(CHROME ? { channel: CHROME, headless: false } : {}) });
  const ver = browser.version().split(".")[0];
  const ctx = await browser.newContext({
    userAgent: mode === "hidden"
      ? `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${ver}.0.0.0 Safari/537.36`
      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    locale: "en-IN", timezoneId: "Asia/Kolkata", viewport: { width: 1366, height: 900 },
  });
  await ctx.route("**/*", r => (["image", "font", "media"].includes(r.request().resourceType()) ? r.abort() : r.continue()));
  const page = await ctx.newPage();
  const tries = mode === "hidden" ? 1 : 3;
  for (let attempt = 1; attempt <= tries; attempt++) {
    try {
      const r = await page.goto("https://www.mcxindia.com/market-data/bhavcopy", { waitUntil: "domcontentloaded", timeout: 90000 });
      console.log(mode, "page status", r && r.status(), "title:", await page.title());
      await page.waitForSelector("#symbol-data", { state: "attached", timeout: 60000 });
      await page.waitForFunction(() => typeof ExportManager !== "undefined", null, { timeout: 60000 });
      console.log("MCX page ready in", mode, "mode");
      return { browser, page };
    } catch (e) {
      let info = ""; try { info = ` url=${page.url()} title=${await page.title()} body=${(await page.evaluate(() => document.body ? document.body.innerText.slice(0, 160) : "")).replace(/\s+/g, " ")}`; } catch (_) {}
      console.log(mode, "attempt", attempt, "failed:", e.message.split("\n")[0], info);
      if (attempt < tries) await page.waitForTimeout(10000 * attempt);
    }
  }
  await browser.close();
  return null;
}

let got = null;
for (const m of MODES) { got = await openMcx(m); if (got) break; }
if (!got) { console.error("MCX page did not load"); process.exit(3); }
const { browser, page } = got;

const res = await page.evaluate(async ([since, cap, SY]) => {
  const MON = { JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5, JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11 };
  const pexp = e => new Date(+e.slice(5, 9), MON[e.slice(2, 5)], +e.slice(0, 2));
  const dmy = d => `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
  const cut = new Date(since + "T00:00:00"), last = new Date(cap + "T00:00:00");
  const list = JSON.parse(document.getElementById("symbol-data").innerText)
    .filter(x => /FUTCOM/i.test(x.InstrumentName || "") && SY.includes((x.SymbolValue || "").trim()));
  const seen = new Set(), jobs = [];
  for (const x of list) {
    const s = x.SymbolValue.trim(), e = x.ExpiryDate.trim(), ed = pexp(e);
    if (ed >= cut && !seen.has(s + e)) { seen.add(s + e); jobs.push({ s, e, ed }); }
  }
  const files = {}, log = [], listed = {}; let captured = null;
  for (const x of list) listed[x.SymbolValue.trim()] = (listed[x.SymbolValue.trim()] || 0) + 1;
  const wait = ms => new Promise(z => setTimeout(z, ms));
  // MCX sometimes drops a run of requests ("Failed to fetch"): each contract is retried up to 4 times, backing off.
  async function get(q) {
    let err = "";
    for (let a = 1; a <= 4; a++) {
      try {
        const r = await fetch("/market-data/bhavcopy/GetCommoditywiseBhavCopy?" + q);
        if (r.ok) { const D = (await r.json()).Data || []; if (D.length || a >= 2) return [D, a, ""]; err = "empty"; }
        else err = "HTTP " + r.status;
      } catch (e) { err = e.message; }
      await wait(1500 * a);
    }
    return [[], 4, err];
  }
  const orig = ExportManager.downloadFile; ExportManager.downloadFile = c => { captured = c; };
  for (const j of jobs) {
    const from = new Date(j.ed.getFullYear() - 2, 0, 1), to = j.ed < last ? j.ed : last;
    const q = new URLSearchParams({ InstrumentName: "FUTCOM", Symbol: j.s, Expiry: j.e, fromDate: dmy(from), toDate: dmy(to) });
    const [D, tries, err] = await get(q);
    if (D.length) { captured = null; ExportManager.exportData(D, j.s + "_" + j.e, "xls", dmy(from)); if (captured) files[j.s + "_" + j.e + ".xls"] = captured; }
    log.push([j.s, j.e, dmy(from), dmy(to), D.length, tries > 1 ? `tries ${tries}` : "", err]);
    await wait(700);
  }
  ExportManager.downloadFile = orig;
  return { files, log, listed };
}, [since, CAP, SY]);
await browser.close();
console.log("listed by MCX:", JSON.stringify(res.listed), " up to", CAP, " requested since", since + ":", res.log.length, " files:", Object.keys(res.files).length);
for (const l of res.log) console.log("  ", l.join("  "));
if (!Object.keys(res.files).length) { console.error("no files returned"); process.exit(4); }
// A contract type that did not come back is reported, not fatal: daily_update.py publishes the day with what MCX
// returned (at least two types) and fetches the missing contracts again on every run until MCX returns them.
const gotSym = new Set(Object.keys(res.files).map(n => n.split("_")[0]));
const miss = SY.filter(s => !gotSym.has(s));
if (miss.length) {
  const why = miss.map(s => `${s}: ${res.listed[s] ? `${res.listed[s]} listed, ` + res.log.filter(l => l[0] === s).map(l => l[6] || "no rows").join("/") : "not in MCX's contract list"}`).join("; ");
  console.log(`::warning title=Fetch incomplete::MCX returned no files for ${miss.join(", ")} (${why}). The other contracts are used; these are fetched again next run.`);
}
writeFileSync(out, gzipSync(JSON.stringify(res.files)));

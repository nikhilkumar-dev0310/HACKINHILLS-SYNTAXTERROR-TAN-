/* Shared data, formatting and reference content for Parity.
   D is the exported analysis (dashboard/data.json), inlined into the page by build.py. */
export const D = window.__PARITY_DATA__;

export const NAME = "Parity";
export const SYMS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"];
export const SYM = {
  GOLDM: { c: "var(--s-m)", d: "100 g bar, 995" }, GOLDTEN: { c: "var(--s-ten)", d: "10 g bar, 999" },
  GOLDGUINEA: { c: "var(--s-gui)", d: "8 g coin, 999" }, GOLDPETAL: { c: "var(--s-pet)", d: "1 g, 999" }
};
export const SHORT = { M: "GOLDM", TEN: "GOLDTEN", GUINEA: "GOLDGUINEA", PETAL: "GOLDPETAL" };
export const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const inr = (v, d = 0) => (v < 0 ? "−" : "") + "₹" + Math.abs(v).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
export const sgn = (v, d = 1, u = "") => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d) + u;
export const fdate = s => { const [y, m, d] = s.split("-"); return `${+d} ${MON[m - 1]} ${y}`; };
export const fmon = s => { const [y, m] = s.split("-"); return `${MON[m - 1]} ${y.slice(2)}`; };
export const T = s => new Date(s + "T00:00:00Z").getTime();
export const mm = v => String(v).replace(/^-/, "−");
export const slug = s => s.toLowerCase().replace(/[^a-z0-9.]+/g, "-").replace(/^-|-$/g, "");
export const r2 = v => v == null || !isFinite(v) ? null : Math.round(v * 100) / 100;
export const pname = k => k.split("-").map(s => SHORT[s]).join(" − ");
export const P = Object.fromEntries(D.pairs.map(p => [p.pair, p]));
export const CRASH = D.crash_window;
export const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export const VIEWS = [
  ["overview", "Overview"], ["brief", "The brief"], ["relative", "Relative value"], ["term", "Term structure"],
  ["backtest", "Backtest"], ["signals", "Signals"], ["calendar", "Contracts"], ["quality", "Data quality"]
];
export const ICON = {
  overview: '<path d="M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-3H4zM14 4v3h6V4z"/>',
  brief: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h4"/>',
  relative: '<path d="M4 17l5-5 4 4 7-8"/><path d="M14 8h6v6"/>',
  term: '<path d="M3 20h18"/><path d="M5 16c4-1 6-5 9-7s5-3 7-3"/>',
  backtest: '<path d="M4 4v16h16"/><path d="M8 14l3-3 3 2 5-6"/>',
  signals: '<path d="M2 12h4l3-8 4 16 3-8h6"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  quality: '<path d="M12 3l8 4v5c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7z"/><path d="M9 12l2 2 4-4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
  news: '<path d="M4 6h16M4 12h10M4 18h7"/><circle cx="18" cy="17" r="3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  auto: '<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 0 0 16z" fill="currentColor"/>',
  download: '<path d="M12 4v11"/><path d="M7 10l5 5 5-5"/><path d="M5 20h14"/>',
  more: '<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  term2: '<path d="M4 19h16M7 15V9M12 15V5M17 15v-3"/>',
  book: '<path d="M5 4h10a4 4 0 0 1 4 4v12H9a4 4 0 0 1-4-4z"/><path d="M5 16a4 4 0 0 1 4-4h10"/>'
};

/* Market events drawn on time charts. Every one is either in our own data (the dated row) or in a cited report;
   the price moves quoted are GOLDM's change in our data on that day. */
export const EVENTS = [
  { date: "2023-11-12", tag: "Muhurat", text: "Diwali Muhurat: a special Sunday session.", src: "Sunday row in the MCX files; testbed check" },
  { date: "2024-07-23", tag: "Duty cut to 6%", text: "Union Budget cuts customs duty on gold to 6%. GOLDM −5.5% on the day.", src: "Business Today, 23 Jul 2024; MCX Bhavcopy" },
  { date: "2025-02-01", tag: "Budget", text: "Union Budget day: special Saturday session.", src: "Saturday row in the MCX files" },
  { date: "2025-04-01", tag: "GOLDTEN lists", text: "GOLDTEN (10 g, 999) starts trading.", src: "Outlook Money, 1 Apr 2025" },
  { date: "2026-01-30", tag: "Gold −10%", text: "Gold falls about 10% in a day. GOLDM settles at its daily limit (−10.4%); the small contracts settle 12% lower.", src: "News Arena and Motilal Oswal, 30 Jan 2026; MCX Bhavcopy" },
  { date: "2026-02-01", tag: "Budget", text: "Union Budget day: special Sunday session. GOLDM −5.6%.", src: "Sunday row in the MCX files" },
  { date: "2026-05-13", tag: "Duty 6% → 15%", text: "Import duty on gold raised from 6% to 15%, effective that day. GOLDM +5.5%.", src: "Customs Notification 16/2026; LiveLaw, 13 May 2026" }
];

/* Plain-English definitions shown on hover/focus of dotted terms and searchable in the command menu. */
export const GLOSSARY = {
  bp: ["bp", "Basis point: one hundredth of a percent. 100 bp = 1%."],
  carry: ["Carry", "Cost of carry: how much more a later-expiring future costs, because holding gold until then ties up money. Quoted as % a year."],
  slippage: ["Slippage", "How much worse than the quoted price a real order fills, charged on every leg, each side. 5 bp is our realistic case."],
  sigma: ["σ (standard deviation)", "The typical size of a swing. A gap 1.5σ from usual is one and a half typical swings away."],
  vwap: ["VWAP", "Volume-weighted average price: the average of all the day's trades, weighted by size. Closer to what a real order gets than the official close."],
  premium: ["Premium", "How much more a contract costs than GOLDM per gram of pure gold, after moving GOLDM to the same expiry."],
  tender: ["Tender period", "The last 5 business days before expiry, when contracts move toward physical delivery. Brokers close positions before it starts."],
  settlement: ["Settlement price", "The official closing price MCX publishes for each contract every day."],
  rolldown: ["Roll-down", "The drift of a futures price toward spot as expiry nears, with nothing else changing."],
  sealed: ["Sealed test", "Data set aside and not looked at until the rules were frozen in Git, then run once. No second tries."],
  insample: ["In-sample", "The same data the settings were chosen on. Results there look better than they will on new data."],
  bhavcopy: ["Bhavcopy", "MCX's official daily file: every contract's prices, volume and open interest."],
  purity: ["Purity", "Share of pure gold. GOLDM is 995 (99.5%); GOLDTEN, GOLDGUINEA and GOLDPETAL are 999 (99.9%)."],
  range95: ["95% range", "From resampling whole weeks of results: the true average sits inside it 95 times in 100."],
  gross: ["Gross and net", "Gross is profit before costs. Net is after MCX fees, taxes, brokerage and slippage."],
  walkforward: ["Walk-forward", "Replaying the market one day at a time, using only what was known on that day."],
  expiry: ["Expiry", "The day a futures contract ends. Each contract here is tracked by its own expiry, never stitched into a series."],
  oi: ["Open interest", "Contracts still open at the end of the day."]
};

export const NAV_KEYS = "12345678";

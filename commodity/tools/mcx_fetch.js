// Round 3 download (2026-10-04). Paste into the browser console on https://www.mcxindia.com/market-data/bhavcopy.
// For every GOLDM / GOLDTEN / GOLDGUINEA / GOLDPETAL futures expiry MCX lists, it calls the page's own
// commodity-wise Bhavcopy endpoint and builds the file with the page's own XLS export (ExportManager),
// so each file is exactly what the page's Download button produces. 250 ms pause between requests.
// At the end it saves one gzip bundle {file name: xls content}; tools/unpack_bundle.py writes raw_clean/.
(async () => {
  const SY = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];
  const MON = { JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5, JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11 };
  const pexp = e => new Date(+e.slice(5, 9), MON[e.slice(2, 5)], +e.slice(0, 2));
  const dmy = d => `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
  const list = JSON.parse(document.getElementById('symbol-data').innerText)
    .filter(x => /FUTCOM/i.test(x.InstrumentName || '') && SY.includes((x.SymbolValue || '').trim()));
  const seen = new Set(), jobs = [];
  for (const x of list) { const s = x.SymbolValue.trim(), e = x.ExpiryDate.trim(); if (!seen.has(s + e)) { seen.add(s + e); jobs.push({ s, e, ed: pexp(e) }); } }
  const today = new Date(), files = {}; let captured = null;
  const orig = ExportManager.downloadFile; ExportManager.downloadFile = c => { captured = c; };
  for (const j of jobs) {
    const from = new Date(j.ed.getFullYear() - 2, 0, 1), to = j.ed < today ? j.ed : today;
    const q = new URLSearchParams({ InstrumentName: 'FUTCOM', Symbol: j.s, Expiry: j.e, fromDate: dmy(from), toDate: dmy(to) });
    const D = (await fetch('/market-data/bhavcopy/GetCommoditywiseBhavCopy?' + q).then(r => r.json())).Data || [];
    if (D.length) { ExportManager.exportData(D, j.s + '_' + j.e, 'xls', dmy(from)); files[j.s + '_' + j.e + '.xls'] = captured; }
    await new Promise(z => setTimeout(z, 250));
  }
  ExportManager.downloadFile = orig;
  const gz = await new Response(new Blob([JSON.stringify(files)]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
  const a = document.createElement('a'); a.href = URL.createObjectURL(gz); a.download = 'mcx_gold_round3.json.gz'; a.click();
})();

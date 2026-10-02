# Polish round 2: progress (paused 3 Oct 2026, 04:50 IST)

Figma file: https://www.figma.com/design/6XRN8oEtTYy9OtnzxcmWGy (Starter plan: ~20 Figma tool calls/month, 1 mode per variable collection)

## Done in Figma
- Pages: Foundations (0:1), Components (2:2), Polish · Oct 2026 (2:3, empty)
- Variables: "Color · Dark" (VariableCollectionId:2:4) and "Color · Light" (2:5), 28 tokens each, code syntax var(--token);
  "Space & radius" (2:62), 12 tokens. 17 text styles (Inter + JetBrains Mono; Mono Semi Bold not in Figma, Bold used).
- Token sheets: Foundations — Dark (2:90), Foundations — Light (2:290), with contrast figures.
- Components (bound to Dark): icons 3:6..3:49 (incl. new auto 3:41, download 3:49), Kbd 3:50, Chip set 3:68,
  Theme switch 3:96 (Full / Icon only), Nav item 3:134, Button 3:147, Segment 3:152, KPI card 3:165, Pill 3:174,
  review frame 3:175.
- Known fix for next call: Pill set shares one Label property, so all variants read "Clear";
  delete property Label#3:36 and set per-variant text (Clear / Rich vs GOLDM / In tender / Too recent).

## Decisions from Figma measurements
- Compact chips: Basis 161 px, Count 188 px; with a 10 px gap = 359 px > 358 px available at 390 px.
- Phone header: row 1 = Basis chip (compact) + icon-only theme switch (109 px), row 2 = contracts chip. Saves one row.

## Next steps
1. Figma: build review frames on "Polish · Oct 2026": phone header now vs compact (dark + light),
   trade log + CSV button, alert log + CSV button, sidebar with key hints and "Turn off shortcuts", KPI count-up spec.
   Real figures to use: A_hold net 5.0 bp Rs 1,90,340 (32%) -> 6.0 bp Rs 1,55,258 (31%); 120 ms frame Rs 1,66,201.
2. Code (template.html), the four approved features:
   - Keys 1-8 jump to sections (ignore inputs and modifier keys), kbd hint on nav hover/focus,
     "Turn off shortcuts" switch saved in localStorage (WCAG 2.1.4).
   - Download CSV on trade log (all rows in current view; strategy, slippage, tender in file name) and alert log.
   - Compact phone header (layout above; icon-only switch with aria-labels; add auto icon to full switch too).
   - KPI numbers count to new values in 400 ms, cubic-bezier(.2,0,0,1), restart from current value, instant with reduced motion.
   - Small consistency fix: .theme button transition uses raw .25s; switch to var(--dur-2) var(--ease).
3. Rebuild (python dashboard/build.py), audit 4 widths x 2 themes x 8 views, sync Figma, commit, push.

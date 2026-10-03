# Polish round 2 (3 Oct 2026): done

Figma file: https://www.figma.com/design/6XRN8oEtTYy9OtnzxcmWGy (Starter plan: about 20 Figma tool calls a month,
1 mode per variable collection, so Dark and Light are two collections with identical variable names)

## In Figma
- Foundations (page 0:1): "Color · Dark" and "Color · Light" variables (28 each, code syntax var(--token)),
  "Space & radius" (12), 21 text styles, token sheets with contrast figures (2:90, 2:290).
- Components (page 2:2): icons, Kbd, Chip, Theme switch (Full / Icon only), Nav item, Button, Segment, KPI card, Pill.
- Polish · Oct 2026 (page 2:3): phone header now vs compact (dark and light), trade log and alert log with CSV,
  sidebar with number keys, KPI count-up spec, notes.

## In the site (commodity/dashboard/template.html)
1. Keys 1-8 switch sections (ignored in inputs and with Ctrl/Cmd/Alt); key cap on nav hover/focus; aria-keyshortcuts;
   "Turn off shortcuts" in the sidebar footer, remembered (WCAG 2.1.4).
2. CSV download on the trade log and the alert log: every row in the current view (all pages), plain numbers,
   file name carries strategy, slippage, tender filter and contract filter.
3. Phones (600 px and below): compact chips, icon-only theme switch (each button labelled), title 52 px higher.
4. Headline numbers on the Backtest page count to their new value in 400 ms on var(--ease); instant with reduced motion.
Also: Auto theme button has an icon; brand mark keeps its own gold in light mode; theme buttons use the motion tokens.

## Checks
- CSV: 156 trades, net Rs 1,90,340 at 5 bp, gross Rs 4,10,652; broker-allowed 139 trades, Rs 1,53,382; 68 alerts (41 closed halfway).
- Audit: 8 views x 1440/1024/768/390 px x dark/light: no overflow, clipped text, unnamed controls or console errors.

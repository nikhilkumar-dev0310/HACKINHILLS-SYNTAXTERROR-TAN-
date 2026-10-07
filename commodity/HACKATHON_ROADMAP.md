# Hack in Hills '26: what to do, and when

Sources: hackinhills.com, the Unstop listing (description and stage list) and the official PPT template. They disagree in places;
the **Unstop stage list** is what actually opens and closes submissions, so it wins where they conflict. Re-check it on Unstop before each deadline.

| When (IST) | Stage | What to submit | Status |
|---|---|---|---|
| **5 Oct 2026, 6:29 PM** (may also have moved with the PPT extension; check Unstop) | Registration closes on Unstop | Team registered on Unstop, every member added | To confirm |
| **10 Oct 2026** (extended from 5 Oct, per the team on 4 Oct; confirm the exact time on Unstop) | Round 1: PPT | `presentation/round1/Parity_SyntaxTerror_Round1.pptx`, built in the official template. Team and roles on slide 1 are filled in | Deck ready (v4: live site on the title slide). Refresh to the latest data day before uploading |
| 9 – 19 Oct 2026 | Round 2: prototype | Working prototype (the dashboard), demo video, GitHub repo link, documentation (README + report PDF) | Ready: live at https://parity-gold-site.vercel.app (Render mirror https://parity-mcx-gold.onrender.com); demo video `presentation/round2/Parity_demo.mp4` (3 min 16 s, re-shot on the current site); the data updates itself every trading day from a team computer (`tools/RUNNER_SETUP.md`) |
| 20 – 25 Oct 2026 | Round 3: social | LinkedIn post, Instagram reel, prototype video | To do |
| 20 – 21 Nov 2026 | Grand finale, Manali (offline) | Live pitch and demo | Pitch ready (`presentation/parity-pitch.html`, timing in its README) |

Prizes are for the whole hackathon, not per problem statement. Galgotias University appears on Unstop as the listing institution only; the finale venue is Manali.

## Before each deadline
- Round 1: rebuild the deck on the latest data (`python presentation/round1/build_deck.py`), check the file size and format Unstop asks for, then upload. Keep the team MacBook on so the live site stays current while judges look.
- Round 2: record a 2–3 minute screen capture of the dashboard (Overview → Backtest → Signals → Contracts), keep the repo public, link the report PDF.
- Round 3: reuse the pitch's verdict line and the sealed-tests chart; the post should say what Parity found, not only what it is.

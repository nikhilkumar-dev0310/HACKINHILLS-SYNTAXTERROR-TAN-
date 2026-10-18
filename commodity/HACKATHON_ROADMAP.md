# Hack in Hills '26: what to do, and when

Sources: hackinhills.com (timeline checked 18 Oct 2026), the Unstop listing and the official PPT template. Where they disagree,
the **Unstop stage list** wins, because it is what actually opens and closes submissions. Re-check it on Unstop before each deadline.

| When (IST) | Stage | What to submit | Status |
|---|---|---|---|
| 5 Oct 2026 | Registration on Unstop | Team registered, every member added | Done |
| 10 Oct 2026 | Round 1: idea and PPT | `presentation/round1/Parity_SyntaxTerror_Round1.pptx`, in the official template | Done: shortlisted in the Top 500 |
| **13 – 19 Oct 2026** | Round 2A: prototype development | Working prototype, demo video, repository link, supporting documentation | Ready. Live at https://parity-gold-site.vercel.app (Render mirror https://parity-mcx-gold.onrender.com), 3D intro at `/intro`, demo video at `/demo` (`presentation/round2/Parity_demo.mp4`, 1 min 28 s, v4.1), report PDF at `/report.pdf`. The data updates itself every trading day from a team computer (`tools/RUNNER_SETUP.md`). **Make the repo public before submitting** |
| **20 – 25 Oct 2026** | Round 2B: social pitch and outreach | Through the organisers' form: a LinkedIn post presenting the idea, an Instagram Reel on why the team is coming, and a short video of the working prototype with the repo link. Tag Eren, BuilderBase, Nexido and Web3 India in the post and the Reel | Prototype video ready: `presentation/round2/Parity_demo_vertical.mp4` (9:16, 1 min 28 s, repo and live links on screen; `pipeline/vertical.py`). Post and Reel drafted in the team's roadmap doc; Reel still to film |
| 30 Oct 2026 | Top 10 finalists announced | Nothing; the prototype and social pitch are judged together | |
| 20 – 21 Nov 2026 | Round 3: grand finale, Manali (24+ hours, offline) | Build, refine and present to mentors and judges | Pitch ready (`presentation/parity-pitch.html`, timing in its README) |

Judging: innovation, technical execution, impact, scalability, problem–solution fit, usability and final presentation.
Prizes are for the whole hackathon, not per problem statement. Galgotias University appears on Unstop as the listing institution only; the finale venue is Manali.

## Before each deadline
- Round 2A: make the repo public, open the Render mirror once so it is awake, keep the team computer on so the site stays current while judges look, then submit the live link, repo, `/demo` and the report PDF.
- Round 2B: post the vertical video with the repo link (the repo must be public by then), reuse the pitch's verdict line, and say what Parity found, not only what it is. Choose each tag from the app's suggestions so it links.
- Finale: the one direction the brief asks for that Parity can't yet answer is order-book depth (MCX's daily files don't include it).

# Voice-over script (optional)

The v3 demo works without a voice: the captions carry the story. A human voice usually holds attention better
(Guo, Kim & Rubin 2014: more energetic speakers kept viewers longer). A synthetic voice would sound robotic and
cost credibility, so if you want one, a team member should record it.

**How to record**
1. Play `Parity_demo.mp4` on a laptop with the sound off, wearing earphones, and record your voice on your phone
   at the same time (Voice Memos is fine), in a quiet room, phone 20–30 cm from your mouth.
2. Speak each line when its caption appears (times below). Lines can be a little looser than the captions: say it
   the way you'd explain it to a friend, with energy, and slightly faster than feels natural.
3. Leave the guess (0:19–0:23) and the card at 1:08 silent. The pauses are part of the design.
4. Save the recording as `commodity/presentation/round2/pipeline/voice.wav` (any format ffmpeg reads; rename to
   `.wav` after converting, or send it to me), trim the start so your first word lands at 0:00.6, then run
   `pipeline/run3.sh`. The music ducks under your voice automatically, and the mix is re-levelled.

| Time | Caption on screen | Say |
|---|---|---|
| 0:00.6 | ₹1,53,382 profit, on a year our rules never saw. | "One lakh fifty-three thousand rupees of profit. On a year our rules had never seen." |
| 0:04.4 | So why aren't we trading it? | "So why aren't we trading it?" |
| 0:07.0 | *(card: Same gold. Four contracts. Four prices.)* | "MCX sells the same gold four ways." |
| 0:09.4 | Per gram of pure gold, they should cost exactly the same. | "Per gram of pure gold, they should cost exactly the same." |
| 0:13.8 | Parity measures every gap, every trading day, after every cost. | "Parity measures every gap between them, every trading day, after every cost." |
| 0:19.5 | Your guess: is any gap worth trading today? | "So, your guess. Is any gap worth trading today?" *(then silence until 0:23)* |
| 0:23.0 | No. The biggest gap is 40.5 bp. A trade needs 47.6. | "No. The biggest gap is forty basis points. A trade needs forty-seven just to pay its costs." |
| 0:27.0 | Most days, the honest answer is wait. | "Most days, the honest answer is: wait." |
| 0:30.3 | Rewind to January 2026… | "But rewind to January 2026…" |
| 0:32.5 | …the gold crash. Every gap blew through the cost line. | "…the gold crash. Every gap blew straight through the cost line." |
| 0:37.0 | 23 years of official MCX data. 711 contracts. | "How do we know? Twenty-three years of official MCX data. Seven hundred and eleven contracts." |
| 0:40.9 | Every fee. Every tax. And slippage you control. | "Every fee, every tax, and slippage you control." |
| 0:45.1 | Past 12 bp of slippage, no result survives. | "Past twelve basis points of slippage, nothing survives." |
| 0:49.8 | Most teams would report this… | "Most teams would report this…" |
| 0:53.0 | …we report this. Up to 89% of the headline disappears. | "…we report this. Up to eighty-nine percent of the headline disappears." |
| 0:57.5 | Every trade placed inside its contract's calendar. None held into delivery. | "Every trade sits inside its contract's calendar. None is held into delivery." |
| 1:03.4 | Rules frozen in Git. Eight years kept sealed, then opened once. | "The rules were frozen in Git first. Eight years of data stayed sealed, and were opened once." |
| 1:08.2 | *(card: Too good to be true?)* | *(silent; let the riser land)* |
| 1:11.2 | January 2026 alone made ₹2,39,815. | "Here's the catch. January 2026 alone made two lakh thirty-nine thousand." |
| 1:14.1 | The other 111 trades lost ₹86,433. | "The other hundred and eleven trades lost eighty-six thousand." |
| 1:16.9 | Outside the crash, the rule loses money. | "Outside the crash, the rule loses money." |
| 1:20.5 | Best of 72 settings? A 65% chance that's noise. | "And picking the best of seventy-two settings? A sixty-five percent chance that's just noise." |
| 1:24.2 | A small edge. Not proven. We say so. | "A small edge. Not proven. And we say so." |
| 1:27.5 | Checked by 10,344 automated tests, before every update. | "Every number is checked by over ten thousand automated tests…" |
| 1:32.1 | And it updates itself, every trading day. | "…and the site updates itself every trading day." |
| 1:35.7 | That was 6 October. | "That was the sixth of October." |
| 1:37.9 | *(card: Tomorrow's answer isn't in this video.)* | "Tomorrow's answer isn't in this video." |
| 1:41.1 | *(end card: live site and QR)* | "It's live, at parity-gold-site dot vercel dot app." |

The numbers come from the site's data at the time the video was rebuilt. If the video is rebuilt on newer data,
re-check them against the captions.

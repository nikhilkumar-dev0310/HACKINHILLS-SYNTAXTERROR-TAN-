# One-time setup: let the daily data update run by itself

MCX's website blocks cloud servers (GitHub's and Vercel's both get "403 Access Denied"), but it serves
ordinary home and office connections, which is how the Bhavcopy files were downloaded by hand. So the
daily job (`.github/workflows/daily-data.yml`) runs on one team computer, registered with GitHub as a
**self-hosted runner**. After this setup nobody touches the data again: every trading day GitHub starts the
job on that computer, it fetches the new Bhavcopy, checks it, rebuilds the site and pushes; Vercel redeploys.

If the computer is asleep or offline at the scheduled time (03:30 IST, retry 08:00 IST), GitHub keeps the
job queued and runs it as soon as the computer is back online.

## Steps (about 10 minutes, once)

Needs: a Mac, Linux or Windows computer that is usually on and online; repo admin on GitHub.

1. On GitHub open the repository → **Settings → Actions → Runners → New self-hosted runner**.
   Pick the computer's OS. GitHub shows a short list of commands with a one-time token.
2. Run the **Download** commands in a terminal on that computer.
3. Run the **Configure** command, and when it asks:
   - runner group: press Enter
   - runner name: press Enter (or type e.g. `nikhil-mac`)
   - **additional labels: type `parity-mcx`**  (this label is how the workflow finds the computer)
   - work folder: press Enter
4. Install it as a background service so it survives restarts:
   - Mac / Linux: `./svc.sh install && ./svc.sh start`
   - Windows: answer **Y** to "run as service" during configure.
5. Test: repository → **Actions → Daily MCX data update → Run workflow**. In a few minutes a commit
   "Daily data: MCX Bhavcopy through …" appears on `main` (or the run says there is no new trading day yet).

The computer needs Git; the job installs Python 3.11, Node 20, the Python packages and a browser itself.
On a Mac with Google Chrome installed you can set the repository variable or environment `PARITY_CHROME=chrome`
to use the real Chrome instead of the bundled Chromium.

## What the job will never do

- rewrite a contract that has already expired, or any row already published (a changed price stops the update);
- re-run a strategy or touch the sealed test results; those are frozen;
- publish if a check fails: the site keeps the last good data and the run shows the reason.

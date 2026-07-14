# Demo script — recording a 3-minute screen capture

A short, followable script for demonstrating the tool on camera. Total runtime
~3 minutes. Have a terminal and the `output/` folder open in an editor.

---

## Before you start (off camera)

```bash
cd infra-legal-radar
./.venv/bin/pip install -r requirements.txt      # if not already installed
cp .env.example .env                             # then paste your ANTHROPIC_API_KEY
```

Confirm it runs: `./.venv/bin/python main.py --detect-only` should print a
detection summary. If you want the demo to show a *fresh* baseline being built,
temporarily move the snapshots aside: `mv snapshots snapshots.bak`.

---

## Scene 1 — "What is this?" (20 sec, talking to camera)

> "This is a legal event radar for AWS. It watches AWS's public outage feed,
> Service Terms, and SLA pages, and turns anything that changes into a legal
> action memo with deadlines — written for infrastructure counsel."

---

## Scene 2 — Detection, no AI (30 sec)

Run detection only — fast, free, no API key needed:

```bash
./.venv/bin/python main.py --detect-only
```

Point at the output while it prints:

> "First it fetches the sources and diffs them against last week's snapshot.
> Right now it's flagging two open regional outages, with the impacted-service
> counts and durations. Nothing legal yet — this is just detection."

---

## Scene 3 — The SLA data it extracted (20 sec)

Show that it parsed the SLA thresholds into structured data:

```bash
./.venv/bin/python - <<'PY'
import json, glob
sla = json.load(open(sorted(glob.glob("snapshots/sla_ec2/*.json"))[-1]))["meta"]["sla"]
print("EC2 commitment:", sla["commitment_percent"], "%")
print("Claim window:", sla["claim_window_text"][:90], "...")
PY
```

> "It's pulled the actual EC2 credit thresholds and the claim-window language
> out of the SLA page — because the next step needs those as data."

---

## Scene 4 — The full run: detection → memo (40 sec)

```bash
./.venv/bin/python main.py
```

> "Now the full run. Each detected event goes through a legal materiality rubric
> — SLA credit screening, data-residency exposure, downstream customer SLAs —
> and comes back as structured JSON. It writes one dated memo."

Wait for `Memo written: output/...` and the triage line.

---

## Scene 5 — Read the memo (50 sec)

Open the newest file in `output/` in your editor. Scroll slowly and narrate the
URGENT item:

> "Here's the payoff. For the UAE regional outage it screens EC2 and S3 credit
> eligibility, gives the credit tiers, and a computed claim deadline. It flags
> that AWS calling this 'conflict damage' is a likely force majeure defense to
> those credits — and that the outage spans multiple billing cycles, so one
> deadline isn't enough. It raises data-residency exposure from AWS telling
> customers to migrate out of region. And because these regions aren't on my
> watchlist, it tells me to confirm footprint before escalating."

Point at the disclaimer at the top:

> "And it's honest about what it is: issue-spotting support, not legal advice —
> every item needs attorney review against the actual agreements."

---

## Scene 6 — Close (20 sec)

> "It runs weekly in GitHub Actions, commits the snapshots so it always has a
> baseline, and saves the memo as an artifact. One command, live public data, a
> memo a transactions attorney would recognize as useful triage."

---

## Reset after the demo

```bash
rm -rf snapshots && mv snapshots.bak snapshots   # if you moved it aside
```

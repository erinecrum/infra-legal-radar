# Infrastructure Legal Event Radar

A monitoring tool for in-house technology transactions counsel who manage
hyperscaler (AWS) relationships. It watches public AWS operational and legal
data sources, detects events and changes, and translates each one into a
**legal action memo with deadlines**.

It is not a "something changed" alert. It answers the question a practicing
infrastructure attorney actually asks: **what should I do about this, and by
when?**

---

## For the attorney

### What it does

Once a week (or whenever you run it), the tool:

1. **Watches three public AWS sources** — the AWS Health Dashboard (service
   outages and disruptions), the AWS Service Terms page, and the AWS Service
   Level Agreement pages (EC2 and S3 to start).
2. **Detects what changed** since the last run — new or escalating operational
   events, and edits to the terms and SLA text (down to a single changed
   percentage).
3. **Translates each event or change into a legal memo item** using a fixed
   materiality rubric (below), via the Claude API. Each item states what
   happened, why counsel should care, specific action items, and deadlines.
4. **Writes one dated Markdown memo** to the `output/` folder, with items ranked
   **URGENT / REVIEW / NOISE**.

### Why it exists

Two kinds of legally significant things happen on a hyperscaler account without
anyone telling the legal team:

- **Operational events** (a regional outage) can create **SLA credit
  eligibility** with a hard claim deadline, **data-residency exposure** if
  engineering fails workloads over to another region, and **downstream exposure**
  under your own customer SLAs — all before legal hears about it.
- **Quiet edits to the SLA or terms text** — a changed uptime commitment, a
  lowered credit percentage, a new AI/ML clause — are exactly the kind of thing
  that is easy to miss and expensive to miss. Catching a silent SLA threshold
  change is the single highest-value thing this tool does.

### What it deliberately does **not** claim to do

- It **does not conclude legal or credit eligibility.** It screens and triages.
  Every memo carries a standing disclaimer and requires attorney review against
  your actual agreements, DPAs, and invoices.
- It **does not read your contracts or any confidential data.** It uses only
  public AWS pages. You apply its output to what you know you run.
- It **does not give investment or other regulated advice**, and the computed
  claim deadlines are **estimates** — billing-cycle boundaries can differ from
  calendar months, so the memo tells you to confirm against the SLA terms and
  your invoices rather than treating a date as authoritative.
- It **does not guarantee completeness.** AWS's public event feed reflects
  currently-open and recent events, not all history.

### The legal materiality rubric (this is the product)

For each detected item, the translation layer evaluates:

**A. Operational events** — (1) SLA credit eligibility screening against the
stored thresholds, with the applicable SLA, credit tiers, and an estimated claim
deadline; (2) data-residency exposure from cross-region failover; (3) downstream
customer-SLA exposure and evidence preservation; (4) capacity-event workarounds
that create contract/compliance facts.

**B. Terms / SLA changes** — classify each change by what it touches (liability,
data handling, service commitments/SLA thresholds, termination, IP/license,
AI/ML terms, pricing); quote short old/new excerpts; recommend an action. **SLA
threshold or credit changes get top billing.** Formatting/typo changes are NOISE.

**C. Output discipline** — rank URGENT (deadline within 30 days or active
exposure) / REVIEW / NOISE; every URGENT item carries a date; state confidence
and caveats honestly.

### Sample output

A real memo produced from live data is checked in at
[`docs/sample-memo.md`](docs/sample-memo.md) (freshly generated memos land in the
gitignored `output/` folder). It was generated with the affected regions on the
watchlist so the events are analyzed in full. It triages two ongoing regional
outages: screening EC2/S3 credit eligibility with a computed claim deadline,
flagging the AWS "conflict damage" framing as a likely **force majeure** defense
to credit claims, and raising data-residency exposure from AWS's directive to
migrate out of region. That is the intended level of triage.

(With the default `config.yaml` — which lists `us-east-1` and `us-west-2` — those
same Middle East events are *out of region*, so they would instead appear as
one-line entries in the memo's NOISE appendix. See Region filtering below.)

---

## Setup

You need Python 3.9+ and an Anthropic API key. Detection (fetch/snapshot/diff)
runs without a key; the legal memo needs one.

```bash
# 1. From the project folder, create an isolated environment and install deps
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

# 2. Add your API key (never commit it — .env is gitignored)
cp .env.example .env
#   then edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. (Optional) edit config.yaml to list the services/regions/concerns you run.
#   Leave it as-is or delete it to report on everything.

# 4. Run it
./.venv/bin/python main.py
```

The memo is written to `output/legal-radar-memo-<date>.md`. A short console
summary prints the triage counts.

**Useful flags**

- `./.venv/bin/python main.py --detect-only` — run detection and print the
  console summary without calling the Claude API (no key needed, no cost).
- `--config PATH`, `--snapshots DIR`, `--output DIR` — override defaults.

### The optional watchlist (`config.yaml`)

All fields optional, nothing confidential:

```yaml
aws_services_used: [EC2, S3]            # prioritize SLA screening for these
regions_used: [us-east-1, us-west-2]    # FILTER operational events by region
region_filter_mode: appendix            # appendix (default) | strict
heightened_concerns: [data_residency, gpu_capacity]
```

If `aws_services_used` / `heightened_concerns` are present, the translation
layer weights relevance toward what you run. If the whole file is absent, the
tool reports on everything.

#### Region filtering (operational events only)

`regions_used` is a **filter** on operational events from the AWS Health feed —
not just a priority hint. When it is set:

- Events affecting a **listed region** are reported in full.
- **Global or region-less events are always in scope** and are never filtered
  out — a global disruption can affect workloads anywhere.
- Events affecting a region **not** on your list are handled per
  `region_filter_mode`:
  - **`appendix`** (default) — demoted to a single-line entry in the memo's
    NOISE appendix (listed for awareness, not analyzed, and no API call spent
    on them).
  - **`strict`** — excluded from the memo entirely.

Leave `regions_used` empty (or omit it) to disable region filtering and report
operational events from every region.

**Terms and SLA page changes are never region-filtered.** They are not
region-specific — a changed liability cap or credit percentage applies to your
account regardless of where you run — so they always appear in the main memo no
matter what `regions_used` or `region_filter_mode` say.

Worked example: with the config above, a disruption in `me-central-1` (UAE) is
not on your list, so in `appendix` mode it shows up only as a one-liner in the
appendix; in `strict` mode it is dropped. A disruption in `us-east-1`, or a
global event, is analyzed in full. An SLA credit-percentage change is analyzed
in full either way.

### Email delivery (optional)

After each run, the tool can email you the memo — rendered as HTML in the body,
with the Markdown file attached. The subject line summarizes the triage counts,
e.g. `Infra Legal Radar: 1 URGENT, 3 REVIEW`, or `Infra Legal Radar: all quiet`
when nothing material was found. Sending uses Gmail over SMTP (Python standard
library — no extra service), and works identically for local and scheduled runs.

**One-time Gmail setup:**

1. Enable **2-Step Verification** on your Google account (required for app
   passwords): https://myaccount.google.com/security
2. Generate a **16-character app password**:
   https://myaccount.google.com/apppasswords (name it e.g. "legal-radar").
3. Put the credentials in `.env` (gitignored — never committed):
   ```
   SMTP_USERNAME=your_address@gmail.com
   SMTP_APP_PASSWORD=abcd efgh ijkl mnop
   ```
   (Spaces in the app password are fine.)
4. Set the recipient in `config.yaml` (this is a config value, not a secret):
   ```yaml
   email_to: your_address@gmail.com
   smtp_host: smtp.gmail.com   # default; change for another provider
   smtp_port: 587
   ```

That's it — the next `python main.py` will send the memo. To disable sending for
a single run, use `--no-email`; to disable it entirely, leave `email_to` blank.
If the credentials are missing or wrong, the run still completes and saves the
memo — it just reports that the email failed.

**Using a non-Gmail provider:** set `smtp_host`/`smtp_port` to your provider's
STARTTLS SMTP endpoint and put your username/password in the same two `.env`
variables. The send path is standard SMTP.

### Weekly automation (GitHub Actions)

The workflow at [`.github/workflows/weekly-radar.yml`](.github/workflows/weekly-radar.yml)
runs the tool every Monday, commits updated snapshots back to the repo (the diff
baseline), and saves the memo as a downloadable build artifact. Add these
repository secrets (Settings → Secrets and variables → Actions):

- `ANTHROPIC_API_KEY` — required, for the translation layer.
- `SMTP_USERNAME` and `SMTP_APP_PASSWORD` — optional; add them to enable the
  scheduled email (same values as your local `.env`). Without them the run still
  succeeds and just skips sending. The recipient comes from `email_to` in the
  committed `config.yaml`, so it needs no secret.

You can also trigger the workflow manually from the Actions tab.

### Public dashboard (GitHub Pages)

Every run also publishes two static JSON files — [`docs/data/memo.json`](docs/data)
(the latest verdict + triage counts) and [`docs/data/events.json`](docs/data) (a
rolling history of parsed AWS events) — which a single-page site in
[`docs/index.html`](docs/index.html) reads to render:

- the latest memo **verdict and triage counts** at the top, and
- a **filterable table of recent events** — filter by date range, region,
  availability zone, and AWS service, entirely **client-side** (no backend, no
  API keys in the page). It's mobile-readable and includes a short explainer and
  a link back to this repo.

The site is served from the `docs/` folder via GitHub Pages. To enable it:
**Settings → Pages → Build and deployment → Source: "Deploy from a branch" →
Branch: `main`, folder: `/docs` → Save.** The scheduled workflow commits the
refreshed JSON each run, so the dashboard stays current with no extra steps.

> Note: the dashboard is **public** — it exposes the memo verdict and the parsed
> public-AWS event data. That's only public AWS information plus the tool's
> triage, never your contracts or credentials. GitHub Pages for a **private**
> repo requires a paid plan; a public repo can serve Pages on any plan.

Run it locally to preview the site before enabling Pages:

```bash
python main.py                       # regenerates docs/data/*.json
python -m http.server -d docs 8099   # then open http://localhost:8099
```

---

## For the technical reader

### Architecture

```
main.py
  └─ radar/
       config.py        # optional YAML watchlist
       registry.py      # the list of active sources (one line each)
       sources/
         base.py        # Source contract + FetchResult (the only shape the pipeline sees)
         service_terms.py
         health_events.py
         sla_pages.py    # + structured threshold/credit extraction
       snapshot.py      # prior-version store (plain files)
       diff.py          # text diff (localized blocks) + item diff (new/updated)
       sla_util.py      # claim-deadline date math
       findings.py      # bundle a detected item + SLA context for the model
       translate.py     # the rubric → Claude API → structured JSON
       memo.py          # rank + render the Markdown memo (+ shared verdict/triage helpers)
       mailer.py        # HTML email render + SMTP send
       publish.py       # write docs/data/*.json for the dashboard
  └─ docs/              # GitHub Pages site
       index.html       # static single-page dashboard (client-side filters)
       data/            # events.json + memo.json, refreshed each run
```

**Pluggable sources.** Every source implements `fetch() -> FetchResult`. The
snapshot store, diff engine, and translation layer only ever see `FetchResult`,
so adding a v2 source (deprecations, egress pricing, GCP/Azure, HIPAA/FedRAMP
scope pages) is a new module plus one line in `registry.py`.

**Snapshot store = plain files, not SQLite.** Each snapshot is a human-readable
`.txt` (the page text) plus a `.json` (metadata + structured records). A lawyer
— or a court — can open any snapshot and see exactly what AWS's terms said on a
given date, and once GitHub Actions commits them weekly, `git diff` becomes a
free, legally legible change history. We compare only "latest vs previous," so
SQLite's relational querying wouldn't earn its opacity.

**Deadlines computed in Python, judgment in Claude.** `sla_util.py` computes the
estimated claim deadline (end of the second billing cycle after the incident
month) and hands it to the model as a fact. Models are unreliable at date
arithmetic; the rubric supplies the legal judgment, the code supplies the dates.

**Structured output.** The translation layer uses the Claude API's structured
outputs (`output_config.format` with a JSON schema) on `claude-opus-4-8` with
adaptive thinking at high effort, so every memo item is guaranteed parseable.

### Data source choices (logged per the spec)

- **AWS Health — the JSON feed at
  `https://health.aws.amazon.com/public/currentevents`** (mirrored by
  `status.aws.amazon.com/data.json`), **not** the per-service RSS feeds. One
  request covers every service and region; each event carries a stable ARN
  (durable id for new/updated detection), a start timestamp, a numeric status
  code (`0` normal/resolved, `1` informational, `2` degraded, `3` disruption),
  the full timestamped update log, and the complete impacted-services list — the
  raw material the rubric needs. RSS would mean polling dozens of mostly-empty
  feeds for title+prose only. The feed is served as UTF-16; the module decodes
  it defensively. Caveat: `currentevents` is current/recent events, not full
  history — which fits the snapshot-and-diff model.
- **AWS Service Terms** (`aws.amazon.com/service-terms/`) and **SLA pages**
  (`aws.amazon.com/legal/service-level-agreements/`, plus the EC2 and S3 SLA
  pages) — snapshotted and diffed as normalized, line-oriented text. The EC2 and
  S3 pages are additionally parsed into structured thresholds (commitment %,
  credit tiers, and the verbatim claim-window language) that the translation
  layer needs as data.

### Deferred to v2 (structured for, not built)

Deprecation announcements, egress/data-transfer pricing pages, compliance scope
pages (HIPAA-eligible services, FedRAMP), and GCP/Azure sources — each a new
source module behind the same `Source`/`FetchResult` contract.

---

## Disclaimer

This tool provides automated issue-spotting support, not legal advice. It does
not conclude legal or credit eligibility. All output requires review by a
qualified attorney against the user's actual agreements.

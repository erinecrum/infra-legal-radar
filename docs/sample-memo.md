# Infrastructure Legal Event Radar — Memo

## 2 URGENT items: deadline May 10

**Triage:** 2 URGENT · 0 REVIEW · 0 NOISE

_Watching EC2 and S3 in me-central-1 and me-south-1_

---

## 🔴 URGENT — deadline within 30 days or active exposure

### 1. me-south-1 (Bahrain) region-wide, multi-month outage from armed conflict — watchlist region down, data residency and force majeure exposure live

**Materiality:** URGENT · **Confidence:** high · **Type:** operational event
*Source: [AWS Health Dashboard](https://health.aws.amazon.com/health/status)*

**What happened.** AWS Health reports the Middle East (Bahrain) Region (me-south-1) has suffered physical damage from regional conflict and is currently unavailable, with 149 services impacted across four AZs since 2026-03-02 (~1,417 hours and counting). AWS is directing customers to recover resources in other regions from remote backups, has suspended billing operations, and estimates restoration will take several months. This is a direct hit on a watchlisted region running the customer's EC2 and S3 workloads.

**Why counsel cares.** A total, multi-month regional loss triggers overlapping legal facts: (1) forced cross-region failover implicates data residency/transfer commitments (a heightened watchlist concern); (2) the customer's own downstream SLAs to its customers remain owed while AWS is down, raising upstream-provider-failure/force-majeure questions in both directions; and (3) although uptime is clearly below every SLA threshold, AWS's SLAs exclude force majeure/events outside its reasonable control (and billing is suspended), so credit eligibility is genuinely uncertain and must be screened, preserved, and asserted rather than assumed.

**Why this ranking.** Watchlist region (me-south-1) hosting EC2/S3 is entirely unavailable and expected to remain so for months; exposure is active and ongoing, and an SLA credit claim window is estimated to close 2026-05-31 (within 30 days).

**SLA credit screening — ⚠️ POTENTIALLY CREDIT ELIGIBLE.**
- Applicable SLA: Amazon EC2 SLA (Region-Level and Instance-Level, https://aws.amazon.com/compute/sla/) and Amazon S3 SLA (https://aws.amazon.com/s3/sla/) — both services are on the watchlist and in the affected region.
- Credit tiers: EC2 Monthly/Instance-Level Uptime: <99.99%(or <99.5% instance)≥99.0% = 10%; <99.0%≥95.0% = 30%; <95.0% = 100%. S3 Monthly Uptime: <99.9%≥99.0% = 10%; <99.0%≥95.0% = 25%; <95.0% = 100% (reduced tiers for IT/IA/Glacier Instant classes). A region-wide multi-week outage would fall in the lowest/highest-credit (100%) tier on availability alone.
- Estimated claim deadline: **2026-05-31**
- Basis: Per finding: credit request must be received by end of the second billing cycle after the incident occurred. NOTE: the incident is ongoing and spans multiple monthly billing cycles (started 2026-03-02, still open), so 2026-05-31 likely reflects only the earliest-affected cycle — later-cycle impact will carry rolling deadlines. Confirm per-month claim windows against the SLA claim terms; do not treat 2026-05-31 as the sole deadline. Separately, AWS SLAs typically exclude outages caused by events outside AWS's reasonable control (force majeure/conflict) and billing is suspended — eligibility is not established; file protectively and preserve the record.

**Action items.**
- [ ] File protective EC2 and S3 SLA credit requests for the March billing cycle (and each subsequent affected cycle) before their respective claim windows close, including region/instance-level uptime evidence; do not concede the force majeure exclusion — reserve rights and let AWS assert it. — **2026-05-31** _(owner: In-house tech transactions counsel + FinOps)_
- [ ] Confirm with engineering whether cross-region failover/recovery out of me-south-1 occurred and to which region(s), then map against DPA/SCC and any data-residency commitments (heightened watchlist concern) to assess transfer/residency exposure. — **no fixed deadline** _(owner: Counsel + Cloud Engineering + Privacy)_
- [ ] Quantify customer-facing downstream impact and review force majeure / upstream-provider-failure clauses in the company's customer agreements to assess the company's own SLA exposure while AWS is down; issue litigation-hold / evidence-preservation on all incident documentation now. — **no fixed deadline** _(owner: Counsel + Customer Success + Engineering)_
- [ ] Assess whether the multi-month regional loss triggers any termination, service-credit-cap, or business-continuity rights under the AWS agreement and enterprise discount/commitment terms (given billing is suspended). — **no fixed deadline** _(owner: In-house tech transactions counsel)_

**Caveats.** Outage caused by armed conflict likely falls within AWS SLA force majeure/'outside reasonable control' exclusions, which may defeat credit eligibility — this is a screening flag, not a conclusion. The estimated_claim_deadline (2026-05-31) is provided verbatim and reflects only one billing cycle of an ongoing multi-cycle event; verify rolling per-month deadlines directly in the SLA claim terms. Actual credit turns on measured monthly uptime for the customer's specific deployment and configuration, which is not in the finding.

### 2. UAE Region (me-central-1) rendered inoperable by regional conflict — 140 services down 1,434+ hrs, AWS urging migration & suspending billing; on watchlist

**Materiality:** URGENT · **Confidence:** high · **Type:** operational event
*Source: [AWS Health Dashboard](https://health.aws.amazon.com/health/status)*

**What happened.** AWS reports the Middle East (UAE) me-central-1 Region has suffered physical damage from regional conflict and cannot reliably support customer applications. All three AZs (mec1-az1/2/3) and 140 services are impacted since 2026-03-01 (~1,434 hours ongoing as of 2026-04-30). AWS strongly recommends migrating all accessible resources to other Regions and restoring inaccessible resources from remote backups, and has suspended billing operations for a recovery expected to take several months.

**Why counsel cares.** This is simultaneously an SLA-credit event, a data-residency event, and a downstream-commitment/force-majeure event, all in a watchlisted region. AWS's own migration directive will drive engineering to move regulated workloads cross-region, and billing suspension complicates the mechanics of any credit claim. Force majeure / events-outside-AWS's-control exclusions in the EC2/S3 SLAs and the master agreement likely bear directly on both AWS's credit liability and the customer's own downstream obligations.

**Why this ranking.** Active, unresolved region-wide destruction directly on the customer watchlist (me-central-1, EC2, S3, data_residency). SLA credit claim window estimated to close 2026-05-31 (within 30 days), and AWS's migration directive creates live data-residency and downstream-SLA exposure right now.

**SLA credit screening — ⚠️ POTENTIALLY CREDIT ELIGIBLE.**
- Applicable SLA: EC2 Compute SLA (99.99% multi-AZ / 99.5% instance-level) and S3 SLA (99.9%) — both watchlisted services in me-central-1.
- Credit tiers: EC2: <99.99%–99.0% =10%, <99.0%–95.0% =30%, <95.0% =100% (Region-level); instance-level <99.5%–99.0%=10%, <99.0%–95.0%=30%, <95.0%=100%. S3: <99.9%–99.0%=10%, <99.0%–95.0%=25%, <95.0%=100%.
- Estimated claim deadline: **2026-05-31**
- Basis: Per finding: credit request must be received by end of the second billing cycle after the incident (calendar-month billing; deadline end of that month). NOTE: incident is ongoing and spans multiple billing cycles, so per-month deadlines may differ for later-month impact — verify each affected month against the SLA claim terms. Also confirm effect of AWS's billing suspension on the credit mechanic. Screening only; eligibility not concluded — force majeure/conflict may fall under SLA exclusions for events outside AWS's reasonable control.

**Action items.**
- [ ] File protective SLA credit requests for EC2 and S3 usage in me-central-1 for each affected billing month; submit the earliest month before the estimated window closes even if eligibility is contested, and preserve the right to claim later months. — **2026-05-31** _(owner: In-house counsel / FinOps)_
- [ ] Confirm with engineering whether cross-region failover/migration out of me-central-1 has occurred (AWS is actively directing it), which regions received the data, and whether regulated/residency-restricted data moved — then map against DPA, SCCs, and any UAE data-residency commitments. — **2026-05-15** _(owner: Counsel + Engineering/Privacy)_
- [ ] Preserve all incident documentation now (Health dashboard updates, revision history, internal impact metrics, migration logs) for both credit claims and potential force-majeure disputes. — **2026-05-10** _(owner: Engineering + Legal ops)_
- [ ] Review customer-facing downstream SLAs and force majeure / upstream-provider-failure exclusions; quantify customer impact and assess notice obligations to your own customers arising from the outage. — **no fixed deadline** _(owner: Commercial counsel)_
- [ ] Assess business-continuity and termination/service-credit rights under the AWS master agreement given AWS's statement that recovery will take several months and billing is suspended. — **no fixed deadline** _(owner: In-house counsel)_

**Caveats.** Event is region-wide, ongoing, and caused by armed conflict — a classic force majeure trigger. AWS SLAs and most master agreements exclude events outside AWS's reasonable control, so credit eligibility is genuinely uncertain; this is screening, not a conclusion. The estimated_claim_deadline (2026-05-31) is provided in the finding and applies cleanly only to the first affected billing month; a multi-month ongoing incident likely generates rolling per-month deadlines. Effect of AWS's suspension of billing operations on the credit-request mechanic is unresolved and should be confirmed directly with AWS.

---

## Run

Sources checked, no changes: Service Terms, SLA Index, EC2 SLA and S3 SLA. Health events: 2 open, both in your regions.

---

_This memo is automated issue-spotting support, not legal advice. It screens and triages public AWS data; it does not conclude legal or credit eligibility. Every item requires attorney review against your actual AWS agreements, DPAs, and invoices before any action or reliance._

_Run: 2026-07-14 06:21 UTC_
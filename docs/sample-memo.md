# Infrastructure Legal Event Radar — Memo
**Run:** 2026-07-14 04:22 UTC
**Watchlist:** services=['EC2', 'S3']; regions=['us-east-1', 'eu-west-1']; concerns=['data_residency', 'gpu_capacity']

*This memo is automated issue-spotting support, not legal advice. It screens and triages public AWS data; it does not conclude legal or credit eligibility. Every item requires attorney review against your actual AWS agreements, DPAs, and invoices before any action or reliance.*

---

**Triage:** 1 URGENT · 1 REVIEW · 0 NOISE

## 🔴 URGENT — deadline within 30 days or active exposure

### 1. me-central-1 (UAE) Region destroyed by regional conflict — 60+ day ongoing full-region outage, 140 services down across all 3 AZs, billing suspended, AWS urging out-of-region migration

**Materiality:** URGENT · **Confidence:** high · **Type:** operational event
*Source: [AWS Health Dashboard](https://health.aws.amazon.com/health/status)*

**What happened.** AWS reports ME-CENTRAL-1 (UAE) has suffered physical damage from the Middle East conflict and cannot reliably support customer applications. All three AZs (mec1-az1/az2/az3) and 140 services (incl. EC2, S3, RDS, KMS, IAM) are impacted; status 'Service disruption,' unresolved. AWS strongly recommends migrating all accessible resources to other regions and restoring inaccessible resources from remote backups; recovery expected to take several months. Billing operations in the region are suspended during recovery.

**Why counsel cares.** Three concurrent exposures: (1) SLA credits — a full-region, multi-AZ outage would drive monthly uptime for any EC2/S3 workloads in-region well below the lowest thresholds (100% credit tier), but AWS's framing as conflict damage signals a likely force majeure defense to credit claims, and suspended billing complicates credit computation; (2) data residency — AWS's directive to migrate out of region means any UAE-residency commitments (DPAs, SCCs, contractual residency promises) may be breached the moment engineering fails over; (3) downstream SLAs — if the customer runs UAE-facing services on this region, its own uptime commitments to end customers are exposed and upstream force-majeure/provider-failure exclusions must be reviewed now. Note: watchlist lists regions us-east-1/eu-west-1, not me-central-1 — confirm whether the customer actually has UAE footprint before escalating credit work.

**Why this ranking.** Active, ongoing exposure (event unresolved since 2026-03-01, ~1,435 hours) affecting an entire region across all three AZs and 140 services. SLA credit claim deadline of 2026-05-31 falls within 30 days. AWS is directing customers to migrate out of region, which directly implicates data-residency commitments — a flagged heightened concern.

**SLA credit screening — ⚠️ POTENTIALLY CREDIT ELIGIBLE.**
- Applicable SLA: Amazon EC2 SLA (Region-Level and Instance-Level) and Amazon S3 SLA — both apply to any affected in-region workloads; a full-region multi-AZ outage of this duration would breach even the multi-AZ region-level commitments.
- Credit tiers: EC2 Region-Level: <99.99%–99.0% = 10%; <99.0%–95.0% = 30%; <95.0% = 100%. EC2 Instance-Level: <99.5%–99.0% = 10%; <99.0%–95.0% = 30%; <95.0% = 100%. S3 (Standard tier): <99.9%–99.0% = 10%; <99.0%–95.0% = 25%; <95.0% = 100%. Given multi-month full-region unavailability, top (100%) tiers are plausibly implicated.
- Estimated claim deadline: **2026-05-31**
- Basis: Per stored EC2/S3 claim window: credit request must be received by end of the second billing cycle after the incident (calendar month). Deadline provided in finding data used verbatim. CAVEAT: incident is ongoing and spans multiple billing cycles — each affected month may carry its own deadline; do not treat 2026-05-31 as covering the full outage window. Also verify AWS is not tolling/waiving deadlines given suspended billing, and whether AWS will assert force majeure to deny credits.

**Action items.**
- [ ] Confirm with engineering whether the customer has ANY resources, data, or workloads in me-central-1 (watchlist shows only us-east-1/eu-west-1 — verify before further work). — **no fixed deadline** _(owner: Counsel + Cloud Engineering)_
- [ ] If UAE footprint exists, file protective SLA credit claim(s) for EC2 and S3 covering the affected billing month(s) before the deadline; preserve right to claim for subsequent months separately. — **2026-05-31** _(owner: Counsel + FinOps/Cloud Billing)_
- [ ] Confirm with engineering whether cross-region failover/migration out of me-central-1 has occurred or is planned, and to which regions — assess against any UAE data-residency, DPA, SCC, and data-transfer commitments before or immediately after migration. — **no fixed deadline** _(owner: Counsel + Privacy/Engineering)_
- [ ] Assess AWS's likely force majeure position (conflict-related damage) against the SLA credit terms and the master agreement; determine whether credits survive a force majeure event or are excluded. — **no fixed deadline** _(owner: Counsel)_
- [ ] Quantify customer-facing impact on any downstream/end-customer SLAs, review upstream-provider-failure and force majeure exclusions in customer agreements, and preserve all incident documentation (Health dashboard notices, timestamps, migration records) now. — **no fixed deadline** _(owner: Counsel + Product/Support)_
- [ ] Track billing suspension — confirm whether suspended billing affects credit calculation methodology and whether AWS is tolling claim deadlines. — **no fixed deadline** _(owner: Counsel + FinOps)_

**Caveats.** Screening only — eligibility not concluded. Credit eligibility is materially uncertain because (a) AWS characterizes this as conflict-caused physical damage, a strong force majeure posture that may excuse both credits and AWS performance; (b) billing is suspended, complicating credit computation and possibly the claim mechanics; (c) the outage spans multiple billing cycles, so the single provided deadline (2026-05-31) likely does not cover the entire window. Critically, the customer's watchlist regions are us-east-1 and eu-west-1, not me-central-1 — if the customer has no UAE footprint, SLA-credit exposure may be nil and the finding collapses to data-residency/force-majeure monitoring. Verify footprint first.

## 🟡 REVIEW — material, no immediate deadline

### 2. Bahrain (me-south-1) region fully unavailable ~59 days due to Middle East conflict; AWS invoking force majeure, billing suspended, 149 services down

**Materiality:** REVIEW · **Confidence:** high · **Type:** operational event
*Source: [AWS Health Dashboard](https://health.aws.amazon.com/health/status)*

**What happened.** Since 2026-03-02 the entire AWS Middle East (Bahrain) Region has been unavailable — 149 services across all listed AZs (mec1-az1/2/3, mes1-az2). AWS states the region 'suffered damage due to the conflict in the Middle East,' directs customers to recover from remote backups in other regions, has suspended billing operations, and expects restoration to take several months. Event is unresolved (status 3, 13 updates, ~1417 hours as of 2026-04-30).

**Why counsel cares.** Three exposures even though the region is off-watchlist: (1) AWS is affirmatively invoking a conflict/force-majeure narrative, which cascades into your own downstream customer SLAs and into any residency/DR commitments; (2) AWS's instruction to 'recover resources in other Regions' means any engineering failover creates data-residency/transfer facts (heightened concern) without legal sign-off; (3) suspended billing complicates any credit math and invoicing reconciliation. If any customer workload, backup, or residency commitment touches Bahrain, this becomes URGENT.

**Why this ranking.** Extraordinary region-wide outage with a live SLA claim deadline (2026-05-31), which would normally read URGENT. Downgraded to REVIEW because me-south-1 is NOT on the customer watchlist (regions_used = us-east-1, eu-west-1) and AWS is expressly attributing the outage to armed conflict — a classic SLA force majeure/excluded-event that likely bars credits and neutralizes direct exposure. Confirm no customer resources or residency ties to Bahrain before deprioritizing entirely.

**SLA credit screening — ⚠️ POTENTIALLY CREDIT ELIGIBLE.**
- Applicable SLA: EC2 Compute SLA (99.99% region-level / 99.9% instance-level) and S3 SLA (99.9%) — but only if customer ran workloads in me-south-1, which the watchlist does not indicate.
- Credit tiers: EC2: <99.99%–≥99.0% = 10%; <99.0%–≥95.0% = 30%; <95.0% = 100%. S3 Standard: <99.9%–≥99.0% = 10%; <99.0%–≥95.0% = 25%; <95.0% = 100%. A ~59-day full-region outage would drive monthly uptime toward the 100%-credit tier for any in-region workload — subject to the force majeure/excluded-event carve-out AWS is invoking.
- Estimated claim deadline: **2026-05-31**
- Basis: Per finding data: credit request must be received by end of the second billing cycle after the incident (calendar-month based). Note the incident spans multiple billing cycles (began March 2026, ongoing); each affected month may carry its own deadline — verify per-month claim windows in the SLA terms rather than relying on a single date. Also note AWS's suspension of billing operations and the conflict-based force majeure position may bar credits entirely.

**Action items.**
- [ ] Confirm with engineering/CloudOps whether the customer has ANY resources, backups, replication targets, or residency commitments in me-south-1 (Bahrain). If none, close as informational; if any, escalate to URGENT. — **2026-05-14** _(owner: In-house counsel + Cloud engineering lead)_
- [ ] If in-region exposure is confirmed, file protective SLA credit request(s) before the claim window(s) close and do not rely on a single date — the outage spans multiple billing cycles; the earliest provided deadline is 2026-05-31. — **2026-05-31** _(owner: FinOps / Procurement with counsel)_
- [ ] Confirm whether any cross-region failover FROM Bahrain occurred (personal/regulated data moved to other regions) and assess against DPA/SCC/data-residency commitments. — **no fixed deadline** _(owner: Privacy counsel + engineering)_
- [ ] Review force majeure / upstream-provider-failure exclusions in the customer's own downstream agreements given AWS's express conflict/force-majeure characterization; preserve incident documentation and AWS Health messaging now. — **no fixed deadline** _(owner: Commercial counsel)_

**Caveats.** Region me-south-1 is not on the customer watchlist (us-east-1, eu-west-1), so likely low direct exposure — but this is unconfirmed and must be verified with engineering. AWS's attribution to armed conflict strongly implicates SLA force majeure/excluded-event exclusions, which would defeat credit eligibility; this is a screening flag, not a legal conclusion. The single provided deadline (2026-05-31) does not account for the multi-month span of an ongoing outage — treat per-billing-cycle. This tool does not conclude credit eligibility.

---

## Run notes

- AWS Service Terms: no change.
- AWS Health Dashboard: 0 new, 0 updated event(s); 2 currently open.
- AWS SLA Index: no change.
- AWS EC2 SLA: no change.
- AWS S3 SLA: no change.

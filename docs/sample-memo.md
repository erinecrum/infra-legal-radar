# Infrastructure Legal Event Radar — Memo
**Run:** 2026-07-14 05:21 UTC
**Watchlist:** services=['EC2', 'S3']; regions=['me-central-1', 'me-south-1'] (filter: appendix); concerns=['data_residency', 'gpu_capacity']

*This memo is automated issue-spotting support, not legal advice. It screens and triages public AWS data; it does not conclude legal or credit eligibility. Every item requires attorney review against your actual AWS agreements, DPAs, and invoices before any action or reliance.*

---

**Triage:** 2 URGENT · 0 REVIEW · 0 NOISE

## 🔴 URGENT — deadline within 30 days or active exposure

### 1. Bahrain (me-south-1) region-wide, multi-month outage from armed conflict — watchlisted region/services hit; SLA credit likely barred by force majeure; data-residency exposure on failover

**Materiality:** URGENT · **Confidence:** high · **Type:** operational event
*Source: [AWS Health Dashboard](https://health.aws.amazon.com/health/status)*

**What happened.** AWS reports the Middle East (Bahrain) Region (me-south-1) has suffered physical damage due to regional conflict and is currently unavailable across 149 services and all listed AZs (mec1-az1/2/3, mes1-az2). AWS is directing customers to recover resources in other regions from remote backups, has suspended billing for the region, and estimates restoration will take several months. Event is unresolved as of the last update 2026-04-30.

**Why counsel cares.** This is a total regional loss in a watchlisted region hosting the customer's EC2 and S3 workloads, triggering three distinct legal fronts: (1) SLA credit eligibility, likely defeated by force majeure/war exclusions but worth screening given the provided deadline; (2) data-residency/transfer exposure if engineering fails over out of me-south-1/me-central-1 to non-approved regions; and (3) downstream customer-facing SLA exposure during a multi-month outage. AWS's characterization ('damage due to the conflict') is a classic force majeure recital that likely both excuses AWS's SLA obligations and may implicate force majeure clauses in the customer's own downstream agreements. Billing suspension does not equal a credit and should not be relied upon as a remedy.

**Why this ranking.** Entire watchlisted region (me-south-1) is unavailable, ongoing since 2026-03-02 (1,417+ hrs) with recovery expected to take months. Both watchlisted services (EC2, S3) are impacted. Active, unresolved exposure plus a provided credit-claim deadline of 2026-05-31 make this URGENT.

**SLA credit screening — ⚠️ POTENTIALLY CREDIT ELIGIBLE.**
- Applicable SLA: Amazon EC2 SLA (Region-Level and Instance-Level) and Amazon S3 SLA — both services are watchlisted and impacted; a full region outage drives Monthly Uptime Percentage well below all thresholds.
- Credit tiers: EC2: <99.99%–99.0%=10%, <99.0%–95.0%=30%, <95.0%=100% (Region-Level, multi-AZ); Instance-Level mirrors at 99.5/99.0/95 breakpoints. S3: <99.9%–99.0%=10%, <99.0%–95.0%=25%, <95.0%=100% (standard tier). A sustained full-region outage would fall in the <95.0% / 100% credit band on raw uptime.
- Estimated claim deadline: **2026-05-31**
- Basis: Per AWS SLA claim-window rule: credit request must be received by the end of the second billing cycle after which the incident occurred (calendar-month billing cycle; deadline = end of that month). Deadline value used verbatim from finding. CAVEAT: incident is ongoing and spans multiple billing cycles; the operative deadline may re-anchor to the cycle(s) in which impact is claimed — confirm against the SLA claim terms before relying on 2026-05-31. Note also that both SLAs almost certainly contain a force majeure/exclusion carve-out that AWS will invoke given the stated cause; file protectively regardless.

**Action items.**
- [ ] File protective SLA credit requests for EC2 (Region-Level and Instance-Level) and S3 for me-south-1 impact, documenting Monthly Uptime Percentage per affected billing cycle, before the AWS deadline — do not rely on the billing suspension as a substitute remedy. — **2026-05-31** _(owner: In-house counsel with FinOps/cloud billing)_
- [ ] Confirm with engineering whether any cross-region failover out of me-south-1 (and me-central-1) occurred during the outage window, and to which regions, to assess data-residency/transfer commitments under DPAs, SCCs, and customer residency promises (data_residency is a heightened watchlist concern). — **no fixed deadline** _(owner: Counsel + Cloud/Infra engineering + Privacy)_
- [ ] Pull and review force majeure / upstream-provider-failure exclusions in the customer's own downstream agreements and quantify customer-facing impact during the outage; preserve all incident documentation (Health dashboard messages, revisions, timestamps) now. — **no fixed deadline** _(owner: Counsel + Customer/Commercial team)_
- [ ] Assess whether AWS's 'damage due to the conflict' characterization triggers or defeats force majeure/SLA exclusions in the AWS agreement, and evaluate business-continuity/termination rights if restoration truly takes several months. — **no fixed deadline** _(owner: In-house counsel)_

**Caveats.** I screen, I do not conclude eligibility. Credit eligibility is materially uncertain: AWS's stated cause (armed conflict/physical damage) will almost certainly be asserted as force majeure/an SLA exclusion, which typically bars credits and may also excuse AWS. The provided 2026-05-31 deadline may not correctly anchor for a multi-cycle ongoing incident — verify against the actual claim terms. Actual uptime percentages and which specific EC2/S3 tiers/configs (multi-AZ vs single-instance) apply must be confirmed from customer telemetry. Whether failover occurred is unknown pending engineering confirmation. Data residency risk depends on approved-region scope in the applicable DPA/contract, not reviewed here.

### 2. me-central-1 (UAE) region-wide, multi-service disruption ongoing since 2026-03-01 — AWS attributes to armed conflict, recommends full migration out of region, suspends billing; ~60 days and counting across all 3 AZs and 140 services

**Materiality:** URGENT · **Confidence:** high · **Type:** operational event
*Source: [AWS Health Dashboard](https://health.aws.amazon.com/health/status)*

**What happened.** AWS Health reports a 'Service disruption' (status 3) for Multiple Services in me-central-1 (UAE), started 2026-03-01T12:51Z, still unresolved as of last update 2026-04-30T07:25Z (~1,434.6 hours, 23 updates). All three AZs (mec1-az1/2/3) and 140 services are impacted, including EC2 and S3. AWS's latest message states the region 'has suffered damage as a result of the conflict in the Middle East and is currently unable to reliably support customer applications,' strongly recommends migrating all accessible resources to other regions and restoring inaccessible resources from remote backups, and states billing operations are suspended with restoration 'expected to take several months.'

**Why counsel cares.** Three simultaneous exposures. (1) SLA credits: EC2 (99.99%) and S3 (99.9%) uptime are almost certainly breached, but AWS's framing (conflict-driven damage) squarely raises the SLA/force-majeure exclusion, and AWS has suspended billing — which complicates both credit computation and the claim mechanism. (2) Data residency: AWS is affirmatively directing cross-region migration and restore-from-backup; if engineering has moved UAE-resident data/workloads to other regions, this may breach data-residency promises, DPAs, or transfer commitments (SCCs) — a watchlisted concern. (3) Downstream: if customer-facing services depending on me-central-1 kept operating under their own SLAs, the customer's own force-majeure/upstream-provider exclusions need review and incident evidence must be preserved now.

**Why this ranking.** Active, unresolved region-wide outage (1,434+ hours) hitting all three AZs and 140 services in a watchlisted region (me-central-1) and watchlisted services (EC2, S3). AWS is explicitly directing customers to migrate/restore out-of-region, directly implicating a watchlisted data-residency concern. A screening claim deadline (2026-05-31) falls within 30 days. Multiple live exposures require immediate action.

**SLA credit screening — ⚠️ POTENTIALLY CREDIT ELIGIBLE.**
- Applicable SLA: Amazon Compute (EC2) SLA — 99.99% Monthly Uptime commitment (region-level, multi-AZ) and 99.5% instance-level; Amazon S3 SLA — 99.9% Monthly Uptime commitment. Both watchlisted services are in the impacted list and a region-wide, all-AZ outage of this duration would drive monthly uptime well below the lowest thresholds.
- Credit tiers: EC2 region-level: <99.99%–99.0% = 10%; <99.0%–95.0% = 30%; <95.0% = 100%. EC2 instance-level: <99.5%–99.0% = 10%; <99.0%–95.0% = 30%; <95.0% = 100%. S3 (Standard/Glacier Flexible/Deep Archive etc.): <99.9%–99.0% = 10%; <99.0%–95.0% = 25%; <95.0% = 100%. S3 (Intelligent-Tiering/IA/Glacier Instant): <99.0%–98.0% = 10%; <98.0%–95.0% = 25%; <95.0% = 100%. Given a multi-week region-wide outage, the 100% tier is plausible for affected months.
- Estimated claim deadline: **2026-05-31**
- Basis: Per provided finding data: credit request must be received by end of the second billing cycle after the incident (calendar-month based). NOTE: incident spans multiple billing months (started 2026-03-01, ongoing) so separate/rolling deadlines likely apply to each affected month; 2026-05-31 is the earliest screening deadline (for the March incident month). Two material caveats: (a) AWS has suspended billing for the region, which may alter credit computation and the claim submission mechanism; (b) AWS's conflict/force-majeure framing may be invoked to deny credits. Confirm exact per-month deadlines and submission process against the live SLA claim terms; do not treat eligibility as established.

**Action items.**
- [ ] File protective SLA credit claim(s) for EC2 and S3 for the March 2026 impact month before the earliest screening deadline, expressly reserving rights and preserving later-month claims; do not let the deadline lapse pending the billing-suspension/force-majeure questions. — **2026-05-31** _(owner: In-house counsel (with FinOps/billing))_
- [ ] Confirm with engineering whether any me-central-1-resident workloads or data were failed over, migrated, or restored to other AWS regions during the outage window (2026-03-01 onward), and to which regions, to assess data-residency / DPA / SCC / transfer-commitment exposure. — **2026-05-15** _(owner: Counsel + Cloud/Infra engineering + Privacy)_
- [ ] Preserve all incident documentation now (Health dashboard captures, internal incident tickets, customer-impact metrics, migration logs) for both the SLA claim and any downstream/force-majeure disputes. — **2026-05-15** _(owner: Counsel + Incident/SRE team)_
- [ ] Review AWS SLA force-majeure/exclusion language and the master agreement to assess whether AWS's 'conflict/damage' characterization defeats credits, and evaluate remedies for the billing suspension and multi-month unavailability (including any termination/relief provisions). — **no fixed deadline** _(owner: In-house counsel)_
- [ ] Quantify customer-facing impact of any downstream services that relied on me-central-1 and review the customer agreements' force-majeure / upstream-provider-failure exclusions to gauge the customer's own SLA exposure. — **no fixed deadline** _(owner: Counsel + Product/Business owners)_

**Caveats.** Confidence is high on the operational facts (region-wide, all-AZ, multi-service, ongoing, watchlisted region and services). This is a screening only — I do not conclude credit eligibility. Two factors materially cloud recovery: (1) AWS attributes the outage to armed conflict, squarely raising SLA force-majeure/exclusion defenses; and (2) AWS has suspended billing for the region, which may change how credits are calculated and claimed. The incident spans multiple billing months, so multiple/rolling claim deadlines likely apply; 2026-05-31 is used verbatim as the earliest provided deadline for the March incident month. Verify exact per-month deadlines and submission mechanics against the live SLA terms before relying on them.

---

## Run notes

- AWS Service Terms: no change.
- AWS Health Dashboard: 0 new, 0 updated event(s); 2 currently open.
- AWS SLA Index: no change.
- AWS EC2 SLA: no change.
- AWS S3 SLA: no change.

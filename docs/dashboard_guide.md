# Metro Vancouver Procurement Analytics
## Dashboard Reading Guide

**Version:** 1.1
**Last updated:** 2026-06-22
**Owner:** Kimia Nazokkar

This guide explains how to read the four Tableau dashboards in this repository. It is
written for GitHub reviewers, hiring managers, and analytics leads who are evaluating
the project from the dashboard screenshots rather than from a live Tableau Public
workbook.

Each section describes the analytical purpose of the dashboard, the main KPIs and
visuals it contains, how to interpret what is shown, and the interpretive limits that
apply.

All metrics reference the final governed dataset:
`data/clean/step5h_deduped_procurement_awards.csv` (2,133 rows, 22 columns).

---

## Context Applicable to All Dashboards

**Source.** All dashboards draw from Metro Vancouver's publicly disclosed Awarded Bids
Register, a procurement transparency publication available at
[metrovancouver.org/bidding-opportunities/awarded-bids](https://metrovancouver.org/bidding-opportunities/awarded-bids).

**Scope.** The dataset covers 2023 through March 2026. The 2026 data represents
January through March only — a partial reporting year. Year-level 2026 figures appear
in several views and are not comparable to 2023–2025 full-year totals.

**Descriptive analysis only.** These dashboards document observed patterns in the
disclosed register. They do not constitute an audit of Metro Vancouver's procurement
practices and do not assess the appropriateness, efficiency, or outcomes of any
procurement decision.

**Disclosed amounts are not final expenditures.** Figures represent awarded amounts at
the time of disclosure. Final contract expenditures may differ due to amendments or
scope changes not captured in the register.

**Awarded competitions, not contracts.** The 679 competition count represents distinct
competition numbers with at least one awarded vendor. A single competition may include
multiple awarded vendors; it should not be interpreted as a count of discrete contracts.

**Normalized supplier entities.** Vendor names were normalized to consolidate legal
name variants, trade names, and spelling differences. The resulting display names represent
normalized supplier entities, not verified unique legal entities.

---

## Dashboard 1 — Executive Summary

### Analytical Purpose

Dashboard 1 provides a portfolio-level view of Metro Vancouver's disclosed procurement
activity. It is designed for an executive or generalist audience that needs a
high-level orientation to the dataset before engaging with the more detailed views in
Dashboards 2 and 3.

### Main KPIs and Visuals

**Header KPI strip.** Five summary KPIs appear at the top of the dashboard:

- **$4.7B** — Total KPI-eligible disclosed awarded spend across the full dataset
  (2023–March 2026). Includes all awarded competitions, including the two
  generational infrastructure projects.
- **~$2.5B** — Normalized spend baseline: KPI-eligible spend after excluding the two
  mega-projects (North Shore Wastewater Treatment Plant, Competition 21-457, ~$1.95B;
  Stanley Park Water Supply Tunnel, Competition 23-346, ~$318M). This is the primary
  baseline for operational spend comparisons.
- **679** — Distinct awarded competitions with at least one awarded vendor.
- **624** — Normalized supplier entities receiving at least one disclosed award.
- **21.9%** — Single-Bidder Rate: the share of competitive procurements (excluding
  direct-award instruments) with exactly one recorded vendor response across the study
  period.

**Normalized spend by source reporting year.** A bar chart shows normalized
KPI-eligible disclosed awarded spend by source reporting year. Normalized spend
excludes the two generational infrastructure projects: North Shore Wastewater
Treatment Plant (NSWWTP), Competition 21-457, and Stanley Park Water Supply Tunnel,
Competition 23-346. The values shown are:

- 2023: ~$0.5B
- 2024: ~$0.8B
- 2025: ~$1.1B
- 2026: ~$0.1B (January–March only)

The full KPI-eligible disclosed awarded spend figures — including both mega-projects —
are $4.7B in total and are already captured in the header KPI strip. The trend chart
is intentionally scoped to the normalized baseline so the annual pattern reflects
operational procurement activity rather than capital program timing.

**Direct award rate by year.** A chart tracks the share of awarded competitions
classified as direct-award instruments (DA, DA/NOIC, SS/NOIC, NOIC) per source year:
2023: 15.7% · 2024: 25.5% · 2025: 30.6% · 2026: 51.9%.

**Awarded spend by competition type.** A horizontal bar chart shows KPI-eligible
disclosed awarded spend by standardized competition type. This view shows which
procurement instruments account for the largest share of disclosed awarded spend in
the portfolio. It should be read as a spend-distribution view by instrument type, not
as a measure of process quality or procurement outcome.

**Top awarded suppliers.** A ranked bar chart shows the leading normalized supplier
entities by normalized KPI-eligible disclosed awarded spend. This view uses the
normalized spend baseline, excluding the two mega-projects, so that supplier
concentration is not dominated by the two generational infrastructure awards. Supplier
names reflect the project's vendor-name normalization process and should be interpreted
as normalized supplier entities, not verified unique legal entities.

### How to Interpret

The $4.7B total is the full KPI-eligible disclosed awarded spend figure. The
~$2.5B normalized baseline is the more analytically useful reference for comparing
vendor concentration and operational patterns, because the two excluded projects are
capital programs of a scale that would distort all other comparisons if included.

The normalized spend chart shows the year-level pattern after removing the two
mega-projects. On this normalized basis, the 2023–2025 bars show consistent
year-on-year growth in normalized disclosed awarded spend, from ~$0.5B in 2023 to
~$1.1B in 2025. The 2026 bar reflects January–March only and should not be
extrapolated to a full-year figure.

The direct award rate chart shows the share of awarded competitions classified as
direct-award instruments by source reporting year. Direct awards are legitimate
procurement instruments and may reflect sole-source requirements, emergency
procurement, standing agreements, contract renewals, or other operational
considerations that this analysis does not observe. The 2026 value is shown for
transparency but reflects January–March only and should not be interpreted as a
full-year trend signal.

### What This Dashboard Does Not Claim

- It does not characterize year-on-year spend or award-rate changes as reflecting
  operational decisions.
- It does not interpret the direct award rate pattern as evidence of procurement
  policy change.
- It does not present the $4.7B or $2.5B figures as total Metro Vancouver
  organizational expenditure.
- It does not compare 2026 figures to full-year 2023–2025 figures.

---

## Dashboard 2 — Vendor Concentration & Supplier Dependence

### Analytical Purpose

Dashboard 2 examines how the normalized spend baseline is distributed across
normalized supplier entities. It is designed to surface supplier concentration
patterns — specifically, how much spend is associated with the largest supplier
entities compared with the broader awarded supplier base — and to show observed
awarded supplier recurrence across source reporting years.

### Main KPIs and Visuals

**Supplier concentration curve.** A cumulative concentration curve plots the
percentage of the normalized spend baseline accounted for by each successive
normalized supplier entity, ranked from largest to smallest. The curve shows how
quickly cumulative spend approaches 100% as more supplier entities are added.

**Top supplier ranking.** A ranked bar chart or table shows the top normalized
supplier entities by normalized spend baseline. Key published figures:

- The largest normalized supplier entity is Halton Recycling Ltd. dba Emterra
  Environmental at approximately $281M, representing ~11.4% of the normalized
  spend baseline.
- The top 11 normalized supplier entities collectively account for approximately
  51.0% of the ~$2.5B normalized spend baseline.

**Supplier recurrence.** Recurrence context summarizes how often normalized awarded
supplier entities appear across source reporting years. Of 624 normalized awarded
supplier entities, 521 (83.5%) appear in only one source reporting year.

### How to Interpret

The concentration curve shows that spend in this disclosed register is concentrated
among a relatively small number of normalized supplier entities. Eleven normalized
supplier entities account for approximately half of the normalized spend baseline.
This is a distributional observation about the shape of the disclosed register — it
does not imply that concentration is inappropriate or that the supplier base is too
narrow for the type of work being procured.

All concentration figures are calculated against the normalized spend baseline
(~$2.5B), which excludes two generational infrastructure projects: North Shore
Wastewater Treatment Plant (NSWWTP), Competition 21-457, and Stanley Park Water
Supply Tunnel, Competition 23-346. Supplier shares expressed as percentages refer to
this baseline, not to the $4.7B total disclosed awarded spend.

The supplier recurrence finding should be interpreted with care. Of 624 normalized
awarded supplier entities, 521 (83.5%) appear in only one source reporting year.
`source_year` reflects the publication year of the annual register, not the fiscal or calendar year of the award.
A supplier appearing in only one source reporting
year may have ongoing work that is not yet reflected in subsequent annual
publications, or may have work recorded in a different reporting period.

### What This Dashboard Does Not Claim

- It does not assess whether concentration levels are appropriate for the type or
  scale of Metro Vancouver's disclosed procurement award portfolio.
- It does not describe the 624 supplier count as a count of unique legal entities or
  unique companies — normalization decisions involve judgment, and 14 REVIEW-confidence
  vendor groups remain flagged for human verification.
- It does not interpret single-year supplier appearance as proof of one-time
  relationships or lack of ongoing work.
- All share figures refer to the normalized spend baseline, not total disclosed
  awarded spend.

---

## Dashboard 3 — Competition Structure & Bid Depth

### Analytical Purpose

Dashboard 3 examines how Metro Vancouver's disclosed procurement activity is structured
across competition types, and how deeply the supplier market engaged with competitive
procurements. It distinguishes between competitive instruments (RFP, ITT, RFQ, and
related types) and direct-award instruments, and then focuses the depth analysis
exclusively on competitive competitions.

### Main KPIs and Visuals

**Competition type mix.** A breakdown of 679 awarded competitions by
`competition_type_standardized`. For readability, types are grouped into competitive
instruments and direct-award instruments. The most common types are RFP (298
competitions) and ITT (102 competitions) among competitive instruments, and SS/NOIC
(101) and DA (82) among direct-award instruments.

**Single-bidder rate.** The overall rate across 494 competitive competitions is 21.9%
(108 competitions received exactly one recorded vendor response). By source year:
2023: 20.0% (29/145) · 2024: 28.0% (40/143) · 2025: 19.4% (36/186) · 2026: 11.5% (3/26).

**Bidder depth distribution.** A bar chart shows the number of competitive competitions
by participant count bucket:

- 1 participant: 108 competitions
- 2 participants: 105 competitions
- 3 participants: 102 competitions
- 4–5 participants: 100 competitions
- 6–10 participants: 55 competitions
- 11+ participants: 24 competitions

**Direct award rate by year.** Reproduced from Dashboard 1 in this context to support
the competition structure narrative: 2023: 15.7% · 2024: 25.5% · 2025: 30.6% ·
2026: 51.9%.

### How to Interpret

The single-bidder rate measures the share of competitive procurements — those using
formal competitive instruments — where only one vendor response was recorded in the
register. Direct-award competitions are excluded from this metric; applying the rate
to the full competition portfolio would conflate two structurally different procurement
approaches.

The 2024 single-bidder rate (28.0%) is the study period peak, meaning more than one
in four competitive procurements in that year recorded a single vendor response. The
2025 rate (19.4%) reflects a lower rate across a larger base of competitive
competitions. The 2026 rate (11.5%) reflects only 26 competitive competitions across
a partial year and is not a meaningful trend signal.

The bidder depth distribution shows that shallow participation (1–3 responses)
accounts for the majority of competitive competitions. Competitions attracting six or
more recorded participants represent a smaller share of the competitive portfolio.
"Participants" includes all vendors listed in the register for a competition — both
awarded and not awarded. Participant counts may not capture every vendor that
expressed interest or engaged informally before formal response.

Direct awards are legitimate procurement instruments. Their share is shown by source
reporting year for transparency, but the 2026 value reflects January–March only and
should not be interpreted as a full-year trend signal.

### What This Dashboard Does Not Claim

- It does not interpret the single-bidder rate as a measure of procurement quality or
  competitive performance.
- It does not characterize direct awards as problematic or as a deviation from
  expected procurement practice.
- It does not present 2026 competition structure rates as full-year trend signals.
- Participant counts reflect the register, not total market engagement — vendors that
  engaged with a competition outside the formal response process are not visible in
  this data.
- Year-level competition counts sum to 686 (not 679) due to multi-year appearances of
  some competitions across source documents.

---

## Dashboard 4 — Methodology & Data Governance

### Analytical Purpose

Dashboard 4 is the governance dashboard. It documents the analytical decisions,
dataset definitions, known limitations, and data quality controls that support the
other three dashboards. It is designed for reviewers who want to understand the
rigor behind the numbers before relying on them — whether for professional evaluation,
portfolio assessment, or further analysis.

### Main Content Areas

**Analytical scope statement.** A plain-language description of what this analysis
does and does not claim. Key framing: this is a descriptive analysis of a publicly
disclosed register; it is not an audit; it does not assess procurement decisions or
vendor performance.

**KPI definitions.** Definitions for the primary metrics used across the dashboard
suite, including:

- *Disclosed Awarded Spend* — sum of KPI-eligible `awarded_amount_numeric` values;
  not final contract expenditure
- *Awarded Competitions* — distinct competition numbers with at least one awarded
  vendor row; not a contract count
- *Awarded Suppliers* — distinct `vendor_name_display` values with at least one
  awarded row; normalized supplier entities, not verified unique companies
- *Normalized Spend Baseline* — KPI-eligible spend excluding competitions 21-457
  (NSWWTP, ~$1.95B) and 23-346 (Stanley Park Water Supply Tunnel, ~$318M)
- *Single-Bidder Rate* — share of competitive competitions (excluding direct-award
  types) with exactly one recorded participant row

**Pipeline summary.** A description of the nine-stage ETL pipeline from PDF extraction
through governed duplicate suppression. Governance signals documented here include
blocking assertion architecture, vendor normalization confidence levels, and the
suppression audit log.

**Known data quality items (KDQI).**

- *KDQI-001 — Source-Level Duplicate Award Records* `Closed` — Five source-level
  duplicate records suppressed through Stage 5H, removing $1.84M in overstated
  KPI-eligible spend. Full audit log retained at
  `data/clean/step5h_suppression_audit_log.csv`.
- *KDQI-002 — Competition Number Format Variation: 22-167 / 22-0167* `Open` —
  Two competition numbers share description prefix and overlapping vendor pool;
  definitive relationship unconfirmed from source documents. Treated as distinct
  events. No published KPI is affected. This is an open investigation item, not a
  confirmed data quality defect.

**Limitations summary.** Key limitations surfaced on the dashboard:

- The disclosed register is not a complete expenditure record
- Disclosed amounts are not final contract values
- `source_year` is publication year, not fiscal year of award
- 2026 covers January–March only
- Vendor normalization involves judgment; REVIEW-confidence groups are tentative
- Participant counts reflect the register, not total market engagement

### How to Interpret

Dashboard 4 is the evidentiary layer for the rest of the suite. A reviewer who wants
to verify any KPI definition, understand a data quality decision, or assess the
robustness of the pipeline controls can use this dashboard as the entry point and then
follow references into the repository documentation (`docs/methodology.md`,
`docs/data_dictionary.md`, `docs/kdqi_register.md`).

The KDQI section is not a list of errors. KDQI-001 is closed and resolved. KDQI-002
is an open investigation item that has been surfaced and quantified but does not affect
any published KPI. Its presence on the dashboard reflects a deliberate governance
decision to disclose uncertainty rather than suppress it.

### What This Dashboard Does Not Claim

- It does not represent the KDQI register as an audit finding against Metro Vancouver.
- It does not claim the dataset is error-free — it claims that known issues are
  documented, quantified, and either resolved or disclosed.
- It does not assert that the pipeline covers all possible data quality risks, only
  those identified during development and pre-publication source verification.

---

## Quick Reference: Framing Boundaries

The table below summarizes the consistent interpretive boundaries applied across all
four dashboards.

| Concept | Approved framing | Avoid |
|---|---|---|
| Spend total | Disclosed awarded spend | Total procurement spend, total expenditure |
| Competitions | Awarded competitions | Contracts, procurement events |
| Suppliers | Normalized supplier entities | Unique companies, unique vendors |
| Direct awards | Legitimate procurement instruments that may reflect sole-source requirements, emergency procurement, standing agreements, renewals, or other operational context | Problematic by default; evidence of poor procurement practice |
| 2026 figures | January–March partial year only | Full-year trend signals |
| Normalized baseline | Excludes 21-457 and 23-346 | "Normalized" without explanation |
| Analysis scope | Descriptive, pattern-based | Audit, performance assessment |
| KDQI-002 | Open investigation item | Confirmed defect, error |

---

*For full field definitions and lineage, see `docs/data_dictionary.md`.
For pipeline architecture and analytical decisions, see `docs/methodology.md`.
For complete data quality issue documentation, see `docs/kdqi_register.md`.*

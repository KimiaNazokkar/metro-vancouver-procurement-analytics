# Metro Vancouver Procurement Analytics
## Fact Inventory

**Version:** 1.1
**Last updated:** 2026-06-22
**Owner:** Kimia Nazokkar

This document is the controlled inventory of every published metric and narrative
claim used across the project's public-facing materials: README, Tableau dashboards,
LinkedIn case study, and portfolio storytelling.

Each fact states its value, calculation basis, source dataset, where it may be used,
and any wording constraints. No number from the project should appear in public
materials unless it is registered here.

Facts are classified by verification status:
  VERIFIED     — computed directly from step5h dataset; matches dashboard output
  VERIFY       — computed from step5h dataset but differs from prior README/dashboard
                 text; requires Tableau cross-check before locking into new materials
  APPROVED     — stated in locked Dashboard 4; treat as authoritative even where
                 Python-computed figure differs slightly (Tableau LOD grain may differ)

**Note:** `VERIFY` is reserved for future dataset updates, pipeline extensions, or facts requiring re-validation after a source refresh. No current facts in this inventory remain in VERIFY status.

---

## Section 1 — Dataset Scope and Coverage

---

### F-01 — Total dataset rows

| Field | Value |
|-------|-------|
| Fact | Total records in final governed dataset |
| Value | **2,133** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `len(df)` |
| Status | VERIFIED |

**Allowed uses:** README, data dictionary, dashboard guide, LinkedIn technical detail, portfolio documentation.

**Wording constraint:** Always pair with the reporting period: *"2,133 vendor-competition records covering 2023 through March 2026."*

---

### F-02 — Source years covered

| Field | Value |
|-------|-------|
| Fact | Reporting period |
| Value | **2023, 2024, 2025, and January–March 2026** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Distinct `source_year` values; min/max `awarded_date_parsed` = 2023-01-04 to 2026-03-31 |
| Status | VERIFIED |

**Allowed uses:** All materials.

**Wording constraint:** 2026 must always be qualified as a partial year. Never compare 2026 totals directly to 2023–2025 full-year figures without explicit caveat.

---

### F-03 — Rows by source year

| Field | Value |
|-------|-------|
| Fact | Row distribution across source years |
| Value | 2023: 516 rows · 2024: 527 rows · 2025: 907 rows · 2026: 183 rows |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `df['source_year'].value_counts()` |
| Status | VERIFIED |

**Allowed uses:** Technical documentation, data dictionary, methodology. Not for narrative storytelling.

**Note:** During duplicate verification, 3 source-level duplicate rows were identified and suppressed from the 2025 records, reducing the 2025 count from 910 extracted rows to 907 final rows. Two additional source-level duplicate rows were identified and suppressed from the 2026 records, reducing the 2026 count from 185 extracted rows to 183 final rows. These suppressions are documented under KDQI-001.

---

### F-04 — Total awarded competitions

| Field | Value |
|-------|-------|
| Fact | Distinct competitions with at least one awarded vendor |
| Value | **679** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `df[df['is_awarded_flag']==True]['competition_number'].nunique()` |
| Status | VERIFIED |

**Allowed uses:** All materials.

**Wording constraint:** Use *"679 awarded competitions"* or *"679 competitions with at least one awarded vendor."* Do not describe this figure as *"679 contracts" or "679 procurement events."* A single competition may include multiple awarded vendors or multiple vendor-level records, so the competition count should not be interpreted as a contract count.

---

### F-05 — KPI-eligible rows

| Field | Value |
|-------|-------|
| Fact | Rows eligible for spend-based KPI calculations |
| Value | **756** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `len(df[df['financial_kpi_eligible'] == True])` |
| Status | VERIFIED |

**Allowed uses:** Technical documentation, methodology, and data dictionary only. Not for README key findings, LinkedIn, or portfolio storytelling because the row-level eligibility rule is too granular for general audiences.

**Wording constraint:** KPI-eligible rows are defined by `amount_scope IN ('vendor_specific', 'group_framework_anchor')`. Vendor-specific awarded amounts are included when the disclosed amount can be attributed to a specific vendor row. For shared group/framework awards, only the designated `group_framework_anchor` row is included in spend KPIs; related `group_framework_member` rows are excluded to avoid double-counting the same disclosed amount. KPI eligibility does not exclude the two mega-projects; mega-project exclusion is a separate normalization step used only for normalized operational spend.

---

## Section 2 — Spend Figures

---

### F-06 — KPI-Eligible Disclosed Awarded Spend

| Field | Value |
|-------|-------|
| Fact | KPI-eligible disclosed awarded spend across the governed dataset |
| Value | **$4,728,617,156** (reported as **~$4.7B**) |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE financial_kpi_eligible = True` |
| Status | VERIFIED |

**Allowed uses:** All materials.

**Wording constraint:** Use *"$4.7B"* in narrative. Use the precise figure only in technical documentation. Always clarify that this figure includes two generational infrastructure projects. Do not say *"total procurement spend"* — the source data is a disclosed register, not a complete expenditure record.

**Preferred phrasing:** *"$4.7B in disclosed procurement activity" or "$4.7B in disclosed awarded spend across 679 competitions."*

---

### F-07 — Mega-project spend: 21-457 (NSWWTP)

| Field | Value |
|-------|-------|
| Fact | KPI-eligible disclosed awarded spend for competition 21-457 |
| Value | **$1,953,651,035** (reported as **~$1.95B**) |
| Competition | 21-457 — North Shore Wastewater Treatment Plant (NSWWTP) Project - C2 |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE competition_number = '21-457' AND financial_kpi_eligible = True` |
| Status | VERIFIED |

**Allowed uses:** All materials where mega-project exclusion is explained.

**Wording constraint:** Use *"~$1.95B"* in narrative. On first reference, use: *"North Shore Wastewater Treatment Plant (NSWWTP), Competition 21-457."* Do not describe this as total project cost; it is KPI-eligible disclosed awarded spend captured in the awarded-bids register.

---

### F-08 — Mega-project spend: 23-346 (Stanley Park Water Supply Tunnel)
| Field | Value |
|-------|-------|
| Fact | KPI-eligible disclosed awarded spend for competition 23-346 |
| Value | **$318,186,261** (reported as **~$318M**) |
| Competition | 23-346 — Stanley Park Water Supply Tunnel |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE competition_number = '23-346' AND financial_kpi_eligible = True` |
| Status | VERIFIED |

**Allowed uses:** All materials where mega-project exclusion is explained.

**Wording constraint:** Use "~$318M" in narrative. On first reference, use: *"Stanley Park Water Supply Tunnel, Competition 23-346."* Do not describe this as total project cost; it is KPI-eligible disclosed awarded spend captured in the awarded-bids register.

---

### F-09 — Normalized Spend Baseline

| Field | Value |
|-------|-------|
| Fact | KPI-eligible disclosed awarded spend excluding the two mega-projects |
| Value | **$2,456,779,860** (reported as **~$2.5B**) |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE financial_kpi_eligible = True AND competition_number NOT IN ('21-457', '23-346')` |
| Status | VERIFIED |

**Allowed uses:** All materials. This is the primary analytical baseline for vendor concentration analysis.

**Wording constraint:** Always explain the exclusion on first reference. *"Normalized spend excludes two generational infrastructure projects — North Shore Wastewater Treatment Plant (NSWWTP), Competition 21-457 (~$1.95B), and Stanley Park Water Supply Tunnel, Competition 23-346 (~$318M) — whose scale would distort operational comparisons."* Do not use *"normalized spend"* alone without this context on first mention in any document.

**Note:** The mega-project exclusion is an analytical scope decision, not a contract-size threshold. It reflects the specific capital programs involved, not a rule about contract value.

---

### F-09a — Normalized Spend Baseline by Source Year

| Field | Value |
|-------|-------|
| Fact | KPI-eligible disclosed awarded spend excluding the two mega-projects, grouped by source reporting year |
| Values | 2023: $544,432,043 · 2024: $793,052,007 · 2025: $1,064,411,860 · 2026: $54,883,949 |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE financial_kpi_eligible = True AND competition_number NOT IN ('21-457', '23-346') GROUP BY source_year` |
| Status | VERIFIED |

**Allowed uses:** Dashboard 1 annual spend trend, dashboard guide, README/dashboard QA reconciliation, and portfolio documentation where the normalized operational spend pattern is described.

**Wording constraint:** Always describe this as normalized spend or normalized spend baseline by source reporting year. Always state that it excludes the two mega-projects: North Shore Wastewater Treatment Plant (NSWWTP), Competition 21-457, and Stanley Park Water Supply Tunnel, Competition 23-346. Do not use these figures as total KPI-eligible spend by year; use F-10 for full KPI-eligible spend by source year.

**Note:** These four values sum to $2,456,779,859 when displayed as whole dollars, a $1 rounding difference from the F-09 normalized spend baseline of $2,456,779,860. The 2023 normalized and full-KPI values are identical because neither Competition 21-457 nor Competition 23-346 has KPI-eligible spend attributed to `source_year = 2023`. The 2026 value represents January–March only and must not be compared directly to full-year 2023–2025 values.

---

### F-10 — KPI-Eligible Spend by Source Year

| Field | Value |
|-------|-------|
| Fact | KPI-eligible disclosed awarded spend per source reporting year |
| Values | 2023: $544,432,043 · 2024: $1,111,238,268 · 2025: $3,018,062,895 · 2026: $54,883,949 |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE financial_kpi_eligible = True GROUP BY source_year` |
| Status | VERIFIED |

**Allowed uses:** Technical documentation, QA reconciliation, and charts explicitly labeled as KPI-eligible disclosed awarded spend by source reporting year. Use with caution in narrative: 2024 includes the Stanley Park Water Supply Tunnel mega-project, 2025 includes NSWWTP, and 2026 is January–March only. Do not use this metric as the normalized spend baseline or as evidence of operational year-over-year trend.

**Wording constraint:** 2026 is January–March only. Do not describe year-over-year changes without noting that 2024 includes the Stanley Park Water Supply Tunnel mega-project, 2025 includes NSWWTP, and 2026 is a partial reporting year.

---

## Section 3 — Vendor Facts

---

### F-11 — Awarded Supplier Entities (Normalized)

| Field | Value |
|-------|-------|
| Fact | Distinct normalized supplier entities receiving at least one disclosed award |
| Value | **624** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `df[df['is_awarded_flag']==True]['vendor_name_display'].nunique()` |
| Status | VERIFIED |

**Allowed uses:** All materials. This is the dashboard KPI labeled *"Awarded Suppliers"*; define it as normalized supplier entities receiving at least one disclosed award.

**Wording constraint:** Use *"624 normalized supplier entities received at least one disclosed award."* Vendor names were normalized to consolidate legal name variants, trade names, and minor spelling differences. Do not describe this as unique companies, unique bidders, or total market participants — normalization decisions involve judgment.

---

### F-12 — KPI-Eligible Supplier Entities

| Field | Value |
|-------|-------|
| Fact | Distinct normalized supplier entities with at least one KPI-eligible disclosed awarded amount |
| Value | **495** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `df[df['financial_kpi_eligible']==True]['vendor_name_display'].nunique()` |
| Status | VERIFIED |

**Allowed uses:** Technical documentation and methodology only. Do not use in narrative storytelling — it is a subset of F-11, and the distinction between 495 and 624 requires technical explanation that may distract from the main message.

**Wording constraint:** Use only in technical or methodology contexts. Preferred phrasing: *"495 normalized supplier entities had at least one KPI-eligible disclosed awarded amount."* Do not describe this as total awarded suppliers, unique vendors, unique companies, or total market participants; use F-11 for the public-facing awarded supplier KPI.

**Note:** The difference between 624 and 495 reflects normalized supplier entities that received disclosed awards but do not have individually disclosed KPI-eligible awarded amounts. These entities are counted in F-11 but excluded from spend calculations.

---

### F-13 — Top Supplier by Normalized Spend

| Field | Value |
|-------|-------|
| Fact | Largest normalized supplier entity by normalized spend baseline |
| Value | **Halton Recycling Ltd. dba Emterra Environmental** — **$281,007,000** — **11.4%** of normalized spend baseline |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE financial_kpi_eligible=True AND competition_number NOT IN ('21-457','23-346') GROUP BY vendor_name_display ORDER BY SUM DESC LIMIT 1` |
| Status | VERIFIED |

**Allowed uses:** Dashboard 2 (Vendor Concentration), README key findings, LinkedIn.

**Wording constraint:** Use *"approximately 11.4% of the normalized spend baseline"* not *"11.4% of total spend."* The 11.4% is calculated against the $2.5B normalized spend baseline, not the $4.7B disclosed awarded spend total.

---

### F-14 — Top 11 Supplier Concentration

| Field | Value |
|-------|-------|
| Fact | Cumulative share of normalized spend baseline held by the top 11 normalized supplier entities |
| Value | **~51.0%** of normalized spend baseline, cumulative at supplier #11 |
| Top 11 supplier entities | Halton Recycling/Emterra, Veolia Water Canada, Kinetic Construction, Michels Canada, GFL Environmental, Jacobs Consultancy Canada, Scott Construction, Fraser Delta Group, NAC Constructors, Pomerleau, Waste Management Canada |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Top 11 normalized supplier entities by normalized spend baseline; cumulative share = 51.0% at supplier #11 |
| Status | VERIFIED |

**Allowed uses:** Dashboard 2, README key findings, LinkedIn.

**Wording constraint:** Use *"Eleven normalized supplier entities account for approximately half of the normalized spend baseline."* The README may use *"approximately 50%"* because it is consistent with 51.0% after rounding. Do not describe this as half of total disclosed awarded spend; the share is calculated against the $2.5B normalized spend baseline.

---

### F-15 — Awarded Supplier Recurrence

| Field | Value |
|-------|-------|
| Fact | Share of normalized awarded supplier entities appearing in only one source reporting year |
| Value | **521 of 624 normalized awarded supplier entities (83.5%) appear in only one source reporting year** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | For each `vendor_name_display` where `is_awarded_flag=True`, count distinct `source_year` values. Supplier entities where this count = 1 are classified as single-year awarded suppliers. 521 of 624 awarded supplier entities have count = 1. |
| Status | VERIFIED |

**Allowed uses:** Dashboard 2 narrative, README key findings.

**Wording constraint:** Use *"521 of 624 normalized awarded supplier entities appear in only one source reporting year."* This supports a finding of limited observed supplier recurrence in the disclosed register. Do not describe this as proof of one-time supplier relationships or lack of ongoing work. Treat with care: source_year reflects publication/reporting year, not necessarily award year.

---

## Section 4 — Competition Structure Facts

---

### F-16 — Single-Bidder Rate

| Field | Value |
|-------|-------|
| Fact | Proportion of competitive competitions with exactly one recorded vendor response |
| Value | **21.9%** (108 of 494 competitive competitions) |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Competitive competitions exclude DA, DA/NOIC, SS/NOIC, and NOIC. Grain = competition_number. Single-bidder competitions have exactly one recorded participant row. 108 / 494 = 21.86%, reported as 21.9%. |
| Status | VERIFIED |

**Allowed uses:** All materials.

**Wording constraint:** Use *"21.9% of competitive procurements had exactly one recorded vendor response."* Direct-award competitions are excluded from this metric; always state this on first use. Do not describe this as a share of all procurement activity.

---

### F-17 — Single-bidder rate by year

| Field | Value |
|-------|-------|
| Fact | Single-bidder rate per source year |
| Values | 2023: **20.0%** (29/145) · 2024: **28.0%** (40/143) · 2025: **19.4%** (36/186) · 2026: **11.5%** (3/26) |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Same as F-16, filtered by source_year. Grain = competition_number, filtered by source_year. |
| Status | VERIFIED |

**Wording constraint:** 2026 rate (11.5%) reflects only 26 competitive competitions in a partial year. Do not present as a meaningful trend signal.

**Note:** Six competitive competitions appear in two source years and are counted once per year at this grain. Year-level denominators therefore sum to 500, not 494.

---

### F-18 — Direct award rate by year

| Field | Value |
|-------|-------|
| Fact | Share of awarded competitions classified as direct-award procurement instruments, per source year |
| Values | 2023: **15.7%** (27/172) · 2024: **25.5%** (49/192) · 2025: **30.6%** (82/268) · 2026: **51.9%** (28/54) |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Direct award types = DA, DA/NOIC, SS/NOIC, NOIC. Denominator = distinct competitions per year with at least one awarded row. Numerator = distinct competitions where competition_type_standardized is a direct type. |
| Status | VERIFIED |

**Allowed uses:** Dashboard 1, Dashboard 3, README key findings, LinkedIn.

**Wording constraint:** Direct awards are legitimate procurement instruments. Always include: *"Direct awards may reflect sole-source requirements, emergency procurement, standing agreements, contract renewals, or other operational considerations."* Do not frame the 2026 rate (51.9%) as a trend — it reflects a partial year with a small number of competitions (54 total). 

**Note:** Seven awarded competitions appear in two source years and are counted once per year at this grain. Year-level denominators therefore sum to 686, not 679.

---

### F-19 — Bidder depth distribution

| Field | Value |
|-------|-------|
| Fact | Distribution of competitive competitions by number of participants |
| Values | 1 participant: **108** · 2 participants: **105** · 3 participants: **102** · 4–5 participants: **100** · 6–10 participants: **55** · 11+ participants: **24** · Total competitive competitions: **494** |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Competitive competitions = rows where `competition_type_standardized NOT IN ('DA', 'DA/NOIC', 'SS/NOIC', 'NOIC')`. Participants = recorded participant rows, including awarded and non-awarded rows, counted per `competition_number`. Buckets = 1, 2, 3, 4–5, 6–10, 11+. |
| Status | VERIFIED |

**Wording constraint:** Participants includes all vendors in a competition (awarded and not awarded). "Participant" or "vendor response" is clearer than "bidder" in public-facing materials, since not all competition types use formal bidding.

---

### F-20 — Competition type breakdown

| Field | Value |
|-------|-------|
| Fact | Distinct competition count by type (awarded competitions only) |
| Values | RFP: 298 · ITT: 102 · SS/NOIC: 101 · DA: 82 · RFQ: 30 · RFP-MA: 17 · ITQ: 15 · RFSQ: 12 · CO-OPERATIVE PROCUREMENT: 10 · RFSO: 5 · DA/NOIC: 3 · SRFEOI: 2 · CSA: 1 · RFSQR: 1 |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | Governed competition-level count of awarded competitions. Grain = `competition_number`; grouped by `competition_type_standardized` after final duplicate/type reconciliation. Type counts reconcile to the 679 awarded competitions KPI. |
| Status | VERIFIED |

**Allowed uses:** Dashboard 3, technical documentation. Summarized groupings acceptable for narrative.

**Wording constraint:** For narrative, group into *"competitive"* (RFP, ITT, RFQ, RFSQ, RFSO, ITQ, RFP-MA, RFSQR, SRFEOI, CSA, CO-OPERATIVE PROCUREMENT) and "direct" (DA, DA/NOIC, SS/NOIC, NOIC). Do not explain each type in public-facing narrative.

---

## Section 5 — Data Quality and Governance Facts

---

### F-21 — Governed duplicate suppression

| Field | Value |
|-------|-------|
| Fact | Rows removed through governed suppression (KDQI-001) |
| Value | **5 rows suppressed · $1,836,534 overstatement removed** |
| Source dataset | `data/clean/step5h_suppression_audit_log.csv` |
| Calculation basis | Direct count from suppression registry; sum of overstatement_removed column |
| Status | VERIFIED |

**Allowed uses:** KDQI register, README data quality section, Dashboard 4, methodology. Not for LinkedIn or portfolio narrative.

**Wording constraint:** Use *"Five source-level duplicate records were suppressed, removing $1.84M in overstated KPI-eligible spend."* All five suppressed records originated from duplicate publication in the source documents. Do not describe any of the five as extraction-level duplicates. Use "duplicates" or "duplicate records"; avoid "errors" in public-facing language.

---

### F-22 — Dataset row count before governed duplicate suppression

| Field | Value |
|-------|-------|
| Fact | Dataset row count before governed duplicate suppression |
| Value | **2,138** |
| Source dataset | `data/clean/step5g_vendor_normalized_procurement_awards.csv` |
| Calculation basis | Confirmed by step5h blocking assertion EXPECTED_ROWS_IN = 2138 |
| Status | VERIFIED |

**Allowed uses:** KDQI register, technical documentation only. Not for narrative.

---

### F-23 — Vendor normalization scale

| Field | Value |
|-------|-------|
| Fact | Total distinct vendor key groups in lookup table |
| Value | **1,197 vendor groups** in lookup: AUTO_HIGH **177 groups** · REVIEW **14 groups** · SINGLE **1,005 groups** · PROMOTED **1 group**. Final dataset row-level distribution: AUTO_HIGH **757 rows** · REVIEW **144 rows** · SINGLE **1,231 rows** · PROMOTED **1 row**. |
| Source dataset | `data/clean/step5f_vendor_lookup_assisted.csv` for lookup-level vendor groups; `data/clean/step5h_deduped_procurement_awards.csv` for final row-level confidence distribution |
| Calculation basis | len(lookup) = 1,197; step5h confidence distribution |
| Status | VERIFIED |

**Allowed uses:** README reproducibility section, methodology. Not for narrative storytelling.

**Wording constraint:** REVIEW-confidence vendor groups represent legal suffix conflicts or qualifier ambiguity flagged for human verification. The lookup contains 14 REVIEW groups; these appear across 144 final dataset rows. Display names for REVIEW groups are tentative.

---

### F-24 — KDQI-002: 22-167 / 22-0167 KPI exposure

| Field | Value |
|-------|-------|
| Fact | Combined KPI-eligible spend exposure for competitions 22-167 and 22-0167 |
| Value | **$235,502,207 KPI-eligible spend exposure** — 22-167: **$233,133,864** = 9.49% of normalized spend baseline; 22-0167: **$2,368,343** = 0.10% of normalized spend baseline |
| Source dataset | `data/clean/step5h_deduped_procurement_awards.csv` |
| Calculation basis | `SUM(awarded_amount_numeric) WHERE financial_kpi_eligible=True AND competition_number IN ('22-167','22-0167')` |
| Status | VERIFIED |

**Allowed uses:** KDQI register, methodology. Not for narrative storytelling.

**Wording constraint:** Both competitions are treated as distinct events. No spend figures are restated pending resolution. This is an open investigation item, not a confirmed data quality defect.

---

## Section 6 — Narrative Claims

These are approved narrative framings derived from the verified facts above. They may be used verbatim or paraphrased in README, LinkedIn, and portfolio materials, subject to the constraints noted.

---

### N-01 — Portfolio framing statement

> Metro Vancouver disclosed $4.7B in awarded procurement activity across 679 awarded competitions covering 2023 through March 2026. This analysis examines spending patterns, supplier concentration, competition structure, and market participation across a major regional public utility.

**Status:** APPROVED. Uses F-06, F-04, F-02.

---

### N-02 — Concentration finding

> Eleven normalized supplier entities account for approximately half of the normalized spend baseline. The largest normalized supplier entity accounts for approximately 11.4% of the normalized spend baseline.

**Status:** APPROVED. Uses F-14, F-13. References normalized spend baseline (F-09).

---

### N-03 — Single-bidder rate finding

> Across competitive procurements, 21.9% of competitions received only one vendor response during the study period.

**Status:** APPROVED for overall rate. Uses F-16.

**Note:** Overall claim uses F-16. Year-level claims must use verified F-17 values: 2023 20.0%, 2024 28.0%, 2025 19.4%, 2026 11.5%. Do not frame 2026 as a trend signal because it reflects a partial year.

---

### N-04 — Direct award finding

> Direct-award instruments represented 15.7% of awarded competitions in 2023 and 51.9% of awarded competitions in the January–March 2026 partial reporting period. Direct awards are a legitimate procurement instrument and may reflect sole-source requirements, emergency procurement, standing agreements, contract renewals, or other operational considerations.

**Status:** APPROVED. Uses F-18. The 2023 and 2026 figures are verified.

---

### N-05 — Descriptive framing boundary

> This analysis is descriptive. It documents observed procurement patterns across Metro Vancouver's publicly disclosed award data and does not constitute an audit, performance assessment, or evaluation of procurement decisions, vendor relationships, or organizational expenditure.

**Status:** APPROVED. Locked framing for all materials. Must appear in README, Dashboard 4, and methodology.

---

## Resolved Verification Log

These items were cross-checked against Dashboard 3 after discrepancies were identified between Python-computed values and earlier README text. The resolved Tableau-aligned values were locked into F-17 and F-19 and should be used as the authoritative figures in future materials.

| Fact ID | Resolved item                    | Previous discrepancy       | Locked authoritative value |
| ------- | -------------------------------- | -------------------------- | -------------------------- |
| F-17    | 2024 single-bidder rate          | Earlier README cited 28.2% | 28.0% (40/143)             |
| F-17    | 2025 single-bidder rate          | Earlier README cited 17.5% | 19.4% (36/186)             |
| F-19    | Competitions with 1 participant  | Earlier README cited 100   | 108                        |
| F-19    | Competitions with 2 participants | Earlier README cited 110   | 105                        |

**Resolution Status:** Dashboard 3 was cross-checked in Tableau Desktop. F-17 and F-19 were updated with Tableau-aligned values and marked VERIFIED. The locked values in this log should be treated as the authoritative figures for README, LinkedIn, dashboard documentation, and portfolio materials.

---

## Restricted Phrasings

The following phrasings are restricted in project materials because they may overstate the analysis scope, imply performance judgment, or misrepresent the dataset.

| Restricted phrasing | Reason | Preferred alternative |
|---|---|---|
| Evaluative competition framing | Implies judgment about procurement practice quality rather than describing observed structure or participation | "competition structure," "competitive participation," or "bid depth" |
| "evaluate" (in procurement context) | Implies performance assessment | "examine," "describe," "analyze" |
| "audit" (applied to Metro Vancouver) | Implies authoritative compliance finding | "analysis of disclosed award data" |
| "governed analytical view" | Jargon with no clear meaning | "governed dataset," "analytical dataset" |
| "evidence-informed procurement intelligence" | Overstates the claim | "observed procurement patterns" |
| "total organizational expenditure" | This data is not a complete expenditure record | "disclosed awarded procurement activity" |
| "unique companies" | Normalization involves judgment | "distinct normalized vendor entities" |
| "unique contracts" | A competition may have multiple awards | "awarded competitions" or "vendor-competition records" |

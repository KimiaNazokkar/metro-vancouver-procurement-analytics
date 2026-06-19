# Metro Vancouver Procurement Analytics
### A governed procurement intelligence project — Python ETL pipeline · Tableau dashboards · 2023– March 2026
---
## Project Summary
This project analyzes Metro Vancouver's publicly disclosed procurement award data from 2023 through March 2026 to examine procurement spending patterns, supplier concentration, competition structure, and market participation across a major regional public utility.

The project covers the full analytical lifecycle: automated PDF extraction, multi-stage data cleaning and normalization, vendor entity resolution, data quality governance, and a four-dashboard Tableau analytics suite designed for executive and operational audiences.

The final governed dataset contains 2,133 vendor-competition records representing 679 awarded competitions and $4.7B in disclosed procurement activity between 2023 and March 2026.

> **Data source:** Metro Vancouver Awarded Bids Register (public procurement records published by Metro Vancouver)
> Official source: https://metrovancouver.org/bidding-opportunities/awarded-bids
---
## Key Findings

### 1. Metro Vancouver disclosed $4.7B in procurement activity across 679 awarded competitions
Metro Vancouver's Awarded Bids Register discloses approximately $4.7B in procurement spending across 679 awarded competitions between 2023 and March 2026. This represents the full disclosed procurement footprint of a major regional public utility operating across water, wastewater, solid waste, and regional parks infrastructure. The governed analytical dataset contains 2,133 vendor-competition records representing 494 normalized suppliers, providing visibility into supplier participation, competition outcomes, and procurement activity across the organization.

### 2. Eleven vendors account for half of normalized procurement spending
Across 494 active suppliers, the top 11 vendors collectively represent approximately 50% of normalized procurement spending. The largest supplier accounts for approximately 11.4% of normalized spend. Most leading vendors appear in only one reporting year, suggesting that concentration is driven primarily by individual large contract awards rather than persistent supplier dominance.

### 3. Single-bidder participation peaked in 2024
Across competitive procurement instruments, 21.9% of competitions received only one vendor response during the study period. The rate peaked at 28.2% in 2024 before declining to 17.5% in 2025, meaning that more than one in four competitive procurements received a single bid at the peak of the study period.

### 4. Direct awards increased from 15.7% to 51.9% of competitions
Direct award competitions represented 15.7% of competitions in 2023 and 51.9% of competitions in the partial 2026 reporting period. Direct awards are a legitimate procurement instrument and may reflect sole-source requirements, emergency procurement, standing agreements, contract renewals, or other operational considerations.

### 5. Deep bidder participation was the exception rather than the norm
Among competitive procurements with recorded bidder counts, 100 competitions received a single bid, 110 received two bids, and 102 received three bids. Competitions attracting six or more bidders represented a minority of the competitive procurement portfolio, indicating that deep market participation was the exception rather than the norm — limiting competitive price discovery for a meaningful share of procurement activity across the study period.

Taken together, these patterns describe a procurement portfolio where competitive market participation is narrower than headline competition counts alone suggest. Spending is concentrated among a relatively small supplier base, competitive instruments frequently attract limited vendor responses, and a meaningful share of disclosed activity is conducted through direct award or other procurement instruments outside the competitive bidding process — all of which are observable features of Metro Vancouver's disclosed procurement record, not assessments of the decisions that produced them. Direct awards are legitimate and commonly used procurement instruments; their use may reflect operational requirements, sole-source conditions, standing agreements, renewals, or other context that this analysis does not observe. What the data makes visible is the structure of market participation across 679 awarded competitions and $4.7B in disclosed procurement activity — a factual baseline for monitoring competitive depth, supplier dependence, and market engagement trends over time.

---
## Dashboard Suite

The analytical results are presented through a four-dashboard Tableau suite designed for executive, operational, and governance audiences.

### Dashboard 1 — Executive Summary

Provides a high-level view of Metro Vancouver's procurement portfolio, including total awarded spend, a normalized baseline that excludes two generational infrastructure projects to enable operational comparison, competition outcomes, supplier participation, and year-over-year spend trends.

<img width="1200" alt="Executive Summary" src="dashboard-screenshots/Executive%20Summary.png" />

---

### Dashboard 2 — Vendor Concentration & Supplier Dependence

Examines supplier concentration, vendor rankings, cumulative spend concentration, and supplier recurrence across reporting years. The concentration curve highlights the degree to which procurement spending is concentrated among a relatively small group of suppliers.

<img width="1200" alt="Vendor Concentration and Supplier Dependence" src="dashboard-screenshots/Vendor%20Concentration%20%26%20Supplier%20Dependence.png" />

---

### Dashboard 3 — Competition Structure & Bid Depth

Analyzes procurement instrument mix, direct award utilization, bidder participation, single-bidder rates, and bidder depth distributions. Tracks direct award utilization over time, bidder depth distributions, and single-bidder rates by year and competition type — including a 2024 peak in which more than one in four competitive procurements received a single vendor response.

<img width="1200" alt="Competition Structure and Bid Depth" src="dashboard-screenshots/Competition%20Structure%20%26%20Bid%20Depth.png" />

---

### Dashboard 4 — Methodology & Data Governance

Documents analytical methodology, KPI definitions, data lineage, known data quality items, governance controls, limitations, and reproducibility considerations supporting the analysis.

<img width="1200" alt="Methodology and Data Governance" src="dashboard-screenshots/Methodology%20%26%20Data%20Governance.png" />

---
## Data Pipeline

The analytical dataset was built through a governed multi-stage ETL pipeline designed to transform Metro Vancouver's annual procurement award disclosures into a consistent, auditable analytical dataset. Each major transformation stage includes schema validation, row-count reconciliation, or blocking assertions that halt execution when data integrity expectations are not met.

**Stage 1 — PDF Extraction**
Extracted procurement award records from Metro Vancouver Awarded Bids PDFs (2023–2026).
Applied year-specific extraction logic to accommodate changes in document structure and formatting across reporting years.

**Stage 2 — Dataset Merge**
Combined annual extracts into a unified dataset with a common schema enforced across all reporting years.
Validated input row counts against extraction baselines and confirmed schema contract before concatenation.

**Stage 3 — Data Cleaning**
Standardized dates, monetary values, award indicators, and text fields.
Classified each record's amount scope and applied seven blocking post-classification validations to confirm data integrity before output.

**Stage 4 — Competition Type Normalization**
Mapped raw procurement method values to a controlled competition type vocabulary.
All classification decisions were applied in Python upstream of Tableau to ensure dashboard calculations operate on governed, consistent values.

**Stage 5A — Vendor Safe Transformations**
Applied non-destructive vendor name standardization — whitespace normalization only.
Preserved original source values while preparing records for entity resolution.

**Stage 5B — Vendor Key Generation**
Generated deterministic vendor entity keys using a six-step normalization pipeline covering abbreviation expansion, suffix removal, and punctuation handling.
Key-building logic is validated against a blocking test suite that must pass before any output is written.

**Stage 5F — Assisted Vendor Curation**
Applied rule-based logic to evaluate vendor key groups, automatically resolving low-risk matches and flagging ambiguous vendor groups for manual review before final lookup application.
Confidence levels and review reasons are recorded for every vendor group decision.

**Stage 5G — Vendor Lookup Application**
Applied curated vendor display names and entity resolution decisions via a governed LEFT JOIN on vendor key.
Preserved both raw and normalized vendor representations for full audit traceability.

**Stage 5H — Source Duplicate Suppression**
Removed five verified duplicate award records identified through source verification against the original Metro Vancouver procurement disclosures.
All suppressed rows are documented in a structured suppression registry and written to a suppression audit log before removal.

> Stage identifiers reflect the published script numbering. Development stages 5C–5E were incorporated into adjacent stages and do not exist as standalone pipeline scripts.

**Final Output**
- 2,133 procurement records
- 679 awarded competitions
- 624 normalized suppliers
- Final governed analytical dataset, frozen prior to dashboard development and used as the source for all Tableau dashboards

---
## Data Quality & Governance

Dashboard 4 documents the analytical methodology, KPI definitions, known limitations, and interpretive framing for this project. This section describes the governance controls and validation architecture implemented in the pipeline itself — the mechanisms that produced the governed dataset the dashboards operate on.

### Analytical Scope

This analysis is descriptive. It documents observed procurement patterns across Metro Vancouver's publicly disclosed award data and does not constitute an audit, performance assessment, or evaluation of procurement decisions, vendor relationships, or organizational expenditure. The 2026 data covers January through March only and should not be compared directly to full-year figures for 2023–2025.

### Governance Controls

**Business logic upstream of Tableau.** All classification decisions — competition type standardization, amount scope classification, vendor entity resolution, and KPI eligibility flags — were applied in Python before the dataset was frozen. Tableau calculations aggregate and filter; they do not define the analytical categories.

**Source values preserved.** Raw vendor names, competition numbers, and award amounts from the source PDFs are retained in the dataset unchanged. Derived fields (`vendor_name_display`, `vendor_name_key`, `competition_type_standardized`, `amount_scope`) are added as separate columns. No source field is overwritten.

**Vendor normalization is documented and auditable.** Legal name variants, trade names, and capitalization differences were consolidated through deterministic key-based matching followed by rule-based curation and manual review. Confidence levels (`AUTO_HIGH`, `REVIEW`, `SINGLE`, `PROMOTED`) and selection reasons are recorded for every vendor group and are available in `data/clean/step5f_vendor_lookup_assisted.csv`.

**Duplicate suppression is governed and traceable.** Five duplicate award records were identified through source verification against the original Metro Vancouver procurement PDFs and removed through a documented suppression step. Each suppressed record is logged in `data/clean/step5h_suppression_audit_log.csv` with its competition number, source year, overstatement amount, retention decision rationale, and PDF page reference. No suppression occurs anywhere else in the pipeline.

### Validation Architecture

The pipeline enforces data integrity through blocking assertions at each major transformation stage. A failed assertion halts execution and prevents output from being written.

| Stage | Validation |
|-------|-----------|
| Stage 2 — Merge | Schema contract (column names and order), per-file row count baselines, post-merge math closure, `is_awarded` domain check |
| Stage 3 — Cleaning | Seven post-classification assertions covering KPI eligibility, amount parsing, scope assignment, and cross-field consistency (V1–V7) |
| Stage 5B — Key Generation | Blocking normalization test suite covering abbreviation expansion, spaced initials, suffix removal, and negative cases |
| Stage 5H — Suppression | Six financial baseline assertions: rows suppressed, registry overstatement, actual baseline reduction, post-suppression baseline, eligible rows removed, output row count |

### Known Data Quality Items

Two items were identified and documented during pipeline development. Neither affects the validity of any published KPI. Full documentation is available in `docs/KDQI_register.md`.

**KDQI-001 — Source Duplicate Awards** `Closed`
Five duplicate award records originating from source publication duplication were identified and removed through the governed suppression step (Stage 5H). Total baseline overstatement removed: $1,836,534. Audit log retained for reproducibility.

**KDQI-002 — Competitions 22-167 / 22-0167: Competition Number Format Variant** `Open`
Two source files record this competition in short format (`22-167`); a third uses a zero-padded format (`22-0167`) for the same Malaspina Phase I project. Available evidence suggests a single procurement vehicle, but this could not be confirmed with certainty. Treated as separate records pending further source confirmation. No KPI is affected.

### Reproducibility

The extraction, cleaning, normalization, and validation pipeline is written in Python and published in this repository. The analytical dataset (`data/clean/step5h_deduped_procurement_awards.csv`, 2,133 rows) was frozen prior to dashboard development. Tableau calculations operate on that frozen dataset rather than modifying it.

Source data is derived from Metro Vancouver's publicly disclosed Awarded Bids Register at [metrovancouver.org/bidding-opportunities/awarded-bids](https://metrovancouver.org/bidding-opportunities/awarded-bids). This analysis reflects a static extract and does not update automatically.

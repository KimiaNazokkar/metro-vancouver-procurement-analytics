# Metro Vancouver Procurement Analytics
## Analytical Methodology

**Version:** 1.1
**Last updated:** 2026-06-23
**Owner:** Kimia Nazokkar

This document describes the analytical methodology, pipeline architecture, dataset
design decisions, and known limitations for the Metro Vancouver Procurement Analytics
project. It is intended for technical reviewers, hiring managers, and analytics
professionals evaluating the rigor and reproducibility of this work.

This project is descriptive in scope. It documents observed patterns in Metro
Vancouver's publicly disclosed procurement awards and does not constitute an audit,
performance assessment, or evaluation of procurement decisions or vendor relationships.
Disclosed awarded amounts are not final contract expenditures.

---

## 1. Source Data

Metro Vancouver publishes an annual Awarded Bids Register as a PDF document on its
public procurement portal. Each register lists competitions that resulted in at least
one awarded vendor during the reporting year, including competition number, competition
type, competition description, award date, vendor name, awarded amount, and award
status.

This project uses four source documents covering the 2023, 2024, 2025, and 2026
(January–March) reporting periods. Source files are stored in `data/raw/` and are not
modified at any stage of the pipeline. All transformations operate on extracted copies.

---

## 2. Pipeline Architecture

The ETL pipeline transforms raw PDFs into a governed analytical dataset through nine
sequential stages. Each stage reads from the previous stage's output and writes to a
versioned intermediate file, maintaining a complete audit trail from source to final
dataset. Stages are implemented as standalone Python scripts in `scripts/`.

### Stage 1 — PDF Extraction

Four year-specific extraction scripts (`step1_extract_2023.py` through
`step1_extract_2026.py`) use `pdfplumber` to extract tabular rows from each source
PDF. Year-specific logic accommodates differences in document structure and formatting
across reporting years, including:

- Regex-based row filtering by competition number format (`\d{2}-\d{3}`) in 2023
- Structured table extraction with header and preamble row removal in 2024–2026
- Currency artifact normalization (`C$.` → `$`) in 2025
- Encoding artifact correction for known vendor name encoding issues in 2024
- Vendor name repair where `pdfplumber` shifted trailing text into the amount column
- Award-status value normalization from `Y/N` to `Yes/No` in 2026
- Source-verified award-status correction for competition 25-064 (2025 extract)
- Source-verified award-status correction for competition 25-0001 (2026 extract)

Each script writes to `data/extracted/step1_extracted_{year}.csv` with a consistent
seven-column schema: `competition_number`, `competition_type`,
`competition_description`, `awarded_date`, `vendor_name`, `awarded_amount`,
`is_awarded`.

### Stage 2 — Dataset Merge and Source-Year Lineage

`step2_merge_datasets.py` combines the four annual extracts into a single dataset.
Before concatenation, the script enforces a schema contract (column names and order)
and validates per-file row counts against extraction baselines. Post-merge math closure
confirms that the concatenated row count equals the sum of the four inputs.

A `source_year` column is added at this stage, recording the reporting year of the
source document for each row. This is distinct from the award date embedded in the
`awarded_date` field. Some competitions appear across multiple source years (for
example, a competition awarded in late 2024 may appear in both the 2024 and 2025
annual registers). The `source_year` field preserves this source attribution without
attempting to resolve publication-year ambiguity.

Output: `data/clean/step2_merged_procurement_awards.csv`

### Stage 3 — Data Cleaning, Amount Classification, and KPI Eligibility

`step3_clean_data.py` applies standardization and classification logic across the
merged dataset. Key transformations include:

**Amount parsing.** `awarded_amount` strings are cleaned (currency symbols, commas,
whitespace removed) and cast to `awarded_amount_numeric`. Amounts recorded as `N/A`
or blank for non-awarded rows are preserved as null without error.

**Amount scope classification.** Each row is assigned an `amount_scope` value
reflecting the relationship between the disclosed amount and the vendor row. The
classifier groups rows by `competition_number` and `source_year` and applies a
case-based decision tree:

- `vendor_specific` — sole awarded vendor in the competition, or one of multiple
  awarded vendors each carrying their own disclosed amount
- `group_framework_anchor` — one of multiple awarded vendors where only a single
  disclosed amount exists for the group; this row carries the amount and serves as
  the spend KPI anchor
- `group_framework_member` — a non-anchor row in a shared group award; excluded from
  spend KPIs to prevent double-counting the same disclosed amount
- `not_awarded` — the row represents a vendor that participated but was not awarded
- `amount_missing_in_parallel_award` — an awarded vendor row with no disclosed or
  extractable amount in a competition where other awarded vendors each have their own
  amounts; flagged for review and excluded from spend KPIs

`source_year` is included in the grouping key to prevent cross-year appearance of the
same competition from incorrectly triggering group-award classification.

**Financial KPI eligibility.** The `financial_kpi_eligible` flag is set to `True` for
rows where `amount_scope IN ('vendor_specific', 'group_framework_anchor')`. This flag
governs all downstream spend calculations. It does not exclude the two mega-projects
(21-457, 23-346); that exclusion is a separate analytical normalization step applied
in dashboard calculations.

**Award flag.** `is_awarded` string values are normalized to the boolean
`is_awarded_flag`.

Seven blocking post-classification assertions (V1–V7) confirm internal consistency
across KPI eligibility, amount parsing, scope assignment, and cross-field relationships
before output is written.

Output: `data/clean/step3_cleaned_procurement_awards.csv`

### Stage 4 — Competition Type Normalization

`step4_normalize_competition_types.py` maps raw `competition_type` values to a
controlled vocabulary stored in `competition_type_standardized`. Standardization covers
case normalization, spacing, abbreviation resolution, and consolidation of minor
formatting variants. All classification decisions are applied in Python at this stage
so that Tableau calculations operate on governed, consistent values.

The controlled vocabulary distinguishes competitive procurement instruments (RFP, ITT,
RFQ, RFSQ, RFSO, ITQ, RFP-MA, RFSQR, SRFEOI, CSA, CO-OPERATIVE PROCUREMENT) from
direct-award instruments (DA, DA/NOIC, SS/NOIC, NOIC). This distinction supports
competition structure analysis in Dashboard 3.

Output: `data/clean/step4_normalized_procurement_awards.csv`

### Stage 5A — Vendor Safe Transformations

`step5a_vendor_safe_transforms.py` applies non-destructive whitespace normalization to
raw vendor names, producing `vendor_name_clean`. Source values are preserved in
`vendor_name` for full audit traceability. No entity resolution occurs at this stage.

Output: `data/clean/step5a_vendor_safe_transforms.csv`

### Stage 5B — Vendor Key Generation

`step5b_build_vendor_keys.py` generates a deterministic `vendor_name_key` for each
vendor using a six-step normalization pipeline:

1. Lowercase and strip
2. Collapse dotted abbreviations (e.g., `b.c.` → `bc`, `j.a.` → `ja`)
3. Collapse spaced initials (e.g., `j a` → `ja`)
4. Remove punctuation
5. Remove legal entity suffixes (Ltd, Inc, Corp, ULC, LLP, and variants)
6. Collapse and strip whitespace

The key is designed to group common legal name variants under a single canonical key.
For example, `J.A. ELECTRIC INC.`, `JA Electric Inc.`, and `J A Electric Inc.` all
normalize to the key `ja electric`, enabling entity resolution without destroying
source values. A blocking test suite covering abbreviation expansion, spaced initials,
suffix removal, and negative cases must pass before any output is written.

The script also outputs a lookup seed file (`step5b_vendor_lookup_seed.csv`) grouping
raw vendor names by key, with variant counts and pipe-delimited variant lists, which
feeds the manual curation step.

Output: `data/clean/step5b_vendor_lookup_seed.csv`

> Stage identifiers 5C–5E reflect development stages that were incorporated into
> adjacent stages and do not exist as standalone pipeline scripts in the published
> repository.

### Stage 5F — Assisted Vendor Curation

`step5f_assisted_curation.py` applies rule-based logic to evaluate vendor key groups
and produce a governed lookup table. Each vendor key group is classified by
`merge_confidence`:

- `AUTO_HIGH` — multiple raw name variants collapsed to the same key with no legal
  suffix or qualifier ambiguity; display name assigned automatically (177 groups)
- `REVIEW` — legal suffix conflicts or qualifier ambiguity detected; flagged for human
  verification; display names are tentative (14 groups)
- `SINGLE` — only one raw name variant maps to this key; no normalization decision
  required (1,005 groups)
- `PROMOTED` — a manual display name override applied for a known source spelling
  artifact (1 group)

The lookup table contains 1,197 distinct vendor key groups and records the display name
decision, confidence level, and review reason for every group.

Output: `data/clean/step5f_vendor_lookup_assisted.csv`

### Stage 5G — Vendor Lookup Application and Date Parsing

`step5g_apply_vendor_lookup.py` joins the governed lookup table to the dataset on
`vendor_name_key` via a LEFT JOIN, adding `vendor_name_display` (the canonical display
name), `vendor_merge_confidence`, and `vendor_display_source` columns. The LEFT JOIN
preserves all dataset rows. Source values (`vendor_name`, `vendor_name_clean`,
`vendor_name_key`) are retained alongside normalized values for full lineage
traceability. Rows whose key is not found in the lookup table are surfaced via
`vendor_display_source = 'unmapped'` rather than silently receiving a null display
name.

Date parsing also occurs at this stage. `awarded_date` strings are parsed to
`awarded_date_parsed` (ISO format datetime) using a two-pass strategy: ISO format
first (covering 2023 source rows), then day-month-year format (covering 2024–2026
source rows). Records with unparseable dates receive a null `awarded_date_parsed`
value; `awarded_date_parse_failed` is set to `True` for diagnostic traceability.

Output: `data/clean/step5g_vendor_normalized_procurement_awards.csv` (2,138 rows)

### Stage 5H — Source Duplicate Suppression

`step5h_suppress_source_duplicates.py` applies the final governed suppression step.
During pre-publication source verification, five records were identified as source-level
duplicates — award rows published more than once in the Metro Vancouver source documents
themselves, which would inflate KPI-eligible spend if retained.

All five originate from the source documents (not from the extraction pipeline). Four
are page-boundary repetitions or same-page double entries in the annual registers. The
fifth (competition 25-154) involves the same award published twice in the source PDF
under case-variant vendor names.

The suppression registry is hard-coded in the script. A pre-suppression check confirms
each registry target is present in the dataset before removal. Six blocking assertions
verify the post-suppression state: rows suppressed, overstatement total, actual baseline
reduction, post-suppression baseline, eligible rows removed, and output row count. All
five suppressed rows are written to `data/clean/step5h_suppression_audit_log.csv`
before removal. No suppression occurs anywhere else in the pipeline.

| Competition | Source Year | Vendor | Overstatement Removed |
|---|---|---|---|
| 24-421 | 2025 | Allnorth Consultants Limited | $831,235 |
| 25-647 | 2025 | ORACLE CANADA ULC | $412,772 |
| 25-154 | 2026 | TEEMA Solutions Group | $250,000 |
| 25-705 | 2025 | Bestway Flooring | $192,527 |
| 26-0119 | 2026 | Petro Canada Lubrications Inc. | $150,000 |
| **Total** | | | **$1,836,534** |

Output: `data/clean/step5h_deduped_procurement_awards.csv` (2,133 rows, 22 columns)
This is the final governed dataset and the sole datasource for all Tableau dashboards.

---

## 3. Dataset Grain and Structure

**Grain.** Each row in the final dataset represents one vendor-competition record — a
single vendor's participation in a single competition. A competition with multiple
vendor participants generates multiple rows. The final dataset contains 2,133 rows
across 679 awarded competitions.

**Column count.** The final governed dataset contains 22 columns, documented in full in
`docs/data_dictionary.md`. Columns span source-extracted fields, pipeline-derived
fields (parsed dates, normalized amounts, eligibility flags), and vendor normalization
fields (key, display name, confidence level, display source).

**Dataset scope.** The dataset covers Metro Vancouver Awarded Bids Register records
from 2023 through March 2026, across four source reporting documents. The 2026 data
covers January through March only and represents a partial reporting year.

---

## 4. Source Year vs. Awarded Date

The dataset preserves a deliberate distinction between two date concepts:

**`source_year`** records the reporting year of the Metro Vancouver source document
from which a row was extracted. This is the publication year of the annual register,
not necessarily the calendar year of the award.

**`awarded_date_parsed`** records the award date as stated in the source document,
parsed to ISO format. This reflects when Metro Vancouver documented the award, which
may differ from the fiscal year in which the work was engaged or the contract value
was committed.

Some competitions appear in multiple source year documents (for example, a competition
awarded late in one year may be reported in both that year's register and the following
year's). At the dataset grain, such competitions carry the source year of each document
they appear in. When grouping by source year for trend analysis, year-level competition
counts sum to 686 rather than the 679 unique competition total, reflecting this
multi-year appearance. This is documented behavior, not a data error.

All time-based trend analysis in the dashboards uses `source_year` as the primary
grouping dimension. Interpretations based on `source_year` reflect publication-year
reporting, not necessarily the fiscal or calendar year of the underlying procurement
activity.

---

## 5. Financial KPI Eligibility and Spend Figures

**KPI eligibility logic.** Of 2,133 total rows, 756 are flagged
`financial_kpi_eligible = True`. Eligibility requires `amount_scope IN
('vendor_specific', 'group_framework_anchor')`, meaning the row carries a disclosed
awarded amount that can be attributed to a specific vendor or serves as the designated
anchor for a shared group or framework award. Non-awarded rows, rows with no disclosed
amount, non-anchor members of shared awards, and rows flagged as
`amount_missing_in_parallel_award` are excluded from spend calculations to prevent
double-counting or inclusion of unverified amounts.

**Total KPI-eligible disclosed awarded spend.** The sum of `awarded_amount_numeric`
across KPI-eligible rows is $4,728,617,156, reported as approximately $4.7B. This
figure includes two generational infrastructure projects that represent a substantial
share of the disclosed register total. It represents KPI-eligible disclosed awarded
spend in the register — not total organizational expenditure and not final contract
values.

**Mega-project exclusion and normalized spend baseline.** Two infrastructure programs
are excluded from the primary operational spend baseline used in vendor concentration
and spend distribution analysis:

- North Shore Wastewater Treatment Plant (NSWWTP), Competition 21-457: ~$1.95B
  disclosed KPI-eligible awarded spend
- Stanley Park Water Supply Tunnel, Competition 23-346: ~$318M disclosed KPI-eligible
  awarded spend

These two projects are excluded from the normalized operational baseline because their
scale would distort vendor concentration and spend distribution analysis. Their
exclusion is an analytical scope decision specific to these two competitions — not a
rule based on contract value thresholds. The normalized spend baseline after exclusion
is approximately $2.5B ($2,456,779,860).

All vendor concentration metrics and spend distribution figures are calculated against
this normalized baseline unless otherwise noted. The $4.7B total figure remains the
correct reference for total disclosed awarded spend.

---

## 6. Vendor Normalization Logic

Metro Vancouver's source documents record vendor names as submitted by vendors, which
produces natural variation: legal suffix differences (`Ltd.` vs. `Limited`),
abbreviation conventions (`B.C.` vs. `BC`), capitalization, and minor spelling
variants. Without normalization, these variants would be counted as distinct entities
in supplier concentration and market participation metrics.

The normalization pipeline (Stages 5A–5G) consolidates known variants under a single
canonical display name (`vendor_name_display`) using deterministic key generation and
rule-based confidence scoring. All normalization decisions are recorded in the lookup
table and both raw and normalized representations are preserved in the dataset.

The final dataset contains 624 distinct `vendor_name_display` values with at least one
awarded row, representing normalized supplier entities that received at least one
disclosed award during the study period. This figure is not equivalent to the count of
unique legal entities or unique companies — normalization decisions involve judgment
where source variation is ambiguous, and 14 REVIEW-confidence vendor groups remain
flagged for human verification. Display names for REVIEW-confidence groups are
tentative.

---

## 7. Competition Structure Metrics

**Awarded competitions.** 679 distinct competition numbers have at least one awarded
vendor row in the final dataset. A competition may have multiple awarded vendor rows
(for example, a multi-vendor framework agreement or a competition awarding distinct
scopes to distinct vendors). The competition count does not equal the number of
discrete contracts or procurement events in the underlying Metro Vancouver system.

**Direct awards.** Competition types classified as direct-award instruments (DA,
DA/NOIC, SS/NOIC, NOIC) are excluded from competitive participation metrics such as
the single-bidder rate. Direct awards are legitimate procurement instruments and may
reflect sole-source requirements, emergency procurement, standing agreements, contract
renewals, or other operational considerations. They are not interpreted as a
procurement quality indicator in this analysis.

**Single-bidder rate.** 21.9% of competitive procurements (108 of 494 competitive
competitions) had exactly one recorded vendor response during the study period. This
metric is computed at the competition grain, excluding all direct-award competition
types. It describes a pattern in the disclosed register — recorded participant counts
may not capture every vendor that engaged with a competition prior to formal response.

**Competition type mix.** 14 distinct competition type values appear in the final
dataset after standardization. For narrative purposes, these are grouped into
competitive instruments and direct-award instruments. Full type-level counts are
available in the dataset and documented in the fact inventory.

---

## 8. Partial-Year Coverage: 2026

The 2026 source document covers January through March 2026 only, representing
approximately one quarter of a reporting year. The 2026 portion of the dataset contains
183 rows and 54 awarded competitions.

Metrics derived from 2026 data — including direct award rate (51.9%), single-bidder
rate (11.5%), and spend totals ($54.9M KPI-eligible) — reflect this limited sample and
should not be treated as full-year trend signals or compared directly to 2023–2025
annual figures. Time-based charts that include 2026 carry explicit partial-year
caveats.

---

## 9. Data Governance: KDQI Register

Known data quality items identified during pipeline development and source verification
are documented in the Known Data Quality Issues Register (`docs/kdqi_register.md`). The
register is the authoritative record of all identified issues. Items are classified by
status, severity, and KPI impact. No item is removed from the register once added —
resolved items are marked Closed with resolution notes.

**KDQI-001 — Source-Level Duplicate Award Records** `Closed`
Five source-level duplicate records were suppressed through Stage 5H, removing $1.84M
in overstated KPI-eligible spend. All five duplicates originate from the source
documents. Full suppression details, including competition number, vendor, overstatement
amount, duplication pattern, and PDF page reference, are available in
`data/clean/step5h_suppression_audit_log.csv`.

**KDQI-002 — Competition Number Format Variation: 22-167 / 22-0167** `Open`
Competition `22-167` appears in the 2023 and 2024 source reports with $233.1M in
KPI-eligible awarded spend across Metro Vancouver Housing Corporation projects.
Competition `22-0167` appears in the 2026 source report with $2.4M in KPI-eligible
awarded spend for Malaspina Phase I Early Works. Available evidence suggests a possible
relationship between these two numbers (shared description prefix, overlapping vendor
pool), but a definitive connection could not be established from source documents. Both
are treated as distinct competition events in the final dataset, which is the
analytically conservative position. This is an open investigation item, not a confirmed
data quality defect. No published KPI is affected. Full resolution would require direct
verification against Metro Vancouver's procurement portal or contract registry.

---

## 10. Known Limitations

The following limitations apply to all analytical outputs derived from this dataset:

**Disclosed register, not a complete expenditure record.** The Metro Vancouver Awarded
Bids Register documents competitions that resulted in at least one disclosed award. It
does not capture all procurement activity, internal sourcing, or expenditure outside
the disclosed register scope.

**Disclosed awarded amounts are not final contract values.** Amounts in the register
reflect the awarded amount at the time of disclosure. Final contract expenditures may
differ due to amendments, change orders, or project scope changes not reflected in the
register.

**Vendor normalization involves judgment.** Display names are assigned through
deterministic key generation and rule-based confidence scoring. REVIEW-confidence
groups (14 groups, 144 rows) represent ambiguous cases where normalization could not be
resolved with high confidence. Supplier counts and concentration metrics reflect the
result of these normalization decisions.

**Source-year attribution, not fiscal-year attribution.** All annual metrics use
`source_year` (publication year of the source document), not fiscal year or calendar
year of award. Comparative year-over-year analysis must account for this distinction.

**2026 is a partial reporting year.** The 2026 data covers January through March only.
Annual totals and rates for 2026 are not comparable to full-year figures.

**Participant counts reflect the register, not total market engagement.** Recorded
participant counts represent vendors listed in the awarded bids register for a given
competition. They may not capture all vendors that expressed interest, requested
documents, or engaged informally prior to formal response.

**KDQI-002 is unresolved.** If competitions 22-167 and 22-0167 are confirmed as a
single procurement vehicle, combined KPI-eligible spend for that program would be
approximately $235.5M. No spend figures are restated pending resolution.

---

## 11. Reproducibility

The full pipeline is implemented in Python and published in the project repository.
All transformation logic, validation assertions, normalization rules, and suppression
decisions are version-controlled in `scripts/`. The final governed dataset
(`data/clean/step5h_deduped_procurement_awards.csv`) was frozen prior to dashboard
development. Tableau dashboard calculations operate on that frozen dataset and do not
modify it.

The pipeline can be re-executed in stage order to reproduce the final dataset from the
source PDFs. Each stage enforces schema contracts or blocking assertions that halt
execution on integrity failures, preventing silently incorrect output from propagating
through downstream stages.

Source data is derived from Metro Vancouver's publicly disclosed Awarded Bids Register,
available at
[metrovancouver.org/bidding-opportunities/awarded-bids](https://metrovancouver.org/bidding-opportunities/awarded-bids).
This analysis reflects a static extract as of March 2026 and does not update
automatically.

---

*This document should be read alongside `docs/data_dictionary.md` (field definitions
and lineage) and `docs/kdqi_register.md` (full data quality issue documentation).*

# Metro Vancouver Procurement Analytics

### Descriptive analytics of a regional public utility's disclosed procurement award data · Python ETL pipeline · Tableau dashboards · 2023–March 2026

---

## Executive Summary

Metro Vancouver disclosed $4.7B in awarded procurement activity across 679 awarded competitions covering 2023 through March 2026. This project examines spending patterns, supplier concentration, competition structure, and recorded vendor participation across Metro Vancouver's publicly disclosed Awarded Bids Register — a procurement transparency publication from a major regional public utility operating water, wastewater, solid waste, and regional parks infrastructure.

The project covers the full analytical lifecycle: automated PDF extraction, a nine-stage governed ETL pipeline with blocking assertion architecture, vendor entity resolution, data quality governance, and a four-dashboard Tableau analytics suite designed for executive, operational, and governance audiences.

The **final governed dataset** contains **2,133 vendor-competition records** covering **679 awarded competitions** and **624 normalized awarded supplier entities** with at least one disclosed award, spanning 2023 through March 2026.

> **This analysis is descriptive.** It documents observed procurement patterns across Metro Vancouver's publicly disclosed award data and does not constitute an audit, performance assessment, or evaluation of procurement decisions, vendor relationships, or organizational expenditure.

> **Data source:** Metro Vancouver Awarded Bids Register, publicly disclosed at [metrovancouver.org/bidding-opportunities/awarded-bids](https://metrovancouver.org/bidding-opportunities/awarded-bids). This analysis reflects a static extract as of March 2026 and does not update automatically.

---

## Dashboard Suite

All four dashboards draw from the final governed dataset (`data/clean/step5h_deduped_procurement_awards.csv`, 2,133 rows, 22 columns). The full Tableau workbook (`tableau/Metro_Vancouver_Procurement_Analytics.twbx`) is included in this repository and opens in Tableau Desktop.

---

### Dashboard 1 — Executive Summary

Provides a portfolio-level view of Metro Vancouver's disclosed procurement activity, including total disclosed awarded spend, a normalized spend baseline, competition and supplier counts, annual normalized spend trends, direct award rates by source year, and disclosed awarded spend by competition type.

![Executive Summary](dashboard-screenshots/Executive_Summary.png)

---

### Dashboard 2 — Supplier Concentration & Recurrence

Examines how the normalized spend baseline is distributed across normalized supplier entities, with a cumulative concentration curve, top supplier rankings, and observed supplier recurrence across source reporting years.

![Supplier Concentration and Recurrence](dashboard-screenshots/Supplier_Concentration.png)

---

### Dashboard 3 — Competition Structure & Bid Depth

Analyzes procurement instrument mix, direct award utilization by source year, recorded vendor participation in competitive procurements, single-bidder rates, and bid depth distributions across competitive instrument types.

![Competition Structure and Bid Depth](dashboard-screenshots/Structure_Bid_Depth.png)

---

### Dashboard 4 — Methodology & Data Governance

Documents analytical methodology, KPI definitions, data lineage, known data quality items, governance controls, interpretive limitations, and reproducibility considerations supporting the analysis.

![Methodology and Data Governance](dashboard-screenshots/Methodology_Data_Governance.png)

---

## Key Findings

All figures derive from the final governed dataset (`data/clean/step5h_deduped_procurement_awards.csv`). The 2026 data covers **January–March only** and is not directly comparable to full-year figures for 2023–2025.

---

### 1 · $4.7B in disclosed awarded spend across 679 awarded competitions, 2023–March 2026

Metro Vancouver's Awarded Bids Register discloses approximately $4.7B in KPI-eligible disclosed awarded spend across 679 awarded competitions during the 2023–March 2026 source reporting period. The governed dataset contains 2,133 vendor-competition records — one row per recorded vendor participation per competition, including awarded and non-awarded outcomes — and 624 normalized awarded supplier entities with at least one disclosed award across the source reporting period.

---

### 2 · Eleven normalized supplier entities account for approximately half of the normalized spend baseline

The normalized spend baseline — KPI-eligible disclosed awarded spend excluding two generational infrastructure projects — totals approximately $2.5B. The two excluded competitions are the North Shore Wastewater Treatment Plant (NSWWTP), Competition 21-457 (~$1.95B), and the Stanley Park Water Supply Tunnel, Competition 23-346 (~$318M). Their exclusion is an analytical scope decision specific to those two competitions, not a rule applied on the basis of contract value thresholds.

Across 624 normalized awarded supplier entities, the top 11 collectively account for approximately 51% of this normalized spend baseline. The largest normalized supplier entity, Halton Recycling Ltd. dba Emterra Environmental, accounts for approximately 11.4% of the normalized spend baseline. 521 of 624 normalized awarded supplier entities appear in only one source reporting year.

---

### 3 · Across competitive procurements, 21.9% of competitions had exactly one recorded vendor response

Of 494 unique competitions conducted through competitive instruments — excluding direct-award types — 108 recorded exactly one vendor response, a single-bidder rate of 21.9%. By source year: 2023: 20.0% (29 of 145), 2024: 28.0% (40 of 143), 2025: 19.4% (36 of 186), and 2026: 11.5% (3 of 26). Year-level denominators are source-year appearances and sum to 500 because six competitions conducted through competitive instruments appear in more than one source year; the overall rate is calculated on 494 unique competitive competitions. The 2024 rate is the peak across full reporting years, meaning more than one in four competitive-instrument source-year appearances in that source year recorded a single vendor response. The 2026 partial-year rate reflects a small sample across one partial quarter and is not a meaningful trend signal.

---

### 4 · Direct-award instruments represented 15.7% of awarded competitions in 2023 and 30.6% in 2025

Direct-award competitions — classified as DA, DA/NOIC, SS/NOIC, or NOIC — represented 15.7% of awarded competitions in 2023 (27 of 172), rising to 25.5% in 2024 (49 of 192) and 30.6% in 2025 (82 of 268). The January–March 2026 partial reporting period shows 51.9% (28 of 54), reflecting a small sample and not a full-year trend signal. Direct awards are a legitimate procurement instrument and may reflect sole-source requirements, emergency procurement, standing agreements, contract renewals, or other operational considerations that this analysis does not observe.

---

### 5 · Shallow recorded bid depth was the norm across competitive procurements

Among 494 competitive competitions with recorded participant counts, the bid depth distribution is: 108 competitions recorded one participant, 105 recorded two, 102 recorded three, 100 recorded four to five, 55 recorded six to ten, and 24 recorded eleven or more. Competitions with six or more recorded participants represent a smaller share of the competitive portfolio. "Participants" refers to vendors recorded in the Awarded Bids Register for each competition — both awarded and non-awarded vendors where disclosed.

---

## Data Pipeline

The ETL pipeline transforms Metro Vancouver's annual procurement award PDFs into a governed analytical dataset through nine sequential stages. Each stage reads from the previous stage's output and writes to a stage-specific intermediate file, maintaining a reproducible data lineage trail from source PDFs to final dataset. Blocking assertions at each major stage halt execution if integrity expectations are not met, preventing incorrectly-shaped data from propagating downstream.

| Stage | Script | Purpose |
|---|---|---|
| Stage 1 | `step1_extract_{year}.py` (×4) | PDF extraction using `pdfplumber`; year-specific logic for document structure, encoding artifacts, currency normalization, and award-status values |
| Stage 2 | `step2_merge_datasets.py` | Schema-validated merge of four annual extracts; adds `source_year`; enforces per-file row count baselines and post-merge math closure |
| Stage 3 | `step3_clean_data.py` | Amount parsing and cast to `awarded_amount_numeric`; `amount_scope` classification to prevent double-counting shared group awards; `financial_kpi_eligible` flagging; seven blocking post-classification assertions (V1–V7) |
| Stage 4 | `step4_normalize_competition_types.py` | Maps raw competition type values to a controlled vocabulary (`competition_type_standardized`); all classification upstream of Tableau |
| Stage 5A | `step5a_safe_transforms.py` | Non-destructive whitespace normalization of vendor names; source values preserved unchanged |
| Stage 5B | `step5b_build_vendor_keys.py` | Deterministic `vendor_name_key` generation via six-step normalization pipeline; blocking test suite must pass before output is written |
| Stage 5F | `step5f_assisted_curation.py` | Rule-based vendor group curation; assigns `merge_confidence` per group (AUTO\_HIGH, REVIEW, SINGLE, PROMOTED); produces governed lookup table of 1,197 vendor key groups |
| Stage 5G | `step5g_apply_vendor_lookup.py` | Joins governed lookup to dataset via LEFT JOIN on `vendor_name_key`; adds `vendor_name_display` and confidence fields; parses `awarded_date` to `awarded_date_parsed` |
| Stage 5H | `step5h_suppress_source_duplicates.py` | Governed suppression of five verified source-level duplicate records; six blocking post-suppression assertions; all suppressed rows written to audit log before removal |

> Stage identifiers 5C–5E reflect development stages incorporated into adjacent stages and do not exist as standalone pipeline scripts in the published repository.

**Final governed dataset:** `data/clean/step5h_deduped_procurement_awards.csv` — 2,133 rows · 22 columns · frozen prior to dashboard development. Tableau calculations operate on this frozen dataset and do not modify it.

**Business logic upstream of Tableau.** All classification decisions — competition type standardization, amount scope classification, vendor entity resolution, and KPI eligibility flags — are applied in Python before the dataset is frozen. Tableau aggregates and filters governed values; it does not define analytical categories.

---

## Data Governance & Limitations

### Governance Controls

**Source values preserved.** Raw vendor names, competition numbers, and award amounts from the source PDFs are retained unchanged in `vendor_name`, `competition_type`, and `awarded_amount`. Derived fields (`vendor_name_display`, `vendor_name_key`, `competition_type_standardized`, `amount_scope`) are added as separate columns. No source field is overwritten at any pipeline stage.

**Vendor normalization is documented and auditable.** Legal name variants, trade names, capitalization differences, and abbreviation styles were consolidated through deterministic key-based matching followed by rule-based curation. Confidence levels and display name selection reasons are recorded for all 1,197 vendor key groups in `data/clean/step5f_vendor_lookup_assisted.csv`. Both raw and normalized vendor representations are preserved in the final dataset for full audit traceability.

**Duplicate suppression is governed and traceable.** Five source-level duplicate award records were identified during pre-publication source verification against the original Metro Vancouver PDFs and removed through a documented suppression step (Stage 5H). Each suppressed record is logged in `data/clean/step5h_suppression_audit_log.csv` with its competition number, source year, overstatement amount, retention decision rationale, and PDF page reference. No suppression occurs at any other stage of the pipeline.

**Validation architecture.** The pipeline enforces data integrity through blocking assertions at each major transformation stage. A failed assertion halts execution and prevents output from being written.

| Stage | Validation mechanism |
|---|---|
| Stage 2 — Merge | Schema contract (column names and order), per-file row count baselines, post-merge math closure, `is_awarded` domain check |
| Stage 3 — Cleaning | Seven post-classification assertions (V1–V7) covering KPI eligibility, amount parsing, scope assignment, and cross-field consistency |
| Stage 5B — Key Generation | Blocking normalization test suite covering abbreviation expansion, spaced initials, suffix removal, and negative cases |
| Stage 5H — Suppression | Six financial baseline assertions: rows suppressed, registry overstatement, actual baseline reduction, post-suppression baseline, eligible rows removed, output row count |

### Known Data Quality Items

Full documentation is in `docs/kdqi_register.md`. Neither item affects the validity of any published KPI.

**KDQI-001 — Source-Level Duplicate Award Records** `Closed`

Five source-level duplicate records were suppressed through Stage 5H, removing $1,836,534 in overstated KPI-eligible spend. All five originated from duplicate publication in the Metro Vancouver source PDFs — page-boundary repetitions, same-page double entries, or publication of the same award under case-variant vendor names. Suppression audit log retained at `data/clean/step5h_suppression_audit_log.csv`.

| Competition | Source Year | Vendor | Overstatement Removed |
|---|---|---|---|
| 24-421 | 2025 | Allnorth Consultants Limited | $831,235 |
| 25-647 | 2025 | ORACLE CANADA ULC | $412,772 |
| 25-154 | 2026 | TEEMA Solutions Group | $250,000 |
| 25-705 | 2025 | Bestway Flooring | $192,527 |
| 26-0119 | 2026 | Petro Canada Lubrications Inc. | $150,000 |
| **Total** | | | **$1,836,534** |

**KDQI-002 — Competition Number Format Variation: 22-167 / 22-0167** `Open — Unresolved Investigation Item`

Competition `22-167` appears in the 2023 and 2024 source reports with $233.1M in KPI-eligible awarded spend across Metro Vancouver Housing Corporation projects. Competition `22-0167` appears in the 2026 source report with $2.4M for Malaspina Phase I Early Works. Both numbers share a description prefix and overlapping vendor pool but differ in project scope; the zero-padding convention remains unconfirmed in Metro Vancouver documentation. Both are treated as distinct competition events, which is the conservative and analytically defensible position. This is an open investigation item, not a confirmed data quality defect. No disclosed awarded spend figures are restated pending resolution.

### Analytical Limitations

- The Awarded Bids Register is a disclosed register, not a complete expenditure record. Disclosed awarded amounts are not final contract values and may not reflect amendments or scope changes.
- `source_year` reflects the publication year of the annual register, not the fiscal or calendar year of the underlying award. Some competitions appear in more than one source year; year-level competition counts therefore sum to 686, not 679.
- The 2026 data covers January–March only. All 2026 figures are partial-year and not directly comparable to 2023–2025 full-year totals.
- Vendor normalization involves judgment; 14 REVIEW-confidence vendor groups (144 rows) are flagged as tentative pending further verification.
- Recorded participant counts reflect the disclosed register and may not capture all vendors that engaged with a competition prior to formal response.

---

## Repository Structure

```
metro-vancouver-procurement-analytics/
│
├── data/
│   ├── raw/                                           # Source PDFs — not modified
│   │   ├── awarded-bids-2023.pdf
│   │   ├── awarded-bids-2024.pdf
│   │   ├── awarded-bids-2025.pdf
│   │   └── awarded-bids-2026.pdf
│   ├── extracted/                                     # Stage 1 outputs
│   │   ├── step1_extracted_2023.csv
│   │   ├── step1_extracted_2024.csv
│   │   ├── step1_extracted_2025.csv
│   │   └── step1_extracted_2026.csv
│   ├── clean/                                         # Stages 2–5H outputs and governed artifacts
│   │   ├── step5h_deduped_procurement_awards.csv      # Final governed dataset (2,133 rows)
│   │   ├── step5h_suppression_audit_log.csv           # KDQI-001 suppression audit log
│   │   ├── step5f_vendor_lookup_assisted.csv          # Governed vendor lookup table
│   │   ├── step5b_vendor_lookup_seed.csv
│   │   ├── step5g_vendor_normalized_procurement_awards.csv
│   │   ├── step5a_vendor_safe_transforms.csv
│   │   ├── step4_normalized_procurement_awards.csv
│   │   ├── step3_cleaned_procurement_awards.csv
│   │   └── step2_merged_procurement_awards.csv
│   └── diagnostics/                                   # Stage-level diagnostic outputs
│       ├── 2023/
│       ├── 2024/
│       ├── 2025/
│       ├── 2026/
│       └── step2_duplicate_inventory.csv
│
├── scripts/
│   ├── step1_extract_2023.py                          # Stage 1 — 2023 PDF extraction
│   ├── step1_extract_2024.py                          # Stage 1 — 2024 PDF extraction
│   ├── step1_extract_2025.py                          # Stage 1 — 2025 PDF extraction
│   ├── step1_extract_2026.py                          # Stage 1 — 2026 PDF extraction
│   ├── step2_merge_datasets.py                        # Stage 2 — validated merge + source_year
│   ├── step3_clean_data.py                            # Stage 3 — cleaning, classification, flags
│   ├── step4_normalize_competition_types.py           # Stage 4 — controlled competition type vocab
│   ├── step5a_safe_transforms.py                      # Stage 5A — whitespace normalization
│   ├── step5b_build_vendor_keys.py                    # Stage 5B — deterministic vendor key generation
│   ├── step5f_assisted_curation.py                    # Stage 5F — rule-based vendor curation
│   ├── step5g_apply_vendor_lookup.py                  # Stage 5G — lookup join + date parsing
│   ├── step5h_suppress_source_duplicates.py           # Stage 5H — governed duplicate suppression
│   ├── shared_utils.py                                # Shared utility functions
│   └── diagnostics/                                   # Diagnostic audit scripts
│       ├── diag_2023_raw_dump.py
│       ├── diag_2024_raw_dump.py
│       ├── diag_2025_raw_dump.py
│       └── diag_2026_raw_dump.py
│
├── docs/
│   ├── data_dictionary.md                             # Field definitions for all 22 columns
│   ├── methodology.md                                 # Pipeline architecture and analytical decisions
│   ├── dashboard_guide.md                             # Dashboard interpretation and metric framing
│   ├── kdqi_register.md                               # Known Data Quality Issues Register
│   └── fact_inventory.md                              # Controlled inventory of all published metrics
│
├── dashboard-screenshots/
│   ├── Executive_Summary.png
│   ├── Supplier_Concentration.png
│   ├── Structure_Bid_Depth.png
│   └── Methodology_Data_Governance.png
│
├── tableau/
│   └── Metro_Vancouver_Procurement_Analytics.twbx     # Tableau workbook
│
├── .gitignore
└── README.md
```

---

## How to Reproduce

**Requirements:** Python 3.8+, `pdfplumber`, `pandas`

```bash
# 1. Clone the repository
git clone https://github.com/KimiaNazokkar/Metro-Vancouver-Procurement-Analytics.git
cd Metro-Vancouver-Procurement-Analytics

# 2. Install dependencies
pip install pdfplumber pandas

# 3. Run the pipeline in stage order
python scripts/step1_extract_2023.py
python scripts/step1_extract_2024.py
python scripts/step1_extract_2025.py
python scripts/step1_extract_2026.py
python scripts/step2_merge_datasets.py
python scripts/step3_clean_data.py
python scripts/step4_normalize_competition_types.py
python scripts/step5a_safe_transforms.py
python scripts/step5b_build_vendor_keys.py
python scripts/step5f_assisted_curation.py
python scripts/step5g_apply_vendor_lookup.py
python scripts/step5h_suppress_source_duplicates.py
```

Running all twelve scripts in stage order reproduces `data/clean/step5h_deduped_procurement_awards.csv` from the source PDFs. Each stage enforces schema contracts or blocking assertions that halt execution on integrity failures, so stage-order execution is required.

**Tableau dashboards:** Open `tableau/Metro_Vancouver_Procurement_Analytics.twbx` in Tableau Desktop. The workbook connects to the final governed dataset at `data/clean/step5h_deduped_procurement_awards.csv`.

---

## Skills Demonstrated

| Area | What this project demonstrates |
|---|---|
| **Python data engineering** | `pdfplumber` for structured PDF extraction with year-specific parsing logic; `pandas` for multi-stage ETL across a nine-stage governed pipeline |
| **Pipeline governance** | Blocking assertion architecture at each transformation stage; schema contracts enforced at merge; math closure validation; suppression audit registry with six post-suppression assertions |
| **Vendor entity resolution** | Deterministic six-step key normalization; rule-based confidence classification (AUTO\_HIGH, REVIEW, SINGLE, PROMOTED); governed lookup table of 1,197 vendor key groups; full raw-to-display audit trail |
| **KPI architecture** | `amount_scope` classification to prevent double-counting shared group awards; `financial_kpi_eligible` flag design; normalized spend baseline as an analytical scope decision distinct from raw totals |
| **Tableau analytics** | Four-dashboard executive suite; LOD-style calculations for competition-grain metrics; controlled vocabulary filtering; governance dashboard documenting analytical controls |
| **Data quality governance** | KDQI register with severity classification and resolution status; audit log design; structured disclosure of unresolved investigation items vs. confirmed defects |
| **Analytical documentation** | Five governed reference documents: data dictionary (22 fields), methodology, dashboard reading guide, KDQI register, fact inventory with wording constraints for all published metrics |
| **Analytical communication** | Descriptive framing discipline — separating observed patterns in the disclosed register from evaluative claims about procurement decisions; executive-readable key findings grounded in locked facts |

---

## Suggested Reviewer Path

**Hiring manager or analytics lead**
Start with the Executive Summary and Key Findings in this README, then review the Dashboard screenshots to assess executive communication and design judgment. Dashboard 4 (Methodology & Data Governance) is the quickest signal of analytical maturity.

**Technical reviewer**
Start with `docs/methodology.md` for full pipeline architecture. Then review `scripts/step5b_build_vendor_keys.py` (vendor normalization with blocking test suite) and `scripts/step5h_suppress_source_duplicates.py` (governed suppression with six post-suppression blocking assertions). `docs/data_dictionary.md` documents all 22 fields and their lineage.

**Data governance reviewer**
Start with `docs/kdqi_register.md` and `data/clean/step5h_suppression_audit_log.csv`, then read `docs/dashboard_guide.md` for the framing boundaries applied across all four dashboards. `docs/fact_inventory.md` documents the controlled fact inventory and wording constraints used across all published materials.

**Procurement analyst**
Start with Key Findings in this README and Dashboard 3 (Competition Structure & Bid Depth). `docs/methodology.md` Section 7 covers competition structure metric definitions, and Section 8 covers the 2026 partial-year coverage constraint.

---

## Source & License

**Data source:** Metro Vancouver Awarded Bids Register, publicly disclosed at [metrovancouver.org/bidding-opportunities/awarded-bids](https://metrovancouver.org/bidding-opportunities/awarded-bids). Source documents cover the 2023, 2024, 2025, and January–March 2026 reporting periods. This analysis reflects a static extract and does not update automatically.

**Analysis:** All analytical work, pipeline code, documentation, and dashboards are the original work of [Kimia Nazokkar](https://github.com/KimiaNazokkar). The analysis is descriptive only and does not constitute an audit, official evaluation, or performance assessment of Metro Vancouver's procurement activities.

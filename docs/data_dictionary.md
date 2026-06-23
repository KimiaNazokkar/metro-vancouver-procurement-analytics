# Metro Vancouver Procurement Analytics
## Data Dictionary

**Dataset:** `data/clean/step5h_deduped_procurement_awards.csv`
**Rows:** 2,133 vendor-competition records
**Reporting period:** 2023 through March 2026 (2026 is a partial year: January–March only)
**Last updated:** 2026-06-22
**Owner:** Kimia Nazokkar

---

## How to Interpret This Dataset

Each row in this dataset represents one vendor's participation in one Metro Vancouver procurement competition. A single competition typically appears as multiple rows — one per participating vendor, covering both awarded and non-awarded outcomes. This grain (one row per vendor per competition) preserves the recorded vendor-participation structure disclosed in Metro Vancouver's Awarded Bids Register.

**Key distinctions for analysis:**

- `is_awarded = "Yes"` identifies vendors who received an award. `is_awarded = "No"` identifies vendors who participated but were not awarded.
- `financial_kpi_eligible = True` identifies the subset of rows used for spend-based KPI calculations. Not all awarded rows are KPI-eligible; see the `amount_scope` field for the classification logic.
- `source_year` records which annual PDF report the row came from. It is not the same as the year in `awarded_date`: a competition awarded in late 2024 may appear in the 2025 annual report, making its `source_year = 2025`.
- `vendor_name_display` is the curated display name for Tableau. `vendor_name` is the raw source name retained for source traceability.
- 2026 figures should never be compared directly to full-year figures for 2023–2025 without an explicit partial-year caveat.

This dataset describes observed procurement patterns from Metro Vancouver's publicly disclosed award data. It does not constitute an audit, performance assessment, or evaluation of procurement decisions, vendor relationships, or organizational expenditure.

---

## Column Reference

Columns are grouped by their role in the pipeline. The order below matches the column order in the CSV file.

---

### Group 1 — Source Fields

These fields originate from the Metro Vancouver Awarded Bids Register PDFs and preserve the source-facing values needed for traceability. Minor extraction-time cleanup may be applied where required to make PDF-derived table values usable, including whitespace or line-break normalization, currency artifact cleanup, award-status normalization, and source-verified corrections documented in the pipeline scripts.

---

#### `competition_number`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |

The Metro Vancouver competition identifier as published in the source PDF. Standard format is `YY-NNN` (two-digit year prefix, three-digit sequence number). Some competitions use non-standard or variant-like formats, including `25-0001` (zero-padded), `25-118.01` through `25-118.05` (sub-numbered scopes), and `22-0167` (zero-padded format; relationship to `22-167` is documented as KDQI-002 and remains unresolved).

**Note:** Competition numbers are not guaranteed to be unique at the row level. The same competition number may appear multiple times within a year if multiple vendors participated, and some competition numbers may appear across multiple source years when award information is published in more than one annual register.

---

#### `competition_type`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |

The raw procurement instrument type as published in the source PDF. Values vary in formatting across reporting years (spacing, capitalization, separators). Use `competition_type_standardized` for all analytical work; this field is preserved for source traceability only.

---

#### `competition_description`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |

The plain-language description of the procurement scope as published in the source PDF. Line breaks introduced by PDF table rendering have been normalized to spaces. Content is otherwise retained as extracted.

---

#### `awarded_date`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |

The award date as published in the source PDF. Format varies by year: ISO format (`YYYY-MM-DD`) for 2023 records; day-month-year format (`DD-Mon-YY`, e.g., `3-Dec-24`) for 2024–2026 records. Use `awarded_date_parsed` for date-based filtering and aggregation in Tableau.

---

#### `vendor_name`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |

The vendor name extracted from the source PDF and retained for source traceability. Minor extraction-time cleanup may be applied where required, including whitespace or line-break normalization and source-verified correction of PDF parsing or encoding artifacts. Casing, punctuation, legal suffixes, and abbreviation styles are otherwise preserved from the source. The same supplier entity may appear under different name variants across competitions or years; use `vendor_name_display` for the curated canonical form used in Tableau.

---

#### `awarded_amount`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |

The disclosed awarded amount as published in the source PDF, retained as a source-facing string. Currency formatting varies by year (`$ 600,000.00` in 2023; `$600,000` in 2024–2026). Non-awarded rows carry `N/A`, `NA`, or a blank value depending on reporting year. Use `awarded_amount_numeric` for all quantitative analysis. This field is retained for source traceability.

---

#### `is_awarded`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Metro Vancouver Awarded Bids Register PDFs |
| Pipeline stage introduced | Step 1 extraction |
| Allowed values | `Yes`, `No` |

Whether this vendor received an award in this competition, as published by Metro Vancouver. Source PDFs for 2023–2025 used `Yes`/`No` directly; the 2026 source PDF used `Y`/`N`, which was normalized to `Yes`/`No` during extraction.

Source-verified award-status corrections were applied during extraction for competition 25-064 in the 2025 extract and competition 25-0001 in the 2026 extract. These corrections are documented in the relevant extraction scripts.

---

### Group 2 — Data Lineage Field

This field is assigned by the pipeline to preserve extraction lineage across annual source reports.

---

#### `source_year`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Source | Assigned during Step 2 merge |
| Pipeline stage introduced | Step 2 merge |
| Allowed values | `2023`, `2024`, `2025`, `2026` |

Identifies which Metro Vancouver annual Awarded Bids Register PDF this row was extracted from. This is the report year, not necessarily the calendar year of the award date.

`source_year` and `awarded_date` can differ: a competition completed in late 2024 may appear in the 2025 annual report, producing `source_year = "2025"` with an `awarded_date` in 2024. Use `source_year` for report-year analysis and for the partial-year 2026 caveat. Use `awarded_date_parsed` for calendar-date analysis.

**Row distribution by source year (final governed dataset):**

| source_year | Rows | Notes |
|-------------|------|-------|
| `2023` | 516 | Full year |
| `2024` | 527 | Full year |
| `2025` | 907 | Full year; 3 source-level duplicate rows suppressed from 910 extracted |
| `2026` | 183 | Partial year (January–March only); 2 source-level duplicate rows suppressed from 185 extracted |

---

### Group 3 — Cleaned Analytical Fields

These fields are derived or normalized during Step 3 (cleaning and classification) and Step 4 (competition type normalization). They standardize source values for consistent analytical use.

---

#### `amount_missing`

| Attribute | Value |
|-----------|-------|
| Type | Boolean |
| Pipeline stage introduced | Step 3 cleaning |
| Allowed values | `True`, `False` |

`True` if the source-facing `awarded_amount` field is null, blank, `NA`, or `N/A`. Used internally for amount scope classification and `financial_kpi_eligible` assignment. Non-awarded rows always have `amount_missing = True`; awarded rows may also have `amount_missing = True` when no vendor-specific amount is published or retained for that awarded row, including group/framework awards where the total amount is recorded on an anchor row.

---

#### `is_awarded_flag`

| Attribute | Value |
|-----------|-------|
| Type | Boolean |
| Pipeline stage introduced | Step 3 cleaning |
| Allowed values | `True`, `False` |

Boolean equivalent of `is_awarded`, derived by comparing the normalized string value to `"YES"`. Convenience field for Tableau calculated fields and filters that require a boolean rather than a string comparison.

---

#### `amount_scope`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 3 cleaning |

Classifies each row's awarded amount structure based on a per-competition, per-source-year decision tree. This classification determines KPI eligibility and prevents double-counting of shared award amounts.

| Value | Meaning |
|-------|---------|
| `vendor_specific` | This vendor has their own disclosed award amount. The amount is attributable to this vendor row specifically. Eligible for spend KPIs. |
| `group_framework_anchor` | This competition has multiple awarded vendors sharing one disclosed total amount. This is the vendor row that carries the amount. Eligible for spend KPIs; the amount represents the group total. |
| `group_framework_member` | This competition has multiple awarded vendors sharing one disclosed total amount. This row does not carry an amount — it is a member of the group. **Excluded from spend KPIs** to prevent double-counting. |
| `not_awarded` | This vendor was not awarded (`is_awarded = "No"`). Excluded from spend KPIs. |
| `amount_missing_in_parallel_award` | This vendor was awarded (`is_awarded = "Yes"`) in a competition where other awarded vendors each have their own amounts, but this vendor's amount was not published or was not extractable. Excluded from spend KPIs; flagged for source review. |

---

#### `group_award_flag`

| Attribute | Value |
|-----------|-------|
| Type | Boolean |
| Pipeline stage introduced | Step 3 cleaning |
| Allowed values | `True`, `False` |

`True` for rows classified as `group_framework_anchor` or `group_framework_member`. Identifies vendor rows participating in a shared group or framework award structure where a single disclosed total covers multiple vendors. This field identifies the award structure only; use `amount_scope` or `financial_kpi_eligible` to determine spend KPI eligibility.

---

#### `financial_kpi_eligible`

| Attribute | Value |
|-----------|-------|
| Type | Boolean |
| Pipeline stage introduced | Step 3 cleaning |
| Allowed values | `True`, `False` |

`True` for rows whose `amount_scope` is `vendor_specific` or `group_framework_anchor`. These are the rows included in spend-based KPI calculations such as total disclosed awarded spend, spend by vendor, and spend by standardized competition type.

**Final dataset KPI-eligible row count: 756.**

Rows with `financial_kpi_eligible = False` are excluded from spend aggregations. This includes non-awarded rows, group framework members, and rows where no KPI-attributable amount is available.

---

#### `awarded_amount_numeric`

| Attribute | Value |
|-----------|-------|
| Type | Float (nullable) |
| Pipeline stage introduced | Step 3 cleaning |

The `awarded_amount` string parsed to a numeric float for Tableau aggregations. Currency symbols, commas, and whitespace are removed before parsing. Null where `amount_missing = True`; non-missing source-facing amounts are required to parse successfully before the dataset is published.

All `financial_kpi_eligible = True` rows are guaranteed to have a non-null, positive `awarded_amount_numeric` value, enforced by Step 3 blocking validations.

---

#### `competition_type_standardized`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 4 competition type normalization |

Raw `competition_type` values mapped to a controlled vocabulary for consistent dashboard filtering and aggregation. Preprocessing normalizes case, whitespace, underscores, and separators before lookup. Unrecognized values pass through unchanged.

| Value | Description |
|-------|-------------|
| `RFP` | Request for Proposals |
| `RFP-MA` | Request for Proposals — Master Agreement |
| `ITT` | Invitation to Tender |
| `RFQ` | Request for Quotations |
| `RFSQ` | Request for Supplier Qualifications |
| `RFSQR` | Request for Supplier Qualifications — Reissue |
| `RFSO` | Request for Standing Offer |
| `ITQ` | Invitation to Quote |
| `CO-OPERATIVE PROCUREMENT` | Cooperative purchasing arrangement (multiple raw variants normalized to this label) |
| `CSA` | Consulting Services Agreement |
| `SRFEOI` | Selective Request for Expression of Interest |
| `DA` | Direct Award |
| `DA/NOIC` | Direct Award / Notice of Intended Contract |
| `SS/NOIC` | Sole Source / Notice of Intended Contract |
| `NOIC` | Notice of Intended Contract |

For narrative and dashboard purposes, these types are grouped into two analytical families: **non-direct / competitive-facing** instruments (RFP, ITT, RFQ, RFSQ, RFSQR, RFSO, ITQ, RFP-MA, CO-OPERATIVE PROCUREMENT, CSA, SRFEOI) and **direct** instruments (DA, DA/NOIC, SS/NOIC, NOIC). This grouping is used for project-level analysis and does not constitute an audit finding or evaluation of procurement decisions.

---

### Group 4 — Vendor Normalization Fields

These fields are produced by the active vendor normalization pipeline (`step5a_safe_transforms.py`, `step5b_build_vendor_keys.py`, `step5f_assisted_curation.py`, and `step5g_apply_vendor_lookup.py`). They provide curated display names and entity-resolution lineage without overwriting the source-facing `vendor_name` field.

---

#### `vendor_name_clean`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 5A safe transforms |

`vendor_name` after whitespace normalization only: leading/trailing whitespace stripped; internal runs of whitespace collapsed to a single space. This field documents the low-risk safe transform applied before vendor normalization while preserving `vendor_name` for source traceability. Title Case normalization was evaluated and excluded because it corrupts all-caps legal entity names and abbreviations.

---

#### `vendor_name_key`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 5B vendor key build; rebuilt in Step 5G using frozen key logic |

A deterministic normalized key used to group candidate vendor-name variants for lookup-based entity resolution. Produced by a six-step pipeline: lowercase and strip → collapse dotted abbreviations → collapse spaced initials → remove punctuation → remove legal suffixes → collapse whitespace. Used only for joining to the curated lookup table; not intended as a display value or final supplier label.

Example: `"J.A. ELECTRIC INC."`, `"JA Electric Inc."`, and `"J A Electric Inc."` all produce the key `"ja electric"`.

---

#### `vendor_name_display`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 5G vendor lookup application |

The curated display label for this vendor, assigned from the curated vendor lookup table (`step5f_vendor_lookup_assisted.csv`). Used as the primary vendor name field in Tableau dashboards. For vendors whose key matched an `AUTO_HIGH` or `SINGLE` lookup entry, the display name was selected deterministically, preferring mixed-case, fuller-form names and preserved branding. For `REVIEW` entries, the display name is tentative and retained with review visibility. For the one `PROMOTED` entry, the display name reflects a governed public-facing spelling correction while the source-facing `vendor_name` is retained.

If a vendor key was not found in the lookup table, the raw `vendor_name` would be used as a fallback. No such unmapped rows exist in the final governed dataset.

---

#### `vendor_merge_confidence`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 5F assisted curation; carried into final dataset in Step 5G |
| Allowed values | `AUTO_HIGH`, `REVIEW`, `SINGLE`, `PROMOTED` |

The confidence level assigned to the vendor name resolution decision for this row, carried forward from the curated lookup table.

| Value | Meaning |
|-------|---------|
| `AUTO_HIGH` | Automated safety checks passed (no legal suffix conflict, no qualifier conflict). Display name assigned deterministically. |
| `REVIEW` | One or more safety checks flagged this group (legal suffix conflict or qualifier ambiguity). Display name is tentative and retained with review visibility. |
| `SINGLE` | This vendor key matched only one raw name variant. No merge decision was required. |
| `PROMOTED` | Manually reviewed and promoted; display name reflects a governed correction, such as spelling cleanup for public-facing display. |

**Row distribution in the final dataset (F-23):**

| Value | Rows |
|-------|------|
| `AUTO_HIGH` | 757 |
| `REVIEW` | 144 |
| `SINGLE` | 1,231 |
| `PROMOTED` | 1 |

---

#### `vendor_display_source`

| Attribute | Value |
|-----------|-------|
| Type | String |
| Pipeline stage introduced | Step 5G vendor lookup application |

Records how the `vendor_name_display` value was assigned for this row. Lineage field for pipeline reproducibility.

| Value | Meaning |
|-------|---------|
| `lookup_high` | Display name assigned from an `AUTO_HIGH` lookup entry |
| `lookup_review` | Display name assigned from a `REVIEW` lookup entry (tentative; retained with review visibility) |
| `lookup_single` | Display name assigned from a `SINGLE` lookup entry (no merge needed) |
| `lookup_promoted` | Display name assigned from a `PROMOTED` lookup entry |
| `lookup_no_merge` | Supported lineage value for vendor keys explicitly excluded from merging; does not appear in the current governed dataset |
| `unmapped` | Vendor key not found in lookup table; raw name used as fallback |
No `unmapped` rows exist in the final governed dataset.

---

### Group 5 — Date Fields

These fields are derived in Step 5G to support calendar-date analysis while preserving the original source-facing `awarded_date` field.

---

#### `awarded_date_parsed`

| Attribute | Value |
|-----------|-------|
| Type | Date (ISO 8601-compatible) |
| Pipeline stage introduced | Step 5G vendor lookup application |

`awarded_date` parsed to a typed date field. The pipeline attempted two date formats in sequence: ISO format (`YYYY-MM-DD`) for 2023 records, then `DD-Mon-YY` format (e.g., `3-Dec-24`) for 2024–2026 records. All 2,133 rows parsed successfully; no parse failures exist in the final dataset.

Date range in the final governed dataset: **2023-01-04 to 2026-03-31**.

---

#### `awarded_date_parse_failed`

| Attribute | Value |
|-----------|-------|
| Type | Boolean |
| Pipeline stage introduced | Step 5G vendor lookup application |
| Allowed values | `True`, `False` |

`True` if `awarded_date` was non-null but could not be parsed to a valid date. All values are `False` in the final governed dataset (zero parse failures). Retained as a diagnostic flag for future pipeline runs.

---

## Known Limitations

The limitations below define the analytical boundaries of the dataset. They do not invalidate the analysis; they identify where source disclosure structure, partial-year coverage, or governed normalization decisions should be considered when interpreting results.

---

### 1. 2026 is a partial year

The 2026 data covers January through March 2026 only, reflecting the content of the Metro Vancouver 2026 Awarded Bids Register as of the extraction date. The 2026 row count (183 rows) and all 2026-derived figures are not comparable to full-year figures for 2023–2025 without an explicit partial-year caveat. Year-over-year trend statements should not include 2026 as a trend data point.

---

### 2. KDQI-002 — Competition number format variation (Open)

Competition `22-167` appears in the 2023 and 2024 source reports and accumulated $233.1M in KPI-eligible disclosed awarded spend across multiple Metro Vancouver Housing Corporation projects. Competition `22-0167` appears in the 2026 source report with a single $2.4M KPI-eligible disclosed award for Malaspina Phase I Early Works.

The two numbers share a description prefix and an overlapping vendor pool, suggesting they may belong to the same procurement family or a related construction-management record. However, the available PDF evidence is insufficient to confirm that they represent the same procurement vehicle, and the zero-padding convention (`167` → `0167`) remains unverified.

Current pipeline treatment: **Both `22-167` and `22-0167` are treated as distinct competition events**.  No spend figures are restated. The combined KPI-eligible spend exposure is $235.5M, representing 9.59% of the normalized spend baseline. This is a spend-exposure disclosure, not a row-count or competition-count adjustment. Current published KPIs use the conservative treatment above and are not restated pending external verification.

Full documentation: `docs/kdqi_register.md`, KDQI-002.

---

### 3. Disclosed amounts are not final contract values or expenditure data

`awarded_amount_numeric` reflects the value disclosed in Metro Vancouver's Awarded Bids Register at the time of publication. Disclosed amounts may represent estimated contract values, ceiling values, or initial award values rather than final contract values or actual expenditures. This dataset does not include contract amendments, change orders, or final expenditure data.

---

### 4. Non-awarded vendor participation is sourced from competition disclosure

`is_awarded = "No"` rows represent vendors recorded as participants in the Metro Vancouver disclosure. The dataset does not capture all vendors who may have viewed, received, or downloaded competition documents; it captures only those whose participation is disclosed in the Awarded Bids Register. These rows should therefore be interpreted as disclosed vendor participation, not total market interest.

---

### 5. REVIEW-confidence vendor groups

Rows with `vendor_merge_confidence = "REVIEW"` (144 rows) belong to vendor groups where automated safety checks detected a legal suffix conflict or qualifier ambiguity. Display names for these rows are tentative and retained with review visibility rather than silently merged. Additional verification may be warranted if precise vendor identity is analytically material.

---

## Suppression and Governance Notes

Five source-level duplicate award records were identified during pre-publication source verification and removed from the final governed dataset (KDQI-001, Closed). All five originated from duplicate publication in the Metro Vancouver source PDFs — the same award appearing more than once due to page-boundary repetition, same-page double entry, or case-variant vendor name publication.

| Competition | Source Year | Overstatement Removed |
|-------------|-------------|----------------------|
| 24-421 | 2025 | $831,235 |
| 25-647 | 2025 | $412,772 |
| 25-154 | 2026 | $250,000 |
| 25-705 | 2025 | $192,527 |
| 26-0119 | 2026 | $150,000 |
| **Total** | | **$1,836,534** |

Each suppressed record is logged in `data/clean/step5h_suppression_audit_log.csv` with its competition number, source year, overstatement amount, suppression/retention metadata, and PDF page reference. No suppression occurs anywhere else in the pipeline.

Full documentation: `docs/kdqi_register.md`, KDQI-001.

---

## Source

Metro Vancouver Awarded Bids Register, publicly disclosed at [metrovancouver.org/bidding-opportunities/awarded-bids](https://metrovancouver.org/bidding-opportunities/awarded-bids). This dataset reflects a static extract of the 2023 through March 2026 source registers and does not update automatically.

# Metro Vancouver Procurement Analytics
# Known Data Quality Issues Register (KDQI)
# Version: 1.3
# Last updated: 2026-06-17
# Owner: Kimia Nazokkar

This register is the authoritative record of all known data quality issues identified
during pipeline development, source verification, and pre-publication QA. It is
referenced by the project README and by Dashboard 4 (Methodology and Data Governance).

Issues are classified by status, severity, and KPI impact. No issue is removed from
this register once added — resolved items are marked Closed with resolution notes,
and reclassified items are documented in the version log.

The register does not constitute an audit of Metro Vancouver procurement practices.
It describes observed data characteristics and pipeline handling decisions only.

---

## Closed Issues

---

### KDQI-001 — Source-Level Duplicate Award Records: Suppressed

| Field | Value |
|-------|-------|
| ID | KDQI-001 |
| Status | **CLOSED** |
| Severity | Medium |
| Identified in | Pre-publication source verification, June 2026 |
| Resolution script | `scripts/step5h_suppress_source_duplicates.py` |
| Audit log | `data/clean/step5h_suppression_audit_log.csv` |

#### Description

During pre-publication source verification, 25 competition numbers with multiple
distinct descriptions were reviewed against the original Metro Vancouver Awarded Bids
Register PDFs (2023–2026). Five records were confirmed as source-level duplicate rows
that would inflate KPI baseline spend if retained in the final dataset.

All five duplicates originate from the source documents. Four are page-boundary
repetitions or same-page double entries in the Metro Vancouver annual reports. The
fifth (competition 25-154) involves the same award published twice in the source PDF
under case-variant vendor names ("TEEMA Solutions Group" and "TEEMA SOLUTIONS GROUP");
the source document, not the extraction pipeline, is the origin of the duplication.

#### Suppressed Records

The table below reflects the suppressed row in each pair. Vendor names match the
`vendor_name_display` column in `data/clean/step5h_suppression_audit_log.csv`.

| Competition | Source Year | Vendor | Overstatement Removed | Duplication Pattern |
|---|---|---|---|---|
| 24-421 | 2025 | Allnorth Consultants Limited | $831,235 | Identical row published twice on same page (2025 PDF p.10) |
| 25-647 | 2025 | ORACLE CANADA ULC | $412,772 | Same award published on two pages with differing descriptions (2025 PDF p.15, p.17) |
| 25-154 | 2026 | TEEMA Solutions Group | $250,000 | Same award published twice with case-variant vendor names (2026 PDF) |
| 25-705 | 2025 | Bestway Flooring | $192,527 | Row repeated on same page, separated by an intervening competition block (2025 PDF p.17) |
| 26-0119 | 2026 | Petro Canada Lubrications Inc. | $150,000 | Identical row published twice (2026 PDF p.3) |
| **Total** | | | **$1,836,534** | |

#### Suppression Result

| Metric | Value |
|---|---|
| Rows suppressed | 5 |
| Overstatement removed | $1,836,534 |
| Dataset rows before suppression | 2,138 |
| Dataset rows after suppression | 2,133 |
| Final governed dataset | `data/clean/step5h_deduped_procurement_awards.csv` |

#### Resolution

Closed through a governed suppression registry defined in
`scripts/step5h_suppress_source_duplicates.py`. Each suppression decision is documented
with a retention rule and PDF page reference. Six blocking assertions at runtime confirm:
row count suppressed, overstatement total, post-suppression KPI baseline, and that no
non-target KPI-eligible rows are removed. All suppressed rows are preserved in
`data/clean/step5h_suppression_audit_log.csv` for reproducibility.

---

## Open Issues

---

### KDQI-002 — Competition Number Format Variation: 22-167 / 22-0167

| Field | Value |
|-------|-------|
| ID | KDQI-002 |
| Status | **OPEN — Unresolved Investigation Item** |
| Severity | Low |
| Identified in | `step2_merge_datasets.py` duplicate/variant review |
| Affected competitions | `22-167` (2023, 2024 source reports) and `22-0167` (2026 source report) |

#### Description

Competition `22-167` appears in the 2023 and 2024 source reports and accumulated
$233.1M in awards across multiple Metro Vancouver Housing Corporation projects
(The Connection Eastburne, Heron's Nest, The Steller). Competition `22-0167` appears
in the 2026 source report with a single award of $2.4M to Kinetic Construction Ltd.
for Malaspina Phase I Early Works.

Both numbers share a description prefix ("Construction Mgmt for Services and
Construction (At-Risk)") and the same recurring competing vendor pool (Kinetic,
Heatherbrae, Peak, Ventana), suggesting they may belong to the same procurement family
or master agreement. However, the available evidence is insufficient to establish that
the two competition numbers represent the same contract vehicle. The zero-padding
convention (167 → 0167) is unconfirmed in Metro Vancouver documentation.

#### Evidence Summary

| Evidence item | Supports connection | Supports distinct events |
|---|---|---|
| Shared description stem: "Construction Mgmt for Services and Construction (At-Risk)" | ✓ | |
| Recurring vendor pool: Kinetic, Heatherbrae, Peak, Ventana | ✓ | |
| Kinetic Construction awarded under both numbers | ✓ | |
| 22-167 is a multi-call-off program ($233.1M, 4 awards, 3 distinct projects) | | ✓ |
| 22-0167 references a distinct project scope (Malaspina Phase I Early Works) | | ✓ |
| Zero-padding convention (167 → 0167) unconfirmed in Metro Vancouver documentation | | ✓ |
| No Metro Vancouver contract registry or procurement portal documentation reviewed | | ✓ |

#### KPI Impact

Percentages are calculated against the normalized operational spend baseline
(`$2,456,779,860`), which excludes competitions 21-457 and 23-346.

| Competition | KPI-eligible rows | Total awarded amount | % of normalized baseline |
|---|---|---|---|
| 22-167 | 6 | $233,133,864 | 9.49% |
| 22-0167 | 1 | $2,368,343 | 0.10% |
| Combined | 7 | $235,502,207 | 9.59% |

#### Current Treatment

Both `22-167` and `22-0167` are treated as distinct competition events throughout the
pipeline and in all Tableau calculations. This is the conservative and analytically
defensible position given the available evidence. No spend figures are restated.

#### Charter Disclosure Language

> **KDQI-002 — Competition number format variation: 22-167 / 22-0167**
> Status: Open — Unresolved Investigation Item
>
> Competition `22-167` appears in 2023 and 2024 source reports and accumulated $233.1M
> in awards across multiple Metro Vancouver Housing Corporation projects (The Connection
> Eastburne, Heron's Nest, The Steller). Competition `22-0167` appears in the 2026
> source report with a single award of $2.4M to Kinetic Construction Ltd. for Malaspina
> Phase I Early Works.
>
> Both numbers share a description prefix and the same competing vendor pool, suggesting
> they may belong to the same procurement family or related construction management
> record. However, the distinct project descriptions, multi-year call-off structure, and
> unconfirmed number format convention mean a definitive relationship has not been
> established from source documents. Both are treated as distinct competition events in
> this dataset, which is the conservative and analytically defensible position. Full
> resolution would require direct verification against Metro Vancouver's procurement
> portal or contract registry.

#### Resolution Path

Direct verification against Metro Vancouver's procurement portal or contract registry.
Out of scope for v1.0. Flagged for follow-up if the project is extended or updated with
future-year data.

---

## Reclassified Items

This section records items that were investigated, documented as open issues, and
subsequently reclassified following source verification. Items are not deleted from the
register; they are preserved here for audit completeness.

---

### Former KDQI-002 — Competition 25-331: Reclassified as Source-Valid

| Field | Value |
|-------|-------|
| Former ID | KDQI-002 (v1.2) |
| Current status | **RECLASSIFIED — Not a data quality issue** |
| Originally identified in | `step2_merge_datasets.py` QA pass |
| Reclassified in | Pre-publication source re-verification, June 2026 |

#### Original Finding (v1.2)

Competition 25-331 was documented in v1.2 as a suspected table-split double extraction
in the 2025 PDF. The issue was identified because 16 rows appeared for this competition
in the dataset (against an expected 8), and both HATCH and GHD appeared once as awarded
(`is_awarded = Yes`) and once as not awarded (`is_awarded = No`).

#### Source Verification Result

Re-inspection of the 2025 Metro Vancouver Awarded Bids PDF confirmed that competition
25-331 covers two distinct procurement scopes published under the same competition
number. The 16 rows are source-valid:

| Competition Description | Awarded Vendor | Amount |
|---|---|---|
| Rice Lake Dam Safety Review | HATCH | $88,514 |
| Campbell Valley McLean Pond Dam Safety Review | GHD | $106,501 |

HATCH was awarded the Rice Lake Dam scope and did not win the Campbell Valley scope.
GHD was awarded the Campbell Valley scope and did not win the Rice Lake Dam scope.
The alternating Yes/No pattern that originally suggested extraction ambiguity is, in
fact, the correct and complete representation of two legitimate competitive outcomes
recorded under one competition number by Metro Vancouver.

No pipeline correction is required. All 16 rows remain in the final governed dataset
(`data/clean/step5h_deduped_procurement_awards.csv`) and are analytically correct.

The $195,015 in combined awarded spend ($88,514 + $106,501) previously flagged as
unverified is confirmed as accurate and requires no restatement.

---

## Register Version Log

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2026-06-04 | Initial register created. Two issues documented: 25-331 double extraction (as KDQI-001) and 22-167 / 22-0167 format variation (as KDQI-002). |
| v1.1 | 2026-06-04 | KDQI-002 (22-167 / 22-0167) reclassified from "resolved non-issue" to "Open — Unresolved Investigation Item" following full evidence review. KPI impact quantified. Charter disclosure language added. |
| v1.2 | 2026-06-16 | Corrected KDQI identity collision between register and README. Added source-duplicate suppression as KDQI-001 (Closed), reflecting Stage 5H pipeline completion. Renumbered 25-331 double extraction from KDQI-001 to KDQI-002. Renumbered 22-167 / 22-0167 format variation from KDQI-002 to KDQI-003. Documented 25-331 KPI impact as low but non-zero ($195,015). Updated current treatment file reference to final governed dataset. |
| v1.3 | 2026-06-17 | Source re-verification confirmed competition 25-331 represents two distinct project scopes (Rice Lake Dam Safety Review and Campbell Valley McLean Pond Dam Safety Review) under the same competition number. Reclassified from open KDQI-002 to source-valid; moved to Reclassified Items section. The $195,015 in combined awarded spend is confirmed accurate. Renumbered 22-167 / 22-0167 from KDQI-003 to KDQI-002. Corrected KDQI-001 suppression description: all five suppressed records are source-level duplicates; the "1 extraction-level duplicate" framing for competition 25-154 was inaccurate — Metro Vancouver published the same award twice in the source PDF under case-variant vendor names. Corrected vendor names in suppression table to match `vendor_name_display` values in the audit log (25-647: ORACLE CANADA ULC; 25-705: Bestway Flooring). Updated KPI impact percentage for 22-167 / 22-0167 from 9.48%/9.58% to 9.49%/9.59% to reflect verified normalized baseline. |

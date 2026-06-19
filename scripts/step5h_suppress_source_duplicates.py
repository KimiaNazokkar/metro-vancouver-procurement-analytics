"""
step5h_suppress_source_duplicates.py

PURPOSE
  Remove five confirmed duplicate award rows identified during pre-publication
  source verification (June 2026). Produces a clean CSV for Tableau publication
  and a suppression audit log for reproducibility.

PIPELINE POSITION
  Reads:  step5g_vendor_normalized_procurement_awards.csv   (2,138 rows)
  Writes: step5h_deduped_procurement_awards.csv             (2,133 rows)
          step5h_suppression_audit_log.csv                  (5 rows)

BACKGROUND
  25 competition numbers with multiple distinct descriptions were reviewed
  against the original Metro Vancouver Awarded Bids PDFs (2023-2026).
  Five records were confirmed as duplicate rows inflating KPI baseline spend:
    - All 5 are source-level duplicates: the same award was published multiple
      times in the Metro Vancouver source reports through page-boundary
      repetition, same-page double entry, or case-variant vendor-name publication
      in the source PDF.

SUPPRESSION POLICY
  One row is retained and one is suppressed per duplicate pair.
  Retention rule (applied in order):
    1. Retain the row with the earlier awarded_date_parsed where dates differ.
    2. Retain the row with source-faithful raw vendor_name casing where raw
       names differ (25-154 only).
    3. Retain the first occurrence by dataset index where rows are otherwise
       identical (24-421, 25-705, 26-0119).

AUDITABILITY
  All suppressed rows are written to step5h_suppression_audit_log.csv before
  removal. The SUPPRESSION_REGISTRY below is the single source of truth.
  No suppression occurs anywhere else in the pipeline.

VALIDATION
  Blocking assertions confirm:
    - Exactly 5 rows suppressed
    - Total overstatement removed equals $1,836,534
    - Post-suppression KPI baseline equals $4,728,617,156
    - No financial_kpi_eligible rows outside the five targets are removed
"""

import sys

import pandas as pd

from shared_utils import CLEAN_DIR


# =============================================================================
# FILE PATHS
# =============================================================================

INPUT_PATH     = CLEAN_DIR / "step5g_vendor_normalized_procurement_awards.csv"
OUTPUT_PATH    = CLEAN_DIR / "step5h_deduped_procurement_awards.csv"
AUDIT_LOG_PATH = CLEAN_DIR / "step5h_suppression_audit_log.csv"


# =============================================================================
# EXPECTED VALUES
# Hard-coded expected values that correspond to the SUPPRESSION_REGISTRY below.
# All six blocking assertions are validated against these constants at runtime.
# =============================================================================

EXPECTED_ROWS_IN        = 2138
EXPECTED_ROWS_OUT       = 2133
EXPECTED_SUPPRESSED     = 5
EXPECTED_OVERSTATEMENT  = 1_836_534.0
EXPECTED_BASELINE_AFTER = 4_728_617_156.0
BASELINE_TOLERANCE      = 1.0


# =============================================================================
# SUPPRESSION REGISTRY
# Single source of truth for all suppression decisions.
# Each entry identifies one duplicate pair: the matching criteria, the drop
# strategy, the overstatement amount, and the source PDF reference.
# =============================================================================

SUPPRESSION_REGISTRY = [
    {
        "competition_number":     "24-421",
        "source_year":            2025,
        "vendor_name_key":        "allnorth consultants",
        "awarded_amount_numeric": 831235.0,
        "drop_by":                "row_index",
        "drop_value":             1,
        "overstatement":          831235.0,
        "duplicate_origin":       "source",
        "pdf_reference":          "2025 PDF p.10 — identical row published twice on same page",
    },
    {
        "competition_number":     "25-647",
        "source_year":            2025,
        "vendor_name_key":        "oracle canada",
        "awarded_amount_numeric": 412772.0,
        "drop_by":                "awarded_date_parsed",
        "drop_value":             "2025-10-22",
        "overstatement":          412772.0,
        "duplicate_origin":       "source",
        "pdf_reference": (
            "2025 PDF p.15 (short-form description, 21-Oct-25, retained) and "
            "p.17 (long-form description, 22-Oct-25, suppressed). "
            "Amount identical ($412,772). No split-component DA precedent in dataset. "
            "Metro Vancouver uses separate competition numbers for distinct Oracle modules "
            "(cf. competition 25-747)."
        ),
    },
    {
        "competition_number":     "25-154",
        "source_year":            2026,
        "vendor_name_key":        "teema solutions group",
        "awarded_amount_numeric": 250000.0,
        "drop_by":                "vendor_name_raw",
        "drop_value":             "TEEMA SOLUTIONS GROUP",
        "overstatement":          250000.0,
        "duplicate_origin":       "source",
        "pdf_reference": (
            "2026 PDF — Metro Vancouver published "
            "the same Recruitment Services award twice "
            "using case-variant vendor names "
            "('TEEMA Solutions Group' and 'TEEMA SOLUTIONS GROUP'). "
            "Mixed-case row retained; all-caps row suppressed."
        ),
    },
    {
        "competition_number":     "25-705",
        "source_year":            2025,
        "vendor_name_key":        "bestway flooring",
        "awarded_amount_numeric": 192527.0,
        "drop_by":                "row_index",
        "drop_value":             1,
        "overstatement":          192527.0,
        "duplicate_origin":       "source",
        "pdf_reference": (
            "2025 PDF p.17 — BESTWAY FLOORING LTD row repeated immediately after "
            "the 25-331 competition block, consistent with table-split page boundary "
            "duplication in the source report."
        ),
    },
    {
        "competition_number":     "26-0119",
        "source_year":            2026,
        "vendor_name_key":        "petro canada lubrications",
        "awarded_amount_numeric": 150000.0,
        "drop_by":                "row_index",
        "drop_value":             1,
        "overstatement":          150000.0,
        "duplicate_origin":       "source",
        "pdf_reference": (
            "2026 PDF p.3 — identical PETRO CANADA LUBRICATIONS INC. row "
            "('Supply and Delivery of Lubricants', $150,000, 26-Feb-26) "
            "published twice."
        ),
    },
]


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    w = 60
    print()
    print("=" * w)
    print(f"  {title}")
    print("=" * w)

def ok(msg):
    print(f"  PASS  {msg}")

def fail(msg):
    print(f"  FAIL  {msg}")
    sys.exit(1)


# =============================================================================
# MAIN
# =============================================================================

def main():

    section("STEP 5H  —  SOURCE DUPLICATE SUPPRESSION")
    print(f"  Input  : {INPUT_PATH}")
    print(f"  Output : {OUTPUT_PATH}")
    print(f"  Log    : {AUDIT_LOG_PATH}")


    # ------------------------------------------------------------------
    # 1. Load
    # ------------------------------------------------------------------
    section("1 / 6   LOAD INPUT")

    df = pd.read_csv(INPUT_PATH)
    print(f"  Rows loaded : {len(df):,}")

    if len(df) != EXPECTED_ROWS_IN:
        fail(f"Row count mismatch — expected {EXPECTED_ROWS_IN:,}, got {len(df):,}")
    ok(f"Input row count = {EXPECTED_ROWS_IN:,}")

    baseline_before = (
        df[df["financial_kpi_eligible"] == True]["awarded_amount_numeric"].sum()
    )
    print(f"  KPI baseline (before) : ${baseline_before:,.0f}")


    # ------------------------------------------------------------------
    # 2. Resolve suppression targets
    # ------------------------------------------------------------------
    section("2 / 6   RESOLVE SUPPRESSION TARGETS")

    drop_indices   = []
    audit_rows     = []
    total_removed  = 0.0

    for entry in SUPPRESSION_REGISTRY:
        comp   = entry["competition_number"]
        yr     = entry["source_year"]
        vkey   = entry["vendor_name_key"]
        amount = entry["awarded_amount_numeric"]

        pair_mask = (
            (df["competition_number"]     == comp)  &
            (df["source_year"]            == yr)    &
            (df["vendor_name_key"]        == vkey)  &
            (df["awarded_amount_numeric"] == amount)
        )
        pair = df[pair_mask].copy()

        if len(pair) != 2:
            fail(
                f"Expected 2 rows for {comp}/{yr}/{vkey}/{amount:.0f}, "
                f"found {len(pair)}"
            )

        if entry["drop_by"] == "row_index":
            drop_idx = pair.index[entry["drop_value"]]

        elif entry["drop_by"] == "awarded_date_parsed":
            date_mask = pair["awarded_date_parsed"] == entry["drop_value"]
            if date_mask.sum() != 1:
                fail(
                    f"Date key '{entry['drop_value']}' matched {date_mask.sum()} "
                    f"rows for {comp} — expected exactly 1"
                )
            drop_idx = pair[date_mask].index[0]

        elif entry["drop_by"] == "vendor_name_raw":
            raw_mask = pair["vendor_name"] == entry["drop_value"]
            if raw_mask.sum() != 1:
                fail(
                    f"Raw vendor name '{entry['drop_value']}' matched {raw_mask.sum()} "
                    f"rows for {comp} — expected exactly 1"
                )
            drop_idx = pair[raw_mask].index[0]

        else:
            fail(f"Unknown drop_by strategy: '{entry['drop_by']}'")

        retain_idx = [i for i in pair.index if i != drop_idx][0]
        drop_indices.append(drop_idx)
        total_removed += entry["overstatement"]

        print(
            f"  {comp} ({yr})  "
            f"{entry['duplicate_origin'].upper():<12}  "
            f"${amount:>12,.0f}"
        )
        print(
            f"    DROP   row {drop_idx:<6}  "
            f"date={df.loc[drop_idx,'awarded_date_parsed']}  "
            f"'{df.loc[drop_idx,'vendor_name']}'"
        )
        print(
            f"    RETAIN row {retain_idx:<6}  "
            f"date={df.loc[retain_idx,'awarded_date_parsed']}  "
            f"'{df.loc[retain_idx,'vendor_name']}'"
        )

    if len(drop_indices) != EXPECTED_SUPPRESSED:
        fail(
            f"Resolved {len(drop_indices)} drop targets — "
            f"expected {EXPECTED_SUPPRESSED}"
        )
    ok(f"All {EXPECTED_SUPPRESSED} suppression targets resolved")

    if len(set(drop_indices)) != len(drop_indices):
        fail("Duplicate drop indices — same row targeted more than once")
    ok("No duplicate drop indices")


    # ------------------------------------------------------------------
    # 3. Write audit log
    # ------------------------------------------------------------------
    section("3 / 6   WRITE SUPPRESSION AUDIT LOG")

    for drop_idx, entry in zip(drop_indices, SUPPRESSION_REGISTRY):
        row = df.loc[drop_idx]
        audit_rows.append({
            "competition_number":      entry["competition_number"],
            "source_year":             entry["source_year"],
            "vendor_name_raw":         row["vendor_name"],
            "vendor_name_display":     row["vendor_name_display"],
            "vendor_name_key":         row["vendor_name_key"],
            "awarded_amount_numeric":  entry["awarded_amount_numeric"],
            "awarded_date_parsed":     row["awarded_date_parsed"],
            "competition_description": row["competition_description"],
            "financial_kpi_eligible":  row["financial_kpi_eligible"],
            "duplicate_origin":        entry["duplicate_origin"],
            "overstatement_removed":   entry["overstatement"],
            "pdf_reference":           entry["pdf_reference"],
            "drop_by_strategy":        entry["drop_by"],
            "drop_by_value":           str(entry["drop_value"]),
            "dataset_row_index":       drop_idx,
        })

    audit_log = pd.DataFrame(audit_rows)
    audit_log.to_csv(AUDIT_LOG_PATH, index=False, encoding="utf-8-sig")
    ok(f"Audit log written: {AUDIT_LOG_PATH.name}  ({len(audit_log)} rows)")


    # ------------------------------------------------------------------
    # 4. Apply suppression
    # ------------------------------------------------------------------
    section("4 / 6   APPLY SUPPRESSION")

    eligible_before_count = int((df["financial_kpi_eligible"] == True).sum())
    df_clean              = df.drop(index=drop_indices).reset_index(drop=True)
    eligible_after_count  = int((df_clean["financial_kpi_eligible"] == True).sum())
    rows_dropped          = len(df) - len(df_clean)
    eligible_dropped      = eligible_before_count - eligible_after_count

    print(f"  Rows dropped                : {rows_dropped}")
    print(f"  KPI-eligible rows before    : {eligible_before_count}")
    print(f"  KPI-eligible rows after     : {eligible_after_count}")
    print(f"  KPI-eligible rows removed   : {eligible_dropped}")


    # ------------------------------------------------------------------
    # 5. Blocking assertions
    # ------------------------------------------------------------------
    section("5 / 6   BLOCKING ASSERTIONS")

    baseline_after   = df_clean[df_clean["financial_kpi_eligible"] == True]["awarded_amount_numeric"].sum()
    actual_reduction = baseline_before - baseline_after

    # A — rows suppressed
    if rows_dropped != EXPECTED_SUPPRESSED:
        fail(f"A  Rows suppressed: expected {EXPECTED_SUPPRESSED}, got {rows_dropped}")
    ok(f"A  Rows suppressed           = {rows_dropped}  (expected {EXPECTED_SUPPRESSED})")

    # B — registry overstatement total
    if abs(total_removed - EXPECTED_OVERSTATEMENT) > 0.01:
        fail(
            f"B  Registry overstatement: "
            f"expected ${EXPECTED_OVERSTATEMENT:,.0f}, got ${total_removed:,.0f}"
        )
    ok(f"B  Registry overstatement    = ${total_removed:,.0f}  (expected ${EXPECTED_OVERSTATEMENT:,.0f})")

    # C — actual baseline reduction
    if abs(actual_reduction - EXPECTED_OVERSTATEMENT) > BASELINE_TOLERANCE:
        fail(
            f"C  Baseline reduction: "
            f"expected ${EXPECTED_OVERSTATEMENT:,.0f}, got ${actual_reduction:,.0f}"
        )
    ok(f"C  Actual baseline reduction = ${actual_reduction:,.0f}  (matches registry)")

    # D — post-suppression baseline
    if abs(baseline_after - EXPECTED_BASELINE_AFTER) > BASELINE_TOLERANCE:
        fail(
            f"D  Post-suppression baseline: "
            f"expected ${EXPECTED_BASELINE_AFTER:,.0f}, got ${baseline_after:,.0f}"
        )
    ok(f"D  Post-suppression baseline = ${baseline_after:,.0f}  (expected ${EXPECTED_BASELINE_AFTER:,.0f})")

    # E — no unintended eligible rows removed
    if eligible_dropped != EXPECTED_SUPPRESSED:
        fail(
            f"E  Eligible rows removed: expected {EXPECTED_SUPPRESSED}, "
            f"got {eligible_dropped} — unintended removal detected"
        )
    ok(f"E  Eligible rows removed     = {eligible_dropped}  (exactly the {EXPECTED_SUPPRESSED} targeted, none unintended)")

    # F — output row count
    if len(df_clean) != EXPECTED_ROWS_OUT:
        fail(f"F  Output rows: expected {EXPECTED_ROWS_OUT:,}, got {len(df_clean):,}")
    ok(f"F  Output row count          = {len(df_clean):,}  (expected {EXPECTED_ROWS_OUT:,})")


    # ------------------------------------------------------------------
    # 6. Write output and print summary
    # ------------------------------------------------------------------
    section("6 / 6   WRITE OUTPUT")

    df_clean.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    ok(f"Output written: {OUTPUT_PATH.name}")

    print()
    print("  +---------------------------------------------------------+")
    print("  |  SUPPRESSION SUMMARY                                   |")
    print("  +---------------------------------------------------------+")
    print(f"  |  Input rows             {EXPECTED_ROWS_IN:>8,}                       |")
    print(f"  |  Rows suppressed        {rows_dropped:>8}                       |")
    print(f"  |  Output rows            {len(df_clean):>8,}                       |")
    print("  +---------------------------------------------------------+")
    print(f"  |  Baseline before   ${baseline_before:>17,.0f}              |")
    print(f"  |  Overstatement removed -${actual_reduction:>14,.0f}              |")
    print(f"  |  Baseline after    ${baseline_after:>17,.0f}              |")
    print(f"  |  Reduction              {'%.4f%%' % (actual_reduction/baseline_before*100):>9}                       |")
    print("  +---------------------------------------------------------+")
    print("  |  Suppressed records:                                   |")
    for entry in SUPPRESSION_REGISTRY:
        tag = "(SRC)" if entry["duplicate_origin"] == "source" else "(EXT)"
        line = f"  |    {entry['competition_number']:<8} {entry['source_year']}  ${entry['overstatement']:>10,.0f}  {tag}"
        print(f"{line:<57}|")
    print("  +---------------------------------------------------------+")
    print("  |  ALL 6 ASSERTIONS PASSED                               |")
    print("  +---------------------------------------------------------+")

    print()
    print("=" * 60)
    print("  FINAL GOVERNED DATASET READY")
    print("=" * 60)
    print(f"  Final dataset : {OUTPUT_PATH.name}")
    print("  This file is the final Tableau-ready governed analytical dataset.")
    print("=" * 60)


if __name__ == "__main__":
    main()

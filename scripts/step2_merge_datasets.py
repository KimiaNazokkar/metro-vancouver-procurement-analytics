"""
step2_merge_datasets.py
=======================
Merge the four yearly extracted procurement award CSVs into a single
Tableau-ready master dataset.

Pipeline position: step1 (×4) → THIS SCRIPT → step3

What this script does
---------------------
  1. Loads each year's extracted CSV
  2. Attaches a source_year column BEFORE concatenation (data lineage)
  3. Validates schema contract on every input (blocking)
  4. Validates row counts against known baselines (blocking)
  5. Concatenates with pd.concat (no row filtering, no column changes)
  6. Validates post-merge math closure (blocking)
  7. Validates is_awarded domain values (blocking)
  8. Produces a non-blocking duplicate inventory audit artifact
  9. Saves the merged output

Blocking vs informational
-------------------------
  BLOCKING    — the script raises an error and does NOT save output.
                Use when data integrity cannot be trusted downstream.

  INFORMATIONAL — the script prints a warning and continues.
                  Use when the finding is known, documented, or downstream-safe.

Current data quality notes
--------------------------
  Competition 25-331 was previously flagged during duplicate review but was
  source-verified as valid: the 2025 source report records two distinct scopes
  under the same competition number. No correction is required at merge time.

  KDQI-002: Competition number format variation 22-167 / 22-0167 remains an
  unresolved investigation item. The available source evidence is insufficient
  to establish that the two numbers represent the same contract vehicle, so the
  pipeline treats them as distinct competition events. No spend figures are
  restated pending external verification.

Output
------
  data/clean/step2_merged_procurement_awards.csv
  data/diagnostics/step2_duplicate_inventory.csv (audit artifact, non-blocking)
"""

import pandas as pd
import sys

# ============================================================
# SHARED PATHS
# Centralized project paths.
# ============================================================
from shared_utils import (
    EXTRACTED_DIR,
    CLEAN_DIR,
    DIAGNOSTICS_DIR,
)

OUTPUT_PATH      = CLEAN_DIR / "step2_merged_procurement_awards.csv"
DUPLICATE_REPORT = DIAGNOSTICS_DIR / "step2_duplicate_inventory.csv"


# ============================================================
# SCHEMA CONTRACT
# Every input file must have exactly these columns in this order.
# If a future extraction script adds or renames a column, this
# assertion fires before any data is merged — preventing silent
# misalignment from propagating to Tableau.
# ============================================================
EXPECTED_COLUMNS = [
    "competition_number",
    "competition_type",
    "competition_description",
    "awarded_date",
    "vendor_name",
    "awarded_amount",
    "is_awarded",
]


# ============================================================
# ROW COUNT BASELINES
# These are the verified row counts from the completed extraction
# audits for each year. They act as a checksum: if an extraction
# script is re-run and produces fewer rows (due to a regression),
# or if a stale partial file is picked up, this assertion fires.
#
# To update these after re-running an extraction:
#   Run the relevant diag_XXXX_raw_dump.py audit first,
#   confirm the new count is correct, then update here.
# ============================================================
EXPECTED_ROW_COUNTS = {
    "step1_extracted_2023.csv": 516,
    "step1_extracted_2024.csv": 527,
    "step1_extracted_2025.csv": 910,
    "step1_extracted_2026.csv": 185,
}

EXPECTED_TOTAL_ROWS = sum(EXPECTED_ROW_COUNTS.values())  # 2138


# ============================================================
# IS_AWARDED DOMAIN
# After merge, is_awarded must contain only these values.
# Any other value indicates a normalization failure in an
# extraction script that slipped through without detection.
# ============================================================
VALID_IS_AWARDED_VALUES = {"Yes", "No"}


# ============================================================
# INPUT FILE REGISTRY
# Each entry is (path, source_year_label).
# source_year is the PDF report year, NOT the awarded_date year.
# Competition 25-0001 was awarded in March 2026 but appears in
# the 2026 report — so its source_year is "2026".
# ============================================================
INPUT_FILES = [
    (EXTRACTED_DIR / "step1_extracted_2023.csv", "2023"),
    (EXTRACTED_DIR / "step1_extracted_2024.csv", "2024"),
    (EXTRACTED_DIR / "step1_extracted_2025.csv", "2025"),
    (EXTRACTED_DIR / "step1_extracted_2026.csv", "2026"),
]


# ============================================================
# HELPER: BLOCKING ASSERTION
# Prints a clear error message and exits with a non-zero code.
# Using sys.exit() rather than raise lets the error message
# be readable in both terminal and CI/CD output.
# ============================================================
def fail(message: str):
    """Print an error message and stop the pipeline."""
    print()
    print("=" * 60)
    print("  MERGE FAILED — DATA INTEGRITY CHECK")
    print("=" * 60)
    print(f"  {message}")
    print()
    print("  The output file was NOT written.")
    print("  Fix the issue above before re-running this step.")
    print("=" * 60)
    sys.exit(1)


# ============================================================
# HELPER: INFORMATIONAL WARNING
# Prints a warning but does NOT stop the pipeline.
# Use for known issues that are documented and downstream-safe.
# ============================================================
def warn(message: str):
    """Print a warning and continue."""
    print(f"  [WARN] {message}")


# ============================================================
# MAIN
# ============================================================
def main():

    # ============================================================
    # STEP 1: LOAD, VALIDATE, AND TAG EACH INPUT FILE
    # ============================================================
    print()
    print("=" * 60)
    print("  step2_merge_datasets.py")
    print("=" * 60)
    print()
    print("  LOADING INPUT FILES")
    print("  " + "-" * 40)

    dfs = []

    for file_path, source_year in INPUT_FILES:

        # --- File existence check ---
        # If the file doesn't exist, fail immediately with a clear message.
        # pd.read_csv would raise FileNotFoundError but the message is less helpful.
        if not file_path.exists():
            fail(
                f"Input file not found: {file_path}\n"
                f"  Run step1_extract_{source_year}.py before this step."
            )

        df = pd.read_csv(file_path)
        print(f"  Loaded {file_path.name}: {len(df):,} rows")

        # ── Schema contract check (BLOCKING) ──────────────────────────────────────
        # Check 1: correct number of columns
        # Catches: extra column added by mistake, column removed, CSV corruption
        actual_cols   = list(df.columns)
        if len(actual_cols) != len(EXPECTED_COLUMNS):
            fail(
                f"Schema mismatch in {file_path.name}:\n"
                f"  Expected {len(EXPECTED_COLUMNS)} columns: {EXPECTED_COLUMNS}\n"
                f"  Got      {len(actual_cols)} columns: {actual_cols}"
            )

        # Check 2: correct column names in correct order
        # Catches: column renamed in extractor, column order changed
        # pd.concat aligns on names, so order matters for downstream positional use
        if actual_cols != EXPECTED_COLUMNS:
            # Build a diff to make the error actionable
            diff_lines = []
            for i, (expected, actual) in enumerate(zip(EXPECTED_COLUMNS, actual_cols)):
                if expected != actual:
                    diff_lines.append(f"  position {i}: expected {expected!r}, got {actual!r}")
            fail(
                f"Column name or order mismatch in {file_path.name}:\n"
                + "\n".join(diff_lines)
            )

        # ── Row count baseline check (BLOCKING) ───────────────────────────────────
        # Verifies the file matches the row count confirmed by the extraction audit.
        # Catches: stale/partial file, extraction regression, wrong file loaded.
        expected_rows = EXPECTED_ROW_COUNTS[file_path.name]
        if len(df) != expected_rows:
            fail(
                f"Row count mismatch in {file_path.name}:\n"
                f"  Expected {expected_rows:,} rows (from extraction audit)\n"
                f"  Got      {len(df):,} rows\n"
                f"  Re-run the extraction audit before proceeding."
            )

        # ── Add source_year BEFORE concatenation (data lineage) ───────────────────
        # source_year records which PDF report this row came from.
        # This is different from the year in awarded_date:
        #   - A competition awarded in 2024 may appear in the 2025 report.
        #   - source_year = "2025" for that row, regardless of awarded_date.
        # This column is essential for Tableau year filters and duplicate analysis.
        df["source_year"] = source_year

        dfs.append(df)

    print()


    # ============================================================
    # STEP 2: CONCATENATE
    # pd.concat with ignore_index resets the row index cleanly.
    # It aligns on column names (not positions) — safe because we
    # already verified all files have identical column names/order.
    # ============================================================
    master = pd.concat(dfs, ignore_index=True)


    # ============================================================
    # STEP 3: POST-MERGE VALIDATIONS
    # ============================================================
    print("  POST-MERGE VALIDATIONS")
    print("  " + "-" * 40)

    # ── Math closure check (BLOCKING) ─────────────────────────────────────────────
    # The total rows in the merged output must equal the sum of all input rows.
    # If this fails, pd.concat dropped or duplicated rows internally — which
    # should never happen with ignore_index=True but is worth asserting anyway.
    actual_total = len(master)
    if actual_total != EXPECTED_TOTAL_ROWS:
        fail(
            f"Row count math closure failed:\n"
            f"  Sum of input files: {EXPECTED_TOTAL_ROWS:,}\n"
            f"  Merged output rows: {actual_total:,}\n"
            f"  Delta: {actual_total - EXPECTED_TOTAL_ROWS:+,}"
        )
    print(f"  ✓ Row count closure: {actual_total:,} rows  "
          f"(516 + 527 + 910 + 185 = {EXPECTED_TOTAL_ROWS:,})")


    # ── is_awarded domain check (BLOCKING) ────────────────────────────────────────
    # After merge, every is_awarded value must be either "Yes" or "No".
    # Any other value means a year's extraction script failed to normalize
    # its awarded values (e.g., 2026 Y/N not converted, blank value slipped through).
    # Blocking because this column drives every downstream financial calculation.
    invalid_awarded = master[
        ~master["is_awarded"].isin(VALID_IS_AWARDED_VALUES)
    ]
    if len(invalid_awarded) > 0:
        bad_values = invalid_awarded["is_awarded"].value_counts(dropna=False).to_dict()
        fail(
            f"is_awarded contains values outside {VALID_IS_AWARDED_VALUES}:\n"
            f"  Invalid values and counts: {bad_values}\n"
            f"  Check the extraction script for the relevant year."
        )
    print(f"  ✓ is_awarded domain: all values are Yes or No")


    # ── source_year coverage check (BLOCKING) ─────────────────────────────────────
    # Every expected source year must appear at least once.
    # If a year is missing, the file was loaded but empty (row count assertion
    # above would catch 0-row files), or the source_year assignment was skipped.
    expected_years = {"2023", "2024", "2025", "2026"}
    actual_years   = set(master["source_year"].unique())
    missing_years  = expected_years - actual_years
    if missing_years:
        fail(
            f"source_year coverage check failed:\n"
            f"  Missing years: {sorted(missing_years)}\n"
            f"  This should not happen if all input files loaded correctly."
        )
    print(f"  ✓ source_year coverage: all 4 years present")


    # ── is_awarded distribution (informational) ────────────────────────────────────
    # Not a blocking check — ratios can legitimately vary.
    # Printed for human review as a sanity signal.
    awarded_dist = master["is_awarded"].value_counts().to_dict()
    print(f"  ✓ is_awarded distribution: {awarded_dist}")


    # ── Column list confirmation (informational) ───────────────────────────────────
    expected_final_cols = EXPECTED_COLUMNS + ["source_year"]
    actual_final_cols   = list(master.columns)
    if actual_final_cols != expected_final_cols:
        # This would be a bug in this script itself
        fail(
            f"Final column list unexpected:\n"
            f"  Expected: {expected_final_cols}\n"
            f"  Got:      {actual_final_cols}"
        )
    print(f"  ✓ Final columns: {actual_final_cols}")
    print()


    # ============================================================
    # STEP 4: DUPLICATE INVENTORY AUDIT ARTIFACT (non-blocking)
    #
    # What this is: a report of every (competition_number, vendor_name)
    # pair that appears more than once in the merged dataset.
    #
    # Why it's non-blocking: many duplicates are legitimate.
    # Types of duplicates in this dataset:
    #
    #   TYPE A — Same file, same comp+vendor, different dates
    #     Cause: Metro Vancouver re-awards under the same competition
    #     number (framework call-offs, phased projects).
    #     Example: 24-046 CDW Canada Corporation — multiple call-offs
    #     in the same Co-Operative Procurement framework.
    #     Action: none required. These are distinct award events.
    #
    #   TYPE B — Same file, same comp+vendor+date
    #     Cause: may indicate a source-valid repeated vendor under multiple
    #     scopes, a repeated publication in the source report, or an extraction
    #     artifact. Requires source review before classification.
    #     Known source-valid instance: 25-331 (2025 source file), where two
    #     distinct project scopes share the same competition number.
    #     Action: none required for source-verified source-valid records.
    #
    #   TYPE C — Different files, same comp+vendor
    #     Cause: Metro Vancouver published updated award information
    #     in a subsequent year's annual report (e.g., 24-097 appeared
    #     in both the 2024 and 2025 reports with different award amounts).
    #     Action: none required. Different award events.
    #     Note: source_year column distinguishes these in Tableau.
    #
    # This report is saved to data/diagnostics/ for auditor review.
    # It is NOT saved to data/clean/ — it is not part of the analysis dataset.
    # ============================================================
    print("  DUPLICATE INVENTORY (non-blocking audit artifact)")
    print("  " + "-" * 40)

    # Count occurrences of each (competition_number, vendor_name, source_year) triple
    # Using source_year in the key lets us separate TYPE A+B (within same year file)
    # from TYPE C (across year files).
    dup_counts = (
        master
        .groupby(["competition_number", "vendor_name", "source_year"])
        .size()
        .reset_index(name="row_count_in_source")
    )

    # Same-file duplicates: same comp+vendor appearing 2+ times in the same year file
    same_file_dupes = dup_counts[dup_counts["row_count_in_source"] > 1].copy()

    # Cross-file duplicates: same comp+vendor appearing in 2+ different year files
    cross_file = (
        master
        .groupby(["competition_number", "vendor_name"])["source_year"]
        .apply(lambda x: "|".join(sorted(x.unique())))
        .reset_index(name="source_years")
    )
    cross_file_dupes = cross_file[cross_file["source_years"].str.contains("|", regex=False)].copy()

    print(f"  Same-file duplicates (comp+vendor in same year file):  "
          f"{len(same_file_dupes)} groups")
    print(f"  Cross-file duplicates (comp+vendor in 2+ year files):  "
          f"{len(cross_file_dupes)} groups")

    # Flag known source-verified records so reviewers can filter them out.
    # 25-331 is not an active KDQI item; it is preserved here as a documented
    # source-valid repeated competition-number pattern.
    SOURCE_VALID_25331_COMP = "25-331"
    same_file_dupes["review_note"] = same_file_dupes["competition_number"].apply(
        lambda c: "Source-valid: 25-331 multi-scope competition" if c == SOURCE_VALID_25331_COMP else ""
    )

    # Save the duplicate inventory
    same_file_dupes.to_csv(DUPLICATE_REPORT, index=False, encoding="utf-8-sig")
    print(f"  Saved duplicate inventory → {DUPLICATE_REPORT.name}")
    print()

    # Surface 25-331 explicitly so it is visible in every run without
    # misclassifying it as an active data quality issue.
    source_valid_25331_rows = same_file_dupes[
        same_file_dupes["competition_number"] == SOURCE_VALID_25331_COMP
    ]
    if len(source_valid_25331_rows) > 0:
        warn(
            "Source-valid note: Competition 25-331 appears multiple times in the 2025 source file.\n"
            "         Source re-verification confirmed two distinct project scopes under the\n"
            "         same competition number. No merge-time correction is required."
        )
        print()


    # ============================================================
    # STEP 5: SAVE OUTPUT
    # Only reached if all blocking checks passed.
    # ============================================================
    master.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  MERGE COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(master):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  Row count by source year:")
    for year, count in master["source_year"].value_counts().sort_index().items():
        note = "  ← partial year (Jan–Mar only)" if year == "2026" else ""
        print(f"    {year}: {count:>5,} rows{note}")
    print()
    print("  Columns in output:")
    for col in master.columns:
        print(f"    {col}")
    print()
    print("  Next step: step3_clean_data.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

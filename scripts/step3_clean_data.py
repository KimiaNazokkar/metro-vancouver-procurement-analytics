"""
step3_clean_data.py

Clean and classify Metro Vancouver procurement award records.

Purpose:
- Normalize awarded_amount text and detect missing values
- Classify each row's amount_scope based on award structure
- Detect and classify group / framework awards using a
  per-competition, per-source-year decision tree (Cases A–D)
- Derive financial_kpi_eligible and group_award_flag columns
- Parse awarded_amount_numeric for Tableau aggregations
- Run seven blocking post-classification validations
- Save the cleaned dataset to data/clean/

Pipeline position:
step2 merge → THIS SCRIPT → step4 normalize competition types

Input:
  data/clean/step2_merged_procurement_awards.csv

Output:
  data/clean/step3_cleaned_procurement_awards.csv

Source-valid repeated competition note:
  Competition 25-331 appears multiple times in the 2025 source report because
  Metro Vancouver recorded two distinct procurement scopes under the same
  competition number. Source re-verification confirmed this as valid source
  structure rather than an active data quality issue. No correction is required
  in this cleaning step.
"""

import re

import pandas as pd

from shared_utils import CLEAN_DIR


INPUT_PATH  = CLEAN_DIR / "step2_merged_procurement_awards.csv"
OUTPUT_PATH = CLEAN_DIR / "step3_cleaned_procurement_awards.csv"


# ============================================================
# HELPER: AMOUNT PARSER
#
# awarded_amount is the raw string from the PDF — never modified.
# awarded_amount_numeric is a float for Tableau aggregations.
#
# Two formats exist in the raw data:
#   "$ 600,000.00"  (2023 PDF — space after dollar sign)
#   "$600,000"      (2024–2026 PDFs)
# re.sub(r"[\$,\s]", "", s) handles both in one pass.
# ============================================================
def parse_amount(raw_value) -> "float | None":
    if pd.isna(raw_value):
        return None
    stripped = str(raw_value).strip()
    if not stripped:
        return None
    cleaned = re.sub(r"[\$,\s]", "", stripped)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


# ============================================================
# MAIN
# ============================================================
def main():

    print()
    print("=" * 60)
    print("  step3_clean_data.py")
    print("=" * 60)
    print()

    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {INPUT_PATH.name}: {len(df):,} rows")
    print()


    # --------------------------------------------------
    # Normalize amount text
    # --------------------------------------------------

    df["awarded_amount"] = (
        df["awarded_amount"]
        .astype("string")
        .str.strip()
    )

    missing_amount = (
        df["awarded_amount"].isna()
        | df["awarded_amount"].isin(["", "NA", "N/A", "nan"])
    )

    df["amount_missing"] = missing_amount

    # --------------------------------------------------
    # Boolean awarded flag for Tableau
    # --------------------------------------------------

    df["is_awarded_flag"] = (
        df["is_awarded"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("YES")
    )

    # --------------------------------------------------
    # Default classification
    # --------------------------------------------------

    df["amount_scope"] = "vendor_specific"


    # --------------------------------------------------
    # Step 1: Non-awarded rows
    #
    # is_awarded is the primary decision driver.
    # No rows are classified here and never touched again.
    # They play no role in framework detection below.
    # --------------------------------------------------

    df.loc[df["is_awarded"] == "No", "amount_scope"] = "not_awarded"


    # --------------------------------------------------
    # Step 2: Framework / group award detection
    #
    # DECISION ORDER (applied per competition_number + source_year):
    #
    #   Only Yes rows are examined. No rows play no role.
    #
    #   yes_count         = number of Yes rows in this group
    #   yes_amount_count  = number of Yes rows with a non-missing amount
    #
    #   Case A — yes_count == 1
    #     → Sole awarded vendor. vendor_specific (default, no change).
    #
    #   Case B — yes_count > 1 AND yes_amount_count == 1
    #     → Group / shared award (merged-cell PDF pattern or true framework).
    #     → Yes row with amount    : group_framework_anchor
    #     → Yes rows without amount: group_framework_member
    #
    #   Case C — yes_count > 1 AND yes_amount_count > 1
    #     → Parallel vendor-specific awards. Each winner has their own amount.
    #     → Yes rows with amounts  : vendor_specific (already the default)
    #     → Yes rows without amounts: amount_missing_in_parallel_award
    #       Flagged for review. NOT silently treated as framework members.
    #
    #   Case D — yes_count > 1 AND yes_amount_count == 0
    #     → All Yes rows missing amounts. No anchor exists.
    #     → vendor_specific + amount_missing = True (default). No framework assigned.
    #
    # WHY source_year IS IN THE GROUPING KEY
    # ----------------------------------------
    # Competition 24-132 appears in both the 2024 and 2025 annual PDFs.
    # Without source_year: yes_count=4, yes_amount_count=2 → Case C.
    #   This incorrectly treats Brown and Caldwell as amount_missing_in_parallel_award.
    # With source_year: each year is yes_count=2, yes_amount_count=1 → Case B.
    #   Each year's entry is its own group_framework award. Correct.
    # --------------------------------------------------

    if "source_year" not in df.columns:
        raise ValueError(
            "Column 'source_year' not found.\n"
            "Run the hardened step2_merge_datasets.py before this step.\n"
            "It adds source_year before concat to preserve data lineage."
        )

    yes_df = df[df["is_awarded"] == "Yes"].copy()

    group_summary = (
        yes_df
        .groupby(["competition_number", "source_year"])
        .agg(
            yes_count=("is_awarded", "size"),
            yes_amount_count=("amount_missing", lambda x: (~x).sum()),
        )
        .reset_index()
    )

    # Case B: exactly one Yes-row has an amount
    case_b = group_summary[
        (group_summary["yes_count"] > 1)
        & (group_summary["yes_amount_count"] == 1)
    ][["competition_number", "source_year"]]

    case_b_set = set(zip(case_b["competition_number"], case_b["source_year"]))

    # Case C: more than one Yes-row has an amount
    case_c = group_summary[
        (group_summary["yes_count"] > 1)
        & (group_summary["yes_amount_count"] > 1)
    ][["competition_number", "source_year"]]

    case_c_set = set(zip(case_c["competition_number"], case_c["source_year"]))

    # Build membership flags
    df["_group_key"] = list(zip(df["competition_number"], df["source_year"]))

    in_case_b = df["_group_key"].isin(case_b_set)
    in_case_c = df["_group_key"].isin(case_c_set)

    df.drop(columns=["_group_key"], inplace=True)


    # --------------------------------------------------
    # Case B assignments
    # --------------------------------------------------

    df.loc[
        in_case_b & (df["is_awarded"] == "Yes") & (~missing_amount),
        "amount_scope"
    ] = "group_framework_anchor"

    df.loc[
        in_case_b & (df["is_awarded"] == "Yes") & (missing_amount),
        "amount_scope"
    ] = "group_framework_member"


    # --------------------------------------------------
    # Case C: flag Yes rows without amounts for review
    #
    # These are Yes-awarded vendors in competitions where other
    # Yes-vendors each have their own amounts. The blank here is
    # not the merged-cell pattern — it means either the PDF did
    # not publish an amount for this vendor, or pdfplumber missed it.
    # A distinct scope surfaces them in Tableau for manual review.
    # --------------------------------------------------

    df.loc[
        in_case_c & (df["is_awarded"] == "Yes") & (missing_amount),
        "amount_scope"
    ] = "amount_missing_in_parallel_award"


    # --------------------------------------------------
    # Flags
    # --------------------------------------------------

    df["group_award_flag"] = df["amount_scope"].isin([
        "group_framework_member",
        "group_framework_anchor",
    ])

    df["financial_kpi_eligible"] = df["amount_scope"].isin([
        "vendor_specific",
        "group_framework_anchor",
    ])


    # --------------------------------------------------
    # Numeric amount column
    # --------------------------------------------------

    df["awarded_amount_numeric"] = df["awarded_amount"].apply(parse_amount)


    # --------------------------------------------------
    # Post-classification validation (blocking)
    # --------------------------------------------------

    print("  POST-CLASSIFICATION VALIDATIONS")
    print("  " + "-" * 40)

    # V1: No KPI-eligible row may have a null numeric amount
    v1_fail = df[
        (df["financial_kpi_eligible"] == True)
        & (df["awarded_amount_numeric"].isna())
    ]
    if len(v1_fail):
        raise AssertionError(
            f"V1 FAILED: {len(v1_fail)} financial_kpi_eligible rows have null "
            f"numeric amount.\n"
            + v1_fail[["competition_number", "vendor_name",
                       "awarded_amount", "amount_scope"]].to_string()
        )

    # V2: All non-missing amounts must parse to a number
    v2_fail = df[
        (df["amount_missing"] == False)
        & (df["awarded_amount_numeric"].isna())
    ]
    if len(v2_fail):
        raise AssertionError(
            f"V2 FAILED: {len(v2_fail)} non-missing amounts did not parse.\n"
            + v2_fail[["competition_number", "vendor_name", "awarded_amount"]].to_string()
        )

    # V3: Missing amounts must stay null after parsing
    v3_fail = df[
        (df["amount_missing"] == True)
        & (df["awarded_amount_numeric"].notna())
    ]
    if len(v3_fail):
        raise AssertionError(
            f"V3 FAILED: {len(v3_fail)} missing amounts parsed to non-null numeric.\n"
            + v3_fail[["competition_number", "vendor_name", "awarded_amount"]].to_string()
        )

    # V4: All KPI-eligible numeric amounts must be positive
    v4_fail = df[
        (df["financial_kpi_eligible"] == True)
        & (df["awarded_amount_numeric"].notna())
        & (df["awarded_amount_numeric"] <= 0)
    ]
    if len(v4_fail):
        raise AssertionError(
            f"V4 FAILED: {len(v4_fail)} KPI-eligible rows have zero or negative amount.\n"
            + v4_fail[["competition_number", "vendor_name",
                       "awarded_amount_numeric"]].to_string()
        )

    # V5: group_framework_member must never be financial_kpi_eligible
    v5_fail = df[
        (df["amount_scope"] == "group_framework_member")
        & (df["financial_kpi_eligible"] == True)
    ]
    if len(v5_fail):
        raise AssertionError(
            f"V5 FAILED: {len(v5_fail)} group_framework_member rows are "
            f"financial_kpi_eligible.\n"
            + v5_fail[["competition_number", "vendor_name"]].to_string()
        )

    # V6: No Yes row may be classified as not_awarded
    v6_fail = df[
        (df["is_awarded"] == "Yes")
        & (df["amount_scope"] == "not_awarded")
    ]
    if len(v6_fail):
        raise AssertionError(
            f"V6 FAILED: {len(v6_fail)} Yes rows classified as not_awarded.\n"
            + v6_fail[["competition_number", "vendor_name"]].to_string()
        )

    # V7: No No row may have any scope other than not_awarded
    v7_fail = df[
        (df["is_awarded"] == "No")
        & (df["amount_scope"] != "not_awarded")
    ]
    if len(v7_fail):
        raise AssertionError(
            f"V7 FAILED: {len(v7_fail)} No rows have a non-not_awarded scope.\n"
            + v7_fail[["competition_number", "vendor_name", "amount_scope"]].to_string()
        )

    print("  ✓ V1–V7 all blocking validations passed")
    print()


    # --------------------------------------------------
    # Informational output
    # --------------------------------------------------

    kpi_spend = df.loc[df["financial_kpi_eligible"] == True, "awarded_amount_numeric"].sum()
    kpi_count = (df["financial_kpi_eligible"] == True).sum()

    flag_rows = df[df["amount_scope"] == "amount_missing_in_parallel_award"]
    if len(flag_rows):
        print(f"  [INFO] {len(flag_rows)} rows flagged as amount_missing_in_parallel_award")
        print("         Yes-awarded vendors with no amount in a competition where")
        print("         other Yes-vendors each have their own amounts.")
        print("         Verify in source PDF before changing these.")
        print(flag_rows[["competition_number", "source_year", "vendor_name"]].to_string())
        print()


    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  CLEAN COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(df):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  amount_scope distribution:")
    for scope, count in df["amount_scope"].value_counts().items():
        print(f"    {scope:<40} {count:>5,}")
    print()
    print(f"  KPI-eligible spend baseline : ${kpi_spend:,.2f}")
    print(f"  KPI-eligible row count      : {kpi_count:,}")
    print()
    print("  Next step: step4_normalize_competition_types.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

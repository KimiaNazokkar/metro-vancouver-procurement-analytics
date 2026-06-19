"""
step5a_safe_transforms.py

Apply low-risk, source-preserving vendor name transforms.

Purpose:
- Strip leading and trailing whitespace from vendor names
- Collapse internal runs of whitespace to a single space
- Produce vendor_name_clean as a new column for downstream key building
- Audit and report how many unique names changed

Note on Title Case: Title Case normalization was evaluated and excluded.
Applying str.title() would corrupt all-caps legal entities (e.g., "GFL
ENVIRONMENTAL INC." → "Gfl Environmental Inc.") and abbreviations, producing
display names less accurate than the source. Whitespace normalization is the
only safe transform at this stage.

Pipeline position:
step4 normalize competition types → THIS SCRIPT → step5b vendor key build

Input:
  data/clean/step4_normalized_procurement_awards.csv

Output:
  data/clean/step5a_vendor_safe_transforms.csv
"""

import pandas as pd

from shared_utils import CLEAN_DIR


INPUT_PATH  = CLEAN_DIR / "step4_normalized_procurement_awards.csv"
OUTPUT_PATH = CLEAN_DIR / "step5a_vendor_safe_transforms.csv"


# ============================================================
# MAIN
# ============================================================
def main():

    print()
    print("=" * 60)
    print("  step5a_safe_transforms.py")
    print("=" * 60)
    print()

    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {INPUT_PATH.name}: {len(df):,} rows")
    print()

    # --- Safe Transform 1: strip whitespace (belt-and-suspenders) ---
    df["vendor_name_clean"] = df["vendor_name"].str.strip()

    # --- Safe Transform 2: collapse internal double spaces ---
    df["vendor_name_clean"] = df["vendor_name_clean"].str.replace(r"\s+", " ", regex=True)

    # --- Audit: how many unique names did we reduce? ---
    before = df["vendor_name"].nunique()
    after  = df["vendor_name_clean"].nunique()

    print("  SAFE TRANSFORM AUDIT")
    print("  " + "-" * 40)
    print(f"  Unique names BEFORE  : {before:,}")
    print(f"  Unique names AFTER   : {after:,}")
    print(f"  Names collapsed      : {before - after:,}")
    print()

    # --- Show what actually changed ---
    changed = df[df["vendor_name"] != df["vendor_name_clean"]][["vendor_name", "vendor_name_clean"]].drop_duplicates()
    print(f"  Rows where name changed: {len(changed)}")
    print()
    if len(changed) > 0:
        print(changed.head(30).to_string(index=False))
        print()

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  SAFE TRANSFORMS COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(df):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  Next step: step5b_build_vendor_keys.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
step4_normalize_competition_types.py

Standardize competition type values for downstream analytics.

Purpose:
- Read the cleaned Metro Vancouver awards dataset
- Map raw competition_type values to a controlled vocabulary
- Write competition_type_standardized as a new column
- Does NOT modify or normalize vendor names

Pipeline position:
step3 clean → THIS SCRIPT → step5 vendor normalization

Input:
  data/clean/step3_cleaned_procurement_awards.csv

Output:
  data/clean/step4_normalized_procurement_awards.csv
"""

import pandas as pd

from shared_utils import CLEAN_DIR


INPUT_PATH  = CLEAN_DIR / "step3_cleaned_procurement_awards.csv"
OUTPUT_PATH = CLEAN_DIR / "step4_normalized_procurement_awards.csv"

# ============================================================
# COMPETITION TYPE MAP
# Maps preprocessed raw competition_type strings to a controlled vocabulary.
# Unrecognized values pass through unchanged (see standardize_competition_type).
# Defined at module level so both the standardizer and the unmapped diagnostic
# can reference the same controlled vocabulary without duplication.
# ============================================================
COMPETITION_TYPE_MAP = {
    "RFP": "RFP",
    "RFP-MA": "RFP-MA",
    "RFQ": "RFQ",
    "RFSQ": "RFSQ",
    "RFSQR": "RFSQR",
    "RFSO": "RFSO",
    "ITT": "ITT",
    "ITQ": "ITQ",
    "DA": "DA",
    "DA/NOIC": "DA/NOIC",
    "SS/NOIC": "SS/NOIC",
    "NOIC": "NOIC",

    # Cooperative procurement variants
    "COOP": "CO-OPERATIVE PROCUREMENT",
    "CO-OPERATIVEPROCUREMENT": "CO-OPERATIVE PROCUREMENT",
    "CO-OPERATIVE/PROCUREMENT": "CO-OPERATIVE PROCUREMENT",
    "COOPERATIVEPROCUREMENT": "CO-OPERATIVE PROCUREMENT",

    "CSA": "CSA",
    "SRFEOI": "SRFEOI",
}

# ============================================================
# HELPER: COMPETITION TYPE STANDARDIZER
#
# Normalizes raw competition_type strings to a controlled vocabulary.
# Preprocessing: uppercase, strip whitespace, collapse spaces,
# replace underscores with slashes before lookup.
# Unrecognized values pass through unchanged (COMPETITION_TYPE_MAP.get(s, s)).
# ============================================================
def standardize_competition_type(value: str) -> str:
    if pd.isna(value):
        return ""

    s = str(value).upper().strip()
    s = s.replace("_", "/")
    s = s.replace(" ", "")

    return COMPETITION_TYPE_MAP.get(s, s)


# ============================================================
# MAIN
# ============================================================
def main():

    print()
    print("=" * 60)
    print("  step4_normalize_competition_types.py")
    print("=" * 60)
    print()

    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {INPUT_PATH.name}: {len(df):,} rows")
    print()

    df["competition_type_standardized"] = (
        df["competition_type"]
        .apply(standardize_competition_type)
    )

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  STEP 4 STANDARDIZATION COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(df):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  competition_type_standardized distribution:")
    type_counts = (
        df["competition_type_standardized"]
        .value_counts(dropna=False)
        .sort_index()
    )

    for ctype, count in type_counts.items():
        print(f"    {ctype:<30} {count:>5,}")
    known_types = set(COMPETITION_TYPE_MAP.values()) | {""}
    unmapped = df[~df["competition_type_standardized"].isin(known_types)]
    if len(unmapped) > 0:
        print(f"  [WARN] {len(unmapped):,} rows have unrecognized competition_type values:")
        print(unmapped["competition_type"].value_counts(dropna=False).to_string())
    else:
        print("  ✓ All competition_type values mapped to controlled vocabulary")
    print()
    print("  Next step: step5a_safe_transforms.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
    
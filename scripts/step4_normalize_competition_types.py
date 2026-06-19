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
# HELPER: COMPETITION TYPE STANDARDIZER
#
# Normalizes raw competition_type strings to a controlled vocabulary.
# Preprocessing: uppercase, strip whitespace, collapse spaces,
# replace underscores with slashes before lookup.
# Unrecognized values pass through unchanged (mapping.get(s, s)).
# ============================================================
def standardize_competition_type(value: str) -> str:
    if pd.isna(value):
        return ""

    s = str(value).upper().strip()
    s = s.replace("_", "/")
    s = s.replace(" ", "")

    mapping = {
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

    return mapping.get(s, s)


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
    print("  STANDARDIZATION COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(df):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  competition_type_standardized distribution:")
    for ctype, count in df["competition_type_standardized"].value_counts(dropna=False).sort_index().items():
        print(f"    {ctype:<30} {count:>5,}")
    print()
    print("  Next step: step5a_safe_transforms.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
step5g_apply_vendor_lookup.py

Apply the curated vendor lookup table to produce vendor_name_display.

Purpose:
- Rebuild vendor_name_key from raw vendor_name using the frozen key builder
- LEFT JOIN the whitespace-normalized source data to the curated lookup table on vendor_name_key
- Assign vendor_name_display as the canonical display name for each vendor
- Flag REVIEW rows for downstream awareness without suppressing them
- Surface unmapped keys as visible diagnostic signals rather than silent nulls
- Parse awarded_date into a typed datetime field
- Write the vendor-normalized dataset with full diagnostic columns preserved

Architecture:
  1. Load step5a whitespace-normalized source data and curated lookup table
  2. Rebuild vendor_name_key from raw vendor_name (frozen key builder)
  3. LEFT JOIN on vendor_name_key
  4. Assign vendor_name_display from lookup
  5. For REVIEW rows: apply display name but flag for downstream awareness
  6. For unmapped keys: surface as visible fallback, never silently fill
  7. Parse awarded_date into awarded_date_parsed
  8. Write output with full diagnostic columns preserved

Column output:
  vendor_name             — original raw name, frozen and never modified
  vendor_name_key         — normalized key, used only for joining
  vendor_name_display     — curated display label for Tableau
  vendor_merge_confidence — AUTO_HIGH / REVIEW / SINGLE / PROMOTED / NO_MERGE
  vendor_display_source   — how the display name was assigned (lineage column)
  awarded_date_parsed     — typed datetime from awarded_date string
  awarded_date_parse_failed — flag for dates that could not be parsed

Design note — frozen build_key copy:
  build_key() and SUFFIX_MAP are intentionally duplicated from
  step5b_build_vendor_keys.py rather than imported. This ensures that
  vendor_name_key values in this output are stable: if step5b is later
  modified to adjust normalization behavior, step5g will not silently
  produce different keys, which would break the join to the curated lookup
  table and potentially reassign or drop display names without warning.
  The frozen copy is the governance-correct choice at this pipeline stage.

Pipeline position:
step5f assisted curation → THIS SCRIPT → step5h suppress source duplicates

Inputs:
  data/clean/step5a_vendor_safe_transforms.csv   (whitespace-normalized source)
  data/clean/step5f_vendor_lookup_assisted.csv   (curated lookup table)

Output:
  data/clean/step5g_vendor_normalized_procurement_awards.csv
"""

import re

import pandas as pd

from shared_utils import CLEAN_DIR


SOURCE_DATA_PATH = CLEAN_DIR / "step5a_vendor_safe_transforms.csv"
LOOKUP_PATH      = CLEAN_DIR / "step5f_vendor_lookup_assisted.csv"
OUTPUT_PATH      = CLEAN_DIR / "step5g_vendor_normalized_procurement_awards.csv"


# ============================================================
# SUFFIX MAP — frozen alongside build_key
# See design note in module docstring.
# ============================================================
SUFFIX_MAP = [
    (r"\bincorporated\b", ""),
    (r"\blimited\b",      ""),
    (r"\bcorporation\b",  ""),
    (r"\bltd\b",          ""),
    (r"\binc\b",          ""),
    (r"\bcorp\b",         ""),
    (r"\bco\b",           ""),
    (r"\bullc\b",         ""),
    (r"\bllc\b",          ""),
    (r"\bllp\b",          ""),
    (r"\bulc\b",          ""),
    (r"\blp\b",           ""),
]


# ============================================================
# KEY BUILDER — frozen copy of step5b_build_vendor_keys.build_key
#
# This function is intentionally duplicated rather than imported.
# See module docstring for the governance rationale.
# Do not modify this function without also updating the curated
# lookup table, which was built using the step5b version of this logic.
# ============================================================
def build_key(name: str) -> str:
    if pd.isna(name):
        return ""
    key = name.lower().strip()
    key = re.sub(r"\b([a-z])\.([a-z])\.([a-z])\.", r"\1\2\3", key)
    key = re.sub(r"\b([a-z])\.([a-z])\.",           r"\1\2",   key)
    key = re.sub(r"\b([a-z])\.",                    r"\1",     key)
    key = re.sub(r"(?<!\w)([a-z]) ([a-z])(?!\w)",  r"\1\2",   key)
    key = re.sub(r"(?<!\w)([a-z]) ([a-z])(?!\w)",  r"\1\2",   key)
    key = re.sub(r"[^\w\s]", " ", key)
    for pattern, replacement in SUFFIX_MAP:
        key = re.sub(pattern, replacement, key)
    key = re.sub(r"\s+", " ", key).strip()
    return key


# ============================================================
# DISPLAY SOURCE CLASSIFIER
#
# vendor_display_source lineage values:
#   "lookup_high"     — confirmed merge, display from lookup
#   "lookup_review"   — tentative merge, needs verification
#   "lookup_single"   — no merge needed, display from lookup
#   "lookup_promoted" — was REVIEW, now confirmed
#   "lookup_no_merge" — explicitly excluded from merging
#   "unmapped"        — key not found in lookup (error surface)
# ============================================================
def assign_source(row):
    conf = row["vendor_merge_confidence"]

    if pd.isna(conf):
        return "unmapped"

    conf = str(conf).strip().upper().replace(" ", "_")

    if "HIGH" in conf:
        return "lookup_high"

    if conf == "REVIEW":
        return "lookup_review"

    if conf == "SINGLE":
        return "lookup_single"

    if conf == "PROMOTED":
        return "lookup_promoted"

    if conf == "NO_MERGE":
        return "lookup_no_merge"

    return "unmapped"


# ============================================================
# MAIN
# ============================================================
def main():

    print()
    print("=" * 60)
    print("  step5g_apply_vendor_lookup.py")
    print("=" * 60)
    print()

    # --------------------------------------------------
    # 1. Load data
    # --------------------------------------------------
    df     = pd.read_csv(SOURCE_DATA_PATH)
    lookup = pd.read_csv(LOOKUP_PATH)

    print(f"  Loaded {SOURCE_DATA_PATH.name}: {len(df):,} rows")
    print(f"  Loaded {LOOKUP_PATH.name}: {len(lookup):,} groups")
    print()

    # --------------------------------------------------
    # 2. Rebuild vendor_name_key from raw vendor_name
    #    Uses frozen build_key — see module docstring.
    # --------------------------------------------------
    df["vendor_name_key"] = df["vendor_name"].apply(build_key)

    # --------------------------------------------------
    # 3. Prepare lookup — keep only the columns we need
    # --------------------------------------------------
    lookup_clean = lookup[[
        "vendor_name_key",
        "vendor_name_display",
        "merge_confidence",
    ]].copy()

    lookup_clean = lookup_clean.rename(columns={
        "merge_confidence": "vendor_merge_confidence"
    })

    # --------------------------------------------------
    # 4. LEFT JOIN — every row in df gets a lookup attempt
    # --------------------------------------------------
    df = df.merge(lookup_clean, on="vendor_name_key", how="left")

    # --------------------------------------------------
    # 5. Assign vendor_display_source for full lineage tracking
    # --------------------------------------------------
    df["vendor_display_source"] = df.apply(assign_source, axis=1)

    # --------------------------------------------------
    # 6. For truly unmapped rows: display name falls back
    #    to raw vendor_name so dashboard never shows null
    #    BUT the source column exposes it for investigation
    # --------------------------------------------------
    unmapped_mask = df["vendor_display_source"] == "unmapped"
    df.loc[unmapped_mask, "vendor_name_display"] = df.loc[unmapped_mask, "vendor_name"]

    # --------------------------------------------------
    # 6b. Typed analytical fields
    # --------------------------------------------------

    # Parse awarded_date into real datetime
    # First attempt: ISO format (2023)
    parsed_dates = pd.to_datetime(
        df["awarded_date"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    # Second attempt: DD-Mon-YY format (2024–2026)
    fallback_dates = pd.to_datetime(
        df["awarded_date"],
        format="%d-%b-%y",
        errors="coerce"
    )

    # Combine results
    df["awarded_date_parsed"] = parsed_dates.fillna(fallback_dates)

    # Optional QA flag
    df["awarded_date_parse_failed"] = (
        df["awarded_date"].notna()
        & df["awarded_date_parsed"].isna()
    )

    # --------------------------------------------------
    # 7. DIAGNOSTIC SUMMARY
    # --------------------------------------------------
    print("  VENDOR LOOKUP APPLICATION — DIAGNOSTIC SUMMARY")
    print("  " + "-" * 40)
    print()

    source_counts = df["vendor_display_source"].value_counts()
    print("  Rows by display source:")
    for src, cnt in source_counts.items():
        print(f"    {src:<25} {cnt:,}")
    print()

    conf_counts = df["vendor_merge_confidence"].value_counts(dropna=False)
    print("  Rows by merge confidence:")
    for conf, cnt in conf_counts.items():
        print(f"    {str(conf):<25} {cnt:,}")
    print()

    unmapped = df[df["vendor_display_source"] == "unmapped"]
    print(f"  Unmapped keys (review required): {len(unmapped)}")
    if len(unmapped) > 0:
        print()
        print("  UNMAPPED VENDOR NAMES:")
        for name in sorted(unmapped["vendor_name"].unique()):
            print(f"    → {name}")
    print()

    dates_parsed = df["awarded_date_parsed"].notna().sum()
    dates_failed = df["awarded_date_parse_failed"].sum()
    print(f"  Dates parsed successfully : {dates_parsed:,}")
    print(f"  Dates parse failed        : {dates_failed:,}")
    print()

    print("  SAMPLE — display name assignments:")
    print()
    sample_keys = [
        "ja electric", "associated engineering bc", "hatch",
        "wsp canada", "ghd", "aecom canada"
    ]
    for key in sample_keys:
        rows = df[df["vendor_name_key"] == key][
            ["vendor_name", "vendor_name_display", "vendor_merge_confidence"]
        ].drop_duplicates()
        if len(rows):
            print(f"  KEY: {key}")
            for _, r in rows.iterrows():
                print(f"    {r['vendor_name']:<45} → {r['vendor_name_display']}")
            print()

    # --------------------------------------------------
    # 8. Save
    # --------------------------------------------------
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  STEP 5G VENDOR LOOKUP APPLICATION COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(df):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  Next step: step5h_suppress_source_duplicates.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

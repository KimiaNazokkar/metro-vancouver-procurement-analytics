"""
step5b_build_vendor_keys.py

Build deterministic vendor name keys for entity resolution.

Purpose:
- Apply a reproducible six-step normalization pipeline to raw vendor names
- Produce vendor_name_key: a lowercase, suffix-free, punctuation-free
  canonical key used to group name variants into single supplier entities
- Run a blocking test suite verifying key behavior before export
- Audit how many raw names collapse to the same key
- Export a lookup seed file for human-assisted curation in step5f

Design notes:
- SUFFIX_MAP and build_key() are module-level: they are the reusable
  normalization kernel and may be imported by downstream steps.
- The normalization test suite is blocking: if any test fails, the script
  halts before writing output. A corrupted lookup seed would silently
  propagate errors through all downstream vendor normalization.
- The lookup seed schema includes three human-fill columns
  (vendor_name_display, merge_confidence, merge_notes). These are left
  blank intentionally — they are populated during the curation step.

Pipeline position:
step5a safe transforms → THIS SCRIPT → step5f assisted curation

Input:
  data/clean/step5a_vendor_safe_transforms.csv

Output:
  data/clean/step5b_vendor_lookup_seed.csv
"""

import re
import sys

import pandas as pd

from shared_utils import CLEAN_DIR


INPUT_PATH  = CLEAN_DIR / "step5a_vendor_safe_transforms.csv"
OUTPUT_PATH = CLEAN_DIR / "step5b_vendor_lookup_seed.csv"


# ============================================================
# SUFFIX MAP
# Legal entity suffixes removed during key normalization.
# Order does not matter — all are applied via re.sub with \b guards.
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
# MANUAL DISPLAY OVERRIDES
#
# Source-faithful raw vendor names and vendor_name_key values are preserved.
# These overrides affect only public-facing display labels in the lookup seed.
# ============================================================
MANUAL_DISPLAY_OVERRIDES = {
    "waste mangement canada": {
        "vendor_name_display": "Waste Management Canada",
        "merge_confidence": "PROMOTED",
        "merge_notes": (
            "Display spelling corrected for public-facing label; "
            "raw source spelling retained."
        ),
    },
    "halton recycling dba emterra environmental": {
        "vendor_name_display": "Halton Recycling Ltd. dba Emterra Environmental",
        "merge_confidence": "AUTO_HIGH",
        "merge_notes": (
            "Display casing standardized for public-facing label; "
            "raw source capitalization retained."
        ),
    },
}

# ============================================================
# HELPER: VENDOR KEY BUILDER
#
# Six-step deterministic normalization pipeline:
#   Step 1 — lowercase and strip
#   Step 2 — collapse dotted abbreviations (b.c. → bc, j.a. → ja)
#   Step 3 — collapse spaced initials (j a → ja, b c → bc)
#            Repeated twice to catch chains: "j a b" needs two passes
#   Step 4 — remove all remaining punctuation
#   Step 5 — remove legal suffixes (via SUFFIX_MAP)
#   Step 6 — collapse spaces and trim
# ============================================================
def build_key(name: str) -> str:
    if pd.isna(name):
        return ""

    # Step 1 — lowercase and strip
    key = name.lower().strip()

    # Step 2 — collapse dotted abbreviations (b.c. → bc, j.a. → ja)
    key = re.sub(r"\b([a-z])\.([a-z])\.([a-z])\.", r"\1\2\3", key)
    key = re.sub(r"\b([a-z])\.([a-z])\.",           r"\1\2",   key)
    key = re.sub(r"\b([a-z])\.",                    r"\1",     key)

    # Step 3 — collapse spaced initials (j a → ja, b c → bc)
    # Repeated twice to catch chains: "j a b" needs two passes
    key = re.sub(r"(?<!\w)([a-z]) ([a-z])(?!\w)", r"\1\2", key)
    key = re.sub(r"(?<!\w)([a-z]) ([a-z])(?!\w)", r"\1\2", key)

    # Step 4 — remove all remaining punctuation
    key = re.sub(r"[^\w\s]", " ", key)

    # Step 5 — remove legal suffixes
    for pattern, replacement in SUFFIX_MAP:
        key = re.sub(pattern, replacement, key)

    # Step 6 — collapse spaces and trim
    key = re.sub(r"\s+", " ", key).strip()

    return key


# ============================================================
# MAIN
# ============================================================
def main():

    print()
    print("=" * 60)
    print("  step5b_build_vendor_keys.py")
    print("=" * 60)
    print()

    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {INPUT_PATH.name}: {len(df):,} rows")
    print()

    df["vendor_name_key"] = df["vendor_name"].apply(build_key)


    # --------------------------------------------------
    # DIAGNOSTIC 1 — overall key collapse
    # --------------------------------------------------
    before = df["vendor_name"].nunique()
    after  = df["vendor_name_key"].nunique()

    print("  KEY BUILD DIAGNOSTIC")
    print("  " + "-" * 40)
    print(f"  Unique raw names : {before:,}")
    print(f"  Unique keys      : {after:,}")
    print(f"  Keys collapsed   : {before - after:,}")
    print()


    # --------------------------------------------------
    # TEST SUITE — normalization (blocking)
    #
    # This suite must pass before the lookup seed is written.
    # Any regression in build_key() will corrupt downstream
    # vendor normalization. The export is gated on all_passed.
    # --------------------------------------------------
    print("  NORMALIZATION TEST SUITE")
    print("  " + "-" * 40)

    test_cases = [
        # Dotted abbreviation fix
        ("Associated Engineering (B.C.) Ltd.",   "associated engineering bc"),
        ("Associated Engineering (BC) Ltd.",     "associated engineering bc"),
        ("ASSOCIATED ENGINEERING (B.C.) LIMITED","associated engineering bc"),
        # Spaced initials fix
        ("J.A. ELECTRIC INC.",                   "ja electric"),
        ("J A Electric Inc.",                    "ja electric"),
        ("JA Electric Inc.",                     "ja electric"),
        ("J.A. Electric inc",                    "ja electric"),
        # Suffix normalization
        ("GHD LIMITED",                          "ghd"),
        ("GHD Ltd.",                             "ghd"),
        ("Flocor Inc.",                          "flocor"),
        ("Flocor",                               "flocor"),
        # Should NOT collapse (different companies)
        ("BC Hydro",                             "bc hydro"),
        ("BC Transit",                           "bc transit"),
    ]

    all_passed = True
    print(f"  {'Raw name':<45} {'Expected':<30} {'Got':<30} {'Pass?'}")
    print(f"  {'-'*45} {'-'*30} {'-'*30} {'-'*5}")
    for raw, expected in test_cases:
        got = build_key(raw)
        passed = "✓" if got == expected else "✗ FAIL"
        if got != expected:
            all_passed = False
        print(f"  {raw:<45} {expected:<30} {got:<30} {passed}")

    print()

    if not all_passed:
        print("=" * 60)
        print("  TEST SUITE FAILED — export blocked")
        print("=" * 60)
        print("  One or more normalization tests did not produce the")
        print("  expected key. Fix build_key() before re-running.")
        print("  The output file was NOT written.")
        print("=" * 60)
        sys.exit(1)

    print("  ✓ All tests passed")
    print()


    # --------------------------------------------------
    # DIAGNOSTIC 2 — merged groups summary
    # --------------------------------------------------
    grouped = (
        df.groupby("vendor_name_key")["vendor_name"]
        .apply(lambda x: sorted(x.unique()))
        .reset_index()
    )
    multi = grouped[grouped["vendor_name"].apply(len) > 1].copy()
    multi["variant_count"] = multi["vendor_name"].apply(len)
    multi = multi.sort_values("variant_count", ascending=False)

    print("=" * 60)
    print(f"  Keys merging 2+ raw names: {len(multi)}")
    print("=" * 60)
    print()
    for _, row in multi.head(30).iterrows():
        print(f"  KEY: '{row['vendor_name_key']}'")
        for v in row["vendor_name"]:
            print(f"       → {v}")
        print()


    # --------------------------------------------------
    # EXPORT — seed file for lookup table curation
    # --------------------------------------------------
    lookup_seed = (
        grouped
        .assign(variant_count=grouped["vendor_name"].apply(len))
        .sort_values("variant_count", ascending=False)
    )
    lookup_seed["vendor_name_display"] = ""  # human fills this column
    lookup_seed["merge_confidence"]    = ""  # human fills: HIGH / REVIEW / NO
    lookup_seed["merge_notes"]         = ""  # human fills: optional rationale

    # Apply governed manual display overrides.
    # These preserve raw vendor names and keys while correcting only the
    # public-facing display label used downstream.
    for vendor_key, override in MANUAL_DISPLAY_OVERRIDES.items():
        mask = lookup_seed["vendor_name_key"] == vendor_key

        if mask.sum() != 1:
            print("=" * 60)
            print("  MANUAL DISPLAY OVERRIDE FAILED")
            print("=" * 60)
            print(f"  Expected exactly one lookup seed row for key: {vendor_key!r}")
            print(f"  Found: {mask.sum()}")
            print("  Fix MANUAL_DISPLAY_OVERRIDES or the key builder before export.")
            print("=" * 60)
            sys.exit(1)

        lookup_seed.loc[mask, "vendor_name_display"] = override["vendor_name_display"]
        lookup_seed.loc[mask, "merge_confidence"] = override["merge_confidence"]
        lookup_seed.loc[mask, "merge_notes"] = override["merge_notes"]

    lookup_seed["variants_pipe"] = (
        lookup_seed["vendor_name"]
        .apply(lambda x: " | ".join(sorted(x)))
    )

    lookup_seed_export = lookup_seed[[
        "vendor_name_key",
        "vendor_name",
        "variant_count",
        "vendor_name_display",
        "merge_confidence",
        "merge_notes",
        "variants_pipe",
    ]].copy()

    lookup_seed_export.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  STEP 5B KEY BUILD COMPLETE")
    print("=" * 60)
    print(f"  Total rows  : {len(df):,}")
    print(f"  Saved to    : {OUTPUT_PATH}")
    print()
    print("  Next step: step5f_assisted_curation.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

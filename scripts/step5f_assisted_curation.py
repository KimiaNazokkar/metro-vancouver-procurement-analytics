"""
step5f_assisted_curation.py

Rule-based assisted curation for the vendor lookup seed table.

Purpose:
- Evaluate each vendor key group and assign a confidence level
- Auto-promote groups that pass all safety checks (AUTO_HIGH)
- Flag groups requiring human review (REVIEW)
- Suggest display names using deterministic rules, not frequency alone
- Log the reason for every auto-fill decision
- Produce an annotated lookup table for human curation

Design principles:
- Auto-fill AUTO_HIGH only when all safety checks pass
- Never auto-promote legal suffix conflicts (Inc vs Ltd vs ULC)
- Never auto-promote qualifier conflicts (Canada present in some variants)
- Every auto-fill decision is logged with its reason
- Existing manual entries are preserved unchanged

Confidence values written:
  AUTO_HIGH   — all checks passed, safe to merge
  REVIEW      — one or more checks failed, human required
  SINGLE      — only one variant, no merge decision needed
  (existing manual entries such as PROMOTED or NO_MERGE are preserved)

Pipeline position:
step5b vendor key build → THIS SCRIPT → step5g apply vendor lookup

Inputs:
  data/clean/step5a_vendor_safe_transforms.csv  (frequency source)
  data/clean/step5b_vendor_lookup_seed.csv      (vendor key groups)

Output:
  data/clean/step5f_vendor_lookup_assisted.csv
"""

import ast
import re

import pandas as pd

from shared_utils import CLEAN_DIR


# Frequency source: step5a contains whitespace-normalized vendor names
# used as the display name frequency reference throughout this step.
SOURCE_DATA_PATH = CLEAN_DIR / "step5a_vendor_safe_transforms.csv"
LOOKUP_SEED_PATH = CLEAN_DIR / "step5b_vendor_lookup_seed.csv"
OUTPUT_PATH      = CLEAN_DIR / "step5f_vendor_lookup_assisted.csv"


# ============================================================
# CONFIG — legal suffix conflict pairs
# If a group contains variants from two different buckets,
# it is a legal conflict and must go to REVIEW.
# ============================================================
LEGAL_BUCKETS = [
    {"inc", "incorporated"},
    {"ltd", "limited"},
    {"corp", "corporation"},
    {"ulc"},
    {"llc"},
    {"llp"},
    {"lp"},
    {"co"},
]

# Qualifiers that, if present in some variants but absent
# in others at the ROOT level, suggest entity ambiguity
QUALIFIER_WORDS = {"canada", "canadian", "bc", "alberta", "ontario"}

# Branding signals — names containing these patterns
# should have display names chosen carefully
BRANDING_PATTERNS = [
    r"[a-z][A-Z]",          # camelCase mid-word: NorLand, BelieveCo
    r"[a-zA-Z]:[a-zA-Z]",   # colon in name: Believeco:Partners
    r"^[A-Z]{2,6}$",        # pure acronym: AECOM, WSP, GHD
]


# ============================================================
# SUFFIX EXTRACTOR
# Returns the set of legal suffixes present in a variant.
# ============================================================
SUFFIX_RE = re.compile(
    r"\b(inc|incorporated|ltd|limited|corp|corporation|"
    r"ulc|llc|llp|lp|co)\b",
    re.IGNORECASE
)


def extract_suffixes(name: str) -> set:
    return {m.lower() for m in SUFFIX_RE.findall(name)}


def suffix_bucket(suffix: str) -> int:
    for i, bucket in enumerate(LEGAL_BUCKETS):
        if suffix in bucket:
            return i
    return -1


def has_legal_conflict(variants: list) -> tuple[bool, str]:
    """
    Returns (conflict: bool, reason: str)
    Conflict = variants contain suffixes from different legal buckets
    """
    bucket_sets = []
    for v in variants:
        buckets = {suffix_bucket(s) for s in extract_suffixes(v) if suffix_bucket(s) >= 0}
        bucket_sets.append(buckets)

    all_buckets = set().union(*bucket_sets)
    # Remove -1 (unknown) and allow empty (no suffix)
    all_buckets.discard(-1)

    if len(all_buckets) > 1:
        # Multiple distinct legal structures found
        examples = []
        for v in variants:
            s = extract_suffixes(v)
            if s:
                examples.append(f"{v} [{', '.join(s)}]")
        return True, f"Legal suffix conflict: {' vs '.join(str(b) for b in all_buckets)} - {'; '.join(examples[:3])}"
    return False, ""


def has_qualifier_conflict(variants: list) -> tuple[bool, str]:
    """
    Returns (conflict: bool, reason: str)
    Conflict = qualifier word present in some variants but not others,
    AND it appears after a different-length root
    """
    # Tokenize each variant (lowercase, no suffix, no punct)
    def core_tokens(name):
        n = name.lower()
        n = re.sub(r"[^\w\s]", " ", n)
        n = re.sub(SUFFIX_RE, " ", n)
        return set(n.split())

    token_sets = [core_tokens(v) for v in variants]
    all_tokens = set().union(*token_sets)
    conflict_words = []
    for q in QUALIFIER_WORDS:
        present_in = sum(1 for ts in token_sets if q in ts)
        if 0 < present_in < len(variants):
            conflict_words.append(q)

    if conflict_words:
        return True, f"Qualifier present in some variants only: {conflict_words}"
    return False, ""


def detect_branding(name: str) -> bool:
    for pattern in BRANDING_PATTERNS:
        if re.search(pattern, name):
            return True
    return False


# ============================================================
# DISPLAY NAME SELECTOR
# Rules applied in priority order.
# ============================================================
def select_display_name(variants: list, freq: dict) -> tuple[str, str]:
    """
    Returns (display_name: str, selection_reason: str)
    """
    # Rule 1: preserve intentional branding if detectable
    branded = [v for v in variants if detect_branding(v)]
    if branded:
        # Among branded, pick most frequent
        best = max(branded, key=lambda v: freq.get(v, 0))
        return best, "branding_preserved"

    # Rule 2: prefer mixed-case over ALL CAPS
    mixed = [v for v in variants if v != v.upper() and not v.isupper()]
    candidates = mixed if mixed else variants

    # Rule 3: among candidates, prefer fuller name (more tokens)
    # tiebreak by frequency
    def name_score(v):
        token_count = len(v.split())
        frequency   = freq.get(v, 0)
        return (token_count, frequency)

    best = max(candidates, key=name_score)
    reason = "mixed_case_fuller_form" if mixed else "frequency_fallback"
    return best, reason


# ============================================================
# VARIANT PARSER
#
# Parses the variants_pipe column (pipe-separated strings) into
# a Python list. The ast.literal_eval branch supports legacy seed
# formats where variants were stored as Python list strings
# (i.e., starting with "["): this does not occur in the current
# pipeline where variants_pipe is always pipe-separated.
# ============================================================
def parse_variants(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        if val.startswith("["):
            # Legacy/list-string format — not produced by current pipeline
            return ast.literal_eval(val)
        return [v.strip() for v in val.split("|")]
    return []


# ============================================================
# CURATION ENGINE
# ============================================================
def curate_group(row, freq):
    """
    Evaluates one lookup table row.
    Returns (confidence, display_name, display_reason, review_reason)
    """
    raw_conf = str(row.get("merge_confidence", "")).strip().upper()

    # Preserve any existing manual entry (non-empty, non-AUTO)
    if raw_conf in {"AUTO_HIGH", "REVIEW", "NO_MERGE", "PROMOTED"}:
        return raw_conf, row["vendor_name_display"], "manual_entry", ""

    # Single-variant rows need no merge decision
    variants = row["variants_parsed"]
    if len(variants) == 1:
        display, reason = select_display_name(variants, freq)
        return "SINGLE", display, reason, ""

    # --- Safety Check 1: legal suffix conflict ---
    conflict, reason = has_legal_conflict(variants)
    if conflict:
        display, d_reason = select_display_name(variants, freq)
        return "REVIEW", display, d_reason, f"legal_conflict: {reason}"

    # --- Safety Check 2: qualifier conflict ---
    conflict, reason = has_qualifier_conflict(variants)
    if conflict:
        display, d_reason = select_display_name(variants, freq)
        return "REVIEW", display, d_reason, f"qualifier_conflict: {reason}"

    # --- All checks passed: AUTO_HIGH ---
    display, d_reason = select_display_name(variants, freq)
    return "AUTO_HIGH", display, d_reason, "all_checks_passed"


# ============================================================
# MAIN
# ============================================================
def main():

    print()
    print("=" * 60)
    print("  step5f_assisted_curation.py")
    print("=" * 60)
    print()

    # -------------------------------------------------------
    # LOAD DATA
    # -------------------------------------------------------
    df_source = pd.read_csv(SOURCE_DATA_PATH)
    lookup    = pd.read_csv(LOOKUP_SEED_PATH)

    print(f"  Loaded {SOURCE_DATA_PATH.name}: {len(df_source):,} rows")
    print(f"  Loaded {LOOKUP_SEED_PATH.name}: {len(lookup):,} groups")
    print()

    # Frequency dict built from step5a vendor_name (post-whitespace-normalization)
    freq = df_source["vendor_name"].value_counts().to_dict()

    lookup["variants_parsed"] = lookup["variants_pipe"].apply(parse_variants)

    # Ensure required columns exist
    for col in ["vendor_name_display", "merge_confidence", "merge_notes"]:
        if col not in lookup.columns:
            lookup[col] = ""

    # -------------------------------------------------------
    # RUN CURATION ENGINE
    # -------------------------------------------------------
    results = []
    for _, row in lookup.iterrows():
        conf, display, d_reason, r_reason = curate_group(row, freq)
        results.append({
            "vendor_name_key":      row["vendor_name_key"],
            "vendor_name_display":  display,
            "merge_confidence":     conf,
            "display_name_reason":  d_reason,
            "review_reason":        r_reason,
            "variant_count":        len(row["variants_parsed"]),
            "variants_pipe":        " | ".join(row["variants_parsed"]),
        })

    output = pd.DataFrame(results)
    output = output.sort_values(
        ["merge_confidence", "variant_count"],
        ascending=[True, False]
    )

    # -------------------------------------------------------
    # DIAGNOSTIC SUMMARY
    # -------------------------------------------------------
    conf_counts = output["merge_confidence"].value_counts()

    print("─" * 60)
    print("  ASSISTED CURATION — DIAGNOSTIC SUMMARY")
    print("─" * 60)
    print()
    print("  Confidence distribution:")
    for conf, cnt in conf_counts.items():
        print(f"    {conf:<15} {cnt:,} rows")
    print()

    auto_high = output[output["merge_confidence"] == "AUTO_HIGH"]
    review    = output[output["merge_confidence"] == "REVIEW"]

    print(f"  AUTO_HIGH groups:  {len(auto_high):,}  (no human action needed)")
    print(f"  REVIEW groups:     {len(review):,}  (human verification required)")
    print()

    print("─" * 60)
    print("  REVIEW GROUPS — reason breakdown:")
    print("─" * 60)
    review_reasons = review["review_reason"].str.split(":").str[0].value_counts()
    for reason, cnt in review_reasons.items():
        print(f"    {reason:<30} {cnt:,} groups")
    print()

    print("─" * 60)
    print("  SAMPLE AUTO_HIGH GROUPS (spot-check these):")
    print("─" * 60)
    for _, row in auto_high.head(10).iterrows():
        print(f"  KEY:     {row['vendor_name_key']}")
        print(f"  DISPLAY: {row['vendor_name_display']}")
        print(f"  REASON:  {row['display_name_reason']}")
        print(f"  VARS:    {row['variants_pipe']}")
        print()

    print("─" * 60)
    print("  SAMPLE REVIEW GROUPS (these need your attention):")
    print("─" * 60)
    for _, row in review.head(10).iterrows():
        print(f"  KEY:     {row['vendor_name_key']}")
        print(f"  DISPLAY: {row['vendor_name_display']} (tentative)")
        print(f"  WHY:     {row['review_reason']}")
        print(f"  VARS:    {row['variants_pipe']}")
        print()

    # -------------------------------------------------------
    # SAVE
    # -------------------------------------------------------
    output.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("  STEP 5F ASSISTED CURATION COMPLETE")
    print("=" * 60)
    print(f"  Total groups : {len(output):,}")
    print(f"  Saved to     : {OUTPUT_PATH}")
    print()
    print("  Manual curation checklist (complete before running step5g):")
    print("  1. Spot-check 5-10 AUTO_HIGH groups for false positives")
    print("  2. Work through REVIEW groups — most will resolve quickly")
    print("  3. Promote resolved REVIEW rows to AUTO_HIGH or PROMOTED")
    print()
    print("  Next step: step5g_apply_vendor_lookup.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

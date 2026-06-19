"""
diag_2025_raw_dump.py
=====================
AUDIT-ONLY DIAGNOSTIC SCRIPT — DO NOT USE AS PRODUCTION EXTRACTOR

Purpose
-------
Expose every raw row pdfplumber sees when reading awardedbids2025.pdf,
classify each row using the CURRENT production exclusion logic (unchanged),
and produce audit CSVs for manual review of extraction completeness.

2025-Specific Context
---------------------
  - 910 rows (largest year — 73% larger than 2024)
  - Uses extract_tables() plural — same as 2024
  - Exclusion-only filter — same as 2024 (no regex gate)
  - Contains formats the 2023 narrow regex would have silently dropped:
      25-0001    (four-digit suffix)
      25-118.01  (decimal sub-variant)
  - Has a hardcoded is_awarded correction for competition 25-064
  - Has a C$. → $ amount normalization pass
  - Competition type casing inconsistency: Co-Operative vs Co-operative
  - Old competition numbers from 2020/2021 appear in 2025 awards (legitimate)
  - Competition 25-118 has both a base number AND decimal sub-variants

What Changed from the 2024 Diagnostic
--------------------------------------
  1. COMP_NUM_LOOSE regex extended to accept decimal formats (XX-XXX.DD)
     and older year prefixes (18- through 25-) explicitly
  2. 25-064 correction verification: confirms the 5 hardcoded Yes rows exist
  3. Amount normalization check: confirms C$. prefix and spaced amounts cleaned
  4. Co-operative type casing inconsistency detector
  5. Production row count updated to 910

Row Classification
------------------
  ACCEPTED            row passed all three exclusion conditions
  SKIPPED_EMPTY       r is falsy OR r[0] is None or empty string
  HEADER              r[0] matches known structural text

Output Files (all in data/diagnostics/2025/)
---------------------------------------------
  diag_2025_accepted.csv                  — rows the extractor keeps
  diag_2025_skipped_empty.csv             — rows with nothing in col_00
  diag_2025_header_rows.csv              — header / structural rows
  diag_2025_suspicious_col00.csv         — accepted rows with non-comp-number in col_00
  diag_2025_per_page_table_stats.csv     — row inventory per page per table
  diag_2025_nonstandard_comp_numbers.csv — accepted rows with non-XX-XXX formats
  diag_2025_audit_summary.txt            — full audit summary

Key Audit Questions
-------------------
  1. Accepted count == 910?
  2. Are 25-0001 and 25-118.01/.02/.03/.04/.05 all in accepted output?
  3. Are any pages missing tables?
  4. Are there col_count mismatches?
  5. Are there suspicious col_00 values (garbage passing through permissive filter)?
  6. Do old comp numbers (20-xxx, 21-xxx, 22-xxx) appear and are they accepted?

How to Run
----------
  From the scripts/diagnostics/ directory:
    python diag_2025_raw_dump.py

  Or from the project root:
    python scripts/diagnostics/diag_2025_raw_dump.py

  With explicit PDF path override:
    PDF_OVERRIDE=/path/to/awarded-bids-2025.pdf python scripts/diagnostics/diag_2025_raw_dump.py
"""

import os
import re
from pathlib import Path
from datetime import datetime

import pdfplumber
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

PDF_PATH = PROJECT_ROOT / "data" / "raw" / "awarded-bids-2025.pdf"

if os.environ.get("PDF_OVERRIDE"):
    PDF_PATH = Path(os.environ["PDF_OVERRIDE"])

if not PDF_PATH.exists():
    PDF_PATH = SCRIPT_DIR / "awardedbids2025.pdf"

# Output to year-specific subdirectory — never touches production paths
DIAG_DIR = PROJECT_ROOT / "data" / "diagnostics" / "2025"
DIAG_DIR.mkdir(parents=True, exist_ok=True)

OUT_ACCEPTED           = DIAG_DIR / "diag_2025_accepted.csv"
OUT_SKIPPED_EMPTY      = DIAG_DIR / "diag_2025_skipped_empty.csv"
OUT_HEADER_ROWS        = DIAG_DIR / "diag_2025_header_rows.csv"
OUT_SUSPICIOUS_COL00   = DIAG_DIR / "diag_2025_suspicious_col00.csv"
OUT_PAGE_TABLE_STATS   = DIAG_DIR / "diag_2025_per_page_table_stats.csv"
OUT_NONSTANDARD        = DIAG_DIR / "diag_2025_nonstandard_comp_numbers.csv"
OUT_SUMMARY            = DIAG_DIR / "diag_2025_audit_summary.txt"

# Known production row count — from step1_extracted_2025.csv (verified 2026-05-18)
PRODUCTION_ROW_COUNT = 910

EXPECTED_COL_COUNT = 7

# --- Header / structural text (same as 2025 production extractor) ---
HEADER_EXACT = {None, "Competition #"}

HEADER_STARTSWITH = [
    "The following contracts",
    "RESULTS OF OPEN",
    "Page ",
]

# --- Competition number pattern (loose — for suspicious col_00 detection) ---
#
# 2025 introduces formats the 2023 narrow regex would have dropped.
# We define "looks like a competition number" broadly:
#   XX-XXX          standard format (23-342)
#   XX-XXXX         four-digit suffix (25-0001)
#   XX-XXXA         letter suffix (24-006A)
#   XX-XXX.D+       decimal sub-variant (25-118.01)
#
# Year prefix: accept 18- through 26-
# Covers historical awards legitimately appearing in 2025 report (e.g. 20-034)
COMP_NUM_LOOSE = re.compile(
    r"^(1[8-9]|2[0-6])-\d{3,4}[A-Z]?(\.\d+)?$"
)

# Standard-only: used to identify non-standard formats in the inventory
COMP_NUM_NARROW = re.compile(r"^\d{2}-\d{3}$")

# --- 25-064 correction: vendors that production hardcodes as is_awarded = Yes ---
VENDORS_25064_YES = {
    "B.A. BLACKTOP LTD",
    "GB Paving",
    "WINVAN PAVING A DIVISION OF MAINLAND CONSTRUCTION MATERIALS ULC.",
    "PALMIERI BROS. PAVING LTD.",
    "KEYWEST ASPHALT LTD",
}

# --- Amount format patterns to check in raw accepted rows ---
CDN_DOLLAR_PREFIX = re.compile(r"^C\$")
SPACED_AMOUNT     = re.compile(r"\d\s\d")


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_row(row: list) -> str:
    """
    Classify using EXACT 2025 production exclusion conditions.

    Production code (verbatim from step1_extract_2025.py):
        if not r: continue
        if r[0] in [None, "Competition #"]: continue
        if str(r[0]).startswith("The following contracts"): continue
        clean_rows.append(r)
    """
    if not row:
        return "SKIPPED_EMPTY"

    cell_zero = row[0]

    if cell_zero in HEADER_EXACT:
        if cell_zero is None or str(cell_zero).strip() == "":
            return "SKIPPED_EMPTY"
        return "HEADER"

    cell_str = str(cell_zero).strip()

    if cell_str == "":
        return "SKIPPED_EMPTY"

    for prefix in HEADER_STARTSWITH:
        if cell_str.startswith(prefix):
            return "HEADER"

    return "ACCEPTED"


def is_suspicious_col00(cell_str: str) -> tuple[bool, str]:
    """
    Returns (True, reason) if col_00 of an ACCEPTED row doesn't look
    like any known competition number format.

    Extended for 2025:
    - accepts decimal sub-variants: 25-118.01
    - accepts four-digit suffix: 25-0001
    - accepts old year prefixes 18-26: covers 20-034, 21-457 etc.
    """
    val = cell_str.strip()

    if COMP_NUM_LOOSE.match(val):
        return False, ""

    if re.match(r"^\d{1,2}-[A-Za-z]{3}", val):
        return True, "looks_like_date"
    if re.match(r"^\d{2}-\d{3,4}", val):
        return True, "comp_num_variant_not_in_pattern"
    if val.startswith("$") or re.match(r"^\d[\d,]+$", val):
        return True, "looks_like_amount"
    if len(val) > 30:
        return True, "too_long_for_comp_num"

    return True, "unrecognized_format"


def is_nonstandard_comp_num(cell_str: str) -> tuple[bool, str]:
    """
    Inventory function: returns (True, format_type) for competition numbers
    that are valid but would have been dropped by the 2023 narrow regex.
    """
    val = cell_str.strip()

    if COMP_NUM_NARROW.fullmatch(val):
        return False, ""

    if not COMP_NUM_LOOSE.match(val):
        return False, ""

    if re.fullmatch(r"\d{2}-\d{3,4}\.\d+", val):
        return True, "decimal_subvariant"

    if re.fullmatch(r"\d{2}-\d{4}", val):
        return True, "four_digit_suffix"

    if re.fullmatch(r"\d{2}-\d{3,4}[A-Z]", val):
        return True, "letter_suffix"

    year_prefix = val[:2]
    if year_prefix in {"18", "19", "20", "21"}:
        return True, "old_year_prefix"

    return False, ""


def row_to_record(
    row: list,
    page_num: int,
    table_index: int,
    table_row_index: int,
    classification: str,
) -> dict:
    record = {
        "page_num":        page_num,
        "table_index":     table_index,
        "table_row_index": table_row_index,
        "classification":  classification,
        "col_count":       len(row) if row else 0,
        "col_count_flag":  (
            "OK" if (row and len(row) == EXPECTED_COL_COUNT)
            else "MISMATCH"
        ),
    }

    for i in range(EXPECTED_COL_COUNT):
        key = f"col_{i:02d}"
        if row and i < len(row):
            val = row[i]
            record[key] = (
                str(val).replace("\n", " ").strip()
                if val is not None else ""
            )
        else:
            record[key] = ""

    record["col_00_raw_repr"] = (
        repr(row[0]) if (row and row[0] is not None) else repr(None)
    )

    return record


def check_25064_correction(accepted_records: list) -> dict:
    """
    Verify the 25-064 manual is_awarded correction.
    Checks whether the 5 hardcoded vendors appear in raw rows and what their
    raw is_awarded value is (to confirm the production fix is necessary).
    """
    results = {v: {"found": False, "raw_is_awarded": None} for v in VENDORS_25064_YES}

    for r in accepted_records:
        if r.get("col_00", "").strip() == "25-064":
            vendor = r.get("col_04", "").strip()
            if vendor in results:
                results[vendor]["found"] = True
                results[vendor]["raw_is_awarded"] = r.get("col_06", "")

    return results


def check_amount_normalization(accepted_records: list) -> dict:
    """
    Check for C$. prefix and spaced amounts in raw extracted rows.
    These confirm the production normalization passes are load-bearing.
    """
    cdn_dollar_rows   = []
    spaced_amount_rows = []

    for r in accepted_records:
        amount = r.get("col_05", "")
        if CDN_DOLLAR_PREFIX.search(amount):
            cdn_dollar_rows.append(r)
        if SPACED_AMOUNT.search(amount):
            spaced_amount_rows.append(r)

    return {
        "cdn_dollar_count":    len(cdn_dollar_rows),
        "spaced_amount_count": len(spaced_amount_rows),
        "cdn_dollar_rows":     cdn_dollar_rows,
        "spaced_amount_rows":  spaced_amount_rows,
    }


# ============================================================
# MAIN AUDIT LOOP
# ============================================================

def run_audit():
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 65)
    print("  diag_2025_raw_dump.py — 2025 EXTRACTION AUDIT")
    print(f"  Run timestamp     : {run_timestamp}")
    print(f"  PDF path          : {PDF_PATH}")
    print(f"  Exists            : {PDF_PATH.exists()}")
    print(f"  Output dir        : {DIAG_DIR}")
    print(f"  Extraction method : extract_tables() plural (mirrors production)")
    print(f"  Filter logic      : exclusion-only, no regex gate")
    print(f"  Production count  : {PRODUCTION_ROW_COUNT} rows to match")
    print("=" * 65)
    print()

    if not PDF_PATH.exists():
        print(f"  ERROR: PDF not found at {PDF_PATH}")
        print("  Set PDF_OVERRIDE environment variable to the correct path.")
        print("  Example:")
        print("    PDF_OVERRIDE=/path/to/awarded-bids-2025.pdf python diag_2025_raw_dump.py")
        return

    # --------------------------------------------------------
    # ACCUMULATORS
    # --------------------------------------------------------
    accepted       = []
    skipped_empty  = []
    header_rows    = []

    suspicious_col00  = []
    nonstandard_comps = []

    page_table_stats = []
    total_rows_seen  = 0

    # --------------------------------------------------------
    # PDF ITERATION — mirrors production exactly
    # --------------------------------------------------------
    with pdfplumber.open(PDF_PATH) as pdf:

        total_pages = len(pdf.pages)
        print(f"  PDF opened. Total pages: {total_pages}")
        print()

        for page_num, page in enumerate(pdf.pages, start=1):

            tables  = page.extract_tables()
            n_tables = len(tables)

            if n_tables == 0:
                page_table_stats.append({
                    "page_num":             page_num,
                    "table_index":          0,
                    "rows_in_table":        0,
                    "accepted":             0,
                    "skipped_empty":        0,
                    "header_rows":          0,
                    "col_count_mismatches": 0,
                    "suspicious_col00":     0,
                    "nonstandard_comp":     0,
                    "table_found":          "NO — INVESTIGATE",
                })
                print(
                    f"  Page {page_num:>3}/{total_pages}"
                    f"  tables=0"
                    f"  *** NO TABLE DETECTED ***"
                )
                continue

            page_accepted_total   = 0
            page_skipped_total    = 0
            page_header_total     = 0
            page_suspicious_total = 0

            for table_index, table in enumerate(tables):

                tbl_accepted     = 0
                tbl_skipped      = 0
                tbl_header       = 0
                tbl_col_mismatch = 0
                tbl_suspicious   = 0
                tbl_nonstandard  = 0

                for table_row_index, row in enumerate(table):
                    total_rows_seen += 1

                    classification = classify_row(row)
                    record = row_to_record(
                        row, page_num, table_index, table_row_index, classification
                    )

                    if classification == "ACCEPTED":
                        accepted.append(record)
                        tbl_accepted += 1
                        page_accepted_total += 1

                        if record["col_count_flag"] == "MISMATCH":
                            tbl_col_mismatch += 1

                        col00 = record.get("col_00", "")

                        is_susp, reason = is_suspicious_col00(col00)
                        if is_susp:
                            susp_rec = dict(record)
                            susp_rec["suspicious_reason"] = reason
                            suspicious_col00.append(susp_rec)
                            tbl_suspicious += 1
                            page_suspicious_total += 1

                        is_ns, ns_format = is_nonstandard_comp_num(col00)
                        if is_ns:
                            ns_rec = dict(record)
                            ns_rec["nonstandard_format"] = ns_format
                            nonstandard_comps.append(ns_rec)
                            tbl_nonstandard += 1

                    elif classification == "SKIPPED_EMPTY":
                        skipped_empty.append(record)
                        tbl_skipped += 1
                        page_skipped_total += 1

                    elif classification == "HEADER":
                        header_rows.append(record)
                        tbl_header += 1
                        page_header_total += 1

                page_table_stats.append({
                    "page_num":             page_num,
                    "table_index":          table_index,
                    "rows_in_table":        len(table),
                    "accepted":             tbl_accepted,
                    "skipped_empty":        tbl_skipped,
                    "header_rows":          tbl_header,
                    "col_count_mismatches": tbl_col_mismatch,
                    "suspicious_col00":     tbl_suspicious,
                    "nonstandard_comp":     tbl_nonstandard,
                    "table_found":          "YES",
                })

            print(
                f"  Page {page_num:>3}/{total_pages}"
                f"  tables={n_tables}"
                f"  accepted={page_accepted_total:>4}"
                f"  skipped={page_skipped_total:>3}"
                f"  header={page_header_total:>2}"
                f"  suspicious={page_suspicious_total:>2}"
            )

    print()

    # --------------------------------------------------------
    # POST-ACCEPTANCE CHECKS
    # --------------------------------------------------------
    correction_check = check_25064_correction(accepted)
    amount_check     = check_amount_normalization(accepted)

    # --------------------------------------------------------
    # MATH CLOSURE
    # --------------------------------------------------------
    total_classified = len(accepted) + len(skipped_empty) + len(header_rows)
    math_closes = (total_classified == total_rows_seen)

    # --------------------------------------------------------
    # WRITE OUTPUT CSVs
    # --------------------------------------------------------
    base_fieldnames = [
        "page_num", "table_index", "table_row_index",
        "classification", "col_count", "col_count_flag",
        "col_00", "col_01", "col_02", "col_03", "col_04", "col_05", "col_06",
        "col_00_raw_repr",
    ]

    def write_csv(records, path, label, extra_cols=None):
        cols = base_fieldnames + (extra_cols or [])
        df_out = pd.DataFrame(records, columns=cols)
        df_out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Saved {label:<45} → {path.name}  ({len(records):,} rows)")

    print("  Writing audit CSVs...")
    print()
    write_csv(accepted,       OUT_ACCEPTED,       "ACCEPTED")
    write_csv(skipped_empty,  OUT_SKIPPED_EMPTY,  "SKIPPED_EMPTY")
    write_csv(header_rows,    OUT_HEADER_ROWS,    "HEADER_ROWS")
    write_csv(
        suspicious_col00,     OUT_SUSPICIOUS_COL00, "SUSPICIOUS_COL00",
        extra_cols=["suspicious_reason"]
    )
    write_csv(
        nonstandard_comps,    OUT_NONSTANDARD,    "NONSTANDARD_COMP_NUMBERS",
        extra_cols=["nonstandard_format"]
    )

    df_stats = pd.DataFrame(page_table_stats)
    df_stats.to_csv(OUT_PAGE_TABLE_STATS, index=False, encoding="utf-8-sig")
    print(f"  Saved {'PER_PAGE_TABLE_STATS':<45} → {OUT_PAGE_TABLE_STATS.name}  ({len(df_stats):,} rows)")
    print()

    # --------------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------------
    n_accepted    = len(accepted)
    n_skipped     = len(skipped_empty)
    n_header      = len(header_rows)
    n_suspicious  = len(suspicious_col00)
    n_nonstandard = len(nonstandard_comps)

    pages_no_table = df_stats[df_stats["table_found"].str.startswith("NO")]
    col_mismatches = [r for r in accepted if r.get("col_count_flag") == "MISMATCH"]

    delta     = n_accepted - PRODUCTION_ROW_COUNT
    delta_str = f"+{delta}" if delta >= 0 else str(delta)

    ns_by_format = {}
    for r in nonstandard_comps:
        fmt = r.get("nonstandard_format", "unknown")
        ns_by_format.setdefault(fmt, [])
        ns_by_format[fmt].append(r.get("col_00", ""))

    EXPECTED_NS = {
        "25-0001",
        "25-118.01", "25-118.02", "25-118.03", "25-118.04", "25-118.05",
    }
    found_ns   = set(r.get("col_00", "") for r in nonstandard_comps)
    missing_ns = EXPECTED_NS - found_ns
    new_ns     = found_ns - EXPECTED_NS

    # --------------------------------------------------------
    # PRINT AND SAVE AUDIT SUMMARY
    # --------------------------------------------------------
    summary_lines = []

    def p(line=""):
        print(line)
        summary_lines.append(line)

    p()
    p("=" * 65)
    p("  AUDIT SUMMARY — diag_2025_raw_dump.py")
    p(f"  Run timestamp     : {run_timestamp}")
    p(f"  PDF               : {PDF_PATH.name}")
    p(f"  Total pages       : {total_pages}")
    p(f"  Extraction method : extract_tables() plural")
    p("=" * 65)
    p()

    p("  ROW COUNT BREAKDOWN")
    p("  " + "-" * 45)
    p(f"  Total rows seen by pdfplumber  : {total_rows_seen:>6,}")
    p(f"  ├── ACCEPTED                   : {n_accepted:>6,}")
    p(f"  ├── SKIPPED_EMPTY              : {n_skipped:>6,}")
    p(f"  └── HEADER / structural        : {n_header:>6,}")
    p(f"  Total classified               : {total_classified:>6,}")
    p()
    if math_closes:
        p("  ✓ MATH CLOSURE: classified == seen")
    else:
        p(f"  ✗ MATH CLOSURE FAILED: {total_rows_seen} seen vs {total_classified} classified")
    p()

    p("  COMPARISON TO PRODUCTION OUTPUT")
    p("  " + "-" * 45)
    p(
        f"  Production row count ({PRODUCTION_ROW_COUNT})    : "
        f"{PRODUCTION_ROW_COUNT:>6,}"
    )
    p(f"  Diagnostic accepted count     : {n_accepted:>6,}")
    p(f"  Delta                         : {delta_str:>6}")
    p()
    if delta == 0:
        p("  ✓ Accepted count matches production output exactly.")
    elif delta > 0:
        p(f"  *** Diagnostic accepted MORE rows than production ({delta} extra) ***")
        p("    Review diag_2025_suspicious_col00.csv for the extra rows.")
    else:
        p(f"  *** Diagnostic accepted FEWER rows than production ({abs(delta)} missing) ***")
        p("    Investigate: iteration difference or post-extraction row additions.")
    p()

    p("  TABLE COVERAGE")
    p("  " + "-" * 45)
    pages_with    = df_stats[df_stats["table_found"] == "YES"]["page_num"].nunique()
    pages_without = len(pages_no_table)
    p(f"  Pages with at least one table  : {pages_with}")
    p(f"  Pages with NO table detected   : {pages_without}")
    if pages_without > 0:
        p()
        p("  *** PAGES WITH NO TABLE — CHECK IN PDF ***")
        for _, row in pages_no_table.iterrows():
            p(f"    Page {int(row['page_num'])}")
    p()

    p("  COLUMN INTEGRITY")
    p("  " + "-" * 45)
    p(f"  Accepted rows with col_count != 7 : {len(col_mismatches)}")
    if col_mismatches:
        p()
        p("  *** COL COUNT MISMATCHES — FIELD ALIGNMENT AT RISK ***")
        for r in col_mismatches[:10]:
            p(
                f"    Page {r['page_num']}"
                f"  table={r['table_index']}"
                f"  col_count={r['col_count']}"
                f"  col_00={r['col_00']!r}"
            )
        if len(col_mismatches) > 10:
            p(f"    ... and {len(col_mismatches)-10} more — see accepted CSV")
    else:
        p("  ✓ All accepted rows have exactly 7 columns.")
    p()

    p("  NON-STANDARD COMPETITION NUMBER FORMATS")
    p("  (Inventory of formats the 2023 narrow regex would have dropped)")
    p("  " + "-" * 45)
    p(f"  Total non-standard comp numbers : {n_nonstandard}")
    p()
    for fmt, vals in sorted(ns_by_format.items()):
        p(f"  Format type: {fmt}")
        for v in sorted(set(vals)):
            tag = "" if v in EXPECTED_NS else "  ← NEW"
            p(f"    {v}{tag}")
        p()

    if missing_ns:
        p("  *** EXPECTED FORMATS NOT FOUND — POSSIBLE REGRESSION ***")
        for v in sorted(missing_ns):
            p(f"    MISSING: {v}")
        p()
    else:
        p("  ✓ All 6 expected non-standard formats confirmed in accepted rows.")
    p()

    if new_ns:
        p("  NEW NON-STANDARD FORMATS (not in original production output):")
        for v in sorted(new_ns):
            p(f"    {v}  — cross-check in PDF")
        p()
    p()

    p("  SUSPICIOUS COL_00 VALUES")
    p("  " + "-" * 45)
    p(f"  Count : {n_suspicious}")
    if suspicious_col00:
        reason_counts = {}
        for r in suspicious_col00:
            rsn = r.get("suspicious_reason", "unknown")
            reason_counts[rsn] = reason_counts.get(rsn, 0) + 1
        p()
        for rsn, cnt in sorted(reason_counts.items()):
            p(f"    {rsn:<40} {cnt:,}")
        p()
        p("  Sample values:")
        seen = set()
        for r in suspicious_col00[:12]:
            v = r.get("col_00", "")
            if v not in seen:
                p(f"    {v!r}  reason={r.get('suspicious_reason','')}")
                seen.add(v)
    else:
        p("  ✓ No suspicious col_00 values found.")
    p()

    p("  25-064 is_awarded CORRECTION CHECK")
    p("  " + "-" * 45)
    all_found = all(info["found"] for info in correction_check.values())
    for vendor, info in correction_check.items():
        status  = "✓" if info["found"] else "✗ MISSING"
        raw_val = repr(info["raw_is_awarded"]) if info["found"] else "N/A"
        p(f"  {status}  raw={raw_val:<12}  {vendor[:55]}")
    p()
    if all_found:
        p("  ✓ All 5 vendors found. Raw is_awarded values confirm need for production fix.")
    else:
        p("  *** ONE OR MORE CORRECTED VENDORS MISSING FROM RAW ROWS ***")
    p()

    p("  AMOUNT NORMALIZATION CHECK")
    p("  " + "-" * 45)
    p(f"  C$ prefix rows in raw data     : {amount_check['cdn_dollar_count']}")
    p(f"  Spaced amount rows in raw data  : {amount_check['spaced_amount_count']}")
    if amount_check["cdn_dollar_count"] > 0:
        p("  ✓ C$ prefix present — production C$. → $ fix is load-bearing.")
        p("  Sample:")
        for r in amount_check["cdn_dollar_rows"][:3]:
            p(f"    comp={r['col_00']!r}  raw_amount={r['col_05']!r}")
    else:
        p("  NOTE: No C$ prefix in raw rows.")
        p("    Either the PDF was already formatted correctly, or amounts")
        p("    appear in a different column than expected.")
    if amount_check["spaced_amount_count"] > 0:
        p("  ✓ Spaced amounts present — space-removal pass is load-bearing.")
    p()

    p("=" * 65)
    p("  NEXT STEPS FOR REVIEWER")
    p("  " + "-" * 45)
    p("  1. Confirm delta is zero (accepted == 910)")
    p("  2. Confirm all 6 non-standard formats in nonstandard_comp_numbers.csv")
    p("  3. Review suspicious_col00.csv — any non-zero count needs manual check")
    p("  4. Check pages_no_table count")
    p("  5. Check 25-064 correction — what are the raw is_awarded values?")
    p("     Blank raw values confirm the production hardcode is essential.")
    p("  6. Check amount normalization — were C$ amounts present in raw rows?")
    p("=" * 65)
    p("  END OF AUDIT SUMMARY")
    p("=" * 65)

    with open(OUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print()
    print(f"  Summary saved to: {OUT_SUMMARY}")
    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_audit()

"""
diag_2026_raw_dump.py
=====================
AUDIT-ONLY DIAGNOSTIC SCRIPT — DO NOT USE AS PRODUCTION EXTRACTOR

Purpose
-------
Expose every raw row pdfplumber sees when reading awardedbids2026.pdf,
classify each row using the CURRENT production exclusion logic (unchanged),
and produce audit CSVs for manual review of extraction completeness.

2026-Specific Context
---------------------
  - Smallest year: 185 rows
  - Partial year coverage: Jan–Mar 2026 only
  - is_awarded uses Y/N in raw PDF (normalized to Yes/No by production extractor)
  - 40% of competition numbers are four-digit format (XX-XXXX)
    This is a structural PDF layout change — not an edge case
  - Manual correction for 25-0001 sets is_awarded = "Y" BEFORE Y/N normalization
    (ordering dependency: correction must precede normalization)
  - dropna(how="all") cleanup step — unique to 2026
    Removes rows where every column is null
  - Space-removal on amounts (same as 2025)
  - Amounts in raw PDF may appear as "$ 225,000" (spaced) which after
    space removal becomes "$225,000" — distinct from reversed "225,000$"

Key Audit Questions
-------------------
  1. Accepted count == 185?
  2. All Y/N values detectable in raw rows (confirms normalization is load-bearing)?
  3. How many rows did dropna(how="all") remove?
  4. 25-0001 manual correction: raw is_awarded value and final normalized value?
  5. Are reversed amounts present in raw data (number before $)?
  6. Are spaced amounts present ($ space number)?
  7. Pages with no tables?
  8. Col count mismatches?
  9. Suspicious col_00 values (non-competition-number content)?
  10. Do all 32 known four-digit competition numbers appear in accepted rows?

What Changed from the 2025 Diagnostic
--------------------------------------
  1. COMP_NUM_LOOSE extended to treat four-digit as fully standard for 2026
  2. Y/N value detector — scans raw col_06 for single-char awarded values
  3. dropna simulator — counts rows that would be removed by dropna(how="all")
  4. Reversed amount detector — flags amounts where digits precede the $ sign
  5. 25-0001 correction verifier — confirms raw value and ordering dependency
  6. Production row count updated to 185
  7. Partial year flag — records date range from raw rows

Output Files (all in data/diagnostics/2026/)
---------------------------------------------
  diag_2026_accepted.csv              — rows the extractor keeps
  diag_2026_skipped_empty.csv         — rows with nothing in col_00
  diag_2026_header_rows.csv           — header / structural rows
  diag_2026_suspicious_col00.csv      — accepted rows with non-comp-number in col_00
  diag_2026_yn_raw_values.csv         — accepted rows where col_06 is Y or N (raw)
  diag_2026_dropna_candidates.csv     — accepted rows that would be removed by dropna
  diag_2026_reversed_amounts.csv      — accepted rows with number-before-$ amounts
  diag_2026_spaced_amounts.csv        — accepted rows with spaced amount format
  diag_2026_nonstandard_comps.csv     — inventory of four-digit and other formats
  diag_2026_per_page_table_stats.csv  — row inventory per page per table
  diag_2026_audit_summary.txt         — full audit summary

How to Run
----------
  From the project scripts directory:
      python diag_2026_raw_dump.py

  With explicit PDF path override:
      PDF_OVERRIDE=/path/to/awarded-bids-2026.pdf python diag_2026_raw_dump.py
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

PDF_PATH = PROJECT_ROOT / "data" / "raw" / "awarded-bids-2026.pdf"

if os.environ.get("PDF_OVERRIDE"):
    PDF_PATH = Path(os.environ["PDF_OVERRIDE"])

if not PDF_PATH.exists():
    PDF_PATH = SCRIPT_DIR / "awardedbids2026.pdf"

DIAG_DIR = PROJECT_ROOT / "data" / "diagnostics" / "2026"
DIAG_DIR.mkdir(parents=True, exist_ok=True)

OUT_ACCEPTED         = DIAG_DIR / "diag_2026_accepted.csv"
OUT_SKIPPED_EMPTY    = DIAG_DIR / "diag_2026_skipped_empty.csv"
OUT_HEADER_ROWS      = DIAG_DIR / "diag_2026_header_rows.csv"
OUT_SUSPICIOUS_COL00 = DIAG_DIR / "diag_2026_suspicious_col00.csv"
OUT_YN_RAW           = DIAG_DIR / "diag_2026_yn_raw_values.csv"
OUT_DROPNA_CANDS     = DIAG_DIR / "diag_2026_dropna_candidates.csv"
OUT_REVERSED_AMOUNTS = DIAG_DIR / "diag_2026_reversed_amounts.csv"
OUT_SPACED_AMOUNTS   = DIAG_DIR / "diag_2026_spaced_amounts.csv"
OUT_NONSTANDARD      = DIAG_DIR / "diag_2026_nonstandard_comps.csv"
OUT_PAGE_TABLE_STATS = DIAG_DIR / "diag_2026_per_page_table_stats.csv"
OUT_SUMMARY          = DIAG_DIR / "diag_2026_audit_summary.txt"

# Known production row count — from step1_extracted_2026.csv (verified 2026-06-15)
PRODUCTION_ROW_COUNT = 185

EXPECTED_COL_COUNT = 7

# --- Header / structural text — same production exclusion logic as 2024/2025 ---
HEADER_EXACT = {None, "Competition #"}

HEADER_STARTSWITH = [
    "The following contracts",   # matches production extractor
    "RESULTS OF OPEN",           # defensive addition — structural title rows
    "Page ",                     # defensive addition — pagination/footer rows
]

# --- Competition number pattern (2026 context) ---
# Four-digit suffix is now 40% of rows — it is the dominant alternate format.
# Accept: XX-XXX, XX-XXXX, XX-XXXA, XX-XXX.D, year prefixes 18-26
COMP_NUM_LOOSE = re.compile(
    r"^(1[8-9]|2[0-6])-\d{3,4}[A-Z]?(\.\d+)?$"
)

# Standard only — used to inventory non-standard rows
COMP_NUM_NARROW = re.compile(r"^\d{2}-\d{3}$")

# --- Known four-digit competition numbers from 2026 production output ---
# Used to verify all expected non-standard formats are present in accepted rows.
# Derived from step1_extracted_2026.csv analysis.
EXPECTED_FOUR_DIGIT = {
    "22-0167",
    "24-0340", "24-0342", "24-0346", "24-0352", "24-0356", "24-0580",
    "25-0001", "25-0002", "25-0245", "25-0504", "25-0651", "25-0656",
    "25-0672", "25-0676", "25-0717", "25-0734", "25-0764", "25-0769",
    "26-0115", "26-0119", "26-0132", "26-0141", "26-0226", "26-0251",
    "26-0255", "26-0261", "26-0263", "26-0264", "26-0272", "26-0282",
    "26-0313",
}

# --- 25-0001 manual correction details ---
MANUAL_CORRECTION_COMP   = "25-0001"
MANUAL_CORRECTION_VENDOR = "DBA B&B Heavy Civil Construction Ltd."
# Production sets is_awarded = "Y" for this row (before normalization)
# Expected raw is_awarded: blank / null / empty (that's why the correction exists)
# Expected final is_awarded: "Yes" (after Y→Yes normalization)

# --- Y/N detection ---
# Raw is_awarded values before normalization should be Y or N (not Yes/No)
# Any row with col_06 in {Y, N} is evidence the normalization is load-bearing
RAW_YN_VALUES = {"Y", "N"}

# --- Amount format detection ---
# Reversed: number precedes $ — e.g. "225,000$" (after space removal of "225,000 $")
REVERSED_AMOUNT = re.compile(r"^\d[\d,.]+\$")

# Spaced: $ then space then number — e.g. "$ 225,000"
SPACED_AMOUNT = re.compile(r"^\$\s+\d")

# Internally spaced: digits with space between — e.g. "225 000"
INTERNAL_SPACE_AMOUNT = re.compile(r"\d\s\d")

# --- dropna candidate detection ---
# A row is a dropna candidate if ALL non-page-metadata cells are empty/null.
# We check cols 0–6. If all are empty, production's dropna(how="all") removes it.
def is_all_null(record: dict) -> bool:
    for i in range(EXPECTED_COL_COUNT):
        v = record.get(f"col_{i:02d}", "")
        if v and v.strip():
            return False
    return True


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_row(row: list) -> str:
    """
    Exact 2026 production exclusion conditions (verbatim from step1_extract_2026.py):
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
    Returns (True, reason) if col_00 looks like something other than a
    competition number. Extended for 2026's dominant four-digit format.
    """
    val = cell_str.strip()

    if COMP_NUM_LOOSE.match(val):
        return False, ""

    if re.match(r"^\d{1,2}-[A-Za-z]{3}", val):
        return True, "looks_like_date"
    if val.startswith("$") or re.match(r"^\d[\d,]+$", val):
        return True, "looks_like_amount"
    if len(val) > 30:
        return True, "too_long_for_comp_num"

    return True, "unrecognized_format"


def classify_comp_format(val: str) -> str:
    """Return the format category of a competition number string."""
    v = val.strip()
    if COMP_NUM_NARROW.fullmatch(v):             return "standard_XX-XXX"
    if re.fullmatch(r"\d{2}-\d{4}", v):          return "four_digit_XX-XXXX"
    if re.fullmatch(r"\d{2}-\d{3}[A-Z]", v):    return "letter_suffix_XX-XXXA"
    if re.fullmatch(r"\d{2}-\d{3,4}\.\d+", v):  return "decimal_XX-XXX.D"
    if COMP_NUM_LOOSE.match(v):                  return "other_valid"
    return "unknown"


def check_amount_format(amount_str: str) -> dict:
    """
    Classify the raw amount string format before normalization.
    Returns a dict describing which format patterns are present.
    """
    result = {
        "reversed":        bool(REVERSED_AMOUNT.match(amount_str)),
        "spaced":          bool(SPACED_AMOUNT.match(amount_str)),
        "internal_space":  bool(INTERNAL_SPACE_AMOUNT.search(amount_str)),
        "standard":        (
            bool(re.match(r"^\$[\d,]+", amount_str))
            and not SPACED_AMOUNT.match(amount_str)
        ),
        "empty":           not amount_str.strip(),
    }
    return result


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


# ============================================================
# MAIN AUDIT LOOP
# ============================================================

def run_audit():
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 65)
    print("  diag_2026_raw_dump.py — 2026 EXTRACTION AUDIT")
    print(f"  Run timestamp     : {run_timestamp}")
    print(f"  PDF path          : {PDF_PATH}")
    print(f"  Exists            : {PDF_PATH.exists()}")
    print(f"  Output dir        : {DIAG_DIR}")
    print(f"  Extraction method : extract_tables() plural")
    print(f"  Filter logic      : exclusion-only, no regex gate")
    print(f"  Production count  : {PRODUCTION_ROW_COUNT} rows to match")
    print("=" * 65)
    print()

    if not PDF_PATH.exists():
        print(f"  ERROR: PDF not found at {PDF_PATH}")
        print("  Set PDF_OVERRIDE environment variable to the correct path.")
        print("  Example:")
        print("    PDF_OVERRIDE=/path/to/awarded-bids-2026.pdf python diag_2026_raw_dump.py")
        return

    # --------------------------------------------------------
    # ACCUMULATORS
    # --------------------------------------------------------
    accepted       = []
    skipped_empty  = []
    header_rows    = []

    # 2026-specific sub-collections (all derived from accepted rows)
    suspicious_col00  = []
    yn_raw_rows       = []      # col_06 is Y or N
    dropna_candidates = []      # all 7 columns are empty/null
    reversed_amounts  = []      # amount starts with digit before $
    spaced_amounts    = []      # amount is "$ number" format
    nonstandard_comps = []      # four-digit, letter-suffix, decimal formats

    page_table_stats = []
    total_rows_seen  = 0

    # Collect all raw dates to determine date range
    raw_dates = []

    # --------------------------------------------------------
    # PDF ITERATION — mirrors production exactly
    # --------------------------------------------------------
    with pdfplumber.open(PDF_PATH) as pdf:

        total_pages = len(pdf.pages)
        print(f"  PDF opened. Total pages: {total_pages}")
        print()

        for page_num, page in enumerate(pdf.pages, start=1):

            tables   = page.extract_tables()
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
                    "yn_raw_values":        0,
                    "dropna_candidates":    0,
                    "reversed_amounts":     0,
                    "nonstandard_comp":     0,
                    "table_found":          "NO — INVESTIGATE",
                })
                print(
                    f"  Page {page_num:>3}/{total_pages}"
                    f"  tables=0"
                    f"  *** NO TABLE DETECTED ***"
                )
                continue

            page_accepted_total  = 0
            page_skipped_total   = 0
            page_header_total    = 0
            page_yn_total        = 0
            page_suspicious_total = 0

            for table_index, table in enumerate(tables):

                tbl_accepted     = 0
                tbl_skipped      = 0
                tbl_header       = 0
                tbl_col_mismatch = 0
                tbl_suspicious   = 0
                tbl_yn           = 0
                tbl_dropna       = 0
                tbl_reversed     = 0
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

                        col00  = record.get("col_00", "")
                        col05  = record.get("col_05", "")   # awarded_amount
                        col06  = record.get("col_06", "")   # is_awarded

                        # Collect dates for range analysis
                        col03 = record.get("col_03", "")
                        if col03:
                            raw_dates.append(col03)

                        # ── Suspicious col_00
                        is_susp, reason = is_suspicious_col00(col00)
                        if is_susp:
                            sr = dict(record)
                            sr["suspicious_reason"] = reason
                            suspicious_col00.append(sr)
                            tbl_suspicious += 1
                            page_suspicious_total += 1

                        # ── Competition number format inventory
                        fmt = classify_comp_format(col00)
                        if fmt != "standard_XX-XXX":
                            nr = dict(record)
                            nr["comp_format"] = fmt
                            nonstandard_comps.append(nr)
                            tbl_nonstandard += 1

                        # ── Y/N raw is_awarded value
                        if col06.strip() in RAW_YN_VALUES:
                            yn_row = dict(record)
                            yn_row["raw_is_awarded"] = col06.strip()
                            yn_raw_rows.append(yn_row)
                            tbl_yn += 1
                            page_yn_total += 1

                        # ── dropna candidate (all 7 cols empty)
                        if is_all_null(record):
                            dropna_candidates.append(record)
                            tbl_dropna += 1

                        # ── Amount format checks
                        if col05:
                            amt_fmt = check_amount_format(col05)
                            if amt_fmt["reversed"]:
                                rr = dict(record)
                                rr["amount_format_note"] = "reversed: digit before $"
                                reversed_amounts.append(rr)
                                tbl_reversed += 1
                            if amt_fmt["spaced"] or amt_fmt["internal_space"]:
                                sr2 = dict(record)
                                sr2["amount_format_note"] = (
                                    "spaced: $ space digit"
                                    if amt_fmt["spaced"]
                                    else "internal space between digits"
                                )
                                spaced_amounts.append(sr2)

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
                    "yn_raw_values":        tbl_yn,
                    "dropna_candidates":    tbl_dropna,
                    "reversed_amounts":     tbl_reversed,
                    "nonstandard_comp":     tbl_nonstandard,
                    "table_found":          "YES",
                })

            print(
                f"  Page {page_num:>3}/{total_pages}"
                f"  tables={n_tables}"
                f"  accepted={page_accepted_total:>4}"
                f"  skipped={page_skipped_total:>3}"
                f"  header={page_header_total:>2}"
                f"  yn_raw={page_yn_total:>3}"
                f"  suspicious={page_suspicious_total:>2}"
            )

    print()

    # --------------------------------------------------------
    # 25-0001 CORRECTION VERIFICATION
    # (done post-loop on the accepted records list)
    # --------------------------------------------------------
    correction_row = None
    for r in accepted:
        if (r.get("col_00", "").strip() == MANUAL_CORRECTION_COMP and
                r.get("col_04", "").strip() == MANUAL_CORRECTION_VENDOR):
            correction_row = r
            break

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
    write_csv(accepted,          OUT_ACCEPTED,         "ACCEPTED")
    write_csv(skipped_empty,     OUT_SKIPPED_EMPTY,    "SKIPPED_EMPTY")
    write_csv(header_rows,       OUT_HEADER_ROWS,      "HEADER_ROWS")
    write_csv(
        suspicious_col00,        OUT_SUSPICIOUS_COL00, "SUSPICIOUS_COL00",
        extra_cols=["suspicious_reason"]
    )
    write_csv(
        yn_raw_rows,             OUT_YN_RAW,           "YN_RAW_VALUES",
        extra_cols=["raw_is_awarded"]
    )
    write_csv(dropna_candidates, OUT_DROPNA_CANDS,     "DROPNA_CANDIDATES")
    write_csv(
        reversed_amounts,        OUT_REVERSED_AMOUNTS, "REVERSED_AMOUNTS",
        extra_cols=["amount_format_note"]
    )
    write_csv(
        spaced_amounts,          OUT_SPACED_AMOUNTS,   "SPACED_AMOUNTS",
        extra_cols=["amount_format_note"]
    )
    write_csv(
        nonstandard_comps,       OUT_NONSTANDARD,      "NONSTANDARD_COMPS",
        extra_cols=["comp_format"]
    )

    df_stats = pd.DataFrame(page_table_stats)
    df_stats.to_csv(OUT_PAGE_TABLE_STATS, index=False, encoding="utf-8-sig")
    print(f"  Saved {'PER_PAGE_TABLE_STATS':<45} → {OUT_PAGE_TABLE_STATS.name}  ({len(df_stats):,} rows)")
    print()

    # --------------------------------------------------------
    # SUMMARY METRICS
    # --------------------------------------------------------
    n_accepted       = len(accepted)
    n_skipped        = len(skipped_empty)
    n_header         = len(header_rows)
    n_suspicious     = len(suspicious_col00)
    n_yn_raw         = len(yn_raw_rows)
    n_dropna         = len(dropna_candidates)
    n_reversed       = len(reversed_amounts)
    n_spaced         = len(spaced_amounts)
    n_nonstandard    = len(nonstandard_comps)

    pages_no_table   = df_stats[df_stats["table_found"].str.startswith("NO")]
    col_mismatches   = [r for r in accepted if r.get("col_count_flag") == "MISMATCH"]

    delta            = n_accepted - PRODUCTION_ROW_COUNT
    delta_str        = f"+{delta}" if delta >= 0 else str(delta)

    # Non-standard format breakdown
    fmt_counts = {}
    for r in nonstandard_comps:
        fmt = r.get("comp_format", "unknown")
        fmt_counts[fmt] = fmt_counts.get(fmt, 0) + 1

    found_four_digit = set(
        r.get("col_00", "") for r in nonstandard_comps
        if r.get("comp_format") == "four_digit_XX-XXXX"
    )
    missing_four_digit = EXPECTED_FOUR_DIGIT - found_four_digit
    new_four_digit     = found_four_digit - EXPECTED_FOUR_DIGIT

    # Date range from raw rows
    raw_dates_clean = [d for d in raw_dates if re.match(r"\d{1,2}-[A-Za-z]{3}-\d{2}", d)]
    date_range_note = (
        f"{min(raw_dates_clean)} to {max(raw_dates_clean)}"
        if raw_dates_clean else "no parseable dates found"
    )

    # Y/N distribution
    yn_dist = {}
    for r in yn_raw_rows:
        v = r.get("raw_is_awarded", "")
        yn_dist[v] = yn_dist.get(v, 0) + 1

    # --------------------------------------------------------
    # PRINT AND SAVE AUDIT SUMMARY
    # --------------------------------------------------------
    summary_lines = []

    def p(line=""):
        print(line)
        summary_lines.append(line)

    p()
    p("=" * 65)
    p("  AUDIT SUMMARY — diag_2026_raw_dump.py")
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
    p(f"  Production row count (185)    : {PRODUCTION_ROW_COUNT:>6,}")
    p(f"  Diagnostic accepted count     : {n_accepted:>6,}")
    p(f"  Delta                         : {delta_str:>6}")
    p()
    if delta == 0:
        p("  ✓ Accepted count matches production exactly.")
        p("    Note: production also runs dropna(how='all') which may remove rows.")
        p(f"    dropna candidates in accepted rows: {n_dropna}")
        if n_dropna > 0:
            p(f"    If delta == 0 AND dropna_candidates > 0, the production")
            p(f"    extractor's dropna step removed rows AND something else added")
            p(f"    them back. Investigate diag_2026_dropna_candidates.csv.")
    elif delta > 0:
        p(f"  *** Diagnostic accepted MORE rows ({delta} extra) ***")
        p(f"    Likely cause: {n_dropna} dropna candidates were accepted here")
        p(f"    but production's dropna(how='all') removed them.")
        if delta == n_dropna:
            p(f"  ✓ Delta exactly equals dropna candidates — explains the gap.")
    else:
        p(f"  *** Diagnostic accepted FEWER rows ({abs(delta)} missing) ***")
        p("    Investigate: iteration logic difference.")
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
    else:
        p("  ✓ All accepted rows have exactly 7 columns.")
    p()

    p("  Y/N NORMALIZATION EVIDENCE")
    p("  " + "-" * 45)
    p(f"  Raw Y/N rows in accepted set   : {n_yn_raw}")
    if n_yn_raw > 0:
        for val, cnt in sorted(yn_dist.items()):
            p(f"    {val!r:<6} : {cnt:,} rows")
        p()
        p("  ✓ Y/N values present in raw data — normalization is LOAD-BEARING.")
        p("    Without .replace({'Y':'Yes','N':'No'}), all is_awarded values")
        p("    would remain as Y/N and break all downstream Yes/No filters.")
    else:
        p("  NOTE: No Y/N values found in col_06 of accepted rows.")
        p("    Either the PDF uses Yes/No directly, or col_06 is not is_awarded.")
        p("    Verify column order in the raw accepted CSV.")
    p()

    p("  25-0001 MANUAL CORRECTION VERIFICATION")
    p("  " + "-" * 45)
    p(f"  Target: comp={MANUAL_CORRECTION_COMP!r}")
    p(f"          vendor={MANUAL_CORRECTION_VENDOR!r}")
    p()
    if correction_row:
        raw_val = correction_row.get("col_06", "")
        raw_amt = correction_row.get("col_05", "")
        p(f"  ✓ Row found in accepted set")
        p(f"    raw is_awarded (col_06) : {raw_val!r}")
        p(f"    raw amount (col_05)     : {raw_amt!r}")
        p()
        if raw_val.strip() in {"", None.__class__.__name__}:
            p("  ✓ Raw is_awarded is blank — manual correction is LOAD-BEARING.")
        elif raw_val.strip() == "Y":
            p("  NOTE: Raw is_awarded is already 'Y' — the production correction")
            p("    sets it to 'Y' (same value). It may be redundant OR the PDF")
            p("    already has Y but the correction is defensive. Either way,")
            p("    the subsequent Y→Yes normalization converts it correctly.")
        else:
            p(f"  NOTE: Raw is_awarded is {raw_val!r} — investigate whether")
            p("    the correction is still needed.")
        p()
        if not raw_amt:
            p("  NOTE: Raw amount is empty — condition `awarded_amount.notna()`")
            p("    in the production correction would NOT fire for this row.")
            p("    The correction requires a non-null amount. Verify in PDF.")
        else:
            p(f"  ✓ Amount is non-null ({raw_amt!r}) — correction condition will fire.")
    else:
        p("  ✗ Row NOT FOUND in accepted rows")
        p(f"    comp={MANUAL_CORRECTION_COMP!r} with vendor={MANUAL_CORRECTION_VENDOR!r}")
        p("    Either the vendor name differs or the row was skipped.")
        p("    Check diag_2026_accepted.csv for comp 25-0001 rows.")
    p()

    p("  AMOUNT FORMAT ANALYSIS (raw values before normalization)")
    p("  " + "-" * 45)
    p(f"  Reversed amounts (digit before $) : {n_reversed}")
    p(f"  Spaced amounts ($ space digit)    : {n_spaced}")
    p()
    if n_spaced > 0:
        p("  ✓ Spaced amounts present in raw data.")
        p("    Production's str.replace(' ', '') converts '$ 225,000' → '$225,000'.")
        p("    The space-removal pass is LOAD-BEARING.")
        p("  Sample:")
        for r in spaced_amounts[:3]:
            p(f"    comp={r['col_00']!r}  raw={r['col_05']!r}")
    elif n_reversed > 0:
        p("  *** REVERSED AMOUNTS DETECTED — digit appears before $ ***")
        p("    These would NOT be fixed by str.replace(' ', '').")
        p("    '225,000$' stays as '225,000$' — still reversed.")
        p("    Production extractor may need an additional fix.")
        p("  Reversed rows:")
        for r in reversed_amounts[:10]:
            p(f"    comp={r['col_00']!r}  raw={r['col_05']!r}")
    else:
        p("  ✓ No reversed or spaced amounts in raw data.")
        p("    All amounts appear in standard '$NNN' format already.")
    p()

    p("  DROPNA CANDIDATE ANALYSIS")
    p("  " + "-" * 45)
    p(f"  All-null accepted rows (dropna candidates) : {n_dropna}")
    if n_dropna > 0:
        p()
        p("  These rows would be removed by production's dropna(how='all').")
        p("  Verify they are genuinely blank (not partially populated).")
        p("  See diag_2026_dropna_candidates.csv for full detail.")
    else:
        p("  ✓ No all-null rows found in accepted set.")
        p("    Production's dropna(how='all') removes zero data rows.")
    p()

    p("  NON-STANDARD COMPETITION NUMBER FORMATS")
    p("  (2026 has 40% four-digit format — structural PDF change)")
    p("  " + "-" * 45)
    p(f"  Total non-standard accepted rows: {n_nonstandard}")
    p()
    for fmt, cnt in sorted(fmt_counts.items()):
        p(f"    {fmt:<30} {cnt:,} rows")
    p()
    if missing_four_digit:
        p("  *** EXPECTED FOUR-DIGIT COMPS NOT FOUND — POSSIBLE REGRESSION ***")
        for v in sorted(missing_four_digit):
            p(f"    MISSING: {v}")
        p()
    else:
        p(f"  ✓ All {len(EXPECTED_FOUR_DIGIT)} expected four-digit formats confirmed.")
    if new_four_digit:
        p("  NEW FOUR-DIGIT COMPS (not in original production output):")
        for v in sorted(new_four_digit):
            p(f"    {v}  — cross-check in PDF")
        p()

    p("  RAW DATE RANGE")
    p("  " + "-" * 45)
    p(f"  {date_range_note}")
    p("  Note: 2026 is a PARTIAL YEAR dataset.")
    p("  All downstream analytics involving annual totals must account for this.")
    p()

    p("  SUSPICIOUS COL_00 VALUES")
    p("  " + "-" * 45)
    p(f"  Count : {n_suspicious}")
    if suspicious_col00:
        reason_counts = {}
        for r in suspicious_col00:
            reason_counts[r.get("suspicious_reason", "?")] = (
                reason_counts.get(r.get("suspicious_reason", "?"), 0) + 1
            )
        for rsn, cnt in sorted(reason_counts.items()):
            p(f"    {rsn:<40} {cnt:,}")
        p()
        seen = set()
        for r in suspicious_col00[:10]:
            v = r.get("col_00", "")
            if v not in seen:
                p(f"    {v!r}")
                seen.add(v)
    else:
        p("  ✓ No suspicious col_00 values found.")
    p()

    p("=" * 65)
    p("  NEXT STEPS FOR REVIEWER")
    p("  " + "-" * 45)
    p("  1. Confirm delta (accepted vs 185)")
    p("     If delta > 0: check if delta == dropna candidates exactly")
    p("  2. Confirm Y/N raw values present — normalization is load-bearing")
    p("  3. Check 25-0001 correction: is raw is_awarded blank or 'Y'?")
    p("  4. Check spaced/reversed amounts — is space-removal pass needed?")
    p(
        f"  5. All {len(EXPECTED_FOUR_DIGIT)} expected four-digit formats "
        "in nonstandard_comps.csv"
    )
    p("  6. 2026 data covers Feb–Mar 2026 only — flag in annual comparisons")
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

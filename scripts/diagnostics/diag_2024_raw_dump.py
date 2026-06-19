"""
diag_2024_raw_dump.py
=====================
AUDIT-ONLY DIAGNOSTIC SCRIPT — DO NOT USE AS PRODUCTION EXTRACTOR

Purpose
-------
Expose every raw row pdfplumber sees when reading awardedbids2024.pdf,
classify each row using the CURRENT production exclusion logic (unchanged),
and produce audit CSVs for manual review of extraction completeness.

Key differences from diag_2023_raw_dump.py
-------------------------------------------
  1. Uses extract_tables() plural — mirrors 2024 production extractor exactly.
     Every record carries both page_num AND table_index (which table on the page)
     so a suspicious row can be located precisely in the PDF.

  2. No regex filter exists in 2024 production code.
     Classification is controlled by the three exclusion conditions only:
       (a) entire row is falsy
       (b) r[0] is None or "Competition #"
       (c) r[0].startswith("The following contracts")
     Everything not excluded is ACCEPTED.

  3. Two additional output files specific to 2024 risk profile:
       diag_2024_suspicious_col00.csv   — accepted rows with unexpected col_00 values
       diag_2024_col_shift_candidates.csv — rows showing the vendor-tail-in-amount pattern

  4. Encoding artifact scan — checks vendor name column for residual Unicode escapes
     that the production hardcoded fix may have missed.

Row Classification
------------------
  ACCEPTED            row passed all three exclusion conditions → would be kept
  SKIPPED_EMPTY       r is falsy OR r[0] is None/empty string
  HEADER              r[0] == "Competition #" OR matches known structural text
  SUSPICIOUS_COL00    ACCEPTED but col_00 does not look like a competition number
                      (informational sub-category — still accepted by production)

Output Files (all in data/diagnostics/2024/)
---------------------------------------------
  diag_2024_accepted.csv             — rows the current extractor keeps
  diag_2024_skipped_empty.csv        — rows with no value in col_00
  diag_2024_header_rows.csv          — column header / structural rows detected
  diag_2024_suspicious_col00.csv     — accepted rows where col_00 looks unexpected
  diag_2024_col_shift_candidates.csv — rows matching vendor-tail-in-amount pattern
  diag_2024_encoding_artifacts.csv   — accepted rows with possible encoding issues
  diag_2024_per_page_table_stats.csv — per-page, per-table row count inventory
  diag_2024_audit_summary.txt        — full audit summary (mirrors console output)

Key Audit Questions
-------------------
  1. Total rows seen vs production output (527)?
  2. Pages or tables with zero rows — are they blank or missed?
  3. Any accepted rows where col_00 is not a competition number?
  4. How many rows match the vendor-tail-in-amount pattern beyond the two known fixes?
  5. Any residual encoding artifacts in vendor names?
  6. Col_count mismatches — rows with more or fewer than 7 cells?

How to Run
----------
  From the scripts/diagnostics/ directory:
    python diag_2024_raw_dump.py

  Or from the project root:
    python scripts/diagnostics/diag_2024_raw_dump.py

  With explicit PDF path override:
    PDF_OVERRIDE=/path/to/awarded-bids-2024.pdf python scripts/diagnostics/diag_2024_raw_dump.py


Author note: This script is intentionally verbose. Every finding is annotated
so the audit log is self-contained and presentable to a reviewer.
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

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# Primary PDF path (mirrors production extractor)
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "awarded-bids-2024.pdf"

# Environment variable override for portability
if os.environ.get("PDF_OVERRIDE"):
    PDF_PATH = Path(os.environ["PDF_OVERRIDE"])

# Flat-layout fallback (PDFs beside scripts)
if not PDF_PATH.exists():
    PDF_PATH = SCRIPT_DIR / "awardedbids2024.pdf"

# --- Output directory ---
# Subdirectory per year: data/diagnostics/2024/
# Never overlaps with data/extracted/ or data/clean/
DIAG_DIR = PROJECT_ROOT / "data" / "diagnostics" / "2024"
DIAG_DIR.mkdir(parents=True, exist_ok=True)

# --- Output file paths ---
OUT_ACCEPTED           = DIAG_DIR / "diag_2024_accepted.csv"
OUT_SKIPPED_EMPTY      = DIAG_DIR / "diag_2024_skipped_empty.csv"
OUT_HEADER_ROWS        = DIAG_DIR / "diag_2024_header_rows.csv"
OUT_SUSPICIOUS_COL00   = DIAG_DIR / "diag_2024_suspicious_col00.csv"
OUT_COL_SHIFT          = DIAG_DIR / "diag_2024_col_shift_candidates.csv"
OUT_ENCODING           = DIAG_DIR / "diag_2024_encoding_artifacts.csv"
OUT_PAGE_TABLE_STATS   = DIAG_DIR / "diag_2024_per_page_table_stats.csv"
OUT_SUMMARY            = DIAG_DIR / "diag_2024_audit_summary.txt"

# --- Known production row count to compare against ---
# From step1_extracted_2024.csv (verified 2026-05-18)
PRODUCTION_ROW_COUNT = 527

# --- Expected column count ---
EXPECTED_COL_COUNT = 7

# --- Header / structural strings ---
# These are the exact conditions in the 2024 production extractor.
# We reproduce them verbatim to ensure our classification matches production.
HEADER_EXACT = {None, "Competition #"}

HEADER_STARTSWITH = [
    "The following contracts",
    "RESULTS OF OPEN",
    "Page ",
]

# --- Regex to detect competition-number-like values in col_00 ---
# This is NOT a filter — it is used to flag ACCEPTED rows where
# col_00 looks suspicious (non-competition-number content passed through).
# The 2024 extractor has no such filter, so anything can slip through.
COMP_NUM_LOOSE = re.compile(
    r"^\d{2}-\d{3,4}[A-Z]?(\.\d+)?$"
)

# --- Pattern to detect vendor-tail-in-amount column shift ---
# Mirrors the exact mask used in the 2024 production extractor.
# Rows matching this pattern had a vendor name suffix spill into awarded_amount.
COL_SHIFT_IS_AWARDED_VALUE = "No"   # production mask: is_awarded == "No"
COL_SHIFT_AMOUNT_HAS_ALPHA = re.compile(r"[A-Za-z]")
COL_SHIFT_AMOUNT_ENDS_NA   = re.compile(r"NA$")

# --- Encoding artifact patterns ---
# The production extractor fixes: AtkinsR√©alis → AtkinsRéalis
# We scan for other unhandled occurrences of this class of encoding corruption.
ENCODING_ARTIFACT_PATTERNS = [
    re.compile(r"√"),          # pdfminer encoding failure marker
    re.compile(r"\ufffd"),     # Unicode replacement character
    re.compile(r"[^\x00-\x7F\xC0-\xFF]"),  # unexpected non-latin characters
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_row(row: list) -> str:
    """
    Classify a raw pdfplumber row using the EXACT 2024 production
    exclusion conditions — in the same order as the production code.

    Production code (verbatim):
        if not r: continue
        if r[0] in [None, "Competition #"]: continue
        if str(r[0]).startswith("The following contracts"): continue
        clean_rows.append(r)

    We extend the HEADER category to cover additional structural strings
    that aren't in the production code but appear in 2024 PDF layout
    (page footers, section titles) — these would be ACCEPTED by production
    but flagged here for manual review under SUSPICIOUS_COL00.

    Returns: 'ACCEPTED' | 'SKIPPED_EMPTY' | 'HEADER'
    """
    # Condition 1: entire row is falsy
    if not row:
        return "SKIPPED_EMPTY"

    cell_zero = row[0]

    # Condition 2: r[0] is None or the column header string
    # (exact match — this is what production uses)
    if cell_zero in HEADER_EXACT:
        if cell_zero is None or str(cell_zero).strip() == "":
            return "SKIPPED_EMPTY"
        return "HEADER"

    cell_zero_str = str(cell_zero).strip()

    # Also treat empty-after-strip as SKIPPED_EMPTY
    if cell_zero_str == "":
        return "SKIPPED_EMPTY"

    # Condition 3: r[0] starts with known structural text
    for prefix in HEADER_STARTSWITH:
        if cell_zero_str.startswith(prefix):
            return "HEADER"

    # All conditions passed — this row would be appended by production
    return "ACCEPTED"


def is_suspicious_col00(cell_zero_str: str) -> bool:
    """
    Returns True if col_00 of an ACCEPTED row does not look like
    a competition number. Used to surface rows that passed through
    the permissive 2024 filter but may contain garbage content.

    A competition number looks like: 23-342, 24-006A, 25-118.01
    Anything else in an accepted row is worth reviewing.
    """
    return not bool(COMP_NUM_LOOSE.match(cell_zero_str.strip()))


def is_col_shift_candidate(record: dict) -> bool:
    """
    Returns True if this accepted row matches the vendor-tail-in-amount
    pattern identified in the 2024 production extractor.

    Pattern: is_awarded == "No" AND awarded_amount contains letters
    AND awarded_amount ends with "NA"

    This mirrors the exact mask the production extractor uses to detect
    and correct the column-shift bug. Any matching row that is NOT one
    of the two known-corrected competitions (24-085, 24-132) may be
    an unhandled column shift.
    """
    col_is_awarded = record.get("col_06", "")   # is_awarded is the 7th column
    col_amount     = record.get("col_05", "")   # awarded_amount is the 6th column

    if col_is_awarded != "No":
        return False
    if not col_amount:
        return False
    if not COL_SHIFT_AMOUNT_HAS_ALPHA.search(col_amount):
        return False
    if not COL_SHIFT_AMOUNT_ENDS_NA.search(col_amount):
        return False
    return True


def has_encoding_artifact(record: dict) -> tuple[bool, str]:
    """
    Scan all text fields in the record for known encoding corruption patterns.
    Returns (True, description) if found, (False, "") otherwise.
    """
    text_fields = {
        "col_01": "competition_type",
        "col_02": "competition_description",
        "col_03": "awarded_date",
        "col_04": "vendor_name",
        "col_05": "awarded_amount",
    }
    for col_key, field_name in text_fields.items():
        val = record.get(col_key, "")
        for pattern in ENCODING_ARTIFACT_PATTERNS:
            if pattern.search(val):
                return True, f"field={field_name}, pattern={pattern.pattern!r}, value={val!r}"
    return False, ""


def row_to_record(
    row: list,
    page_num: int,
    table_index: int,
    table_row_index: int,
    classification: str,
) -> dict:
    """
    Convert a raw pdfplumber row to a flat audit record.

    New in 2024 vs 2023:
      - table_index: which table on the page this row came from (0-based)
      - table_row_index: row index within that table (0-based)

    These two fields let a reviewer pinpoint the exact location of any
    suspicious row in the PDF (page N, table M, row K).
    """
    record = {
        "page_num":         page_num,
        "table_index":      table_index,
        "table_row_index":  table_row_index,
        "classification":   classification,
        "col_count":        len(row) if row else 0,
        "col_count_flag":   (
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

    record["col_00_raw_repr"] = repr(row[0]) if (row and row[0] is not None) else repr(None)

    return record


# ============================================================
# MAIN AUDIT LOOP
# ============================================================

def run_audit():
    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 65)
    print("  diag_2024_raw_dump.py — 2024 EXTRACTION AUDIT")
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
        print("    PDF_OVERRIDE=/path/to/awarded-bids-2024.pdf python diag_2024_raw_dump.py")
        return

    # --------------------------------------------------------
    # ACCUMULATORS
    # --------------------------------------------------------
    accepted            = []
    skipped_empty       = []
    header_rows         = []

    # Sub-classification lists (derived from accepted)
    suspicious_col00    = []
    col_shift_candidates = []
    encoding_artifacts  = []

    page_table_stats    = []
    total_rows_seen     = 0

    # --------------------------------------------------------
    # PDF ITERATION
    # Mirrors production 2024 extractor exactly:
    #   - pdfplumber.open() (no context manager in production; we use one
    #     here to ensure proper resource cleanup in the diagnostic)
    #   - page.extract_tables() — plural, list of tables
    #   - for table in tables: rows.extend(table)
    # --------------------------------------------------------
    with pdfplumber.open(PDF_PATH) as pdf:

        total_pages = len(pdf.pages)
        print(f"  PDF opened. Total pages: {total_pages}")
        print()

        for page_num, page in enumerate(pdf.pages, start=1):

            tables = page.extract_tables()
            n_tables_on_page = len(tables)

            page_accepted_total    = 0
            page_skipped_total     = 0
            page_header_total      = 0
            page_suspicious_total  = 0
            page_col_shift_total   = 0
            page_encoding_total    = 0

            if n_tables_on_page == 0:
                # No tables at all on this page — log it explicitly
                page_table_stats.append({
                    "page_num":          page_num,
                    "table_index":       0,
                    "rows_in_table":     0,
                    "accepted":          0,
                    "skipped_empty":     0,
                    "header_rows":       0,
                    "col_count_mismatches": 0,
                    "suspicious_col00":  0,
                    "col_shift_candidates": 0,
                    "table_found":       "NO — INVESTIGATE",
                })
                print(
                    f"  Page {page_num:>3}/{total_pages}"
                    f"  tables=0"
                    f"  *** NO TABLE DETECTED — INVESTIGATE ***"
                )
                continue

            for table_index, table in enumerate(tables):

                tbl_accepted       = 0
                tbl_skipped        = 0
                tbl_header         = 0
                tbl_col_mismatch   = 0
                tbl_suspicious     = 0
                tbl_col_shift      = 0
                tbl_encoding       = 0

                for table_row_index, row in enumerate(table):
                    total_rows_seen += 1

                    classification = classify_row(row)
                    record = row_to_record(
                        row, page_num, table_index, table_row_index, classification
                    )

                    if record["col_count_flag"] == "MISMATCH" and classification == "ACCEPTED":
                        tbl_col_mismatch += 1

                    if classification == "ACCEPTED":
                        accepted.append(record)
                        tbl_accepted += 1
                        page_accepted_total += 1

                        # Sub-classification 1: suspicious col_00
                        col00_val = record.get("col_00", "")
                        if is_suspicious_col00(col00_val):
                            suspicious_rec = dict(record)
                            suspicious_rec["suspicious_reason"] = (
                                f"col_00 does not match competition number pattern: {col00_val!r}"
                            )
                            suspicious_col00.append(suspicious_rec)
                            tbl_suspicious += 1
                            page_suspicious_total += 1

                        # Sub-classification 2: vendor-tail-in-amount column shift
                        if is_col_shift_candidate(record):
                            shift_rec = dict(record)
                            col_shift_candidates.append(shift_rec)
                            tbl_col_shift += 1
                            page_col_shift_total += 1

                        # Sub-classification 3: encoding artifacts
                        has_artifact, artifact_desc = has_encoding_artifact(record)
                        if has_artifact:
                            enc_rec = dict(record)
                            enc_rec["artifact_description"] = artifact_desc
                            encoding_artifacts.append(enc_rec)
                            tbl_encoding += 1
                            page_encoding_total += 1

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
                    "col_shift_candidates": tbl_col_shift,
                    "table_found":          "YES",
                })

            print(
                f"  Page {page_num:>3}/{total_pages}"
                f"  tables={n_tables_on_page}"
                f"  accepted={page_accepted_total:>4}"
                f"  skipped={page_skipped_total:>3}"
                f"  header={page_header_total:>2}"
                f"  suspicious={page_suspicious_total:>2}"
                f"  col_shift={page_col_shift_total:>2}"
                f"  encoding={page_encoding_total:>2}"
            )

    print()

    # --------------------------------------------------------
    # MATH CLOSURE CHECK
    # --------------------------------------------------------
    total_classified = len(accepted) + len(skipped_empty) + len(header_rows)
    math_closes = (total_classified == total_rows_seen)

    # --------------------------------------------------------
    # WRITE ALL OUTPUT CSVs
    # --------------------------------------------------------
    base_fieldnames = [
        "page_num", "table_index", "table_row_index",
        "classification", "col_count", "col_count_flag",
        "col_00", "col_01", "col_02", "col_03", "col_04", "col_05", "col_06",
        "col_00_raw_repr",
    ]

    def write_csv(records: list, path: Path, label: str, extra_cols: list = None):
        cols = base_fieldnames + (extra_cols or [])
        df_out = pd.DataFrame(records, columns=cols)
        df_out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Saved {label:<40} → {path.name}  ({len(records):,} rows)")

    print("  Writing audit CSVs...")
    print()
    write_csv(accepted,             OUT_ACCEPTED,         "ACCEPTED")
    write_csv(skipped_empty,        OUT_SKIPPED_EMPTY,    "SKIPPED_EMPTY")
    write_csv(header_rows,          OUT_HEADER_ROWS,      "HEADER_ROWS")
    write_csv(
        suspicious_col00,           OUT_SUSPICIOUS_COL00, "SUSPICIOUS_COL00",
        extra_cols=["suspicious_reason"]
    )
    write_csv(
        col_shift_candidates,       OUT_COL_SHIFT,        "COL_SHIFT_CANDIDATES"
    )
    write_csv(
        encoding_artifacts,         OUT_ENCODING,         "ENCODING_ARTIFACTS",
        extra_cols=["artifact_description"]
    )

    df_stats = pd.DataFrame(page_table_stats)
    df_stats.to_csv(OUT_PAGE_TABLE_STATS, index=False, encoding="utf-8-sig")
    print(f"  Saved {'PER_PAGE_TABLE_STATS':<40} → {OUT_PAGE_TABLE_STATS.name}  ({len(df_stats):,} rows)")

    print()

    # --------------------------------------------------------
    # COMPUTE SUMMARY METRICS
    # --------------------------------------------------------
    n_accepted     = len(accepted)
    n_skipped      = len(skipped_empty)
    n_header       = len(header_rows)
    n_suspicious   = len(suspicious_col00)
    n_col_shift    = len(col_shift_candidates)
    n_encoding     = len(encoding_artifacts)

    pages_no_table = df_stats[df_stats["table_found"].str.startswith("NO")]
    col_mismatches = [r for r in accepted if r.get("col_count_flag") == "MISMATCH"]

    delta          = n_accepted - PRODUCTION_ROW_COUNT
    delta_str      = f"+{delta}" if delta >= 0 else str(delta)

    # Unique suspicious col_00 values
    suspicious_values = sorted(set(r.get("col_00", "") for r in suspicious_col00))

    # Known corrected competitions — col_shift candidates from these are expected
    KNOWN_CORRECTIONS = {"24-085", "24-132"}
    new_col_shift = [
        r for r in col_shift_candidates
        if r.get("col_00", "") not in KNOWN_CORRECTIONS
    ]

    # --------------------------------------------------------
    # PRINT AND SAVE AUDIT SUMMARY
    # --------------------------------------------------------
    summary_lines = []

    def p(line=""):
        print(line)
        summary_lines.append(line)

    p()
    p("=" * 65)
    p("  AUDIT SUMMARY — diag_2024_raw_dump.py")
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
        p("  ✓ MATH CLOSURE: classified == seen  (audit accounting is complete)")
    else:
        p(f"  ✗ MATH CLOSURE FAILED: {total_rows_seen} seen vs {total_classified} classified")
        p("    This indicates a classification gap in this diagnostic script.")
        p("    Do not trust results until this is resolved.")
    p()

    p("  COMPARISON TO PRODUCTION OUTPUT")
    p("  " + "-" * 45)
    p(f"  Production row count (527)    : {PRODUCTION_ROW_COUNT:>6,}")
    p(f"  Diagnostic accepted count     : {n_accepted:>6,}")
    p(f"  Delta                         : {delta_str:>6}")
    p()
    if delta == 0:
        p("  ✓ Accepted count matches production output exactly.")
        p("    The diagnostic and production extractor agree on which rows to keep.")
    elif delta > 0:
        p(f"  *** Diagnostic accepted MORE rows than production ({delta} extra) ***")
        p("    Possible cause: production applies a post-extraction filter not")
        p("    captured here (e.g. the col_shift or manual correction logic).")
        p("    Review diag_2024_suspicious_col00.csv for the extra rows.")
    else:
        p(f"  *** Diagnostic accepted FEWER rows than production ({abs(delta)} missing) ***")
        p("    Possible cause: extract_tables() iteration difference, or")
        p("    the production extractor's manual .loc[] corrections add rows.")
        p("    Note: manual corrections in production do not add rows — they")
        p("    only reassign values. A negative delta needs further investigation.")
    p()

    p("  TABLE COVERAGE")
    p("  " + "-" * 45)
    pages_with_tables = df_stats[df_stats["table_found"] == "YES"]["page_num"].nunique()
    pages_without_tables = len(pages_no_table)
    p(f"  Pages with at least one table : {pages_with_tables}")
    p(f"  Pages with NO table detected  : {pages_without_tables}")
    if pages_without_tables > 0:
        p()
        p("  *** PAGES WITH NO TABLE — CHECK MANUALLY IN PDF ***")
        for _, row in pages_no_table.iterrows():
            p(f"    Page {int(row['page_num'])}")
        p("    Open these pages in the PDF. If they contain data rows,")
        p("    extract_tables() failed to detect the table geometry.")
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
            p(f"    ... and {len(col_mismatches) - 10} more — see diag_2024_accepted.csv")
    p()

    p("  SUSPICIOUS COL_00 VALUES (accepted rows, non-competition-number content)")
    p("  " + "-" * 45)
    p(f"  Count : {n_suspicious}")
    if suspicious_values:
        p()
        p("  These rows passed through the permissive 2024 filter but col_00")
        p("  does not look like a competition number. Review manually.")
        for val in suspicious_values[:20]:
            p(f"    {val!r}")
        if len(suspicious_values) > 20:
            p(f"    ... and {len(suspicious_values) - 20} more — see diag_2024_suspicious_col00.csv")
    else:
        p("  ✓ No suspicious col_00 values found.")
    p()

    p("  VENDOR-TAIL-IN-AMOUNT COLUMN SHIFT CANDIDATES")
    p("  " + "-" * 45)
    p(f"  Total candidates found        : {n_col_shift}")
    p(f"  Known corrected competitions  : {sorted(KNOWN_CORRECTIONS)}")
    p(f"  NEW (potentially unhandled)   : {len(new_col_shift)}")
    p("  Note: This diagnostic uses a deliberately broad detection mask.")
    p("  Non-awarded rows with null/NaN amounts may appear in this count.")
    p("  Review rows containing actual vendor-name text in the amount column")
    p("  before treating a candidate as a true column-shift issue.")
    
    if new_col_shift:
        p()
        p("  *** UNHANDLED COLUMN SHIFTS DETECTED — REVIEW REQUIRED ***")
        for r in new_col_shift[:10]:
            p(
                f"    comp={r['col_00']!r}"
                f"  vendor={r['col_04']!r}"
                f"  amount={r['col_05']!r}"
                f"  awarded={r['col_06']!r}"
                f"  page={r['page_num']}"
            )
        if len(new_col_shift) > 10:
            p(f"    ... and {len(new_col_shift) - 10} more — see diag_2024_col_shift_candidates.csv")
    else:
        p("  ✓ No new column shift candidates beyond known corrections.")
    p()

    p("  ENCODING ARTIFACTS")
    p("  " + "-" * 45)
    p(f"  Rows with encoding artifacts  : {n_encoding}")
    if encoding_artifacts:
        p()
        p("  *** NON-ASCII CHARACTERS DETECTED — REVIEW SAMPLE VALUES ***")
        p("  Note: This check flags all non-ASCII Unicode characters.")
        p("  Legitimate PDF typography (en dashes, smart quotes, non-breaking")
        p("  hyphens, etc.) may appear in this count and does not indicate")
        p("  an extraction error.")
        for r in encoding_artifacts[:10]:
            p(f"    comp={r['col_00']!r}  desc={r.get('artifact_description', '')[:80]}")
        if n_encoding > 10:
            p(f"    ... and {n_encoding - 10} more — see diag_2024_encoding_artifacts.csv")
    else:
        p("  ✓ No non-ASCII character flags detected.")
    p()

    p("  NEXT STEPS FOR REVIEWER")
    p("  " + "-" * 45)
    p("  1. Check delta between accepted and production (527)")
    p("     → If zero: extractor and diagnostic agree — proceed to manual spot-checks")
    p("     → If non-zero: investigate which rows differ and why")
    p()
    p("  2. Open diag_2024_suspicious_col00.csv")
    p("     → Any rows where col_00 contains text that is not a competition number")
    p("     → These rows passed through the permissive filter but may be garbage")
    p()
    p("  3. Open diag_2024_col_shift_candidates.csv")
    p("     → Filter to rows where col_00 NOT IN ('24-085', '24-132')")
    p("     → Any remaining rows are potentially unhandled column shifts")
    p("     → Cross-reference against the source PDF to confirm")
    p()
    p("  4. Check pages with no table detected")
    p("     → Open those pages in the PDF directly")
    p("     → Do they contain visible data rows?")
    p()
    p("  5. Open diag_2024_per_page_table_stats.csv")
    p("     → Pages with 2+ tables: confirm both tables contain real data")
    p("     → Unusually high skipped_empty counts may indicate wrapped descriptions")
    p()
    p("  6. Manual spot-check: confirm 24-006A and 24-006B appear in accepted output")
    p("     → These non-standard formats must be present to confirm permissive")
    p("       filter correctly captures letter-suffix competition numbers")
    p()
    p("=" * 65)
    p("  OUTPUT FILES")
    p("  " + "-" * 45)
    for fpath in [
        OUT_ACCEPTED, OUT_SKIPPED_EMPTY, OUT_HEADER_ROWS,
        OUT_SUSPICIOUS_COL00, OUT_COL_SHIFT, OUT_ENCODING,
        OUT_PAGE_TABLE_STATS, OUT_SUMMARY,
    ]:
        p(f"  {fpath.name}")
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

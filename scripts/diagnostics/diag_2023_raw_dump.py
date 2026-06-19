"""
diag_2023_raw_dump.py
=====================
AUDIT-ONLY DIAGNOSTIC SCRIPT — DO NOT USE AS PRODUCTION EXTRACTOR

Purpose
-------
Expose every raw row that pdfplumber sees when reading awardedbids2023.pdf,
classify each row using the CURRENT production regex (unchanged), and save
four separate audit CSVs so a reviewer can manually assess extraction gaps.

This script:
  - reads awardedbids2023.pdf directly
  - mirrors the production extractor's iteration logic exactly
  - applies the CURRENT production regex: r"\\d{2}-\\d{3}"
  - does NOT modify, overwrite, or touch any production output file
  - writes only to: data/diagnostics/2023/  (created if it doesn't exist)

Row Classification
------------------
  ACCEPTED        row[0] matched the production regex → would be kept
  REJECTED_REGEX  row[0] was non-empty, non-header, but failed the regex
  SKIPPED_EMPTY   row[0] was None or empty string
  HEADER          row[0] matched a known column-header string

Output Files (all in data/diagnostics/2023/)
----------------------------------------
  diag_2023_accepted.csv        — rows the current extractor keeps
  diag_2023_rejected_regex.csv  — rows seen but silently dropped by regex
  diag_2023_skipped_empty.csv   — rows with no value in column 0
  diag_2023_header_rows.csv     — column header rows detected per page

Audit Questions This Script Answers
-------------------------------------
  1. How many total rows did pdfplumber see?
  2. Are any rejected rows real competition numbers?
  3. Are empty-row counts consistent with wrapped-line risk?
  4. Do the four category counts sum to total rows seen? (math closure check)
  5. Does accepted row count match step1_extracted_2023.csv row count?

How to Run
----------
  From the scripts/diagnostics/ directory:
    python diag_2023_raw_dump.py

  Or from the project root:
    python scripts/diagnostics/diag_2023_raw_dump.py

  Or with an explicit PDF path override:
    PDF_OVERRIDE=/path/to/awarded-bids-2023.pdf python scripts/diagnostics/diag_2023_raw_dump.py

Author note: this script is intentionally verbose in its logging.
Every decision point prints its reasoning so the audit trail is self-contained.
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

# --- Path resolution ---
# The production extractor uses shared_utils.py to locate the PDF.
# This diagnostic resolves paths relative to its own location,
# matching the project layout while remaining portable.
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent        # scripts/diagnostics/ → scripts/ → project root

# Primary PDF location (mirrors production extractor's hard-coded path)
PDF_PATH = PROJECT_ROOT / "data" / "raw" / "awarded-bids-2023.pdf"

# Allow environment variable override for portability
if os.environ.get("PDF_OVERRIDE"):
    PDF_PATH = Path(os.environ["PDF_OVERRIDE"])

# Fallback: if the project has a flat layout (PDF beside scripts)
if not PDF_PATH.exists():
    PDF_PATH = SCRIPT_DIR / "awardedbids2023.pdf"

# --- Output directory ---
# Deliberately SEPARATE from data/extracted/ and data/clean/
# This prevents any accidental overwrite of production files.
DIAG_DIR = PROJECT_ROOT / "data" / "diagnostics" / "2023"
DIAG_DIR.mkdir(parents=True, exist_ok=True)

# --- Output file paths ---
OUT_ACCEPTED       = DIAG_DIR / "diag_2023_accepted.csv"
OUT_REJECTED_REGEX = DIAG_DIR / "diag_2023_rejected_regex.csv"
OUT_SKIPPED_EMPTY  = DIAG_DIR / "diag_2023_skipped_empty.csv"
OUT_HEADER_ROWS    = DIAG_DIR / "diag_2023_header_rows.csv"
OUT_SUMMARY        = DIAG_DIR / "diag_2023_audit_summary.txt"

# --- Production regex (UNCHANGED from step1_extract_2023.py) ---
# This is the exact regex in production. Do not modify.
# We test against it to reproduce what production drops.
PRODUCTION_REGEX = re.compile(r"\d{2}-\d{3}")

# --- Known header strings ---
# These are values that appear in row[0] as column headers, not data.
# Mirrors the logic in 2024/2025/2026 extractors.
HEADER_STRINGS = {
    "Competition #",
    "competition #",
    "COMPETITION #",
    "Competition#",
}

# --- Known preamble/footer strings ---
# Row[0] values that are structural PDF text, not data rows.
# The 2025/2026 extractors explicitly skip these.
PREAMBLE_STRINGS_STARTSWITH = [
    "The following contracts",
    "RESULTS OF OPEN",
    "Page ",
]

# --- Expected column count in production output ---
# The production extractor assigns exactly 7 columns.
# Rows with a different cell count are flagged for investigation.
EXPECTED_COL_COUNT = 7
PRODUCTION_ROW_COUNT = 516


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_row(row: list) -> str:
    """
    Classify a single raw pdfplumber row into one of four categories.

    Mirrors the production extractor's decision logic in order:
      1. Check for None/empty row (entire row is null)
      2. Check for None/empty row[0]
      3. Check for header strings in row[0]
      4. Check for preamble strings in row[0]
      5. Apply production regex to row[0]
      6. Anything remaining that failed regex = REJECTED_REGEX

    Returns one of: 'ACCEPTED', 'REJECTED_REGEX', 'SKIPPED_EMPTY', 'HEADER'
    """
    # Entire row is falsy (pdfplumber can return None rows)
    if not row:
        return "SKIPPED_EMPTY"

    cell_zero = row[0]

    # row[0] is None or empty string
    if cell_zero is None or str(cell_zero).strip() == "":
        return "SKIPPED_EMPTY"

    cell_zero_stripped = str(cell_zero).strip()

    # Known column header
    if cell_zero_stripped in HEADER_STRINGS:
        return "HEADER"

    # Preamble/footer structural text
    for prefix in PREAMBLE_STRINGS_STARTSWITH:
        if cell_zero_stripped.startswith(prefix):
            return "HEADER"  # treat structural text same as headers

    # Apply the EXACT production regex
    # Note: production uses re.fullmatch() — we preserve that here.
    if PRODUCTION_REGEX.fullmatch(cell_zero_stripped):
        return "ACCEPTED"

    # Non-empty, non-header, failed regex → the drop zone
    return "REJECTED_REGEX"


def row_to_record(row: list, page_num: int, classification: str) -> dict:
    """
    Convert a raw pdfplumber row to a flat audit record.

    We preserve:
      - page_num: which PDF page this came from
      - classification: the category assigned
      - col_count: how many cells pdfplumber returned (7 = normal)
      - col_00 through col_06: the raw cell values (up to 7)
      - col_00_raw_repr: repr() of cell_zero for whitespace inspection

    For rows with more or fewer than 7 cells, extra columns are
    blank and missing columns are noted — this surfaces Failure Mode D.
    """
    record = {
        "page_num":        page_num,
        "classification":  classification,
        "col_count":       len(row) if row else 0,
        "col_count_flag":  "OK" if (row and len(row) == EXPECTED_COL_COUNT) else "MISMATCH",
    }

    # Store cell values by position, padded to 7 slots
    for i in range(EXPECTED_COL_COUNT):
        key = f"col_{i:02d}"
        if row and i < len(row):
            val = row[i]
            record[key] = str(val).replace("\n", " ").strip() if val is not None else ""
        else:
            record[key] = ""

    # Raw repr of cell 0 to expose hidden whitespace or newlines
    if row and row[0] is not None:
        record["col_00_raw_repr"] = repr(row[0])
    else:
        record["col_00_raw_repr"] = repr(None)

    return record


# ============================================================
# MAIN AUDIT LOOP
# ============================================================

def run_audit():
    """
    Main entry point. Opens the PDF, iterates every page and every row,
    classifies each row, accumulates results, and writes audit outputs.
    """

    run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 65)
    print("  diag_2023_raw_dump.py — 2023 EXTRACTION AUDIT")
    print(f"  Run timestamp : {run_timestamp}")
    print(f"  PDF path      : {PDF_PATH}")
    print(f"  Exists        : {PDF_PATH.exists()}")
    print(f"  Output dir    : {DIAG_DIR}")
    print(f"  Production regex: {PRODUCTION_REGEX.pattern!r}")
    print("=" * 65)
    print()

    if not PDF_PATH.exists():
        print(f"  ERROR: PDF not found at {PDF_PATH}")
        print("  Set PDF_OVERRIDE environment variable to the correct path.")
        print("  Example: PDF_OVERRIDE=/path/to/awarded-bids-2023.pdf python diag_2023_raw_dump.py")
        return

    # Accumulators — one list per classification bucket
    accepted        = []
    rejected_regex  = []
    skipped_empty   = []
    header_rows     = []

    # Per-page stats for the audit summary
    page_stats = []

    # Grand total of every row pdfplumber handed us
    total_rows_seen = 0

    # --------------------------------------------------------
    # PDF ITERATION
    # This mirrors the production extractor exactly:
    #   - uses pdfplumber.open() as context manager
    #   - iterates pdf.pages with page_num starting at 1
    #   - calls page.extract_table() (singular) — same as production 2023
    #   - uses `or []` fallback — same as production 2023
    # --------------------------------------------------------
    with pdfplumber.open(PDF_PATH) as pdf:

        total_pages = len(pdf.pages)
        print(f"  PDF opened. Total pages: {total_pages}")
        print()

        for page_num, page in enumerate(pdf.pages, start=1):

            # Production 2023 uses extract_table() — singular, not plural.
            # This is a known difference from 2024/2025/2026 extractors.
            # We reproduce it exactly so results are comparable.
            raw_table = page.extract_table() or []

            page_accepted       = 0
            page_rejected_regex = 0
            page_skipped_empty  = 0
            page_header_rows    = 0
            page_total          = len(raw_table)

            for row in raw_table:
                total_rows_seen += 1
                classification = classify_row(row)
                record = row_to_record(row, page_num, classification)

                if classification == "ACCEPTED":
                    accepted.append(record)
                    page_accepted += 1

                elif classification == "REJECTED_REGEX":
                    rejected_regex.append(record)
                    page_rejected_regex += 1

                elif classification == "SKIPPED_EMPTY":
                    skipped_empty.append(record)
                    page_skipped_empty += 1

                elif classification == "HEADER":
                    header_rows.append(record)
                    page_header_rows += 1

            page_stats.append({
                "page_num":          page_num,
                "total_rows":        page_total,
                "accepted":          page_accepted,
                "rejected_regex":    page_rejected_regex,
                "skipped_empty":     page_skipped_empty,
                "header_rows":       page_header_rows,
                "table_found":       "YES" if page_total > 0 else "NO — INVESTIGATE",
            })

            # Print per-page progress so the analyst sees live feedback
            table_indicator = "" if page_total > 0 else "  *** NO TABLE DETECTED ***"
            print(
                f"  Page {page_num:>3}/{total_pages}"
                f"  rows_seen={page_total:>4}"
                f"  accepted={page_accepted:>4}"
                f"  rejected={page_rejected_regex:>3}"
                f"  empty={page_skipped_empty:>3}"
                f"  header={page_header_rows:>2}"
                f"{table_indicator}"
            )

    print()

    # --------------------------------------------------------
    # MATH CLOSURE CHECK
    # The four bucket counts MUST sum to total_rows_seen.
    # Any discrepancy means classify_row() has a gap — a bug
    # in this diagnostic script itself.
    # --------------------------------------------------------
    total_classified = (
        len(accepted)
        + len(rejected_regex)
        + len(skipped_empty)
        + len(header_rows)
    )

    math_closes = (total_classified == total_rows_seen)

    # --------------------------------------------------------
    # WRITE OUTPUT CSVs
    # --------------------------------------------------------
    fieldnames = [
        "page_num", "classification", "col_count", "col_count_flag",
        "col_00", "col_01", "col_02", "col_03", "col_04", "col_05", "col_06",
        "col_00_raw_repr",
    ]

    def write_csv(records: list, path: Path, label: str):
        df_out = pd.DataFrame(records, columns=fieldnames)
        df_out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"  Saved {label:<30} → {path.name}  ({len(records):,} rows)")

    print("  Writing audit CSVs...")
    print()
    write_csv(accepted,       OUT_ACCEPTED,       "ACCEPTED")
    write_csv(rejected_regex, OUT_REJECTED_REGEX, "REJECTED_REGEX")
    write_csv(skipped_empty,  OUT_SKIPPED_EMPTY,  "SKIPPED_EMPTY")
    write_csv(header_rows,    OUT_HEADER_ROWS,    "HEADER_ROWS")

    # --------------------------------------------------------
    # COMPUTE SUMMARY METRICS
    # --------------------------------------------------------
    n_accepted      = len(accepted)
    n_rejected      = len(rejected_regex)
    n_empty         = len(skipped_empty)
    n_header        = len(header_rows)

    rejection_rate  = (n_rejected / (n_accepted + n_rejected) * 100) if (n_accepted + n_rejected) > 0 else 0.0

    pages_no_table  = [p for p in page_stats if p["table_found"].startswith("NO")]
    pages_high_reject = [
        p for p in page_stats
        if p["rejected_regex"] > 0
    ]

    # Col-count mismatches in accepted rows
    accepted_mismatch = [r for r in accepted if r["col_count_flag"] == "MISMATCH"]

    # Unique values seen in col_00 of rejected rows
    # These are the most important values to review manually
    rejected_col00_values = sorted(set(r["col_00"] for r in rejected_regex))

    # --------------------------------------------------------
    # PRINT AUDIT SUMMARY
    # --------------------------------------------------------
    summary_lines = []

    def p(line=""):
        print(line)
        summary_lines.append(line)

    p()
    p("=" * 65)
    p("  AUDIT SUMMARY — diag_2023_raw_dump.py")
    p(f"  Run timestamp    : {run_timestamp}")
    p(f"  PDF              : {PDF_PATH.name}")
    p(f"  Total pages      : {total_pages}")
    p("=" * 65)
    p()
    p("  ROW COUNT BREAKDOWN")
    p("  " + "-" * 45)
    p(f"  Total rows seen by pdfplumber : {total_rows_seen:>6,}")
    p(f"  ├── ACCEPTED (regex match)    : {n_accepted:>6,}")
    p(f"  ├── REJECTED_REGEX            : {n_rejected:>6,}")
    p(f"  ├── SKIPPED_EMPTY             : {n_empty:>6,}")
    p(f"  └── HEADER / structural       : {n_header:>6,}")
    p(f"  Total classified              : {total_classified:>6,}")
    p()
    if math_closes:
        p("  ✓ MATH CLOSURE: classified count == rows seen  (audit is complete)")
    else:
        p(f"  ✗ MATH CLOSURE FAILED: {total_rows_seen} seen vs {total_classified} classified")
        p("    This is a bug in this diagnostic script. Do not trust results.")
    p()

    p("  KEY METRICS")
    p("  " + "-" * 45)
    p(f"  Rejection rate (rejected / accepted+rejected): {rejection_rate:.1f}%")
    p(f"  Pages with no table detected    : {len(pages_no_table)}")
    p(f"  Pages with at least 1 rejection : {len(pages_high_reject)}")
    p(f"  Accepted rows with col mismatch : {len(accepted_mismatch)}")
    p()

    if pages_no_table:
        p("  *** PAGES WITH NO TABLE — INVESTIGATE MANUALLY ***")
        for pg in pages_no_table:
            p(f"    Page {pg['page_num']}")
        p()

    if rejected_col00_values:
        p("  UNIQUE COL_00 VALUES IN REJECTED ROWS")
        p("  (Read these carefully — are any real competition numbers?)")
        p("  " + "-" * 45)
        for val in rejected_col00_values:
            # Add a hint flag for values that look like they COULD be comp numbers
            # but don't match the current narrow regex
            looks_like_comp = bool(re.match(r"\d{2}-", val))
            flag = "  ← possible comp# — REVIEW" if looks_like_comp else ""
            p(f"    {val!r}{flag}")
        p()
    else:
        p("  No rejected rows found. Regex may be capturing everything visible.")
        p()

    p("  COMPARISON POINT FOR REVIEWER")
    p("  " + "-" * 45)
    p(f"  step1_extracted_2023.csv row count   : {PRODUCTION_ROW_COUNT}  (known production output)")
    p(f"  diag_2023_accepted row count         : {n_accepted:,}")
    delta = n_accepted - PRODUCTION_ROW_COUNT
    delta_str = f"+{delta}" if delta >= 0 else str(delta)
    p(f"  Delta (accepted - production)        : {delta_str}")
    if delta != 0:
        p(f"  *** Delta is non-zero — investigate why accepted != production output ***")
    else:
        p(f"  ✓ Accepted count matches production output exactly")
    p()

    p("  OUTPUT FILES")
    p("  " + "-" * 45)
    p(f"  {OUT_ACCEPTED.name:<45} {n_accepted:,} rows")
    p(f"  {OUT_REJECTED_REGEX.name:<45} {n_rejected:,} rows")
    p(f"  {OUT_SKIPPED_EMPTY.name:<45} {n_empty:,} rows")
    p(f"  {OUT_HEADER_ROWS.name:<45} {n_header:,} rows")
    p(f"  {OUT_SUMMARY.name:<45} (this summary)")
    p()
    p("  NEXT STEPS FOR REVIEWER")
    p("  " + "-" * 45)
    p("  1. Open diag_2023_rejected_regex.csv")
    p("     → Look at col_00 values. Any that look like comp numbers?")
    p("     → Look at col_00_raw_repr. Any hidden whitespace causing false rejects?")
    p()
    p("  2. Open diag_2023_skipped_empty.csv")
    p("     → Are empty rows clustered on the same pages?")
    p("     → Do adjacent accepted rows have truncated descriptions?")
    p("       (evidence of wrapped-line split problem)")
    p()
    p("  3. Check pages_no_table list above")
    p("     → Open those page numbers in the PDF directly")
    p("     → Do they contain real data rows?")
    p()
    p("  4. Check accepted rows with col_count_flag == MISMATCH")
    p("     → A row with 6 or 8 cells may have field misalignment")
    p("     → These are the rows most likely to have corrupt vendor/date values")
    p()
    p(f"  5. Compare accepted row count to production ({PRODUCTION_ROW_COUNT})")
    p("     → If equal: production and this diagnostic agree on what was seen")
    p("     → If different: the two scripts are iterating the PDF differently")
    p("       (most likely cause: extract_table vs extract_tables)")
    p()
    p("=" * 65)
    p("  END OF AUDIT SUMMARY")
    p("=" * 65)

    # --------------------------------------------------------
    # WRITE SUMMARY TO TEXT FILE
    # --------------------------------------------------------
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

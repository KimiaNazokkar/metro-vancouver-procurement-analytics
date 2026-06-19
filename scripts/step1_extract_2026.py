"""
step1_extract_2026.py

Extract Metro Vancouver 2026 awarded-bids data from the source PDF.

Purpose:
- Read the 2026 Awarded Bids Register PDF using pdfplumber
- Extract tabular procurement award rows
- Remove PDF header and explanatory rows
- Normalize line breaks in extracted text
- Normalize award-status values from Y/N to Yes/No
- Apply source-verified award-status correction for competition 25-0001
- Normalize currency spacing in awarded_amount
- Save extracted rows to data/extracted/step1_extracted_2026.csv

Pipeline position:
raw PDF → step1 extraction → step2 merge
"""

import pandas as pd
import pdfplumber

from shared_utils import RAW_DIR, EXTRACTED_DIR


PDF_PATH = RAW_DIR / "awarded-bids-2026.pdf"
OUTPUT_PATH = EXTRACTED_DIR / "step1_extracted_2026.csv"

COLUMNS = [
    "competition_number",
    "competition_type",
    "competition_description",
    "awarded_date",
    "vendor_name",
    "awarded_amount",
    "is_awarded",
]


def clean_text(value):
    """Normalize line breaks and surrounding whitespace in extracted PDF text."""
    if isinstance(value, str):
        return value.replace("\n", " ").strip()

    return value


def normalize_amount(value):
    """Normalize spacing and blank values in awarded_amount."""
    if not isinstance(value, str):
        return value

    value = value.replace(" ", "").strip()

    if value == "":
        return None

    return value


def main():
    rows = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []

            for table in tables:
                rows.extend(table)

    clean_rows = []

    for row in rows:
        if not row:
            continue

        if row[0] in [None, "Competition #"]:
            continue

        if str(row[0]).startswith("The following contracts"):
            continue

        clean_rows.append(row)

    df = pd.DataFrame(clean_rows, columns=COLUMNS)

    df = df.map(clean_text)

    df = df.replace("", pd.NA)
    df = df.dropna(how="all")

    source_correction_mask = (
        (df["competition_number"] == "25-0001")
        & (df["vendor_name"] == "DBA B&B Heavy Civil Construction Ltd.")
        & (df["awarded_amount"].notna())
    )
    # Correction uses pre-normalized "Y" so it flows through the same Y/N → Yes/No mapping as source rows.
    df.loc[source_correction_mask, "is_awarded"] = "Y"

    df["is_awarded"] = df["is_awarded"].replace({
        "Y": "Yes",
        "N": "No",
    })

    df["awarded_amount"] = df["awarded_amount"].apply(normalize_amount)

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    amount_blank = (
        df["awarded_amount"].isna()
        | (df["awarded_amount"] == "")
    ).sum()

    amount_na_upper = (df["awarded_amount"] == "N/A").sum()
    amount_na_plain = (df["awarded_amount"] == "NA").sum()

    yes_blank = (
        (df["is_awarded"] == "Yes")
        & (
            df["awarded_amount"].isna()
            | (df["awarded_amount"] == "")
        )
    ).sum()

    no_numeric = (
        (df["is_awarded"] == "No")
        & (~df["awarded_amount"].isin(["N/A", "NA", "", None]))
    ).sum()

    print("=" * 60)
    print("STEP 1 EXTRACTION — 2026")
    print("=" * 60)
    print(f"Rows extracted: {len(df):,}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nAwarded values:")
    print(df["is_awarded"].value_counts(dropna=False))

    print("\nAmount validation:")
    print(f"Blank amounts: {amount_blank:,}")
    print(f"N/A amounts: {amount_na_upper:,}")
    print(f"NA amounts: {amount_na_plain:,}")
    print(f"Yes + blank: {yes_blank:,}")
    print(f"No + numeric: {no_numeric:,}")

    print("\n2026-specific corrections:")
    print(
        "Source-verified award-status corrections: "
        f"{source_correction_mask.sum():,} rows "
        "(competition 25-0001)"
    )


if __name__ == "__main__":
    main()
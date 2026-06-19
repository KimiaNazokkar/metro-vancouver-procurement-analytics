"""
step1_extract_2025.py

Extract Metro Vancouver 2025 awarded-bids data from the source PDF.

Purpose:
- Read the 2025 Awarded Bids Register PDF using pdfplumber
- Extract tabular procurement award rows
- Remove PDF header and explanatory rows
- Normalize line breaks in extracted text
- Normalize currency spacing and C$. currency artifacts
- Apply source-verified award-status correction for competition 25-064
- Save extracted rows to data/extracted/step1_extracted_2025.csv

Pipeline position:
raw PDF → step1 extraction → step2 merge
"""

import pandas as pd
import pdfplumber

from shared_utils import RAW_DIR, EXTRACTED_DIR


PDF_PATH = RAW_DIR / "awarded-bids-2025.pdf"
OUTPUT_PATH = EXTRACTED_DIR / "step1_extracted_2025.csv"

COLUMNS = [
    "competition_number",
    "competition_type",
    "competition_description",
    "awarded_date",
    "vendor_name",
    "awarded_amount",
    "is_awarded",
]

VENDORS_25064_YES = [
    "B.A. BLACKTOP LTD",
    "GB Paving",
    "WINVAN PAVING A DIVISION OF MAINLAND CONSTRUCTION MATERIALS ULC.",
    "PALMIERI BROS. PAVING LTD.",
    "KEYWEST ASPHALT LTD",
]


def clean_text(value):
    """Normalize line breaks and surrounding whitespace in extracted PDF text."""
    if isinstance(value, str):
        return value.replace("\n", " ").strip()

    return value


def normalize_amount(value):
    """Normalize spacing and known currency artifacts in awarded_amount."""
    if not isinstance(value, str):
        return value

    value = value.replace(" ", "").strip()
    value = value.replace("C$.", "$")  # pdfplumber artifact: C$. → $

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

    source_correction_mask = (
        (df["competition_number"] == "25-064")
        & (df["vendor_name"].isin(VENDORS_25064_YES))
    )

    df.loc[source_correction_mask, "is_awarded"] = "Yes"

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
    print("STEP 1 EXTRACTION — 2025")
    print("=" * 60)
    print(f"Rows extracted: {len(df):,}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nAwarded values:")
    print(df["is_awarded"].value_counts(dropna=False))

    print("\nAmount validation:")
    print(f"Blank amounts: {amount_blank:,}")
    print(f"N/A amounts: {amount_na_upper:,}")
    print(f"NA amounts: {amount_na_plain:,}")
    print(
        f"Yes + blank: {yes_blank:,} "
        "(includes group awards, framework values, and non-disclosed amounts)"
    )
    print(f"No + numeric: {no_numeric:,}")

    print("\n2025-specific corrections:")
    print(
        "Source-verified award-status corrections: "
        f"{source_correction_mask.sum():,} rows "
        "(competition 25-064)"
    )


if __name__ == "__main__":
    main()
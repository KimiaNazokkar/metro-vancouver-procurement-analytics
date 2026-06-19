"""
step1_extract_2023.py

Extract Metro Vancouver 2023 awarded-bids data from the source PDF.

Purpose:
- Read the 2023 Awarded Bids Register PDF using pdfplumber
- Extract tabular procurement award rows
- Keep rows with valid competition numbers
- Normalize line breaks in competition descriptions
- Save extracted rows to data/extracted/step1_extracted_2023.csv

Pipeline position:
raw PDF → step1 extraction → step2 merge
"""

import re

import pandas as pd
import pdfplumber

from shared_utils import RAW_DIR, EXTRACTED_DIR


PDF_PATH = RAW_DIR / "awarded-bids-2023.pdf"
OUTPUT_PATH = EXTRACTED_DIR / "step1_extracted_2023.csv"

COLUMNS = [
    "competition_number",
    "competition_type",
    "competition_description",
    "awarded_date",
    "vendor_name",
    "awarded_amount",
    "is_awarded",
]


def main():
    rows = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            table = page.extract_table() or []

            for row in table:
                if not row or not row[0]:
                    continue

                competition_number = str(row[0]).strip()

                if re.fullmatch(r"\d{2}-\d{3}", competition_number):
                    rows.append(row)

    df = pd.DataFrame(rows, columns=COLUMNS)

    df["competition_description"] = (
        df["competition_description"]
        .astype("string")
        .str.replace("\n", " ", regex=False)
    )

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("=" * 60)
    print("STEP 1 EXTRACTION — 2023")
    print("=" * 60)
    print(f"Rows extracted: {len(df):,}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nAwarded values:")
    print(df["is_awarded"].value_counts(dropna=False))

    amount_blank = (
        df["awarded_amount"].isna()
        | (df["awarded_amount"] == "")
    ).sum()

    amount_na = (df["awarded_amount"] == "N/A").sum()

    yes_blank = (
        (df["is_awarded"] == "Yes")
        & (
            df["awarded_amount"].isna()
            | (df["awarded_amount"] == "")
        )
    ).sum()

    no_numeric = (
        (df["is_awarded"] == "No")
        & (~df["awarded_amount"].isin(["N/A", "", None]))
    ).sum()

    print("\nAmount validation:")
    print(f"Blank amounts: {amount_blank:,}")
    print(f"N/A amounts: {amount_na:,}")
    print(f"Yes + blank: {yes_blank:,}")
    print(f"No + numeric: {no_numeric:,}")


if __name__ == "__main__":
    main()
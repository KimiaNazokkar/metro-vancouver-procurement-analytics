"""
step1_extract_2024.py

Extract Metro Vancouver 2024 awarded-bids data from the source PDF.

Purpose:
- Read the 2024 Awarded Bids Register PDF using pdfplumber
- Extract tabular procurement award rows
- Remove PDF header and explanatory rows
- Normalize currency spacing
- Correct known encoding artifact in one vendor name (AtkinsRéalis)
- Repair vendor names where pdfplumber shifted trailing text into awarded_amount
- Apply source-verified corrections for selected parsing artifacts
- Save extracted rows to data/extracted/step1_extracted_2024.csv

Pipeline position:
raw PDF → step1 extraction → step2 merge
"""

import re

import pandas as pd
import pdfplumber

from shared_utils import RAW_DIR, EXTRACTED_DIR


PDF_PATH = RAW_DIR / "awarded-bids-2024.pdf"
OUTPUT_PATH = EXTRACTED_DIR / "step1_extracted_2024.csv"

COLUMNS = [
    "competition_number",
    "competition_type",
    "competition_description",
    "awarded_date",
    "vendor_name",
    "awarded_amount",
    "is_awarded",
]


def normalize_amount_spacing(value):
    """Remove internal whitespace from currency-formatted values."""
    if not isinstance(value, str):
        return value

    value = value.strip()

    if "$" not in value:
        return value

    return re.sub(r"\s+", "", value)


def merge_vendor_tail(vendor, amount):
    """Repair vendor names where a trailing fragment shifted into awarded_amount."""
    vendor = str(vendor).strip()
    tail = str(amount).replace("NA", "").strip()

    if not tail:
        return vendor

    if tail[0].islower():
        return vendor + tail

    return vendor + " " + tail


def main():
    rows = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []

            for table in tables:
                rows.extend(table)

    filtered_rows = []

    for row in rows:
        if not row:
            continue

        if row[0] in [None, "Competition #"]:
            continue

        if str(row[0]).startswith("The following contracts"):
            continue

        filtered_rows.append(row)

    df = pd.DataFrame(filtered_rows, columns=COLUMNS)

    df = df.map(
        lambda value: value.replace("\n", " ").strip()
        if isinstance(value, str)
        else value
    )

    df["awarded_amount"] = df["awarded_amount"].apply(normalize_amount_spacing)

    df["vendor_name"] = (
        df["vendor_name"]
        .astype("string")
        # Correct pdfplumber encoding artifact: √© → é (AtkinsRéalis)
        .str.replace("AtkinsR√©alis", "AtkinsRéalis", regex=False)
    )

    mask_vendor_tail_in_amount = (
        (df["is_awarded"] == "No")
        & (df["awarded_amount"].astype("string").str.contains(r"[A-Za-z]", na=False))
        & (df["awarded_amount"].astype("string").str.strip().str.endswith("NA", na=False))
    )

    df.loc[mask_vendor_tail_in_amount, "vendor_name"] = [
        merge_vendor_tail(vendor, amount)
        for vendor, amount in zip(
            df.loc[mask_vendor_tail_in_amount, "vendor_name"],
            df.loc[mask_vendor_tail_in_amount, "awarded_amount"],
        )
    ]

    df.loc[mask_vendor_tail_in_amount, "awarded_amount"] = "NA"

    # Manual source-verified corrections for pdfplumber column-shift parsing artifacts
    # in the 2024 PDF layout. The source document values are correct; the PDF layout
    # caused pdfplumber to misalign wrapped text into adjacent fields for these rows.
    df.loc[
        (df["competition_number"] == "24-085")
        & (df["is_awarded"] == "Yes"),
        ["awarded_date", "vendor_name"],
    ] = ["3-Dec-24", "Prime Boiler Services Ltd."]

    df.loc[
        (df["competition_number"] == "24-085")
        & (df["is_awarded"] == "No"),
        ["awarded_date", "vendor_name"],
    ] = ["3-Dec-24", "Emona Sales Ltd."]

    df.loc[
        (df["competition_number"] == "24-132")
        & (df["is_awarded"] == "Yes")
        & (df["awarded_amount"].notna()),
        ["awarded_date", "vendor_name"],
    ] = ["1-Dec-24", "Jacobs Consultancy Canada Inc."]

    df.loc[
        (df["competition_number"] == "24-132")
        & (df["is_awarded"] == "Yes")
        & (df["awarded_amount"].isna()),
        ["awarded_date", "vendor_name"],
    ] = ["1-Dec-24", "Brown and Caldwell"]

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
    print("STEP 1 EXTRACTION — 2024")
    print("=" * 60)
    print(f"Rows extracted: {len(df):,}")
    print(f"Saved to: {OUTPUT_PATH}")

    print("\nAwarded values:")
    print(df["is_awarded"].value_counts(dropna=False))

    print("\nAmount field summary (extracted values, pre-cleaning):")
    print(f"Blank amounts: {amount_blank:,}")
    print(f"N/A amounts: {amount_na_upper:,}")
    print(f"NA amounts: {amount_na_plain:,}")
    print(f"Yes + blank: {yes_blank:,}")
    print(f"No + numeric: {no_numeric:,}")

    manual_correction_mask = df["competition_number"].isin(["24-085", "24-132"])

    print("\n2024-specific corrections:")
    print(
        "Vendor-tail column shift repairs applied: "
        f"{mask_vendor_tail_in_amount.sum():,} rows"
    )
    print(
        "Source-verified manual corrections: "
        f"{manual_correction_mask.sum():,} rows "
        "(competitions 24-085, 24-132)"
    )


if __name__ == "__main__":
    main()
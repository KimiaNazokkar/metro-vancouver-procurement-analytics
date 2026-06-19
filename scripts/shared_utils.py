"""
shared_utils.py

Shared path configuration for the Metro Vancouver procurement analytics pipeline.

This module centralizes project directory paths so extraction, cleaning, and
normalization scripts read from and write to consistent locations.
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
CLEAN_DIR = DATA_DIR / "clean"
DIAGNOSTICS_DIR = DATA_DIR / "diagnostics"

# Ensure required project directories exist.
for directory in [RAW_DIR, EXTRACTED_DIR, CLEAN_DIR, DIAGNOSTICS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
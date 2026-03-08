"""
electrical_data_loader.py
=========================
Single-responsibility script: load, clean, and persist electrical
measurements data from the raw TXT file.

This script does ONE thing only:
  Read  →  data/data-example.txt
  Write →  data/electrical_data.parquet   (used by the dashboard)

Run with:
    python scripts/electrical_data_loader.py

Output columns
--------------
  DateTime            combined date + time (pandas Timestamp)
  Date                original date string  (dd/mm/yyyy)
  Time                original time string
  AN(V)  BN(V)  CN(V)  NG(V)   phase-to-neutral voltages  (float, Volts)
  A(A)   B(A)   C(A)   N(A)    line currents              (float, Amps)
  ...any additional columns present in the source file are preserved...

Parquet format is used for the output because it:
  - Preserves dtypes (datetime, float64) exactly — no re-parsing on load
  - Compresses well for large measurement files
  - Loads in milliseconds compared with CSV re-parsing
"""

import os
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Path setup — allow running from the project root OR from scripts/
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from logger import logger
from utils.decorators.schedule import schedule

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

INPUT_FILE  = os.path.join(_PROJECT_ROOT, "data", "data-example.txt")
OUTPUT_FILE = os.path.join(_PROJECT_ROOT, "data", "electrical_data.parquet")

# All measurement columns we expect.  Any that are absent are silently skipped.
VOLTAGE_COLUMNS = ["AN(V)", "BN(V)", "CN(V)", "NG(V)"]
CURRENT_COLUMNS = ["A(A)",  "B(A)",  "C(A)",  "N(A)"]
NUMERIC_COLUMNS = VOLTAGE_COLUMNS + CURRENT_COLUMNS

# ---------------------------------------------------------------------------
# DATA LOADER
# ---------------------------------------------------------------------------


@schedule()
def get_data() -> pd.DataFrame:
    """
    Load electrical measurements from the tab-separated TXT file.

    Steps
    -----
    1. Read the raw file — all columns as strings to avoid silent coercion.
    2. Convert measurement columns to float64.
    3. Combine 'Date' + 'Time' into a single DateTime column.
    4. Return the clean DataFrame.
    """
    try:
        logger.info("Loading electrical measurements data from TXT file …")

        # ── 1. Read raw ──────────────────────────────────────────────────────
        df = pd.read_csv(
            INPUT_FILE,
            sep="\t",
            dtype=str,
            na_values=["", "NA", "N/A", "null", "NULL", "None", "#N/A"],
            keep_default_na=True,
        )

        logger.info(f"Raw data loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        logger.info(f"Columns: {list(df.columns)}")

        # ── 2. Convert numeric columns ────────────────────────────────────────
        for col in NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ── 3. Build DateTime ─────────────────────────────────────────────────
        if "Date" in df.columns and "Time" in df.columns:
            # Raw time strings sometimes carry milliseconds written as
            # "10:45:30 AM.471" — strip the dot-millisecond suffix so
            # strptime can parse the remainder cleanly.
            clean_time = df["Time"].str.replace(
                r"\.(AM|PM)\.(\d+)|(AM|PM)\.(\d+)",
                lambda m: (m.group(1) or m.group(3)) or "",
                regex=True,
            )
            # Also normalise the simpler "AM.471" / "PM.123" pattern
            clean_time = clean_time.str.replace(
                r"(AM|PM)\.\d+", r"\1", regex=True
            )

            df["DateTime"] = pd.to_datetime(
                df["Date"] + " " + clean_time,
                format="%d/%m/%Y %I:%M:%S %p",
                errors="coerce",
            )

            # Report any rows that failed to parse
            bad = df["DateTime"].isna().sum()
            if bad:
                logger.warning(
                    f"{bad} rows could not be parsed into DateTime — "
                    "they will appear as NaT in the output."
                )
            logger.info("DateTime column created.")

        logger.info(
            f"Data processing complete: {df.shape[0]} rows, "
            f"{df.shape[1]} columns"
        )
        logger.info(f"Data types:\n{df.dtypes.to_string()}")

        return df

    except FileNotFoundError:
        logger.error(f"Input file not found: {INPUT_FILE}")
        raise
    except Exception as exc:
        logger.error(f"Error loading data: {exc}")
        raise


# ---------------------------------------------------------------------------
# PERSIST OUTPUT
# ---------------------------------------------------------------------------


def save_data(df: pd.DataFrame) -> None:
    """Save the cleaned DataFrame to Parquet so the dashboard can load it."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False, engine="pyarrow")
    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    logger.info(f"Saved → {OUTPUT_FILE}  ({size_kb:.1f} KB)")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Electrical Data Loader — starting")
    logger.info("=" * 60)

    df = get_data()
    save_data(df)

    logger.info("=" * 60)
    logger.info("Done.  Run electrical_dashboard.py to view the data.")
    logger.info("=" * 60)

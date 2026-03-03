"""
csv_cleaner.py
==============
CSV cleaner for pantograph monitoring system data — Arc Analysis M12.

Pantograph CSVs have a non-standard layout that plain pd.read_csv() cannot
handle correctly.  This script deals with the following quirks automatically:

  QUIRK 1 — Paired columns
    Each measurement has TWO columns in the raw file:
      Column A: the numeric value   e.g.  42.7
      Column B: the unit string     e.g.  µA/cm²
    We extract the unit, rename column A to include it, and drop column B.

  QUIRK 2 — Timestamp in the column header
    Headers look like:  "Arc 14:32:01"  or  "Contact Force 09:15:00"
    We strip the time suffix to get a clean measurement name.

  QUIRK 3 — Extra rows before the data starts
    The file may have 1–4 rows of metadata (date, run ID, channel numbers,
    units row) sitting between the header row and the actual data rows.
    We detect and skip these automatically.

  QUIRK 4 — Mixed numeric / text cells
    Unit strings, dashes, and blank cells appear in value columns.
    We coerce everything to numeric and report how many cells were invalid.

What this script produces:
  - A cleaned CSV with standardised column names and numeric values only.
  - A plain-English cleaning report printed to the terminal.
  - The output file saved to your OneDrive Outputs folder.

Run with:
    python 02-Scripts/csv_cleaner.py

Required libraries:  pandas  numpy  chardet  tqdm
"""

import os
import re
import sys

import chardet
import numpy as np
import pandas as pd
from tqdm import tqdm

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Where to save the cleaned output.
# Adjust to match your OneDrive path.
ONEDRIVE_OUTPUTS = os.path.join(
    os.path.expanduser("~"), "OneDrive", "Projects", "Arc-Analysis-M12", "Outputs"
)

# How many rows to read at a time when processing large files.
# 10,000 rows is safe on most machines.  Increase to 50,000 if you have
# plenty of RAM and want faster processing.
CHUNK_SIZE = 10_000

# Maximum number of header rows to scan when auto-detecting the layout.
HEADER_SCAN_ROWS = 10

# Physics-based sanity ranges for pantograph measurements.
# Readings outside these ranges are flagged (not deleted) as suspect.
# Adjust if your specific line has different operating parameters.
SANITY_RANGES = {
    # column keyword  : (min,   max,   unit hint)
    "arc"             : (0,     10_000, "µA/cm²"),
    "contact_force"   : (0,     500,    "N"),
    "force"           : (0,     500,    "N"),
    "height"          : (2_000, 8_000,  "mm"),   # contact wire height
    "stagger"         : (-400,  400,    "mm"),
    "speed"           : (0,     400,    "km/h"),
    "acceleration"    : (-50,   50,     "m/s²"),
    "current"         : (0,     5_000,  "A"),
    "uplift"          : (-50,   300,    "mm"),
}

# Regex that matches a time suffix in a column header, e.g. "14:32:01"
# or a date like "01/03/2026" or "2026-03-01".
_TIME_RE  = re.compile(r"\b\d{1,2}:\d{2}(:\d{2})?\b")
_DATE_RE  = re.compile(r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b")

# ---------------------------------------------------------------------------
# STEP 1 — ENCODING DETECTION
# ---------------------------------------------------------------------------


def detect_encoding(filepath: str) -> str:
    """
    Read up to 100 KB of the file as raw bytes and use the chardet library
    to guess the character encoding.

    Why this matters: pantograph system software is often set to a European
    locale that writes files in Windows-1252 rather than UTF-8.  If we open
    the file with the wrong encoding, special characters (µ, °, ±) turn into
    garbage and some cells fail to parse.
    """
    print("\n[1/6] Detecting file encoding …")
    with open(filepath, "rb") as fh:
        sample = fh.read(100_000)
    result   = chardet.detect(sample)
    encoding = result.get("encoding") or "utf-8"
    conf     = result.get("confidence", 0) * 100
    print(f"      Detected : {encoding}  (confidence {conf:.0f}%)")
    # chardet sometimes returns 'ascii' for plain latin-1 files; widen it.
    if encoding.lower() in ("ascii",):
        encoding = "latin-1"
        print("      Widened  : latin-1  (ascii is a subset — safer choice)")
    return encoding


# ---------------------------------------------------------------------------
# STEP 2 — RAW PREVIEW & HEADER DETECTION
# ---------------------------------------------------------------------------


def sniff_header_row(filepath: str, encoding: str) -> int:
    """
    Read the first HEADER_SCAN_ROWS lines and decide which line is the
    real column-header row.

    Heuristic: the header row is the one with the most non-numeric cells
    (because column names are text, whereas data rows are mostly numbers).

    Returns the 0-based row index to pass to pd.read_csv(header=...).
    """
    print("\n[2/6] Detecting header row position …")
    raw_rows = []
    with open(filepath, encoding=encoding, errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= HEADER_SCAN_ROWS:
                break
            raw_rows.append(line.rstrip("\n").split(","))

    if not raw_rows:
        return 0

    scores = []
    for i, row in enumerate(raw_rows):
        # Count cells that look like text (not purely numeric / blank)
        text_count = sum(
            1 for cell in row
            if cell.strip() and not _looks_numeric(cell.strip())
        )
        scores.append((text_count, i))

    best_row = max(scores, key=lambda x: x[0])[1]
    print(f"      Raw first {len(raw_rows)} rows:")
    for i, row in enumerate(raw_rows):
        marker = "  ← header" if i == best_row else ""
        preview = ", ".join(f'"{c}"' for c in row[:6])
        if len(row) > 6:
            preview += f", … (+{len(row)-6} more)"
        print(f"      Row {i}: {preview}{marker}")

    print(f"\n      Using row {best_row} as header.")
    return best_row


def _looks_numeric(value: str) -> bool:
    """Return True if the string looks like a number (int, float, NaN, dash)."""
    value = value.strip().replace(",", ".")
    if value in ("", "-", "–", "—", "nan", "NaN", "N/A", "n/a"):
        return True
    try:
        float(value)
        return True
    except ValueError:
        return False


def preview_raw(filepath: str, encoding: str, header_row: int):
    """
    Print a readable preview of the raw file so you can see the layout
    before we start transforming anything.
    """
    print("\n      Raw file preview (first 8 rows after header):")
    df_raw = pd.read_csv(
        filepath,
        encoding=encoding,
        header=header_row,
        nrows=8,
        low_memory=False,
    )
    print(df_raw.to_string())


# ---------------------------------------------------------------------------
# STEP 3 — PARSE THE PANTOGRAPH FORMAT
# ---------------------------------------------------------------------------


def parse_pantograph_csv(filepath: str, encoding: str, header_row: int) -> pd.DataFrame:
    """
    Load the full file and apply pantograph-specific structural fixes:

      A) Strip timestamps from column headers
         "Arc 14:32:01"  →  "Arc"

      B) Identify units columns
         Pantograph CSVs place a units column immediately after each value
         column.  The units column contains strings like "N", "mm", "µA/cm²".
         We read the first unit value, append it to the measurement name,
         then drop the units column entirely.

         Example:
           Before:  | Contact Force 09:00 | Unnamed: 3 | Height 09:00 | Unnamed: 5 |
           After:   | contact_force_n     |             | height_mm    |             |

      C) Skip non-data rows
         Rows where the first column contains a time or date string
         (not a number) are metadata rows — we skip them.

      D) Coerce all value columns to numeric
         Any remaining text (dashes, blanks, stray unit strings that slipped
         into value cells) becomes NaN.

    Returns a clean DataFrame ready for analysis.
    """
    print("\n[3/6] Parsing pantograph CSV format …")

    # ── Load in chunks to handle large files ──────────────────────────────
    reader = pd.read_csv(
        filepath,
        encoding=encoding,
        header=header_row,
        chunksize=CHUNK_SIZE,
        low_memory=False,
        dtype=str,          # read everything as text first — we convert later
    )

    chunks = []
    for chunk in tqdm(reader, desc="      Loading chunks", unit="chunk"):
        chunks.append(chunk)

    if not chunks:
        print("ERROR: File appears to be empty after the header row.")
        sys.exit(1)

    df = pd.concat(chunks, ignore_index=True)
    print(f"      Raw shape : {df.shape[0]:,} rows × {df.shape[1]} columns")

    # ── A: Strip timestamps from column names ────────────────────────────
    df.columns = [_strip_timestamp(c) for c in df.columns]
    print("      Stripped timestamps from column headers.")

    # ── B: Detect and process units columns ──────────────────────────────
    df, col_units = _process_units_columns(df)
    print(f"      Units columns processed.  Measurement→unit map:")
    for col, unit in col_units.items():
        print(f"        {col:35s} → {unit}")

    # ── C: Drop non-data rows (timestamp / metadata rows) ────────────────
    first_col = df.columns[0]
    is_data_row = df[first_col].apply(_looks_numeric)
    dropped = (~is_data_row).sum()
    if dropped:
        print(f"      Dropped {dropped:,} non-data rows (metadata / timestamp rows).")
    df = df[is_data_row].reset_index(drop=True)

    # ── D: Coerce all columns to numeric ─────────────────────────────────
    coerce_report = {}
    for col in df.columns:
        before_nulls = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col].str.strip(), errors="coerce")
        new_nulls = df[col].isna().sum() - before_nulls
        if new_nulls > 0:
            coerce_report[col] = new_nulls

    if coerce_report:
        print("      Cells coerced to NaN (unparseable text found in value columns):")
        for col, count in coerce_report.items():
            print(f"        {col}: {count:,} cells")
    else:
        print("      All value columns parsed cleanly — no coercion needed.")

    print(f"      Clean shape : {df.shape[0]:,} rows × {df.shape[1]} columns")
    return df


def _strip_timestamp(header: str) -> str:
    """
    Remove time (HH:MM or HH:MM:SS) and date substrings from a column name.
    Also strips leading/trailing whitespace and collapses internal spaces.

    Examples:
      "Arc 14:32:01"         →  "Arc"
      "Contact Force 09:00"  →  "Contact Force"
      "Height 2026-03-01"    →  "Height"
      "Unnamed: 3"           →  "Unnamed: 3"   (left alone — will be a units col)
    """
    s = str(header).strip()
    s = _TIME_RE.sub("", s)
    s = _DATE_RE.sub("", s)
    return s.strip()


def _process_units_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Pantograph CSVs interleave value and units columns.  The pattern is:

        [value col]  [units col]  [value col]  [units col]  …

    Units columns are identified by these signs:
      - Header starts with "Unnamed" (pandas' default for columns with no name)
      - OR the first few non-null values are short strings like "N", "mm", "km/h"

    For each units column we:
      1. Extract the most common unit string from that column.
      2. Append it (sanitised) to the preceding value column's name.
      3. Drop the units column from the DataFrame.

    Returns (cleaned_df, {col_name: unit_string}).
    """
    col_units   = {}
    cols_to_drop = []
    rename_map   = {}

    cols = list(df.columns)

    for i, col in enumerate(cols):
        if _is_units_column(df, col):
            # Extract the dominant unit string from this column
            unit = _extract_unit(df[col])
            cols_to_drop.append(col)

            # Apply the unit to the preceding value column (if there is one)
            if i > 0:
                prev_col = cols[i - 1]
                if prev_col not in cols_to_drop:  # don't rename another units col
                    safe_unit  = _sanitise_unit(unit)
                    new_name   = f"{prev_col}_{safe_unit}" if safe_unit else prev_col
                    rename_map[prev_col] = new_name
                    col_units[new_name]  = unit

    df = df.drop(columns=cols_to_drop)
    df = df.rename(columns=rename_map)

    # Standardise column names: lowercase, spaces → underscores
    df.columns = [
        re.sub(r"[^\w]", "", c.lower().replace(" ", "_").replace("-", "_"))
        for c in df.columns
    ]

    return df, col_units


def _is_units_column(df: pd.DataFrame, col: str) -> bool:
    """
    Return True if this column looks like a units column rather than a
    value column.

    Signs it's a units column:
      - Header is "Unnamed: N" (pandas default for headerless columns)
      - The non-null values are short strings (≤10 chars) that aren't numbers
    """
    if str(col).startswith("Unnamed"):
        return True

    non_null = df[col].dropna()
    if non_null.empty:
        return False

    # Sample up to 20 values and check if they're all short non-numeric strings
    sample = non_null.head(20)
    short_text = sum(
        1 for v in sample
        if isinstance(v, str) and len(v.strip()) <= 10 and not _looks_numeric(v)
    )
    return short_text / len(sample) > 0.6  # >60% short text → units column


def _extract_unit(series: pd.Series) -> str:
    """
    Return the most common non-null, non-numeric string from a units column.
    Falls back to empty string if nothing useful is found.
    """
    candidates = (
        series.dropna()
              .astype(str)
              .str.strip()
              .loc[lambda s: s.apply(lambda v: bool(v) and not _looks_numeric(v))]
    )
    if candidates.empty:
        return ""
    return candidates.mode().iloc[0]


def _sanitise_unit(unit: str) -> str:
    """
    Convert a unit string to something safe for use in a column name.

    Examples:
      "µA/cm²"  →  "ua_per_cm2"
      "km/h"    →  "km_h"
      "N"       →  "n"
      "m ASL"   →  "m_asl"
    """
    replacements = [
        ("µ",  "u"),
        ("²",  "2"),
        ("³",  "3"),
        ("/",  "_per_"),
        (" ",  "_"),
        ("°",  "deg"),
        ("%",  "pct"),
    ]
    s = unit.strip()
    for old, new in replacements:
        s = s.replace(old, new)
    s = re.sub(r"[^\w]", "", s).lower()
    return s


# ---------------------------------------------------------------------------
# STEP 4 — DATA QUALITY PROFILE
# ---------------------------------------------------------------------------


def profile_data(df: pd.DataFrame):
    """
    Print a column-by-column quality report:
      - Data type
      - Non-null count and percentage
      - Min, mean, max for numeric columns
      - Sanity-range warnings for pantograph-specific columns

    This is the 'show me what I have' step before we decide what to clean.
    """
    print("\n[4/6] Data quality profile …")
    print(f"\n      {df.shape[0]:,} rows × {df.shape[1]} columns\n")

    header = f"  {'Column':<35} {'Type':<10} {'Non-null':>9} {'Null%':>6}  {'Min':>10}  {'Mean':>10}  {'Max':>10}  Notes"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for col in df.columns:
        dtype    = str(df[col].dtype)
        non_null = df[col].notna().sum()
        null_pct = df[col].isna().mean() * 100

        if pd.api.types.is_numeric_dtype(df[col]):
            col_min  = df[col].min()
            col_mean = df[col].mean()
            col_max  = df[col].max()
            notes    = _sanity_check(col, col_min, col_max)
            print(
                f"  {col:<35} {dtype:<10} {non_null:>9,} {null_pct:>5.1f}%"
                f"  {col_min:>10.3f}  {col_mean:>10.3f}  {col_max:>10.3f}  {notes}"
            )
        else:
            print(
                f"  {col:<35} {dtype:<10} {non_null:>9,} {null_pct:>5.1f}%"
                f"  {'—':>10}  {'—':>10}  {'—':>10}"
            )


def _sanity_check(col_name: str, col_min: float, col_max: float) -> str:
    """
    Compare the column's actual range against the known physics-based
    limits for pantograph measurements.  Returns a warning string if
    something looks wrong, or an empty string if everything is fine.
    """
    col_lower = col_name.lower()
    for keyword, (lo, hi, unit) in SANITY_RANGES.items():
        if keyword in col_lower:
            issues = []
            if col_min < lo:
                issues.append(f"min {col_min:.2f} < {lo} {unit}")
            if col_max > hi:
                issues.append(f"max {col_max:.2f} > {hi} {unit}")
            if issues:
                return "WARN: " + "; ".join(issues)
            return "OK"
    return ""


# ---------------------------------------------------------------------------
# STEP 5 — INTERACTIVE CLEANING
# ---------------------------------------------------------------------------


def ask_yes_no(question: str, default: str = "y") -> bool:
    """
    Prompt for a yes/no answer.  'default' sets what pressing Enter gives.
    Returns True for yes, False for no.
    """
    hint = "[Y/n]" if default == "y" else "[y/N]"
    while True:
        raw = input(f"\n  {question} {hint}: ").strip().lower()
        if raw == "":
            return default == "y"
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Please enter y or n.")


def choose_cleaning_steps(df: pd.DataFrame) -> dict:
    """
    Ask the user which cleaning steps to apply.
    Offers pantograph-relevant options, with sensible defaults.

    Returns a dict of booleans keyed by step name.
    """
    print("\n[5/6] Choose cleaning steps (press Enter to accept the default):\n")
    steps = {}

    # ── General structural cleaning ───────────────────────────────────────
    steps["drop_duplicate_rows"] = ask_yes_no(
        "Remove duplicate rows?  (identical readings at the same position)"
    )

    steps["drop_all_null_rows"] = ask_yes_no(
        "Remove rows where every column is empty / NaN?"
    )

    # ── Pantograph-specific cleaning ──────────────────────────────────────
    # Zero-speed rows: many monitoring systems keep recording while the train
    # is stationary, filling the dataset with repeated readings at distance=0.
    speed_cols = [c for c in df.columns if "speed" in c.lower()]
    if speed_cols:
        pct_zero_speed = (df[speed_cols[0]] == 0).mean() * 100
        steps["drop_zero_speed"] = ask_yes_no(
            f"Remove zero-speed rows?  "
            f"({pct_zero_speed:.1f}% of rows have speed = 0 — "
            f"stationary readings are usually not needed for arc analysis)",
            default="y" if pct_zero_speed > 5 else "n",
        )
    else:
        steps["drop_zero_speed"] = False

    # Out-of-range clamping: replace physically impossible values with NaN.
    # This is different from flagging — it modifies the data.
    steps["clamp_out_of_range"] = ask_yes_no(
        "Replace out-of-range values with NaN?  "
        "(values outside the sanity limits shown above)",
        default="n",
    )

    # High-null columns: columns that are mostly empty add noise.
    null_pct = df.isnull().mean() * 100
    high_null = null_pct[null_pct > 50].index.tolist()
    if high_null:
        print(f"\n  Columns with >50% missing values: {high_null}")
        steps["drop_high_null_cols"] = ask_yes_no(
            "Drop these mostly-empty columns?"
        )
    else:
        steps["drop_high_null_cols"] = False

    # Interpolation: fill small gaps in numeric columns using linear
    # interpolation.  Useful when a sensor briefly drops out for 1–3 samples.
    steps["interpolate_small_gaps"] = ask_yes_no(
        "Fill small gaps (≤3 consecutive NaNs) by linear interpolation?  "
        "(do NOT use this if large sections of data are missing)",
        default="n",
    )

    return steps


def apply_cleaning(df: pd.DataFrame, steps: dict) -> pd.DataFrame:
    """
    Apply the chosen cleaning steps in order and print a row-count summary
    after each one so you can see exactly what changed.
    """
    print("\n[6/6] Applying cleaning steps …\n")
    rows_before = len(df)
    cols_before = len(df.columns)

    # ── 1. Duplicate rows ─────────────────────────────────────────────────
    if steps["drop_duplicate_rows"]:
        n = len(df)
        df = df.drop_duplicates()
        print(f"  drop_duplicate_rows    : removed {n - len(df):,} rows  ({len(df):,} remaining)")

    # ── 2. All-null rows ──────────────────────────────────────────────────
    if steps["drop_all_null_rows"]:
        n = len(df)
        df = df.dropna(how="all")
        print(f"  drop_all_null_rows     : removed {n - len(df):,} rows  ({len(df):,} remaining)")

    # ── 3. Zero-speed rows ────────────────────────────────────────────────
    if steps["drop_zero_speed"]:
        speed_cols = [c for c in df.columns if "speed" in c.lower()]
        if speed_cols:
            n = len(df)
            df = df[df[speed_cols[0]] != 0].reset_index(drop=True)
            print(f"  drop_zero_speed        : removed {n - len(df):,} rows  ({len(df):,} remaining)")

    # ── 4. Clamp out-of-range values ──────────────────────────────────────
    if steps["clamp_out_of_range"]:
        total_clamped = 0
        for col in df.columns:
            col_lower = col.lower()
            for keyword, (lo, hi, _) in SANITY_RANGES.items():
                if keyword in col_lower and pd.api.types.is_numeric_dtype(df[col]):
                    mask = (df[col] < lo) | (df[col] > hi)
                    n_bad = mask.sum()
                    if n_bad:
                        df.loc[mask, col] = np.nan
                        total_clamped += n_bad
                        print(f"  clamp_out_of_range     : {col}: {n_bad:,} values → NaN")
        if total_clamped == 0:
            print("  clamp_out_of_range     : no out-of-range values found")

    # ── 5. Drop high-null columns ─────────────────────────────────────────
    if steps["drop_high_null_cols"]:
        null_pct = df.isnull().mean()
        to_drop  = null_pct[null_pct > 0.5].index.tolist()
        df = df.drop(columns=to_drop)
        print(f"  drop_high_null_cols    : dropped {len(to_drop)} columns: {to_drop}")

    # ── 6. Interpolate small gaps ─────────────────────────────────────────
    if steps["interpolate_small_gaps"]:
        num_cols = df.select_dtypes(include="number").columns
        df[num_cols] = df[num_cols].interpolate(
            method="linear", limit=3, limit_direction="both"
        )
        print(f"  interpolate_small_gaps : applied to {len(num_cols)} numeric columns  (limit=3)")

    print(f"\n  Before: {rows_before:,} rows × {cols_before} columns")
    print(f"  After : {len(df):,} rows × {len(df.columns)} columns")
    print(f"  Reduction: {rows_before - len(df):,} rows removed  "
          f"({(1 - len(df)/rows_before)*100:.1f}%)")

    return df


# ---------------------------------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------------------------------


def save_output(df: pd.DataFrame, original_filepath: str) -> str:
    """
    Save the cleaned DataFrame as a UTF-8 CSV (with BOM so Excel opens it
    correctly on Windows without garbling special characters like µ).
    """
    os.makedirs(ONEDRIVE_OUTPUTS, exist_ok=True)

    stem    = os.path.splitext(os.path.basename(original_filepath))[0]
    outfile = os.path.join(ONEDRIVE_OUTPUTS, f"{stem}_cleaned.csv")
    df.to_csv(outfile, index=False, encoding="utf-8-sig")

    print(f"\n  Saved: {outfile}")
    print(f"  Size : {os.path.getsize(outfile) / 1024:.1f} KB")
    return outfile


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main():
    print()
    print("=" * 65)
    print("  Pantograph Monitoring CSV Cleaner — Arc Analysis M12")
    print("=" * 65)

    # ── Get the file path ─────────────────────────────────────────────────
    print("\nEnter the full path to your raw sensor CSV file.")
    print(r"Example: C:\Users\YourName\Projects\Arc-Analysis-M12\01-Raw-Data\M12_run1.csv")
    filepath = input("\nFile path: ").strip().strip('"').strip("'")

    if not os.path.isfile(filepath):
        print(f"\nERROR: File not found:\n  {filepath}")
        sys.exit(1)

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"\nFile size: {file_size_mb:.1f} MB")

    # ── Step 1: Detect encoding ───────────────────────────────────────────
    encoding = detect_encoding(filepath)

    # ── Step 2: Detect header row ─────────────────────────────────────────
    header_row = sniff_header_row(filepath, encoding)
    preview_raw(filepath, encoding, header_row)

    confirm = ask_yes_no(
        f"\nDoes row {header_row} look like the correct header row?",
        default="y",
    )
    if not confirm:
        header_row = int(input("  Enter the correct row number (0 = first row): ").strip())
        print(f"  Using row {header_row}.")

    # ── Step 3: Parse pantograph format ──────────────────────────────────
    df = parse_pantograph_csv(filepath, encoding, header_row)

    # ── Step 4: Profile data quality ─────────────────────────────────────
    profile_data(df)

    # ── Step 5: Choose and apply cleaning ────────────────────────────────
    steps    = choose_cleaning_steps(df)
    df_clean = apply_cleaning(df, steps)

    # ── Save ──────────────────────────────────────────────────────────────
    output_path = save_output(df_clean, filepath)

    print()
    print("=" * 65)
    print("  Cleaning complete!")
    print(f"  Output : {output_path}")
    print("  Next   : run arc_monitor.py and upload this cleaned file.")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()

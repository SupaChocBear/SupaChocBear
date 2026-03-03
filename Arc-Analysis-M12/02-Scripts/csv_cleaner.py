"""
csv_cleaner.py
==============
Interactive large CSV cleaner for Arc Analysis M12 project.

What this script does:
  1. Asks you to provide the path to your raw CSV file.
  2. Auto-detects the file encoding (so it won't crash on special characters).
  3. Profiles the data — shows you row counts, column names, missing values, etc.
  4. Asks which cleaning steps you want to apply (interactively).
  5. Processes the file in chunks so even very large files can be handled.
  6. Saves the cleaned file to your OneDrive Outputs folder.

Run with:
    python 02-Scripts/csv_cleaner.py
"""

import os
import sys
import pandas as pd
import chardet
from tqdm import tqdm

# ---------------------------------------------------------------------------
# CONFIGURATION — adjust these paths to match your setup
# ---------------------------------------------------------------------------

# Where to save the cleaned output file.
# On Windows this will be something like:
#   C:\Users\YourName\OneDrive\Projects\Arc-Analysis-M12\Outputs
ONEDRIVE_OUTPUTS = os.path.join(
    os.path.expanduser("~"), "OneDrive", "Projects", "Arc-Analysis-M12", "Outputs"
)

# How many rows to read at a time when processing large files.
# 10,000 is a safe default — increase if your machine has plenty of RAM.
CHUNK_SIZE = 10_000

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------


def detect_encoding(filepath: str) -> str:
    """
    Read a sample of the file (up to 100 KB) and use chardet to guess
    the character encoding.  This prevents UnicodeDecodeError crashes
    when the file was created on a different system.
    """
    print("\n[1/5] Detecting file encoding …")
    with open(filepath, "rb") as f:
        raw_sample = f.read(100_000)  # 100 KB sample is usually enough
    result = chardet.detect(raw_sample)
    encoding = result.get("encoding", "utf-8") or "utf-8"
    confidence = result.get("confidence", 0) * 100
    print(f"      Detected: {encoding}  (confidence {confidence:.1f}%)")
    return encoding


def profile_data(filepath: str, encoding: str) -> pd.DataFrame:
    """
    Read the whole file (in chunks) and build a summary DataFrame that
    shows: column names, data types, non-null counts, and null counts.

    We also print the first 5 rows so you can see the raw layout.
    """
    print("\n[2/5] Profiling data …")

    chunks = []
    total_rows = 0

    reader = pd.read_csv(
        filepath,
        encoding=encoding,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    )

    for chunk in tqdm(reader, desc="      Reading chunks", unit="chunk"):
        chunks.append(chunk)
        total_rows += len(chunk)

    df_full = pd.concat(chunks, ignore_index=True)

    print(f"\n      Total rows  : {total_rows:,}")
    print(f"      Total columns: {len(df_full.columns)}")
    print("\n      Column profile:")

    profile = pd.DataFrame({
        "Column": df_full.columns,
        "Dtype": df_full.dtypes.values,
        "Non-null": df_full.notnull().sum().values,
        "Null": df_full.isnull().sum().values,
        "Null %": (df_full.isnull().mean().values * 100).round(2),
    })
    print(profile.to_string(index=False))

    print("\n      First 5 rows:")
    print(df_full.head().to_string())

    return df_full


def ask_yes_no(question: str) -> bool:
    """
    Simple yes/no prompt.  Returns True for 'y', False for 'n'.
    Keeps asking until a valid answer is given.
    """
    while True:
        answer = input(f"\n  {question} [y/n]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please enter y or n.")


def choose_cleaning_steps(df: pd.DataFrame) -> dict:
    """
    Ask the user which cleaning operations to perform.
    Returns a dict of booleans, e.g.:
        {"drop_duplicates": True, "drop_empty_rows": False, …}
    """
    print("\n[3/5] Choose cleaning steps:")
    steps = {}

    steps["drop_duplicates"] = ask_yes_no(
        "Remove duplicate rows?"
    )

    steps["drop_empty_rows"] = ask_yes_no(
        "Remove rows where ALL columns are empty?"
    )

    steps["strip_whitespace"] = ask_yes_no(
        "Strip leading/trailing whitespace from text columns?"
    )

    steps["standardise_column_names"] = ask_yes_no(
        "Standardise column names? (lowercase, spaces → underscores)"
    )

    null_pct = (df.isnull().mean() * 100).round(2)
    high_null_cols = null_pct[null_pct > 50].index.tolist()
    if high_null_cols:
        print(f"\n  Columns with >50% missing values: {high_null_cols}")
        steps["drop_high_null_cols"] = ask_yes_no(
            "Drop columns with more than 50% missing values?"
        )
    else:
        steps["drop_high_null_cols"] = False

    return steps


def apply_cleaning(df: pd.DataFrame, steps: dict) -> pd.DataFrame:
    """
    Apply the selected cleaning steps to the DataFrame and return
    the cleaned version.  We print a brief summary after each step
    so you can see what changed.
    """
    print("\n[4/5] Applying cleaning steps …")
    original_rows = len(df)
    original_cols = len(df.columns)

    if steps["drop_duplicates"]:
        before = len(df)
        df = df.drop_duplicates()
        print(f"      drop_duplicates  : removed {before - len(df):,} rows")

    if steps["drop_empty_rows"]:
        before = len(df)
        df = df.dropna(how="all")
        print(f"      drop_empty_rows  : removed {before - len(df):,} rows")

    if steps["strip_whitespace"]:
        text_cols = df.select_dtypes(include="object").columns
        df[text_cols] = df[text_cols].apply(
            lambda col: col.str.strip() if col.dtype == object else col
        )
        print(f"      strip_whitespace : applied to {len(text_cols)} text columns")

    if steps["standardise_column_names"]:
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(r"[\s\-/]+", "_", regex=True)
            .str.replace(r"[^\w]", "", regex=True)
        )
        print("      standardise_column_names: done")

    if steps["drop_high_null_cols"]:
        null_pct = df.isnull().mean()
        cols_to_drop = null_pct[null_pct > 0.5].index.tolist()
        df = df.drop(columns=cols_to_drop)
        print(f"      drop_high_null_cols: dropped {len(cols_to_drop)} columns: {cols_to_drop}")

    print(f"\n      Before: {original_rows:,} rows × {original_cols} columns")
    print(f"      After : {len(df):,} rows × {len(df.columns)} columns")

    return df


def save_output(df: pd.DataFrame, original_filepath: str) -> str:
    """
    Save the cleaned DataFrame to the OneDrive Outputs folder.
    The output filename is the original name with '_cleaned' appended.
    """
    print("\n[5/5] Saving cleaned file …")

    # Create the Outputs folder if it doesn't exist yet
    os.makedirs(ONEDRIVE_OUTPUTS, exist_ok=True)

    original_name = os.path.splitext(os.path.basename(original_filepath))[0]
    output_filename = f"{original_name}_cleaned.csv"
    output_path = os.path.join(ONEDRIVE_OUTPUTS, output_filename)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"      Saved to: {output_path}")

    return output_path


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("  Arc Analysis M12 — CSV Cleaner")
    print("=" * 60)

    # --- Step 0: Get the input file path ---
    print("\nEnter the full path to your raw CSV file.")
    print("Example: C:\\Users\\YourName\\Projects\\Arc-Analysis-M12\\01-Raw-Data\\sensor_data.csv")
    filepath = input("\nFile path: ").strip().strip('"').strip("'")

    if not os.path.isfile(filepath):
        print(f"\nERROR: File not found: {filepath}")
        sys.exit(1)

    # --- Step 1: Detect encoding ---
    encoding = detect_encoding(filepath)

    # --- Step 2: Profile the data ---
    df = profile_data(filepath, encoding)

    # --- Step 3: Choose cleaning steps ---
    steps = choose_cleaning_steps(df)

    # --- Step 4: Apply cleaning ---
    df_clean = apply_cleaning(df, steps)

    # --- Step 5: Save output ---
    output_path = save_output(df_clean, filepath)

    print("\n" + "=" * 60)
    print("  Cleaning complete!")
    print(f"  Output: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()

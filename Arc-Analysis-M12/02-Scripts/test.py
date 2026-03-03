"""
test.py
=======
Environment and setup verification script for Arc Analysis M12.

What this script does:
  1. Checks that Python 3.12 (or compatible) is in use.
  2. Tries to import every required library and reports pass/fail.
  3. Checks that the expected project folder structure exists.
  4. Prints a summary — green ticks for pass, red crosses for fail.

Run with:
    python 02-Scripts/test.py

No real data is required to run this script.
"""

import importlib
import os
import sys

# ---------------------------------------------------------------------------
# COLOURS for terminal output (work on Windows with modern terminal too)
# ---------------------------------------------------------------------------

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"

TICK  = f"{GREEN}✔{RESET}"
CROSS = f"{RED}✘{RESET}"


def check(condition: bool, label: str, detail: str = "") -> bool:
    """Print a labelled pass/fail line and return the result."""
    symbol = TICK if condition else CROSS
    line = f"  {symbol}  {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return condition


# ---------------------------------------------------------------------------
# CHECKS
# ---------------------------------------------------------------------------


def check_python_version() -> bool:
    """Verify Python version is 3.10 or higher (3.12 recommended)."""
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}.{sys.version_info.micro}"
    ok = major == 3 and minor >= 10
    return check(ok, f"Python version: {version_str}", "need 3.10+")


def check_libraries() -> bool:
    """Try importing each required library."""
    required = [
        ("pandas",    "pandas"),
        ("numpy",     "numpy"),
        ("tqdm",      "tqdm"),
        ("chardet",   "chardet"),
        ("streamlit", "streamlit"),
        ("plotly",    "plotly"),
        ("docx",      "python-docx"),
        ("kaleido",   "kaleido"),
    ]

    all_ok = True
    for module_name, package_name in required:
        try:
            importlib.import_module(module_name)
            check(True, f"import {module_name}", f"pip: {package_name}")
        except ImportError:
            check(False, f"import {module_name}", f"MISSING — run: pip install {package_name}")
            all_ok = False

    return all_ok


def check_folder_structure() -> bool:
    """Check that expected project folders exist relative to this script."""
    # This script lives in 02-Scripts/, so the project root is one level up
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    expected_folders = [
        "01-Raw-Data",
        "02-Scripts",
        "03-Notebooks",
    ]

    all_ok = True
    for folder in expected_folders:
        path = os.path.join(project_root, folder)
        exists = os.path.isdir(path)
        check(exists, f"Folder: {folder}", path if exists else "NOT FOUND")
        if not exists:
            all_ok = False

    return all_ok


def check_scripts_present() -> bool:
    """Check that all four project scripts are present."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    expected_scripts = [
        "csv_cleaner.py",
        "arc_monitor.py",
        "report_generator.py",
        "test.py",
    ]

    all_ok = True
    for script in expected_scripts:
        path = os.path.join(script_dir, script)
        exists = os.path.isfile(path)
        check(exists, f"Script: {script}", "✔ present" if exists else "MISSING")
        if not exists:
            all_ok = False

    return all_ok


def check_onedrive_outputs() -> bool:
    """
    Check whether the OneDrive Outputs folder exists.
    This is optional — warn but don't fail if it's missing.
    """
    outputs_path = os.path.join(
        os.path.expanduser("~"), "OneDrive", "Projects", "Arc-Analysis-M12", "Outputs"
    )
    exists = os.path.isdir(outputs_path)
    symbol = TICK if exists else f"{RED}!{RESET}"
    status = "found" if exists else "not found — will be created when scripts run"
    print(f"  {symbol}  OneDrive Outputs folder  ({status})")
    return True  # non-fatal


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main():
    print()
    print(f"{BOLD}Arc Analysis M12 — Environment Check{RESET}")
    print("=" * 50)

    results = []

    print(f"\n{BOLD}Python version:{RESET}")
    results.append(check_python_version())

    print(f"\n{BOLD}Required libraries:{RESET}")
    results.append(check_libraries())

    print(f"\n{BOLD}Project folder structure:{RESET}")
    results.append(check_folder_structure())

    print(f"\n{BOLD}Project scripts:{RESET}")
    results.append(check_scripts_present())

    print(f"\n{BOLD}OneDrive outputs folder:{RESET}")
    check_onedrive_outputs()

    print("\n" + "=" * 50)
    if all(results):
        print(f"{GREEN}{BOLD}All checks passed!  Environment is ready.{RESET}")
        print("\nNext step: run csv_cleaner.py on your raw data.")
    else:
        print(f"{RED}{BOLD}Some checks failed.  See details above.{RESET}")
        print("\nFix the issues above, then re-run this script.")
    print()


if __name__ == "__main__":
    main()

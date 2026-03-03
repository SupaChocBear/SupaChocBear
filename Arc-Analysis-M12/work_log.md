# Arc Analysis M12 — Work Log

**Project:** Arc event investigation, mileage marker M12, Up line
**Analyst:** [Your name]
**Started:** 2026-03-03

---

## Progress Checklist

### Phase 1 — Environment & Scripts

- [x] **Step 1** — Project folder structure created
  - `01-Raw-Data/`, `02-Scripts/`, `03-Notebooks/`
  - `notes.md`, `work_log.md`

- [x] **Step 2** — Virtual environment set up in VS Code
  - `.venv` created inside project folder
  - Python 3.12 selected as interpreter

- [x] **Step 3** — Libraries installed and verified
  - `pip install pandas numpy tqdm chardet streamlit plotly kaleido python-docx`
  - Verified with `test.py`

- [x] **Step 4** — Scripts created
  - `csv_cleaner.py` — interactive large CSV cleaner
  - `arc_monitor.py` — Streamlit dashboard
  - `report_generator.py` — PNG export + Word report
  - `test.py` — environment check

### Phase 2 — Data Analysis

- [ ] **Step 5** — Load and inspect real CSV data file
  - Paste first 10 rows into notes.md
  - Confirm column layout with parser

- [ ] **Step 6** — Run csv_cleaner.py on real data
  - Note: keep raw file untouched in 01-Raw-Data
  - Cleaned file saved to OneDrive Outputs

- [ ] **Step 7** — Run arc_monitor.py dashboard
  - Upload cleaned CSV in browser
  - Confirm charts load correctly

- [ ] **Step 8** — Identify arc event at M12
  - Locate spike(s) above detection threshold
  - Note: distance/chainage, arc intensity, GPS position

- [ ] **Step 9** — Export charts and generate Word report
  - Run report_generator.py
  - Review Word document
  - Share draft with engineering team for sense-check

- [ ] **Step 10** — Share findings with engineering team
  - Email report PDF or share via SharePoint
  - Attach events CSV

---

## Session Log

### Session 1 — 2026-03-03

**Duration:** ~1 hour
**Completed:**
- Created full project folder structure
- Built all four Python scripts from scratch
- Created notes.md and work_log.md

**Output files created:**
- `02-Scripts/csv_cleaner.py`
- `02-Scripts/arc_monitor.py`
- `02-Scripts/report_generator.py`
- `02-Scripts/test.py`
- `notes.md`
- `work_log.md`

**Blocked on:**
- Real CSV data not yet available in this environment
- Need to paste first 10 rows next session to confirm column layout

**Next session goal:**
- Load real sensor CSV → inspect column layout → run csv_cleaner.py

---

## Technical Notes

### Arc Event Detection Logic

```
threshold = mean(arc) + 3 × std(arc)
event = True  if  arc > threshold
```

The 3σ threshold is the standard for statistical outlier detection.
It means only ~0.3% of readings will be flagged as events.
If this is too sensitive or not sensitive enough, adjust `SIGMA_MULTIPLIER`
in arc_monitor.py and report_generator.py.

### CSV Parser Strategy

The flexible parser in arc_monitor.py tries reading the CSV with
0, 1, 2, and 3 header rows skipped, then scores each attempt by how
many expected columns it can find.  The best-scoring parse is used.

Columns are matched by keyword:
- `arc` → arc, µa, ua, microamp
- `distance` → distance, dist, metres, meter, chainage
- `height` → height, elevation, asl, altitude
- `latitude` → lat, latitude
- `longitude` → lon, lng, longitude

If the auto-parse fails, paste the first 10 rows in notes.md and
we can tune the keywords.

### File Handling Rules

| Rule | Reason |
|---|---|
| Never edit files in 01-Raw-Data | Preserve original evidence |
| Always save outputs to OneDrive | IT policy / data governance |
| Scripts only in Git | No sensitive data in version control |
| Cleaned CSV saved as UTF-8 BOM | Compatible with Excel on Windows |

---

## Reference

- Detection standard: mean + 3σ (3 standard deviations above mean)
- Arc unit: µA/cm² (microamps per square centimetre)
- Distance unit: metres along track
- Height unit: metres above sea level (ASL)

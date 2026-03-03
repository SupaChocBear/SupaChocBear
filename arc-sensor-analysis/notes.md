# Arc Sensor Analysis — Session Notes

---

## Session 1 — Project Setup

**Date:** 2026-03-03
**Goal:** Create project structure and build all four scripts.

### What we did

1. Created the project folder structure:
   ```
   arc-sensor-analysis/
   ├── 01-Raw-Data/        ← raw sensor CSVs go here (never edit originals)
   ├── 02-Scripts/         ← all Python scripts
   │   ├── csv_cleaner.py
   │   ├── arc_monitor.py
   │   ├── report_generator.py
   │   └── test.py
   ├── 03-Notebooks/       ← Jupyter notebooks (future use)
   ├── notes.md            ← this file
   └── work_log.md         ← formal session record
   ```

2. Built **csv_cleaner.py**
   - Auto-detects encoding with chardet
   - Reads in chunks (10,000 rows at a time) — handles huge files
   - Interactive: asks which cleaning steps to apply
   - Saves cleaned CSV to OneDrive Outputs folder

3. Built **arc_monitor.py** (Streamlit dashboard)
   - Upload CSV directly in the browser
   - Flexible column parser — handles non-standard CSV headers
   - Detects arc events: mean + 3σ threshold
   - Interactive charts: arc intensity, height, distance
   - GPS track map coloured by arc intensity
   - Download buttons: cleaned CSV, events CSV

4. Built **report_generator.py**
   - Reads cleaned CSV from OneDrive Outputs
   - Generates all charts as PNG files (requires kaleido)
   - Creates formatted Word document (.docx) with:
     - Executive summary
     - Statistics table
     - All four charts embedded
     - Events table (top 50 rows)
     - Conclusions and recommended actions

5. Built **test.py**
   - Checks Python version (needs 3.10+)
   - Imports all required libraries and reports pass/fail
   - Verifies folder structure and scripts are present
   - Warns if OneDrive Outputs folder doesn't exist yet

### Libraries required
```
pandas, numpy, tqdm, chardet, streamlit, plotly, kaleido, python-docx
```

Install with:
```
pip install pandas numpy tqdm chardet streamlit plotly kaleido python-docx
```

### How to run

**1. Test your setup first:**
```
python 02-Scripts/test.py
```

**2. Clean your raw CSV:**
```
python 02-Scripts/csv_cleaner.py
```

**3. Run the dashboard:**
```
streamlit run 02-Scripts/arc_monitor.py
```

**4. Generate the report (after step 3 export):**
```
python 02-Scripts/report_generator.py
```

---

## Next Session — Goals

- [ ] Load the real M12 sensor CSV into csv_cleaner.py
- [ ] Inspect the actual column layout (paste first 10 rows here)
- [ ] Note any CSV quirks (extra header rows, merged cells, etc.)
- [ ] Run csv_cleaner.py — apply appropriate cleaning steps
- [ ] Run arc_monitor.py dashboard on cleaned data
- [ ] Confirm arc events visible at M12

---

## CSV Column Layout (to fill in next session)

*Paste the first 10 rows of your CSV here so we can confirm the
column names and adjust the parser if needed.*

```
[paste CSV rows here]
```

**Column mapping we'll need to confirm:**
- Which column is Arc intensity? (look for µA or microamp)
- Which column is Distance? (metres along track)
- Which column is Height? (ASL)
- Are Latitude/Longitude present?
- Are there extra header rows (units row, timestamp row)?

---

## Key Decisions Made

| Decision | Reasoning |
|---|---|
| Threshold = mean + 3σ | Standard statistical outlier detection — captures top ~0.3% of readings |
| Chunk size = 10,000 rows | Safe for most machines; increase if you have plenty of RAM |
| Output to OneDrive | IT policy — real data stays on company systems |
| Scripts only in Git | No sensitive data in version control |

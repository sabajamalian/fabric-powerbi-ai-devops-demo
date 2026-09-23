# Synthetic data

Everything in this folder is synthetic. It was produced by a seeded random generator and describes fictional stores, generic medication names, and anonymous fill events. There are no patients, prescribers, members, addresses, or health records, and the repository is not meant to hold PHI. Don't add real data here, even for a quick test.

## What's here

| Path | What it is |
|---|---|
| `generated/dim_date.csv` | One row per day, 2024-01-01 to 2025-12-31 (731 rows). |
| `generated/dim_store.csv` | 12 fictional stores in four regions. |
| `generated/dim_med.csv` | 60 generic medications in eight therapeutic categories. Codes like `M001` aren't real drug codes. |
| `generated/fact_rx_fill.csv` | About 41,500 fill events, new and refill. |
| `schema/tables.json` | Column names, types, and descriptions for every file. |

The column names are short, database-style codes on purpose (`rgn`, `ther_cat`, `proc_mins`, `fill_typ`). The baseline semantic model copies them as-is, and the labs turn them into business names with Copilot's help.

## The signals the questions depend on

The generator plants a few patterns so the five business questions have clear answers:

- **Seasonality and trend.** Respiratory fills rise in the winter months, and total volume grows slowly across the two years.
- **Category change.** From November to December 2025, Respiratory has the largest increase and Dermatology has one of the largest drops.
- **Slow store.** Sunset Mesa (`S008`) has the longest average processing time.
- **Refill outliers.** Riverbend (`S003`) and Granite Park (`S010`) have unusually high refill rates in 2025-Q4.
- **Previous period.** December 2025 has 2,052 fills against 1,761 in November 2025.

The reference answers live in `evaluation/expected/`, computed from these files with DuckDB.

## Regenerate or verify

The files are deterministic for a given seed. CI fails if they drift from the generator.

```powershell
# Check that the committed files match the generator
pwsh ./scripts/New-SyntheticData.ps1 -Check

# Rewrite them (only after changing tools/python/pharmacy_demo/datagen.py)
pwsh ./scripts/New-SyntheticData.ps1
pwsh ./scripts/Update-ExpectedResults.ps1
```

On macOS or Linux you can call the Python tool directly:

```bash
.venv/bin/python -m pharmacy_demo data --check
```

Don't edit the CSV files by hand. The Copilot hooks in this repo deny agent edits under `data/generated/` for the same reason.

## How Power BI finds the files

The semantic model reads the CSVs through a Power Query parameter, `DataFolderPath`, which defaults to `C:\ContosoPharmacyDemo\data\`. That fixed path avoids spaces and user names in the model. `scripts/Set-LocalDataLink.ps1` creates it as a directory junction that points at `data/generated/` in your clone (Windows only; no admin rights needed). Remove it with `-Remove`.

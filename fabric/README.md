# Power BI project (PBIP)

This folder is a Power BI Project saved as text so Git, pull requests, and Copilot can work with it.

| Path | Format | What it holds |
|---|---|---|
| `ContosoPharmacy.pbip` | JSON | The file you open in Power BI Desktop. |
| `ContosoPharmacy.SemanticModel/definition/` | TMDL | Tables, columns, measures, relationships, and model settings. |
| `ContosoPharmacy.Report/definition/` | PBIR | Report pages and visuals, one JSON file per visual. |
| `ai-prep/` | Markdown and YAML | Drafts of AI instructions, synonyms, and verified answers (added in Lab 09). |

## Open it

Power BI Desktop runs on Windows only. On Windows 11:

1. Run `pwsh ./scripts/Set-LocalDataLink.ps1` once so `C:\ContosoPharmacyDemo\data\` points at `data/generated/`.
2. In Power BI Desktop, turn on the preview features **Power BI Project (.pbip) save option** and **Store semantic model using TMDL format** (File > Options and settings > Options > Preview features), then restart Desktop.
3. Open `fabric/ContosoPharmacy.pbip` and select **Refresh**.

On macOS you can still read and edit the TMDL and PBIR files, run every validator, and do the Copilot labs. You just can't open the model in Desktop or run the DAX tests.

## The baseline is rough on purpose

The model on `main` is the starting point for the labs. It has problems a real team would recognize:

- Tables and columns use source codes (`fact_rx_fill`, `rgn`, `proc_mins`) instead of business names.
- No descriptions, and keys are visible and summarized.
- No relationships in the model yet, plus one bidirectional relationship that shouldn't be.
- No marked date table, auto date/time is on, and there are no measures.
- No AI instructions, synonyms, or verified answers.

Run `pwsh ./scripts/Test-ModelConventions.ps1` to see the full list. The labs fix these step by step, and the finished model is on the `reference/ai-ready` branch and the `ai-ready-v1` tag.

## Rules for editing

- TMDL uses tabs for indentation. `pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl` catches mistakes.
- When you rename a table or column, update the report too. `pwsh ./scripts/Test-ReportBindings.ps1` lists visuals that point at fields that no longer exist.
- Don't commit `.pbi/localSettings.json` or `.pbi/cache.abf`; `.gitignore` already excludes them.
- Don't edit the `Copilot/` folder that newer versions of Desktop create inside the semantic model. Draft in `ai-prep/` and apply through **Prep data for AI** in Desktop or the Power BI service.

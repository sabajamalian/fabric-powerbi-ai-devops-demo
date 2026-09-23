---
name: pharmacy-model-conventions
description: House conventions for the Contoso Pharmacy semantic model, covering business names, descriptions, hidden keys, summarization, display folders, required relationships and measures, and the AI-readiness checklist. Use when you assess, review, or change model names, descriptions, measures, relationships, or the date table, or when you need the standard business name for a source column.
---
# Contoso Pharmacy model conventions

These conventions make the model easy for people and for AI tools (Power BI Copilot, Fabric data agents, and coding agents) to read. They are checked by rules C01 to C15.

The rules themselves are data, not prose. Read them from:

- `rules/naming-conventions.yaml`: name pattern, forbidden abbreviations, description length, hidden-column patterns, additive columns, raw-code columns, display folders.
- `rules/required-model-objects.yaml`: required tables, relationships, date table settings, the twelve required measures by display folder, default labels, and the AI prep requirements.

## Get the current findings

Run the checker instead of reviewing by eye. It's deterministic and it's the same code the lab checks use.

```powershell
pwsh ./scripts/Test-ModelConventions.ps1            # table of findings
pwsh ./scripts/Test-ModelConventions.ps1 -Json      # for agents
pwsh ./scripts/Test-ModelConventions.ps1 -Rule C07,C08
```

On macOS or Linux, `pwsh` runs the same scripts. Every finding has a rule, severity, object, finding, and fix.

## Rules

| Rule | Title | What good looks like |
|---|---|---|
| C01 | Business-friendly names | Title Case words with spaces. No underscores or abbreviations like `rx`, `dt`, `nm`, `qty`. Use the names in [the data dictionary](references/data-dictionary.md). |
| C02 | Descriptions present | Every table, visible column, and measure has a `///` description. |
| C03 | Description length | 20 to 200 characters. Say what it is, its grain or unit, and when to use it. |
| C04 | Keys and helpers hidden | Surrogate keys, foreign keys, `Fill ID`, and sort-by number columns are hidden. |
| C05 | Default summarization | `summarizeBy: none` everywhere except `Quantity` and `Days Supply` (sum) and `Processing Time (min)` (average). |
| C06 | Raw codes decoded | `Fill Type Code` (N or R) is hidden, and a visible `Fill Type` column shows New or Refill. |
| C07 | Required relationships | Prescription Fill to Date, Store, and Medication, many-to-one. |
| C08 | Single-direction filters | No bidirectional relationships. |
| C09 | Marked date table | `Date` has `dataCategory: Time`, and its `Date` column has `isKey`. |
| C10 | Auto date/time off | No `LocalDateTable` tables; `__PBI_TimeIntelligenceEnabled = 0`. |
| C11 | Sort-by columns | Month, Year Month, and Day of Week sort by their number columns. |
| C12 | Required measures | The twelve measures in `rules/required-model-objects.yaml`, with those exact names. |
| C13 | Measure format strings and folders | Every measure has `formatString` and a `displayFolder` from Volume, Refills, Processing, or Time Comparison. |
| C14 | Default labels | `Store Name` and `Medication Name` are the default labels of their tables. |
| C15 | Q&A and AI prep drafts | Q&A is enabled and `fabric/ai-prep/` has the five draft files. See the `prep-data-for-ai` skill. |

## Writing descriptions

A good description answers "what is this, and when do I use it?" in one or two short sentences.

- Tables: the grain and what it's for. "One row per prescription fill (new or refill) at a store."
- Columns: meaning, values or unit, and anything surprising. "Minutes from intake to ready for pickup."
- Measures: what it counts or computes, and the business words people use for it. Mention how it differs from similar measures.
- Don't restate the name ("The store name column"). Don't mention patients; this data has none.
- Stay under 200 characters. Power BI Copilot reads only the first 200.

More examples are in [references/examples.md](references/examples.md). The full AI-readiness checklist is in [references/ai-readiness-checklist.md](references/ai-readiness-checklist.md).

## Measures

- One measure, one idea. Build on base measures: `[Refills]` is `CALCULATE([Prescriptions Filled], ...)`, not a second `COUNTROWS`.
- Use `DIVIDE()` for ratios so empty periods return blank instead of an error.
- Time intelligence uses the marked `Date` table: `DATEADD('Date'[Date], -1, MONTH)`, `SAMEPERIODLASTYEAR('Date'[Date])`.
- Formats: counts `#,0`; rates `0.0%`; changes in percent `+0.0%;-0.0%;0.0%`; minutes `0.0`; indexes `0.00`; flags `0`.

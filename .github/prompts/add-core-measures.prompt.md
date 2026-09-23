---
name: add-core-measures
description: Add the 12 core measures, with these exact names, definitions, format strings, and display folders, to the Prescription Fill table, plus the Fill Type column.
agent: model-improver
---
Add these measures to the `Prescription Fill` table. Use the exact names so the lab checks and DAX tests find them. Each one needs a `///` description, a `formatString`, and the `displayFolder` shown. Use the `tmdl-authoring` skill.

| Display folder | Measure | Definition |
|---|---|---|
| Volume | Prescriptions Filled | Count of fill rows (new and refill) |
| Volume | New Prescriptions | Prescriptions Filled where the fill is new |
| Refills | Refills | Prescriptions Filled where the fill is a refill |
| Refills | Refill Rate | Refills divided by Prescriptions Filled |
| Refills | Refill Rate Index vs Chain | Refill Rate divided by the Refill Rate for all stores in the same period |
| Refills | High Refill Activity Flag | 1 when Refill Rate Index vs Chain is 1.25 or more, otherwise 0 |
| Processing | Avg Processing Time (min) | Average of the processing minutes column. Never a sum. |
| Time Comparison | Prescriptions Filled PM | Prescriptions Filled in the previous month, using the Date table |
| Time Comparison | MoM Change | Prescriptions Filled minus Prescriptions Filled PM |
| Time Comparison | MoM % | MoM Change divided by Prescriptions Filled PM |
| Time Comparison | Prescriptions Filled PY | Prescriptions Filled in the same period last year |
| Time Comparison | YoY % | Change from Prescriptions Filled PY, divided by Prescriptions Filled PY |

Also:

- Add a calculated column `Fill Type` that decodes `Fill Type Code`: `N` is `New`, `R` is `Refill`. Hide `Fill Type Code`.
- Use `DIVIDE` for every ratio. Build measures on other measures rather than repeating logic.
- Formats: whole numbers `#,0`; rates and percentages `0.0%`; the index `0.00`; minutes `0.0`; the flag `0`.
- After the measures exist, rebind report visuals that still count or sum raw columns (see the `pbir-rebinding` skill).

Validate with:

```powershell
pwsh ./scripts/Invoke-Validation.ps1
pwsh ./scripts/Test-ModelConventions.ps1 -Rule C02,C06,C12,C13
```

On Windows with the model open in Desktop, also run `pwsh ./scripts/Invoke-DaxQuestionTests.ps1`.

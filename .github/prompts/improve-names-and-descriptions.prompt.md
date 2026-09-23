---
name: improve-names-and-descriptions
description: Rename tables and columns to business names, add descriptions, hide keys, set summarization and display folders, then rebind the report.
agent: model-improver
---
Improve names and descriptions in the Contoso Pharmacy semantic model. Use the `pharmacy-model-conventions`, `tmdl-authoring`, and `pbir-rebinding` skills.

Scope for this change:

1. Rename every table and visible column to the business name in the conventions skill's data dictionary. Keep `sourceColumn` values unchanged. Update `model.tmdl`, `relationships.tmdl`, table file names, and any DAX.
2. Rebind every report visual to the new names, and replace implicit aggregations with measures if the measures already exist.
3. Add a `///` description to every table and visible column: what one row is, or what the value means, with an example value where it helps. Keep each under 200 characters.
4. Hide surrogate keys and sort helpers. Set `summarizeBy: none` on keys, codes, years, and other non-additive numbers.

Out of scope: new measures, relationship changes, and AI prep drafts.

After each group of edits run:

```powershell
pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl,bindings
pwsh ./scripts/Test-ModelConventions.ps1 -Rule C01,C02,C03,C04,C05
```

Finish when the lint and bindings pass and C01 to C05 report no findings.

---
applyTo: "fabric/**/*.tmdl"
description: Rules for editing the Contoso Pharmacy semantic model in TMDL.
---
# TMDL files

- Indent with tabs, one level per nesting depth. Properties of an object sit one tab deeper than the object line.
- Put descriptions on the line directly above the object as `/// text`. Keep them under 200 characters, because Power BI Copilot reads only the first 200.
- Quote names that contain spaces or special characters with single quotes: `column 'Store Key'`, `measure 'MoM %'`. In DAX, refer to columns as `'Table Name'[Column Name]` and to measures as `[Measure Name]`.
- Never change or remove a `lineageTag`. When you add an object, leave `lineageTag` out; Desktop adds one when it saves.
- When you rename a column, keep `sourceColumn` pointing at the CSV header. Rename references in `relationships.tmdl`, measures, sort-by columns, hierarchies, `cultures/en-US.tmdl`, and the report.
- Set `summarizeBy: none` on keys, IDs, years, month numbers, and other numbers that must not be added up. Only the columns listed as `additive` in `rules/naming-conventions.yaml` may summarize.
- Hide keys and sort helpers with `isHidden`.
- Every measure needs a description, a `formatString`, and a `displayFolder` from the list in `rules/naming-conventions.yaml`.
- Relationships to Date, Store, and Medication are many-to-one and single direction. Don't add `crossFilteringBehavior: bothDirections`.
- Don't edit `expressions.tmdl` unless the task is about the data source. The `DataFolderPath` parameter must stay a placeholder path, never a personal path.
- After editing, run `pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl`. Load the `tmdl-authoring` skill for syntax details.

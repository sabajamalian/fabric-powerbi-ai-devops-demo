---
applyTo: "fabric/**/*.Report/**"
description: Rules for the Contoso Pharmacy report in PBIR format.
---
# PBIR report files

- The report is PBIR: one `visual.json` per visual under `definition/pages/<page>/visuals/<visual>/`. Folder names are stable IDs; don't rename them.
- A field reference has an `Entity` (table name) and a `Property` (column or measure name). Both must match the semantic model exactly, including spaces and case.
- When the model renames a table, column, or measure, update every `Entity`, `Property`, and `queryRef` that uses the old name. Also update `nativeQueryRef` and any `displayName` that shows the old name.
- Don't change visual positions, sizes, or formatting unless the task asks for it.
- Keep JSON valid and keep the `$schema` line. Two-space indentation, as Desktop writes it.
- After editing, run `pwsh ./scripts/Test-ReportBindings.ps1`. The `pbir-rebinding` skill has the full procedure.

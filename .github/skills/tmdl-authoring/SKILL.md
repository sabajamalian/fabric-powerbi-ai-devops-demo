---
name: tmdl-authoring
description: How to safely edit Power BI semantic model files written in TMDL (Tabular Model Definition Language), including indentation, descriptions, quoting, lineage tags, renames across files, calculated columns, measures, relationships, and the local lint. Use whenever you create or change files under fabric/**/*.SemanticModel/definition/, or when a TMDL lint error needs fixing.
---
# Editing TMDL safely

The semantic model lives in `fabric/ContosoPharmacy.SemanticModel/definition/`:

| File | Holds |
|---|---|
| `model.tmdl` | Model settings, the `ref table` list, and the auto date/time annotation |
| `tables/<Table Name>.tmdl` | One table: columns, measures, hierarchies, and its partition (Power Query source) |
| `relationships.tmdl` | Every relationship |
| `expressions.tmdl` | The `DataFolderPath` parameter. Leave it alone. |
| `cultures/en-US.tmdl` | Linguistic metadata. Desktop maintains it. |
| `database.tmdl` | Compatibility level. Leave it alone. |

## Before you edit

1. Ask whether Power BI Desktop has the project open. If it does, either edit through Power BI Modeling MCP or ask the user to close Desktop first. Desktop overwrites TMDL files that change underneath it.
2. Make sure you're on a feature branch, so the diff is easy to review and undo.

## Syntax rules that break the model when you get them wrong

- **Tabs only.** Each nesting level is one tab. Spaces cause lint error TMDL001 and can fail to load in Desktop.
- **Descriptions** are `///` lines directly above the object, at the same indentation as the object, with no blank line between them (TMDL004). Plain `//` comments aren't valid TMDL (TMDL003).
- **Quoting.** Names with spaces or symbols take single quotes: `table 'Prescription Fill'`, `column 'Store Key'`, `measure 'MoM %'`. A name without spaces needs no quotes: `table Store`.
- **Measures** are one line `measure 'Name' = <DAX>` followed by indented properties. For long DAX, put the expression on the following lines, indented one extra tab, or wrap it in a ```` ``` ```` block.
- **Calculated columns** use `column 'Name' = <DAX>` with a `dataType` and no `sourceColumn`.
- **Flags** such as `isHidden`, `isKey`, and `isDefaultLabel` are bare words on their own line.
- **`lineageTag`**: never change or delete one. Leave it out when you add an object.

## Renaming a table or column

A rename touches more than one file. For a table named `dim_store` becoming `Store`:

1. Rename the declaration: `table Store`, and the partition: `partition Store = m`.
2. Rename the file to `tables/Store.tmdl`.
3. In `model.tmdl`, change `ref table dim_store` to `ref table Store`.
4. In `relationships.tmdl`, change every `fromColumn` and `toColumn` that uses the table.
5. Update DAX in every measure that refers to it: `'Store'[Region]`.
6. Update the report. Use the `pbir-rebinding` skill.

For a column, change the `column` line only. Keep `sourceColumn` as the CSV header, because the Power Query step still produces that name. Then update relationships, DAX, `sortByColumn` values, hierarchy levels, and the report.

## Check your work

```powershell
pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl       # lint
pwsh ./scripts/Test-ReportBindings.ps1                # report still binds
pwsh ./scripts/Test-ModelConventions.ps1              # house conventions
```

The lint is structural. It catches tabs, orphan descriptions, missing `ref table` entries, unknown DAX references, and broken relationships. It doesn't prove the DAX returns the right numbers; the DAX question tests in Lab 08 do that.

See [references/tmdl-cheatsheet.md](references/tmdl-cheatsheet.md) for complete examples and the lint codes.

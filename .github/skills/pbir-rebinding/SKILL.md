---
name: pbir-rebinding
description: Repair Power BI report visuals stored in PBIR format (visual.json files) after semantic model tables, columns, or measures are renamed, and swap implicit column aggregations for explicit measures. Use after any rename in the TMDL model, when Test-ReportBindings.ps1 reports problems, or when a visual still shows raw names like "Count of fill_id".
---
# Rebinding PBIR visuals after a model change

The report is `fabric/ContosoPharmacy.Report/`, in PBIR format. Each visual is a JSON file:

```
definition/pages/<page id>/visuals/<visual id>/visual.json
```

A visual refers to the model by **name**, not by lineage tag. When you rename `dim_store` to `Store` in TMDL, every visual that used `dim_store` breaks until you update it. Power BI Desktop does this for you when you rename inside Desktop; when an agent renames files, the agent must do it.

## Step 1. Find what's broken

```powershell
pwsh ./scripts/Test-ReportBindings.ps1
pwsh ./scripts/Test-ReportBindings.ps1 -Json   # machine-readable
```

Each problem names the file and the missing table, column, or measure. Zero problems means the report binds.

## Step 2. Fix each field reference

A field reference has three parts that must agree. Here's a column before and after renaming `dim_date.yr_mth` to `Date[Year Month]`:

```json
{
  "field": {
    "Column": {
      "Expression": { "SourceRef": { "Entity": "Date" } },
      "Property": "Year Month"
    }
  },
  "queryRef": "Date.Year Month",
  "nativeQueryRef": "Year Month"
}
```

| Key | Set it to |
|---|---|
| `SourceRef.Entity` | The table name, exactly as in TMDL, without quotes |
| `Property` | The column, measure, or hierarchy name |
| `queryRef` | `Entity.Property`, or `Function(Entity.Property)` for an aggregation |
| `nativeQueryRef` | The display name, usually the `Property` |

Use the rename map in the `pharmacy-model-conventions` skill (`references/data-dictionary.md`) to translate old names.

## Step 3. Replace implicit aggregations with measures

The baseline counts `fill_id` and sums `proc_mins` directly. Summing minutes is wrong: a store with more fills looks slower. After the core measures exist, replace the whole `Aggregation` block with a `Measure` block:

```json
{
  "field": {
    "Measure": {
      "Expression": { "SourceRef": { "Entity": "Prescription Fill" } },
      "Property": "Prescriptions Filled"
    }
  },
  "queryRef": "Prescription Fill.Prescriptions Filled",
  "nativeQueryRef": "Prescriptions Filled"
}
```

| Baseline aggregation | Measure |
|---|---|
| `CountNonNull(fact_rx_fill.fill_id)` (Function 5) | `[Prescriptions Filled]` |
| `Sum(fact_rx_fill.proc_mins)` (Function 0) | `[Avg Processing Time (min)]` |

`Entity` for a measure is the table the measure lives in (its home table), which is `Prescription Fill` for every measure in this model.

## Step 4. Check again

```powershell
pwsh ./scripts/Test-ReportBindings.ps1
pwsh ./scripts/Invoke-Validation.ps1 -Only bindings
```

## Rules

- Edit only the field reference blocks. Don't change `name`, `position`, or visual formatting.
- Keep the JSON valid and keep two-space indentation, so the diff stays small.
- Don't touch `definition.pbir`. It points the report at the semantic model by relative path.
- If Desktop has the report open, ask the user to close it first. Desktop rewrites visual files on save.
- Visual and page folder names are IDs. Never rename them.

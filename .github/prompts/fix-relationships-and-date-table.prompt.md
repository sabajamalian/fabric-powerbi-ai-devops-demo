---
name: fix-relationships-and-date-table
description: Fix the model's relationships and Date table so time intelligence works, including single-direction many-to-one joins, a marked date table, sort-by columns, and auto date/time turned off.
agent: model-improver
---
Fix the relationships and the Date table in the Contoso Pharmacy semantic model. Use the `tmdl-authoring` skill. The model must already use business names (Lab 07).

Target state:

| Relationship | From | To |
|---|---|---|
| Prescription Fill to Date | `'Prescription Fill'[Fill Date]` | `'Date'[Date]` |
| Prescription Fill to Store | `'Prescription Fill'[Store Key]` | `'Store'[Store Key]` |
| Prescription Fill to Medication | `'Prescription Fill'[Medication Key]` | `'Medication'[Medication Key]` |

- All three are many-to-one and single direction. Remove any bidirectional filter.
- The Date relationship uses `joinOnDateBehavior: datePartOnly`.
- Mark `Date` as the date table: `dataCategory: Time` on the table and `isKey` on `Date`.
- Sort `Month` by `Month Number`, `Year Month` by `Year Month Number`, and `Day of Week` by `Day of Week Number`. Hide the number columns.
- Add a `Calendar` hierarchy with levels Year, Year Quarter, Year Month, Date.
- Turn off auto date/time with `annotation __PBI_TimeIntelligenceEnabled = 0` in `model.tmdl`.

Validate with:

```powershell
pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl,bindings
pwsh ./scripts/Test-ModelConventions.ps1 -Rule C07,C08,C09,C10,C11
```

# Prep data for AI draft formats

All examples use the AI-ready names from the Contoso Pharmacy model.

## ai-instructions.md

Markdown. One H1, then short sections. Refer to objects the way DAX does: `[Measure]`, `'Table'[Column]`.

```markdown
# AI instructions for Contoso Pharmacy

This model describes prescription fills at 12 Contoso Pharmacy stores from January 2024 to December 2025. All data is synthetic and contains no patient information.

## Time periods
- The latest complete month is December 2025. The latest quarter is 2025-Q4 (October to December 2025).
- "Previous period" means the previous month unless the user names another period. Use [MoM Change] and [MoM %] for month-over-month and [YoY %] for year-over-year.

## Metric routing
- Processing time means [Avg Processing Time (min)]. Never sum processing minutes. Lower is better.
- "Unusually high refill activity" means [Refill Rate Index vs Chain] of 1.25 or more.
- Medication category means 'Medication'[Therapeutic Category].
```

## ai-data-schema.yaml

List only what differs from the model's own visibility. Hidden keys are already hidden, so don't repeat them.

```yaml
include:
  tables: [Date, Store, Medication, Prescription Fill]
exclude:
  - table: Store
    column: Open Date
    reason: Not related to the Date table; confuses time questions.
  - table: Prescription Fill
    measure: Prescriptions Filled PY
    reason: Helper for YoY %; steer AI to YoY %.
```

Each `exclude` entry has `table`, then either `column` or `measure`, then `reason`.

## synonyms.yaml

Three maps. Table keys are table names. Column and measure keys are `Table[Object]`, without quotes. Values are lists of lowercase phrases people actually use.

```yaml
tables:
  Store: [pharmacy, location, branch]
columns:
  Store[Region]: [area, territory]
  Medication[Therapeutic Category]: [drug category, medication category, therapeutic class]
measures:
  Prescription Fill[Prescriptions Filled]: [fills, prescription volume, scripts filled]
  Prescription Fill[Avg Processing Time (min)]: [processing time, turnaround time, wait time]
```

The lab check requires at least these four keys: `Prescription Fill[Prescriptions Filled]`, `Prescription Fill[Avg Processing Time (min)]`, `Medication[Therapeutic Category]`, and `Store[Region]`.

Avoid a synonym that could mean two objects. "Volume" alone is ambiguous between fills and refills, so prefer "prescription volume".

## verified-answers.yaml

One candidate per business question. `visual` describes what the person builds in the report; `phrases` are the trigger phrases they add when setting up the verified answer. Include the original question and at least one paraphrase.

```yaml
candidates:
  - question_id: Q03
    visual: Table, 'Store'[Store Name] and [Avg Processing Time (min)], sorted descending
    phrases:
      - What was the average prescription processing time by store?
      - Which stores are slowest to process prescriptions?
```

Get question IDs and wording from `pwsh ./scripts/Get-BusinessQuestions.ps1`.

## README.md

Say that the files are drafts, and give the Desktop path for each one:

| File | Apply it in Power BI Desktop |
|---|---|
| `ai-instructions.md` | Home > Prep data for AI > Add AI instructions |
| `ai-data-schema.yaml` | Home > Prep data for AI > Simplify the data schema |
| `synonyms.yaml` | Model view > select the object > Properties > Synonyms |
| `verified-answers.yaml` | Select the visual > More options > Set up a verified answer |

Close with the synthetic-data notice and the rule that the `Copilot/` folder is committed as Desktop writes it.

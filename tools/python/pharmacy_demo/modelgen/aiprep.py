"""Prep data for AI drafts for the AI-ready checkpoint. Maintainers only.

These are drafts. Power BI's supported route is for a person to review them and apply them in
Power BI Desktop through Home > Prep data for AI. Agents never write the persisted Copilot folder.
"""

from __future__ import annotations

AI_PREP = "fabric/ai-prep"

README = """# Prep data for AI drafts

These files are **drafts** for the Contoso Pharmacy semantic model. Power BI's supported route for AI instructions, the AI data schema, synonyms, and verified answers is the **Prep data for AI** dialog in Power BI Desktop. An agent may draft them; a person reviews and applies them.

| File | Apply it in Power BI Desktop |
|---|---|
| `ai-instructions.md` | Home > Prep data for AI > Add AI instructions. Paste the text below the first heading. Stays under 10,000 characters. |
| `ai-data-schema.yaml` | Home > Prep data for AI > Simplify the data schema. Clear every object listed under `exclude`. |
| `synonyms.yaml` | Model view > select the object > Properties > Synonyms, or the Q&A setup synonyms page. |
| `verified-answers.yaml` | Build each visual on the report, then select the visual > ... > Set up a verified answer, and add the listed trigger phrases. |

After you apply them, Desktop writes its own files under `ContosoPharmacy.SemanticModel/Copilot/`. Commit those as Desktop wrote them. Don't edit them by hand or with an agent.

Synthetic data only. Nothing here describes a real pharmacy, patient, or customer.
"""

AI_INSTRUCTIONS = """# AI instructions for Contoso Pharmacy

This model describes prescription fills at 12 Contoso Pharmacy stores from January 2024 to December 2025. All data is synthetic and contains no patient information.

## Time periods
- The latest complete month is December 2025. The latest quarter is 2025-Q4 (October to December 2025).
- "Previous period" means the previous month unless the user names another period. Use [MoM Change] and [MoM %] for month-over-month and [YoY %] for year-over-year.
- For monthly trends, group by 'Date'[Year Month]. For quarters, use 'Date'[Year Quarter]. Always use the Date table for time, not 'Prescription Fill'[Fill Date].

## Metric routing
- Prescriptions filled, fills, scripts, and prescription volume all mean [Prescriptions Filled]. It counts new prescriptions and refills.
- Processing time means [Avg Processing Time (min)]. Never sum processing minutes. Lower is better.
- Refill activity means [Refill Rate]. "Unusually high refill activity" means [Refill Rate Index vs Chain] of 1.25 or more ([High Refill Activity Flag] = 1). Unless the user names a period, evaluate it for the latest quarter, 2025-Q4.
- Medication category, drug category, and therapeutic class all mean 'Medication'[Therapeutic Category].
- "Largest volume change" by category means the absolute [MoM Change] for the latest month unless the user names other periods. Report increases and decreases.

## Presentation
- Show stores by 'Store'[Store Name] and regions by 'Store'[Region].
- State the period you used in every answer.
"""

AI_DATA_SCHEMA = """# Draft AI data schema for Contoso Pharmacy.
# Apply in Power BI Desktop: Home > Prep data for AI > Simplify the data schema.
# Only objects that differ from the model's report visibility are listed. Hidden keys are already
# hidden from everyone, so they aren't repeated here.
include:
  tables: [Date, Store, Medication, Prescription Fill]
exclude:
  - table: Prescription Fill
    column: Refill Number
    reason: Sequence attribute that invites wrong sums; use Refills or Refill Rate.
  - table: Store
    column: Open Date
    reason: Not related to the Date table; confuses time questions.
  - table: Medication
    column: Medication Code
    reason: Synthetic code with no business meaning; use Medication Name.
  - table: Prescription Fill
    measure: Prescriptions Filled PY
    reason: Helper for YoY %; keep it for reports but steer AI to YoY %.
"""

SYNONYMS = """# Draft synonyms. Apply in Model view > Properties > Synonyms, or through Q&A setup.
tables:
  Prescription Fill: [prescriptions, fills, scripts, dispensing, rx]
  Medication: [drug, medicine, product]
  Store: [pharmacy, location, branch]
  Date: [calendar, period]
columns:
  Store[Region]: [area, territory]
  Store[Store Name]: [pharmacy name, location name]
  Medication[Therapeutic Category]: [drug category, medication category, therapeutic class, drug class]
  Prescription Fill[Fill Type]: [new or refill, fill kind]
  Prescription Fill[Payer Type]: [payer, insurance type, plan type]
  Date[Year Month]: [month, calendar month]
measures:
  Prescription Fill[Prescriptions Filled]: [fills, prescription volume, scripts filled, rx count]
  Prescription Fill[Avg Processing Time (min)]: [processing time, turnaround time, wait time, time to fill]
  Prescription Fill[Refill Rate]: [refill share, refill percentage]
  Prescription Fill[Refill Rate Index vs Chain]: [refill index, refill activity index]
  Prescription Fill[MoM Change]: [month over month change, change from last month]
"""

VERIFIED_ANSWERS = """# Draft verified answer candidates, one per business question.
# Build the visual, then select it > More options > Set up a verified answer, and add the phrases.
candidates:
  - question_id: Q01
    visual: Line chart, 'Date'[Year Month] on the X-axis, [Prescriptions Filled] on the Y-axis, 'Store'[Region] as the legend
    phrases:
      - How many prescriptions were filled by region and month?
      - Monthly fills by region
  - question_id: Q02
    visual: Clustered column chart, 'Medication'[Therapeutic Category] by [MoM Change], filtered to Year Month 2025-12
    phrases:
      - Which medication categories experienced the largest volume changes?
      - Which drug categories changed the most last month?
  - question_id: Q03
    visual: Table, 'Store'[Store Name] and [Avg Processing Time (min)], sorted descending
    phrases:
      - What was the average prescription processing time by store?
      - Which stores are slowest to process prescriptions?
  - question_id: Q04
    visual: Table, 'Store'[Store Name], [Refill Rate], [Refill Rate Index vs Chain], filtered to Year Quarter 2025-Q4 and High Refill Activity Flag = 1
    phrases:
      - Which stores had unusually high refill activity?
      - Stores with abnormal refill rates
  - question_id: Q05
    visual: Card set, [Prescriptions Filled], [Prescriptions Filled PM], [MoM Change], [MoM %], filtered to Year Month 2025-12
    phrases:
      - How did prescription volume compare with the previous period?
      - Month over month prescription volume
"""


def render() -> dict[str, str]:
    return {
        f"{AI_PREP}/README.md": README,
        f"{AI_PREP}/ai-instructions.md": AI_INSTRUCTIONS,
        f"{AI_PREP}/ai-data-schema.yaml": AI_DATA_SCHEMA,
        f"{AI_PREP}/synonyms.yaml": SYNONYMS,
        f"{AI_PREP}/verified-answers.yaml": VERIFIED_ANSWERS,
    }

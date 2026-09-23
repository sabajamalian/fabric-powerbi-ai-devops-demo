---
name: prep-data-for-ai
description: Draft the Power BI "Prep data for AI" artifacts for the Contoso Pharmacy model (AI instructions, a simplified AI data schema, synonyms, and verified answer candidates) as reviewable files in fabric/ai-prep/. Use when asked to make the model ready for Power BI Copilot or a Fabric data agent, write AI instructions, add synonyms, or propose verified answers. Drafts only; never writes the Desktop-managed Copilot folder.
---
# Drafting Prep data for AI artifacts

Power BI Copilot and Fabric data agents read a semantic model's metadata plus three kinds of AI prep: **AI instructions**, an **AI data schema** (which objects AI may use), and **verified answers**. Power BI's supported way to apply them is the Prep data for AI dialog in Power BI Desktop, which writes its own files under `ContosoPharmacy.SemanticModel/Copilot/`.

So this skill writes **drafts** in `fabric/ai-prep/` that a person reviews in the pull request and then applies in Desktop.

## Hard rules

- Write only in `fabric/ai-prep/`. Never create or edit anything under `*.SemanticModel/Copilot/`. The repo's hooks deny it.
- Every name you write must exist in the model. Read the TMDL (or use Power BI Modeling MCP `model_operations`) first; don't work from memory.
- Business questions come from `pwsh ./scripts/Get-BusinessQuestions.ps1`. Don't open `evaluation/expected/`.
- Keep `ai-instructions.md` under 10,000 characters. Aim for 2,000 to 3,000; shorter instructions are followed more reliably.

## The five files

| File | Contents | Checked by |
|---|---|---|
| `README.md` | What the drafts are and how to apply each one in Desktop | L09-ai-prep-files |
| `ai-instructions.md` | Business rules and routing, in plain sentences | L09-ai-instructions |
| `ai-data-schema.yaml` | `include.tables` plus an `exclude` list, each entry with a `reason` | L09-ai-prep-files |
| `synonyms.yaml` | `tables`, `columns`, `measures` maps; keys look like `Store[Region]` | L09-synonyms |
| `verified-answers.yaml` | `candidates:` with `question_id`, `visual`, and `phrases` for each question | L09-verified-answers |

Formats and a worked example are in [references/formats.md](references/formats.md).

## What the AI instructions must settle

These are the ambiguities that make baseline answers wrong. Settle each one in a sentence:

1. **The latest period.** The data runs January 2024 to December 2025, so the latest complete month is December 2025 and the latest quarter is 2025-Q4.
2. **"Previous period"** means the previous month unless the user says otherwise. Name the measures: `[MoM Change]`, `[MoM %]`, and `[YoY %]`.
3. **Metric routing.** "Prescriptions filled", "fills", and "scripts" mean `[Prescriptions Filled]`. Processing time means `[Avg Processing Time (min)]` (an average; never sum minutes).
4. **"Unusually high refill activity"** means `[Refill Rate Index vs Chain]` of 1.25 or more, for the latest quarter unless a period is named.
5. **Medication category** means `'Medication'[Therapeutic Category]`.
6. **Time grouping** uses the `Date` table (`'Date'[Year Month]`), never the fact table's own date column.
7. **Presentation.** Show stores by Store Name, and state the period in every answer.

## Model flags that go with the drafts

Two settings live in the model, not in the drafts. Make them with the `tmdl-authoring` skill:

- `"qnaEnabled": true` under `settings` in `ContosoPharmacy.SemanticModel/definition.pbism`.
- `isDefaultLabel` on `'Store'[Store Name]` and `'Medication'[Medication Name]` (rule C14).

## Check your work

```powershell
pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 09
```

The output names any missing term, synonym key, or question ID.

## Handing off to a person

End with a short list for the reviewer: what each file changes, and the Desktop steps from `README.md`. After they apply the drafts, Desktop writes the `Copilot/` folder. They commit it as Desktop wrote it.

---
name: write-ai-prep-drafts
description: Draft Prep data for AI artifacts (AI instructions, AI data schema, synonyms, verified answers) in fabric/ai-prep/ and set the model flags that go with them.
agent: model-improver
---
Draft the Prep data for AI files for the Contoso Pharmacy model. Use the `prep-data-for-ai` skill and follow its hard rules.

1. Read the current model so every name you write exists.
2. Get the business questions with `pwsh ./scripts/Get-BusinessQuestions.ps1`.
3. Write the five files in `fabric/ai-prep/`: `README.md`, `ai-instructions.md`, `ai-data-schema.yaml`, `synonyms.yaml`, `verified-answers.yaml`.
4. Set `"qnaEnabled": true` in `definition.pbism`, and `isDefaultLabel` on `'Store'[Store Name]` and `'Medication'[Medication Name]`.
5. Run `pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 09` and fix anything it reports.

Don't create or edit anything under `ContosoPharmacy.SemanticModel/Copilot/`. End with the Desktop steps a person follows to apply the drafts.

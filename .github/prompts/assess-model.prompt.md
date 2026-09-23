---
name: assess-model
description: Assess the semantic model against the team conventions and AI-readiness checklist and write out/assessment.md.
agent: model-assessor
argument-hint: Optional focus area
---
Assess the Contoso Pharmacy semantic model in `fabric/ContosoPharmacy.SemanticModel/`.

${input:focus:Optional focus, or leave blank for the whole model}

1. Run `pwsh ./scripts/Test-ModelConventions.ps1 -Markdown` for the deterministic findings.
2. Inspect the model through Power BI Modeling MCP if it's connected, otherwise read the TMDL files.
3. Write `out/assessment.md` in the format your instructions define, with at least 8 findings.
4. In chat, list the three fixes that would most improve AI answers to the business questions.

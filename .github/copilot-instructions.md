# Copilot instructions for the Contoso Pharmacy lab

This repository is a hands-on lab. It teaches GitHub Copilot's agent features (instructions, prompt files, skills, custom agents, handoffs, hooks, MCP, the Copilot CLI, the cloud agent, and code review) using a Power BI semantic model stored as code.

## Synthetic data only

Every row of data here is synthetic and generated from a fixed seed. Never add real patient, customer, employee, or tenant data, names, identifiers, or screenshots. Never add credentials, tokens, tenant IDs, workspace IDs, or connection strings. Use placeholders such as `${input:...}` or `${env:...}`.

## Repository map

| Path | What it holds |
|---|---|
| `fabric/ContosoPharmacy.pbip` | Power BI Project. Open it in Power BI Desktop (Windows only). |
| `fabric/ContosoPharmacy.SemanticModel/definition/` | The semantic model as TMDL. This is what most tasks change. |
| `fabric/ContosoPharmacy.Report/definition/` | The report as PBIR JSON. Field references must match model names. |
| `fabric/ai-prep/` | Drafts for Power BI's Prep data for AI (AI instructions, schema, synonyms, verified answers). |
| `data/generated/` | Synthetic CSVs. Generated; never edit by hand. |
| `evaluation/` | Business questions, run files, and the grading rubric. Expected answers are hidden from agents. |
| `rules/` | Naming conventions and required model objects, read by the checks and the skills. |
| `tools/python/pharmacy_demo/` | Python tools behind every script: data generation, lint, conventions, grading, lab checks, hooks. |
| `scripts/` | PowerShell 7 entry points. Learners run these. |
| `lab/` | Lab verification contract (`checks.yaml`) and checkpoint manifest (`checkpoints.json`). |
| `site/` | The self-paced lab site (Astro Starlight), published to GitHub Pages. |
| `.github/agents`, `skills`, `prompts`, `instructions`, `hooks` | The Copilot customizations the labs teach. |

## Commands

Windows PowerShell 7 is the primary shell. The same scripts run in `pwsh` on macOS and Linux.

| Task | Command |
|---|---|
| Set up the Python environment | `pwsh ./scripts/Initialize-DevEnvironment.ps1` |
| Validate everything (no Fabric tenant needed) | `pwsh ./scripts/Invoke-Validation.ps1` |
| TMDL lint only | `pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl` |
| Check report field bindings | `pwsh ./scripts/Test-ReportBindings.ps1` |
| Convention and AI-readiness findings | `pwsh ./scripts/Test-ModelConventions.ps1` (add `-Rule C07,C08` or `-Json`) |
| List the business questions | `pwsh ./scripts/Get-BusinessQuestions.ps1` |
| Grade a question run | `pwsh ./scripts/Grade-QuestionRun.ps1 -Run <label>` |
| Check a lab | `pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 07` |

Run validation after every model change and fix the first error before moving on.

## Rules for every task

- Don't edit `data/generated/**` or `evaluation/expected/**`. Change the generator or the questions and rerun the scripts instead.
- When you answer the business questions, don't read `evaluation/expected/**`, `evaluation/questions.yaml`, or the reference DAX. Get the questions from `pwsh ./scripts/Get-BusinessQuestions.ps1` and answer from the model only.
- Don't edit `fabric/ContosoPharmacy.SemanticModel/Copilot/**`. Power BI Desktop writes it. Draft AI metadata in `fabric/ai-prep/` instead.
- Keep `lineageTag` values when you rename or edit model objects. Keep `sourceColumn` unchanged when you rename a column.
- If Power BI Desktop has the model open, edit through Power BI Modeling MCP, or ask the user to close Desktop before you edit TMDL files. Desktop overwrites external file edits when it saves.
- After renaming model objects, fix the report with the `pbir-rebinding` skill and run `Test-ReportBindings.ps1`.
- Work on a feature branch. Don't commit, push, force push, or change global Git config unless the user asks.
- Follow `rules/naming-conventions.yaml` and the `pharmacy-model-conventions` skill for names, descriptions, display folders, and measures.

## Writing style for prose

For Markdown, lab pages, descriptions, and PR text: be direct and specific, use short sentences, and lead with the point. Don't use em dashes or en dashes (use a comma, colon, parentheses, or "to"). Don't use emojis. Validation fails on dashes in Markdown prose.

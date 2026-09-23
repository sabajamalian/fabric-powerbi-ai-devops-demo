# Agent guide

Instructions for any coding agent working in this repository. GitHub Copilot also reads `.github/copilot-instructions.md`, which has the full repository map.

## What this repo is

A self-paced lab that improves a Power BI semantic model (PBIP with TMDL and PBIR) using GitHub Copilot's agent features. All data is synthetic. It never needs a Microsoft Fabric tenant.

## Set up and validate

```powershell
pwsh ./scripts/Initialize-DevEnvironment.ps1   # creates .venv from hashed lock files
pwsh ./scripts/Invoke-Validation.ps1           # data, expected answers, runs, TMDL lint, bindings, customizations, hygiene
pwsh ./scripts/Invoke-Validation.ps1 -Tests    # plus pytest and Pester
```

On macOS or Linux the same commands work in `pwsh`. Python tools can also run directly: `.venv/bin/python -m pharmacy_demo validate`.

## Boundaries

- Never edit generated files: `data/generated/**`, `evaluation/expected/**`, `fabric/**/.pbi/cache.abf`, `fabric/**/.pbi/localSettings.json`, or `fabric/**/Copilot/**`.
- Never read expected answers or reference DAX while answering the business questions.
- Never add real people, customers, credentials, tenant IDs, or workspace IDs.
- Never force push or change global Git config.
- Repository hooks in `.github/hooks/guardrails.json` enforce the first, second, and fourth rules for Copilot CLI, VS Code, and the cloud agent.

## Custom agents

| Agent | Use it to |
|---|---|
| `question-tester` | Answer the five business questions from the model and grade the run |
| `model-assessor` | Review the model against the conventions without changing it |
| `model-improver` | Fix names, descriptions, relationships, measures, and AI prep drafts |
| `model-reviewer` | Review a model pull request |
| `lab-author` | Write or update lab pages (maintainers) |

Agent files live in `.github/agents/`. Skills they load live in `.github/skills/`.

## Done means

- `pwsh ./scripts/Invoke-Validation.ps1` passes.
- Renamed objects are rebound in the report (`pwsh ./scripts/Test-ReportBindings.ps1`).
- New model objects have descriptions, and new measures have format strings and display folders.

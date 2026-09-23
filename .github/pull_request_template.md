## What changed

<!-- One or two sentences. What does this PR change and why? -->

## Type of change

- [ ] Semantic model (TMDL) or report (PBIR)
- [ ] Synthetic data, questions, or expected results
- [ ] Copilot customization (instructions, agents, skills, prompts, hooks, MCP)
- [ ] Scripts, CI, or tooling
- [ ] Lab site content

## Checks

- [ ] `pwsh ./scripts/Invoke-Validation.ps1` passes locally
- [ ] If I renamed model objects, `pwsh ./scripts/Test-ReportBindings.ps1` passes
- [ ] If I changed data or questions, I ran `pwsh ./scripts/Update-ExpectedResults.ps1` and committed the results
- [ ] No credentials, tenant IDs, workspace IDs, or real customer details
- [ ] No `.pbi/localSettings.json`, `.pbi/cache.abf`, or `.pbix` files

## Business question results (model changes only)

<!-- Paste the output of: pwsh ./scripts/Compare-QuestionRuns.ps1 -Before <label> -After <label> -->

## Lab pages (site changes only)

- [ ] Ten sections in order; `npm run check` passes in `site/`
- [ ] Code shown with `RepoFile`
- [ ] Screenshots follow the checklist in CONTRIBUTING.md

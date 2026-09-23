# Contributing

Thanks for helping improve the Contoso Pharmacy agentic Copilot lab. This repo is both a working demo and the source for the self-paced lab site, so most changes touch code, lab pages, or both.

## Ground rules

- Synthetic data only. Never add real names, identifiers, customer details, or screenshots from a real tenant. See [SECURITY.md](SECURITY.md).
- Windows 11 and PowerShell 7 come first. Every script must run with `pwsh` on Windows, macOS, and Ubuntu.
- Python uses `pathlib` for paths and runs on Python 3.12 or later.
- No em dashes or en dashes in prose. `site/scripts/check-content.mjs` enforces this on the lab site.

## Local setup

```powershell
pwsh ./scripts/Test-Prerequisites.ps1
pwsh ./scripts/Initialize-DevEnvironment.ps1
pwsh ./scripts/Invoke-Validation.ps1
```

For the lab site:

```powershell
pwsh ./scripts/lab/Start-LabSite.ps1
```

## Branches and pull requests

1. Branch from `main` with a descriptive name, for example `feature/rename-store-columns` or `docs/lab-07-troubleshooting`.
2. Keep each pull request focused on one change.
3. Run `pwsh ./scripts/Invoke-Validation.ps1` before you push.
4. Fill in the pull request template, including the screenshot checklist if you changed lab pages.

`main` holds the **baseline** model that learners start from. The AI-ready model lives on `reference/ai-ready` and in the checkpoint tags. Maintainers regenerate those with `scripts/maintainer/New-LabCheckpoints.ps1`; see the script's help.

## Changing the model

- Edit TMDL as text or through Power BI Modeling MCP, then run `pwsh ./scripts/Invoke-Validation.ps1`.
- If you rename a table, column, or measure, run `pwsh ./scripts/Test-ReportBindings.ps1` and fix every report reference.
- Don't commit `.pbi/localSettings.json` or `.pbi/cache.abf`.
- Don't edit `fabric/**/Copilot/**` by hand or with an agent. Those files are written by Power BI Desktop's "Prep data for AI" feature. Draft AI metadata in `fabric/ai-prep/` instead.

## Changing the data or questions

- Change the generator, not the CSVs: `pwsh ./scripts/New-SyntheticData.ps1`.
- After any data or question change, run `pwsh ./scripts/Update-ExpectedResults.ps1` and commit the updated `evaluation/expected/*.json`.

## Lab pages

- Use the `lab-author` agent or the `/new-lab-page` prompt. Both follow the `lab-page-authoring` skill.
- Every lab page keeps the ten sections in order. `npm run check` in `site/` tells you if one is missing.
- Show code with the `RepoFile` component, not by pasting it.

### Screenshot checklist

- [ ] Captured on Windows 11 with a local account named `demo`.
- [ ] No account menus, avatars, email addresses, organization names, or tenant details visible.
- [ ] No window title or path showing a real username.
- [ ] PNG, 1600 px wide or less, stored under `site/src/assets/screenshots/labNN/`.
- [ ] Alt text describes the state shown.

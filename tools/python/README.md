# pharmacy_demo (Python tooling)

Python 3.12+ package behind the PowerShell entry points in `scripts/`. You normally don't call it directly; use the scripts.

| Module | Used by |
|---|---|
| `datagen` | `scripts/New-SyntheticData.ps1` |
| `oracle` | `scripts/Update-ExpectedResults.ps1` |
| `tmdl` | `scripts/Invoke-Validation.ps1`, the `postToolUse` hook |
| `pbir` | `scripts/Test-ReportBindings.ps1` |
| `repo_checks` | `scripts/Invoke-Validation.ps1` (hygiene and identifier guard) |
| `evaluation` | `scripts/Grade-QuestionRun.ps1`, `scripts/Compare-QuestionRuns.ps1` |
| `labcheck` | `scripts/lab/Test-LabProgress.ps1` |
| `modelgen` | Maintainers only: `scripts/maintainer/New-LabCheckpoints.ps1` |

Run the tests from the repo root:

```powershell
.\.venv\Scripts\python.exe -m pytest tools/python/tests
```

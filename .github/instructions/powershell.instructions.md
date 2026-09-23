---
applyTo: "scripts/**/*.ps1"
description: Conventions for the lab's PowerShell 7 scripts.
---
# PowerShell scripts

- Target PowerShell 7.2 or later (`#Requires -Version 7.2`). Scripts must run on Windows, macOS, and Linux under `pwsh`.
- Start every script with comment-based help (`.SYNOPSIS`, `.DESCRIPTION`, `.PARAMETER`, `.EXAMPLE`) and `[CmdletBinding(PositionalBinding = $false)]`. The lab site generates its script reference from the help.
- Take list parameters as comma-separated strings and split them inside the script, so `-Rule C07,C08` works the same from any shell.
- Dot-source `_Common.ps1` for `Get-RepoRoot`, `Get-VenvPython`, and `Invoke-PharmacyDemo`. Build paths with `Join-Path` and quote them with `-LiteralPath`, because learners clone into folders with spaces.
- Never install software. Check for it and print the install command instead.
- Pass arguments to external tools as arrays. Use `Invoke-Git -Arguments @(...)` from `_Checkpoints.ps1` for Git.
- Wrap single results in `@()` before indexing, because PowerShell unrolls one-item arrays.
- Guard Windows-only code with `$IsWindows` and exit 0 with a clear SKIP message elsewhere.
- Run `Invoke-ScriptAnalyzer -Path scripts -Recurse -Settings PSScriptAnalyzerSettings.psd1` and `Invoke-Pester -Path scripts/tests` before you commit.

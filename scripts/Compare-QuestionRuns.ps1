#Requires -Version 7.2
<#
.SYNOPSIS
    Compares two graded question runs and writes a Markdown before-and-after table.
.PARAMETER Before
    Run label or path for the earlier run, for example local-baseline.
.PARAMETER After
    Run label or path for the later run, for example local-ai-ready.
.PARAMETER OutFile
    Where to write the table. Default: out/question-comparison.md.
.EXAMPLE
    pwsh ./scripts/Compare-QuestionRuns.ps1 -Before local-baseline -After local-ai-ready
.EXAMPLE
    pwsh ./scripts/Compare-QuestionRuns.ps1 -Before sample-baseline -After sample-ai-ready
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)] [string] $Before,
    [Parameter(Mandatory)] [string] $After,
    [string] $OutFile
)

. (Join-Path $PSScriptRoot '_Common.ps1')
if (-not $OutFile) { $OutFile = Join-Path (Get-RepoRoot) 'out' 'question-comparison.md' }
$target = [System.IO.Path]::GetFullPath($OutFile, (Get-Location).Path)
exit (Invoke-PharmacyDemo compare --before $Before --after $After --out $target)

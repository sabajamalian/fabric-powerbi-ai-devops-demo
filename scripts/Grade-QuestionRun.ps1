#Requires -Version 7.2
<#
.SYNOPSIS
    Grades a question run against the expected answers and writes the grade into the run file.
.DESCRIPTION
    A run file (evaluation/runs/<label>.json) holds the answers an agent or person gave to the five
    business questions. Each question scores 0, 1, or 2 using the rubric in evaluation/rubric.md.
.PARAMETER Run
    A run label such as local-baseline, or a path to a run file.
.PARAMETER NoWrite
    Print the grade without updating the run file.
.PARAMETER Json
    Print the grade as JSON.
.EXAMPLE
    pwsh ./scripts/Grade-QuestionRun.ps1 -Run local-baseline
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)] [string] $Run,
    [switch] $NoWrite,
    [switch] $Json
)

. (Join-Path $PSScriptRoot '_Common.ps1')
$arguments = @('grade', $Run)
if ($NoWrite) { $arguments += '--no-write' }
if ($Json) { $arguments += '--json' }
exit (Invoke-PharmacyDemo @arguments)

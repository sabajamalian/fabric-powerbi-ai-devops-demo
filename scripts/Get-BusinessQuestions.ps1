#Requires -Version 7.2
<#
.SYNOPSIS
    Prints the five business questions, their paraphrases, and the answer columns, without answers.
.DESCRIPTION
    This is the only way agents and learners should read the question set. The full file,
    evaluation/questions.yaml, also holds reference answers and is hidden from agents by the hooks.
.PARAMETER Json
    Print the questions as JSON.
.EXAMPLE
    pwsh ./scripts/Get-BusinessQuestions.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param([switch] $Json)

. (Join-Path $PSScriptRoot '_Common.ps1')
$arguments = @('questions')
if ($Json) { $arguments += '--json' }
exit (Invoke-PharmacyDemo @arguments)

#Requires -Version 7.2
<#
.SYNOPSIS
    Recomputes evaluation/expected/*.json from the synthetic CSVs with DuckDB, or checks them.
.DESCRIPTION
    The expected answers come from reference SQL that runs directly over the CSV files, so they
    never depend on the semantic model being right. Run this after regenerating the data.
.PARAMETER Check
    Don't write anything. Exit 1 if the committed answers are out of date.
.EXAMPLE
    pwsh ./scripts/Update-ExpectedResults.ps1 -Check
#>
[CmdletBinding(PositionalBinding = $false)]
param([switch] $Check)

. (Join-Path $PSScriptRoot '_Common.ps1')
exit (Invoke-PharmacyDemo expected ($Check ? 'check' : 'generate'))

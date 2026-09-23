#Requires -Version 7.2
<#
.SYNOPSIS
    Checks that every field used by a report visual exists in the semantic model.
.DESCRIPTION
    Reads the PBIR visual.json files and the TMDL model, then lists visuals that point at a table,
    column, or measure that doesn't exist (usually after a rename). Use the pbir-rebinding skill to
    fix what it finds.
.PARAMETER Json
    Print problems as JSON.
.EXAMPLE
    pwsh ./scripts/Test-ReportBindings.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param([switch] $Json)

. (Join-Path $PSScriptRoot '_Common.ps1')
$arguments = @('bindings')
if ($Json) { $arguments += '--json' }
exit (Invoke-PharmacyDemo @arguments)

#Requires -Version 7.2
<#
.SYNOPSIS
    Regenerates the synthetic CSV files in data/generated/, or checks that they match the seed.
.DESCRIPTION
    The data is deterministic: the same seed always produces the same bytes on Windows, macOS,
    and Linux. Only change the data by changing tools/python/pharmacy_demo/datagen.py; then run
    this script and scripts/Update-ExpectedResults.ps1.
.PARAMETER Check
    Don't write anything. Exit 1 if the committed files differ from the generator.
.EXAMPLE
    pwsh ./scripts/New-SyntheticData.ps1 -Check
#>
[CmdletBinding(PositionalBinding = $false)]
param([switch] $Check)

. (Join-Path $PSScriptRoot '_Common.ps1')
exit (Invoke-PharmacyDemo data ($Check ? 'check' : 'generate'))

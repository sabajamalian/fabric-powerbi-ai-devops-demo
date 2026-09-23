#Requires -Version 7.2
<#
.SYNOPSIS
    Checks whether you finished a lab, and tells you what to fix and where on the lab site.
.DESCRIPTION
    Runs the checks for one lab from lab/checks.yaml. Each result is PASS, FAIL, WARN (an optional
    check failed), or SKIP (Windows-only check on another OS). Failures include a hint and a link to
    the step on the lab site. Exits 0 when every required check passes.

    Lab 00 runs before the Python environment exists, so it uses scripts/Test-Prerequisites.ps1.
.PARAMETER Lab
    Lab number, for example 7 or 07.
.PARAMETER Only
    Run only these check IDs, comma-separated.
.PARAMETER Json
    Print results as JSON.
.EXAMPLE
    pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 07
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)] [ValidatePattern('^\d{1,2}$')] [string] $Lab,
    [string[]] $Only,
    [switch] $Json
)

. (Join-Path $PSScriptRoot '..' '_Common.ps1')

$Lab = '{0:D2}' -f [int] $Lab
if ($Lab -eq '00' -and -not (Get-VenvPython)) {
    & (Join-Path $PSScriptRoot '..' 'Test-Prerequisites.ps1') -Json:$Json
    exit $LASTEXITCODE
}

$arguments = @('labcheck', '--lab', $Lab)
$Only = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object Trim | Where-Object { $_ })
if ($Only) { $arguments += '--only'; $arguments += $Only }
if ($Json) { $arguments += '--json' }
exit (Invoke-PharmacyDemo @arguments)

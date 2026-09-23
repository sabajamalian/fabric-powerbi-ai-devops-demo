#Requires -Version 7.2
<#
.SYNOPSIS
    Runs every validation step that doesn't need a Fabric tenant or Power BI Desktop.
.DESCRIPTION
    Checks that the synthetic data matches the seed, the expected answers are current, the question
    and run files match their schemas, the TMDL lints clean, every report visual binds to a field
    that exists, and the repository hygiene rules pass (no PHI-like columns, identifiers, secrets,
    forbidden files, or dashes in prose). This is the same check CI runs on every pull request.
.PARAMETER Only
    Run only these steps, comma-separated: data, expected, questions, runs, tmdl, bindings, customizations, hygiene.
.PARAMETER Json
    Print results as JSON.
.PARAMETER Tests
    Also run the Python unit tests (pytest) and the Pester tests.
.EXAMPLE
    pwsh ./scripts/Invoke-Validation.ps1
.EXAMPLE
    pwsh ./scripts/Invoke-Validation.ps1 -Only tmdl,bindings
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [string[]] $Only,
    [switch] $Json,
    [switch] $Tests
)

. (Join-Path $PSScriptRoot '_Common.ps1')

$steps = 'data', 'expected', 'questions', 'runs', 'tmdl', 'bindings', 'customizations', 'hygiene'
$Only = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object Trim | Where-Object { $_ })
$unknown = @($Only | Where-Object { $_ -notin $steps })
if ($unknown) {
    Write-Error "Unknown step(s): $($unknown -join ', '). Choose from: $($steps -join ', ')."
    exit 2
}

$arguments = @('validate')
if ($Only) { $arguments += '--only'; $arguments += $Only }
if ($Json) { $arguments += '--json' }
$code = Invoke-PharmacyDemo @arguments

if ($Tests) {
    $root = Get-RepoRoot
    $python = Get-VenvPython -Root $root
    Write-Section 'pytest'
    Push-Location (Join-Path $root 'tools' 'python')
    try {
        & $python -m pytest -q | Out-Host
        if ($LASTEXITCODE -ne 0) { $code = 1 }
    } finally {
        Pop-Location
    }
    Write-Section 'Pester'
    if (Get-Module -ListAvailable -Name Pester | Where-Object Version -GE ([version]'5.5')) {
        $result = Invoke-Pester -Path (Join-Path $root 'scripts' 'tests') -Output Detailed -PassThru
        if ($result.FailedCount -gt 0) { $code = 1 }
    } else {
        Write-Host 'Pester 5.5+ is not installed; skipping. Install-Module Pester -Scope CurrentUser' -ForegroundColor Yellow
    }
}
exit $code

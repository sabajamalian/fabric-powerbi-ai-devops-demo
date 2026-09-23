#Requires -Version 7.2
<#
.SYNOPSIS
    Creates the repo's Python environment (.venv) and installs the pinned lab tools.
.DESCRIPTION
    1. Finds Python 3.12+ (the py launcher on Windows, then python3 or python).
    2. Creates .venv in the repo root if it doesn't exist.
    3. Installs tools/python/requirements-dev.txt with --require-hashes, then the pharmacy_demo
       package in editable mode.
    4. Optionally runs npm ci in site/ so you can preview the lab site locally.
    5. Runs the validation suite once.

    It doesn't install system software. Run scripts/Test-Prerequisites.ps1 first if you're not sure
    what's installed.
.PARAMETER Force
    Delete and recreate .venv.
.PARAMETER Site
    Also install the lab site's Node packages (needs Node.js 20+).
.EXAMPLE
    pwsh ./scripts/Initialize-DevEnvironment.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [switch] $Force,
    [switch] $Site
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_Common.ps1')

$root = Get-RepoRoot
$venv = Join-Path $root '.venv'

Write-Section 'Python'
$system = Find-SystemPython
if (-not $system) {
    Write-Host 'Python 3.12 or later was not found. Run scripts/Test-Prerequisites.ps1 for the install command.' -ForegroundColor Red
    exit 1
}
Write-Host "Using Python $($system.Version) at $($system.Command)"

if ($Force -and (Test-Path -LiteralPath $venv)) {
    Write-Host 'Removing the existing .venv'
    Remove-Item -LiteralPath $venv -Recurse -Force
}
if (-not (Get-VenvPython -Root $root)) {
    Write-Host "Creating $venv"
    $createArgs = @($system.Arguments) + @('-m', 'venv', $venv)
    & $system.Command @createArgs
    if ($LASTEXITCODE -ne 0) { throw 'python -m venv failed.' }
}
$python = Get-VenvPython -Root $root

Write-Section 'Pinned packages'
$requirements = Join-Path $root 'tools' 'python' 'requirements-dev.txt'
& $python -m pip install --disable-pip-version-check --quiet --require-hashes -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'pip install of the pinned requirements failed.' }
# setuptools is pinned in requirements-dev.txt, so the editable build doesn't fetch anything unhashed.
& $python -m pip install --disable-pip-version-check --quiet --no-deps --no-build-isolation -e (Join-Path $root 'tools' 'python')
if ($LASTEXITCODE -ne 0) { throw 'Installing the pharmacy_demo package failed.' }
Write-Host 'Installed pharmacy_demo and its pinned dependencies.'

if ($Site) {
    Write-Section 'Lab site packages'
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) {
        Write-Host 'npm not found; skipping. Install Node.js 20+ to preview the site locally.' -ForegroundColor Yellow
    } else {
        Push-Location (Join-Path $root 'site')
        try {
            & $npm.Source ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
        } finally {
            Pop-Location
        }
    }
}

Write-Section 'Validation'
$code = Invoke-PharmacyDemo validate
if ($code -eq 0) {
    Write-Host ''
    Write-Host 'Ready. Next: pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab 01' -ForegroundColor Green
}
exit $code

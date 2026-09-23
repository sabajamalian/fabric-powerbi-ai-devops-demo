#Requires -Version 7.2
<#
.SYNOPSIS
    Runs the lab site locally at http://localhost:4321/ so you can read the labs offline or preview edits.
.DESCRIPTION
    Installs the site's pinned Node packages with npm ci the first time, then starts the Astro dev
    server. Press Ctrl+C to stop it. Needs Node.js 20 or later.
.PARAMETER Build
    Build the static site into site/dist and run the content checks instead of starting the server.
.EXAMPLE
    pwsh ./scripts/lab/Start-LabSite.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param([switch] $Build)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..' '_Common.ps1')

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host 'npm not found. Install Node.js 20+ (winget install OpenJS.NodeJS.LTS) and open a new terminal.' -ForegroundColor Red
    exit 1
}
$site = Join-Path (Get-RepoRoot) 'site'
Push-Location $site
try {
    if (-not (Test-Path -LiteralPath (Join-Path $site 'node_modules'))) {
        & $npm.Source ci --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & $npm.Source run ($Build ? 'build' : 'dev')
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

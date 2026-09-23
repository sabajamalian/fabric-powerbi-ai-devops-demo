#Requires -Version 7.2
<#
.SYNOPSIS
    Maintainers and upstream CI: checks that every checkpoint tag exists and passes its lab checks.
.DESCRIPTION
    For each checkpoint in lab/checkpoints.json, checks out the tag into a temporary worktree,
    creates the outputs a restore would create, runs the full validation, and runs the lab checks
    listed under `verify`. Aliases (baseline-v1, ai-ready-v1) must point at the same commit.
.PARAMETER Fetch
    Fetch tags from this remote first, for example origin.
.PARAMETER AllowMissing
    Report missing tags as warnings instead of failures (useful before the first release).
.EXAMPLE
    pwsh ./scripts/lab/Test-CheckpointTags.ps1 -Fetch origin
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [string] $Fetch,
    [switch] $AllowMissing
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..' '_Common.ps1')
. (Join-Path $PSScriptRoot '..' '_Checkpoints.ps1')

$root = Get-RepoRoot
$python = Get-VenvPython -Root $root
if (-not $python) { throw 'Run scripts/Initialize-DevEnvironment.ps1 first.' }
$manifest = Get-LabCheckpointManifest -Root $root
if ($Fetch) { Invoke-Git -Root $root -Arguments @('fetch', '--tags', '--force', $Fetch) | Out-Null }

$failures = 0
$missing = 0
foreach ($c in $manifest.checkpoints) {
    Write-Section $c.tag
    $commit = Invoke-Git -Root $root -Arguments @('rev-parse', '--verify', '--quiet', "refs/tags/$($c.tag)^{commit}") -AllowFailure
    if (-not $commit) {
        if ($AllowMissing) { Write-Host 'WARN  tag not found' -ForegroundColor Yellow; $missing++; continue }
        Write-Host 'FAIL  tag not found' -ForegroundColor Red; $failures++; continue
    }
    foreach ($alias in $c.aliases) {
        $aliasCommit = Invoke-Git -Root $root -Arguments @('rev-parse', '--verify', '--quiet', "refs/tags/$alias^{commit}") -AllowFailure
        if ("$aliasCommit" -ne "$commit") {
            Write-Host "FAIL  alias $alias doesn't point at the same commit" -ForegroundColor Red
            $failures++
        }
    }
    $worktree = Join-Path ([IO.Path]::GetTempPath()) "cpdemo-$($c.name)-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    Invoke-Git -Root $root -Arguments @('worktree', 'add', '--detach', $worktree, $c.tag) | Out-Null
    try {
        Initialize-CheckpointOutput -Root $worktree -Checkpoint $c | Out-Null
        & $python -m pharmacy_demo --root $worktree validate | Out-Host
        if ($LASTEXITCODE -ne 0) { $failures++ }
        foreach ($lab in $c.verify) {
            & $python -m pharmacy_demo --root $worktree labcheck --lab $lab | Out-Host
            if ($LASTEXITCODE -ne 0) { $failures++ }
        }
    } finally {
        Invoke-Git -Root $root -Arguments @('worktree', 'remove', '--force', $worktree) | Out-Null
    }
}
Write-Host ''
if ($failures) { Write-Host "$failures checkpoint problem(s)." }
elseif ($missing) { Write-Host "No failures, but $missing of $(@($manifest.checkpoints).Count) checkpoint tags are missing. Run scripts/maintainer/New-LabCheckpoints.ps1 and push the tags." }
else { Write-Host 'All checkpoints pass.' }
exit ($failures ? 1 : 0)

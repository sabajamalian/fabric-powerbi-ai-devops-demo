#Requires -Version 7.2
<#
.SYNOPSIS
    Maintainers only: builds the reference/ai-ready branch and the checkpoint tags.
.DESCRIPTION
    Starting from a commit with the baseline model (normally the release commit on main):

    1. Tags it baseline-v1, checkpoint/lab02-start, and checkpoint/lab05-complete.
    2. In a temporary worktree on reference/ai-ready, commits one step per checkpoint:
       lab06 (sample assessment), lab07 (names), lab08 (relationships and measures),
       lab09 (AI metadata), generating each model stage with pharmacy_demo modelgen.
    3. Runs validation and the lab checks for every step before tagging it.
    4. Removes the worktree. Nothing is pushed unless you pass -Push.

    The answers live only on reference/ai-ready and the tags, so learner copies made with
    Use this template don't contain them.
.PARAMETER Source
    Commit to build from. Default: HEAD.
.PARAMETER Force
    Move existing tags and reset reference/ai-ready.
.PARAMETER Push
    Push reference/ai-ready and all checkpoint tags to -Remote when done.
.PARAMETER Remote
    Remote to push to. Default: origin.
.EXAMPLE
    pwsh ./scripts/maintainer/New-LabCheckpoints.ps1
.EXAMPLE
    pwsh ./scripts/maintainer/New-LabCheckpoints.ps1 -Force -Push
#>
[CmdletBinding(PositionalBinding = $false, SupportsShouldProcess)]
param(
    [string] $Source = 'HEAD',
    [switch] $Force,
    [switch] $Push,
    [string] $Remote = 'origin'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..' '_Common.ps1')
. (Join-Path $PSScriptRoot '..' '_Checkpoints.ps1')

$root = Get-RepoRoot
$python = Get-VenvPython -Root $root
if (-not $python) { throw 'Run scripts/Initialize-DevEnvironment.ps1 first.' }
$manifest = Get-LabCheckpointManifest -Root $root
$branch = $manifest.branch

if (Invoke-Git -Root $root -Arguments @('status', '--porcelain', '--untracked-files=no')) {
    throw 'Commit your changes first; the checkpoints are built from committed history.'
}
$base = @(Invoke-Git -Root $root -Arguments @('rev-parse', '--verify', "$Source^{commit}"))[0]

$allTags = @($manifest.checkpoints | ForEach-Object { $_.tag; $_.aliases })
if (-not $Force) {
    $existing = @($allTags | Where-Object { Invoke-Git -Root $root -Arguments @('rev-parse', '--verify', '--quiet', "refs/tags/$_") -AllowFailure })
    if ($existing) { throw "Tags already exist: $($existing -join ', '). Use -Force to move them." }
}

function Add-CheckpointTag {
    param([string] $Worktree, $Checkpoint)
    foreach ($name in @($Checkpoint.tag) + @($Checkpoint.aliases)) {
        Invoke-Git -Root $Worktree -Arguments @('tag', '-a', '-f', $name, '-m', "Lab checkpoint: $($Checkpoint.name). $($Checkpoint.description)") | Out-Null
        Write-Host "  tagged $name"
    }
}

function Test-Checkpoint {
    param([string] $Worktree, $Checkpoint)
    $probe = Join-Path ([IO.Path]::GetTempPath()) "cpdemo-probe-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
    Invoke-Git -Root $Worktree -Arguments @('worktree', 'add', '--detach', $probe, 'HEAD') | Out-Null
    try {
        Initialize-CheckpointOutput -Root $probe -Checkpoint $Checkpoint | Out-Null
        & $python -m pharmacy_demo --root $probe validate | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Validation failed for $($Checkpoint.name)." }
        foreach ($lab in $Checkpoint.verify) {
            & $python -m pharmacy_demo --root $probe labcheck --lab $lab | Out-Null
            if ($LASTEXITCODE -ne 0) {
                & $python -m pharmacy_demo --root $probe labcheck --lab $lab | Out-Host
                throw "Lab $lab checks failed for $($Checkpoint.name)."
            }
        }
    } finally {
        Invoke-Git -Root $Worktree -Arguments @('worktree', 'remove', '--force', $probe) | Out-Null
    }
}

$worktree = Join-Path ([IO.Path]::GetTempPath()) "cpdemo-reference-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
Invoke-Git -Root $root -Arguments @('worktree', 'add', '-B', $branch, $worktree, $base) | Out-Null
$env:CPDEMO_MAINTAINER = '1'
try {
    foreach ($c in $manifest.checkpoints) {
        Write-Section $c.name
        switch ($c.name) {
            'lab06-complete' {
                $sampleDir = Join-Path $worktree 'lab' 'samples'
                New-Item -ItemType Directory -Force -Path $sampleDir | Out-Null
                $table = & $python -m pharmacy_demo --root $worktree conventions --markdown
                $header = @(
                    '# Sample assessment of the baseline model',
                    '',
                    'Checkpoint copy of what the model-assessor agent produces in Lab 06. Generated from',
                    'rules/*.yaml by scripts/Test-ModelConventions.ps1, so it lists every finding; an agent',
                    'report groups and prioritizes them.',
                    ''
                )
                ($header + $table) | Set-Content -LiteralPath (Join-Path $sampleDir 'assessment.md') -Encoding utf8NoBOM
            }
            { $_ -in 'lab07-complete', 'lab08-complete', 'lab09-complete' } {
                & $python -m pharmacy_demo --root $worktree modelgen --stage $c.stage | Out-Null
                if ($LASTEXITCODE -ne 0) { throw "modelgen stage $($c.stage) failed." }
            }
        }
        $paths = @($manifest.restore_paths | Where-Object { Test-Path -LiteralPath (Join-Path $worktree $_) })
        Invoke-Git -Root $worktree -Arguments (@('add', '-A', '--') + $paths) | Out-Null
        $staged = @(Invoke-Git -Root $worktree -Arguments @('diff', '--cached', '--name-only'))
        if ($staged) {
            Invoke-Git -Root $worktree -Arguments @('commit', '-q', '-m', "Lab checkpoint: $($c.name)", '-m', $c.description) | Out-Null
            Write-Host "  committed $($staged.Count) file(s)"
        }
        Test-Checkpoint -Worktree $worktree -Checkpoint $c
        Write-Host '  checks pass'
        Add-CheckpointTag -Worktree $worktree -Checkpoint $c
    }
} finally {
    Remove-Item Env:CPDEMO_MAINTAINER -ErrorAction SilentlyContinue
    Invoke-Git -Root $root -Arguments @('worktree', 'remove', '--force', $worktree) | Out-Null
}

$refs = @("refs/heads/$branch") + @($allTags | ForEach-Object { "refs/tags/$_" })
if ($Push) {
    if ($PSCmdlet.ShouldProcess($Remote, "Push $branch and $($allTags.Count) tags")) {
        $pushArgs = @('push') + ($Force ? @('--force') : @()) + @($Remote) + $refs
        Invoke-Git -Root $root -Arguments $pushArgs | Out-Host
    }
} else {
    Write-Host ''
    Write-Host 'Built locally. To publish:'
    Write-Host "  git push $($Force ? '--force ' : '')$Remote $($refs -join ' ')"
}
exit 0

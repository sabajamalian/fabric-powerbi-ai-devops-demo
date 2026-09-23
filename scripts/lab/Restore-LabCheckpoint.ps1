#Requires -Version 7.2
<#
.SYNOPSIS
    Catches you up to the end of a lab by restoring the model from an upstream checkpoint tag.
.DESCRIPTION
    Use this when you want to skip a lab or start over from a known-good state.

    1. Stops if you have uncommitted changes. Commit or stash them first; the script won't do it.
    2. Fetches the checkpoint tag from the upstream lab repo.
    3. Creates a new branch, lab/<checkpoint>-<timestamp>, from your current commit.
    4. Restores only fabric/ and lab/samples/ from the tag and stages the result.
    5. Creates the gitignored outputs the checkpoint implies (a local-baseline run, the sample
       assessment) when they don't exist yet.

    Your other files (instructions, agents, skills, prompts you wrote) are left alone.
    Close Power BI Desktop first, and reopen the project afterward.
.PARAMETER Checkpoint
    lab02-start, lab05-complete, lab06-complete, lab07-complete, lab08-complete, or lab09-complete.
.PARAMETER Remote
    The remote that points at the upstream lab repo. Default: upstream.
.PARAMETER List
    List the checkpoints and exit.
.EXAMPLE
    pwsh ./scripts/lab/Restore-LabCheckpoint.ps1 -Checkpoint lab07-complete
.EXAMPLE
    pwsh ./scripts/lab/Restore-LabCheckpoint.ps1 -List
#>
[CmdletBinding(PositionalBinding = $false, DefaultParameterSetName = 'Restore')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Restore')]
    [ValidateSet('lab02-start', 'lab05-complete', 'lab06-complete', 'lab07-complete', 'lab08-complete', 'lab09-complete')]
    [string] $Checkpoint,
    [Parameter(ParameterSetName = 'Restore')]
    [string] $Remote = 'upstream',
    [Parameter(Mandatory, ParameterSetName = 'List')]
    [switch] $List
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..' '_Common.ps1')
. (Join-Path $PSScriptRoot '..' '_Checkpoints.ps1')

$root = Get-RepoRoot
$manifest = Get-LabCheckpointManifest -Root $root

if ($List) {
    foreach ($c in $manifest.checkpoints) {
        $alias = $c.aliases ? " (also $($c.aliases -join ', '))" : ''
        Write-Host ('{0,-16} {1}{2}' -f $c.name, $c.description, $alias)
    }
    exit 0
}

$entry = $manifest.checkpoints | Where-Object name -EQ $Checkpoint
$tag = $entry.tag

# 1. Clean tree
$dirty = Invoke-Git -Root $root -Arguments @('status', '--porcelain', '--untracked-files=no')
if ($dirty) {
    Write-Host 'You have uncommitted changes. Commit or stash them, then run this again:' -ForegroundColor Red
    $dirty | ForEach-Object { Write-Host "  $_" }
    exit 1
}

# 2. Fetch the tag
$remotes = Invoke-Git -Root $root -Arguments @('remote')
if ($remotes -notcontains $Remote) {
    Write-Host "There's no '$Remote' remote. Add it with:" -ForegroundColor Red
    Write-Host "  git remote add $Remote $($manifest.upstream)"
    exit 1
}
Write-Host "Fetching $tag from $Remote"
Invoke-Git -Root $root -Arguments @('fetch', '--no-tags', $Remote, "+refs/tags/${tag}:refs/tags/$tag") | Out-Null

# 3. New branch
$branch = "lab/$Checkpoint-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Invoke-Git -Root $root -Arguments @('switch', '-c', $branch) | Out-Null
Write-Host "Created branch $branch"

# 4. Restore paths from the tag
foreach ($path in $manifest.restore_paths) {
    $inTag = Invoke-Git -Root $root -Arguments @('ls-tree', '--name-only', $tag, '--', $path)
    $tracked = Invoke-Git -Root $root -Arguments @('ls-files', '--', $path)
    if ($inTag) {
        Invoke-Git -Root $root -Arguments @('restore', "--source=$tag", '--staged', '--worktree', '--', $path) | Out-Null
    } elseif ($tracked) {
        Invoke-Git -Root $root -Arguments @('rm', '-r', '-q', '--', $path) | Out-Null
    }
}

# 5. Local outputs
$created = Initialize-CheckpointOutput -Root $root -Checkpoint $entry

Write-Section "Restored $Checkpoint"
$changes = Invoke-Git -Root $root -Arguments @('diff', '--cached', '--stat')
if ($changes) { $changes | ForEach-Object { Write-Host $_ } } else { Write-Host 'No model changes; you were already at this checkpoint.' }
foreach ($file in $created) { Write-Host "Created $([IO.Path]::GetRelativePath($root, $file))" }
Write-Host ''
Write-Host 'Next:'
Write-Host "  git commit -m `"Restore checkpoint $Checkpoint`""
Write-Host '  Close and reopen fabric/ContosoPharmacy.pbip in Power BI Desktop, then Refresh.'
if ($entry.verify) {
    Write-Host "  pwsh ./scripts/lab/Test-LabProgress.ps1 -Lab $($entry.verify[-1])"
}
exit 0

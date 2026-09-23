#Requires -Version 7.2
<#
.SYNOPSIS
    Checkpoint helpers shared by the lab and maintainer scripts. Dot-source after _Common.ps1.
#>

Set-StrictMode -Version 3.0

function Get-LabCheckpointManifest {
    [CmdletBinding()]
    param([string] $Root = (Get-RepoRoot))
    $path = Join-Path $Root 'lab' 'checkpoints.json'
    return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}

function Invoke-Git {
    <#
    Runs git -C $Root with an explicit argument array, throws on failure unless -AllowFailure, and
    returns output lines. Pass arguments as an array so '--' and short flags reach git unchanged.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $Root,
        [Parameter(Mandatory)] [string[]] $Arguments,
        [switch] $AllowFailure
    )
    $output = & git -C $Root @Arguments 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0 -and -not $AllowFailure) {
        throw "git $($Arguments -join ' ') failed ($code): $($output | Out-String)"
    }
    return @($output | ForEach-Object { "$_" })
}

function Initialize-CheckpointOutput {
    <#
    Creates the gitignored files a checkpoint implies: evaluation/runs/local-baseline.json (from the
    committed sample) and out/assessment.md (from lab/samples/assessment.md). Existing files are kept.
    Returns the list of files it created.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string] $Root,
        [Parameter(Mandatory)] $Checkpoint
    )
    $created = @()
    if ($Checkpoint.seed_baseline_run) {
        $target = Join-Path $Root 'evaluation' 'runs' 'local-baseline.json'
        $sample = Join-Path $Root 'evaluation' 'runs' 'sample-baseline.json'
        if (-not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $sample)) {
            $run = Get-Content -LiteralPath $sample -Raw | ConvertFrom-Json -AsHashtable
            $run.label = 'local-baseline'
            $run.notes = "Restored from checkpoint $($Checkpoint.name) (copy of sample-baseline). $($run.notes)"
            $run | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $target -Encoding utf8NoBOM
            $created += $target
        }
    }
    if ($Checkpoint.seed_assessment) {
        $target = Join-Path $Root 'out' 'assessment.md'
        $sample = Join-Path $Root 'lab' 'samples' 'assessment.md'
        if (-not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $sample)) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $sample -Destination $target
            $created += $target
        }
    }
    return $created
}

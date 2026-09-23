#Requires -Version 7.2
<#
.SYNOPSIS
    Shared helpers for the scripts in this folder. Dot-source it; don't run it directly.
#>

Set-StrictMode -Version 3.0

function Get-RepoRoot {
    <# Returns the repository root by walking up from this file until tools/python/pyproject.toml is found. #>
    [CmdletBinding()]
    [OutputType([string])]
    param([string] $Start = $PSScriptRoot)

    $dir = Get-Item -LiteralPath $Start
    while ($null -ne $dir) {
        $marker = Join-Path $dir.FullName 'tools' 'python' 'pyproject.toml'
        if (Test-Path -LiteralPath $marker -PathType Leaf) {
            return $dir.FullName
        }
        $dir = $dir.Parent
    }
    throw "Couldn't find the repository root above '$Start'."
}

function Get-VenvPython {
    <# Returns the path to the repo's .venv Python, or $null when the venv doesn't exist yet. #>
    [CmdletBinding()]
    [OutputType([string])]
    param([string] $Root = (Get-RepoRoot))

    $candidates = if ($IsWindows) {
        @(Join-Path $Root '.venv' 'Scripts' 'python.exe')
    } else {
        @((Join-Path $Root '.venv' 'bin' 'python3'), (Join-Path $Root '.venv' 'bin' 'python'))
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    return $null
}

function Find-SystemPython {
    <#
    Finds a Python 3.12+ interpreter to create the venv with. Tries the Windows py launcher first,
    then python3 and python on PATH. Returns @{ Command; Arguments; Version } or $null.
    #>
    [CmdletBinding()]
    param([version] $Minimum = [version]'3.12')

    $attempts = @()
    if ($IsWindows) {
        $attempts += , @('py', @('-3'))
    }
    $attempts += , @('python3', @())
    $attempts += , @('python', @())

    foreach ($attempt in $attempts) {
        # Check every match on PATH: an old system python3 can shadow a newer one.
        foreach ($command in @(Get-Command $attempt[0] -CommandType Application -All -ErrorAction SilentlyContinue)) {
            # The Microsoft Store alias for python.exe opens the Store instead of running Python.
            if ($command.Source -like '*\WindowsApps\python*.exe') { continue }
            $pyArgs = [string[]] $attempt[1]
            $text = & $command.Source @pyArgs -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>$null
            if ($LASTEXITCODE -ne 0 -or -not $text) { continue }
            $version = [version] ($text | Select-Object -First 1).Trim()
            if ($version -ge $Minimum) {
                return @{ Command = $command.Source; Arguments = $pyArgs; Version = $version }
            }
        }
    }
    return $null
}

function Invoke-PharmacyDemo {
    <#
    Runs `python -m pharmacy_demo <args>` with the repo venv and returns its exit code.
    Output goes straight to the console.
    #>
    [CmdletBinding()]
    [OutputType([int])]
    param(
        [Parameter(ValueFromRemainingArguments)]
        [string[]] $Arguments
    )

    $root = Get-RepoRoot
    $python = Get-VenvPython -Root $root
    if (-not $python) {
        Write-Host "The Python environment isn't set up yet. Run: pwsh ./scripts/Initialize-DevEnvironment.ps1" -ForegroundColor Yellow
        return 2
    }
    & $python -m pharmacy_demo --root $root @Arguments | Out-Host
    return $LASTEXITCODE
}

function Write-Section {
    [CmdletBinding()]
    param([Parameter(Mandatory)] [string] $Title)
    Write-Host ''
    Write-Host "== $Title" -ForegroundColor Cyan
}

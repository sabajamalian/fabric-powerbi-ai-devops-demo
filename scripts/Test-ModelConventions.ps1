#Requires -Version 7.2
<#
.SYNOPSIS
    Lists where the semantic model breaks the team conventions in rules/*.yaml.
.DESCRIPTION
    Rules C01 to C15 cover names, descriptions, hidden keys, summarization, relationships, the date
    table, measures, display folders, and AI metadata flags. The baseline model breaks most of them
    on purpose. This is the deterministic check behind the model-assessor agent and Labs 07 to 09.
    By default it reports findings and exits 0; use -Strict to exit 1 when there are findings.
.PARAMETER Rule
    Only report these rule IDs, comma-separated, for example C01,C02.
.PARAMETER Json
    Print findings as JSON.
.PARAMETER Markdown
    Print findings as a Markdown table (Rule, Severity, Object, Finding, Fix).
.PARAMETER OutFile
    Also write the Markdown table to this file.
.PARAMETER Strict
    Exit 1 when there are findings.
.EXAMPLE
    pwsh ./scripts/Test-ModelConventions.ps1 -Rule C01
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [string[]] $Rule,
    [switch] $Json,
    [switch] $Markdown,
    [string] $OutFile,
    [switch] $Strict
)

. (Join-Path $PSScriptRoot '_Common.ps1')

$Rule = @($Rule | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim().ToUpperInvariant() } | Where-Object { $_ })
$bad = @($Rule | Where-Object { $_ -notmatch '^C\d{2}$' })
if ($bad) {
    Write-Error "Rule IDs look like C01. Got: $($bad -join ', ')."
    exit 2
}

$arguments = @('conventions')
if ($Rule) { $arguments += '--rule'; $arguments += $Rule }
if ($Strict) { $arguments += '--strict' }
if ($OutFile) {
    $root = Get-RepoRoot
    $python = Get-VenvPython -Root $root
    if (-not $python) { exit (Invoke-PharmacyDemo @arguments) }
    $text = & $python -m pharmacy_demo --root $root @arguments --markdown
    $code = $LASTEXITCODE
    $target = [System.IO.Path]::GetFullPath($OutFile, (Get-Location).Path)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Set-Content -LiteralPath $target -Value $text -Encoding utf8NoBOM
    $text | Out-Host
    Write-Host "wrote $target"
    exit $code
}
if ($Json) { $arguments += '--json' }
elseif ($Markdown) { $arguments += '--markdown' }
exit (Invoke-PharmacyDemo @arguments)

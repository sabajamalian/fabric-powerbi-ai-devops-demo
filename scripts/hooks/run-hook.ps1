#Requires -Version 7.2
<#
.SYNOPSIS
    Copilot hook entry point on Windows. Forwards the hook payload to python -m pharmacy_demo hook.
.DESCRIPTION
    Referenced by .github/hooks/guardrails.json. Reads the JSON payload from stdin and passes it to
    the Python handler, which prints a decision (deny or ask) or nothing. If the repo's .venv doesn't
    exist yet, the hook does nothing and lets the tool call through, so a fresh clone still works
    before scripts/Initialize-DevEnvironment.ps1 has run.
.PARAMETER HookEvent
    session-start, pre-tool-use, post-tool-use, or session-end.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('session-start', 'pre-tool-use', 'post-tool-use', 'session-end')]
    [string] $HookEvent
)

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..' '..')).Path
$python = $IsWindows ? (Join-Path $root '.venv' 'Scripts' 'python.exe') : (Join-Path $root '.venv' 'bin' 'python')
if (-not (Test-Path -LiteralPath $python)) {
    [Console]::Error.WriteLine('Lab hooks inactive: run scripts/Initialize-DevEnvironment.ps1 to create .venv.')
    exit 0
}
$payload = [Console]::In.ReadToEnd()
$payload | & $python -m pharmacy_demo --root $root hook $HookEvent
exit 0

#Requires -Version 7.2
<#
.SYNOPSIS
    Checks that the tools the labs need are installed. Installs nothing.
.DESCRIPTION
    Reports each tool as PASS, FAIL, WARN (optional or old), or SKIP (not applicable on this OS),
    with the install command to run yourself. Exits 1 when a required tool is missing.

    Required everywhere: PowerShell 7.4+, Git 2.40+, Python 3.12+, VS Code.
    Required on Windows: Power BI Desktop, Git core.longpaths.
    Optional: Node.js 20+ (lab site and Power BI Modeling MCP via npx), GitHub CLI, Copilot CLI.
.PARAMETER Json
    Print results as JSON.
.EXAMPLE
    pwsh ./scripts/Test-Prerequisites.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param([switch] $Json)

. (Join-Path $PSScriptRoot '_Common.ps1')

$results = [System.Collections.Generic.List[object]]::new()

function Add-Result {
    param([string] $Name, [string] $Status, [string] $Detail, [string] $Fix = '')
    $results.Add([pscustomobject]@{ Tool = $Name; Status = $Status; Detail = $Detail; Fix = $Fix })
}

function Get-ToolVersion {
    param([string] $Command, [string[]] $Arguments, [string] $Pattern = '(\d+\.\d+(\.\d+)?)')
    $tool = Get-Command $Command -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $tool) { return $null }
    try {
        $text = (& $tool.Source @Arguments 2>&1 | Out-String)
    } catch {
        return $null
    }
    if ($text -match $Pattern) { return [version] $Matches[1] }
    return [version] '0.0'
}

# PowerShell
$ps = $PSVersionTable.PSVersion
if ($ps -ge [version]'7.4') { Add-Result 'PowerShell' 'PASS' "$ps" }
else { Add-Result 'PowerShell' 'FAIL' "$ps" 'winget install Microsoft.PowerShell' }

# Git
$git = Get-ToolVersion git @('--version')
if (-not $git) { Add-Result 'Git' 'FAIL' 'not found' 'winget install Git.Git' }
elseif ($git -lt [version]'2.40') { Add-Result 'Git' 'WARN' "$git (2.40+ recommended)" 'winget upgrade Git.Git' }
else { Add-Result 'Git' 'PASS' "$git" }

if ($IsWindows) {
    $longPaths = if ($git) { (& git config --get core.longpaths 2>$null) } else { $null }
    if ($longPaths -eq 'true') { Add-Result 'Git core.longpaths' 'PASS' 'true' }
    else { Add-Result 'Git core.longpaths' 'FAIL' 'not set' 'git config --global core.longpaths true' }
} else {
    Add-Result 'Git core.longpaths' 'SKIP' 'Windows only'
}

# Python
$python = Find-SystemPython
if ($python) { Add-Result 'Python' 'PASS' "$($python.Version) ($($python.Command))" }
else {
    $fix = $IsWindows ? 'winget install Python.Python.3.12' : 'Install Python 3.12+ from python.org or your package manager'
    Add-Result 'Python' 'FAIL' '3.12+ not found' $fix
}

# VS Code
$code = Get-Command code -ErrorAction SilentlyContinue | Select-Object -First 1
if ($code) { Add-Result 'VS Code' 'PASS' $code.Source }
else { Add-Result 'VS Code' 'FAIL' "'code' not on PATH" 'winget install Microsoft.VisualStudioCode (enable Add to PATH)' }

if ($code) {
    $extensions = @(& $code.Source --list-extensions 2>$null)
    foreach ($ext in @(
            @{ Id = 'github.copilot-chat'; Name = 'Copilot Chat extension'; Required = $false },
            @{ Id = 'analysis-services.tmdl'; Name = 'TMDL extension'; Required = $false },
            @{ Id = 'analysis-services.powerbi-modeling-mcp'; Name = 'Power BI Modeling MCP extension'; Required = $false }
        )) {
        if ($extensions -contains $ext.Id) { Add-Result $ext.Name 'PASS' $ext.Id }
        else {
            $status = $ext.Required ? 'FAIL' : 'WARN'
            $detail = $ext.Id -eq 'github.copilot-chat' ?
                'not listed (recent VS Code builds include Copilot Chat; check that the Chat view opens)' : 'not installed'
            Add-Result $ext.Name $status $detail "code --install-extension $($ext.Id)"
        }
    }
}

# Power BI Desktop (Windows only)
if ($IsWindows) {
    $desktop = @(
        (Join-Path ${env:ProgramFiles} 'Microsoft Power BI Desktop' 'bin' 'PBIDesktop.exe'),
        (Join-Path $env:LOCALAPPDATA 'Microsoft' 'WindowsApps' 'PBIDesktopStore.exe')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
    if ($desktop) { Add-Result 'Power BI Desktop' 'PASS' $desktop }
    else { Add-Result 'Power BI Desktop' 'FAIL' 'not found' 'winget install Microsoft.PowerBI (or install from the Microsoft Store)' }
} else {
    Add-Result 'Power BI Desktop' 'SKIP' 'Windows only. You can still do the Copilot labs on this machine.'
}

# Node.js (optional)
$node = Get-ToolVersion node @('--version')
if (-not $node) { Add-Result 'Node.js' 'WARN' 'not found (needed for the local lab site and npx MCP servers)' 'winget install OpenJS.NodeJS.LTS' }
elseif ($node.Major -lt 20) { Add-Result 'Node.js' 'WARN' "$node (20+ needed)" 'winget upgrade OpenJS.NodeJS.LTS' }
else { Add-Result 'Node.js' 'PASS' "$node" }

# GitHub CLI (optional)
$gh = Get-ToolVersion gh @('--version')
if ($gh) { Add-Result 'GitHub CLI' 'PASS' "$gh" }
else { Add-Result 'GitHub CLI' 'WARN' 'not found (used in Labs 12 and 13)' 'winget install GitHub.cli' }

# Copilot CLI (optional)
$copilot = Get-Command copilot -ErrorAction SilentlyContinue | Select-Object -First 1
if ($copilot) { Add-Result 'Copilot CLI' 'PASS' $copilot.Source }
else { Add-Result 'Copilot CLI' 'WARN' 'not found (used in Lab 11)' 'npm install -g @github/copilot' }

if ($Json) {
    $results | ConvertTo-Json -Depth 3
} else {
    $colors = @{ PASS = 'Green'; FAIL = 'Red'; WARN = 'Yellow'; SKIP = 'DarkGray' }
    foreach ($r in $results) {
        Write-Host ('{0,-5} ' -f $r.Status) -ForegroundColor $colors[$r.Status] -NoNewline
        Write-Host ('{0,-32} {1}' -f $r.Tool, $r.Detail)
        if ($r.Fix -and $r.Status -in 'FAIL', 'WARN') { Write-Host "      Fix: $($r.Fix)" -ForegroundColor DarkGray }
    }
    $failed = @($results | Where-Object Status -EQ 'FAIL').Count
    Write-Host ''
    Write-Host ($failed ? "$failed required tool(s) missing. Nothing was installed." : 'All required tools found.')
}
exit (@($results | Where-Object Status -EQ 'FAIL').Count -gt 0 ? 1 : 0)

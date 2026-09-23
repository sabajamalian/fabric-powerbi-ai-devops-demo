#Requires -Version 7.2
<#
.SYNOPSIS
    Runs the reference DAX for each business question against the model open in Power BI Desktop
    and checks the results against the expected answers (Windows only).
.DESCRIPTION
    1. Finds the local Analysis Services instance that Power BI Desktop starts for an open model.
    2. Loads ADOMD.NET from .tools/adomd/. With -AllowDownload it downloads the pinned
       Microsoft.AnalysisServices.AdomdClient package from nuget.org first and checks its SHA-512.
    3. Runs each question's reference DAX and grades the rows with the same grader the question
       runs use.
    4. Writes out/dax-tests.json with PASS or FAIL per question. The DAX itself isn't printed.

    The reference DAX uses the business names from Lab 08, so run this after Lab 08 with
    fabric/ContosoPharmacy.pbip open and refreshed.
.PARAMETER Port
    The Desktop Analysis Services port. Default: found from msmdsrv.port.txt (newest instance).
.PARAMETER AllowDownload
    Download ADOMD.NET from nuget.org into .tools/adomd/ if it isn't there yet.
.PARAMETER OutFile
    Where to write results. Default: out/dax-tests.json.
.EXAMPLE
    pwsh ./scripts/Invoke-DaxQuestionTests.ps1 -AllowDownload
#>
[CmdletBinding(PositionalBinding = $false)]
param(
    [int] $Port,
    [switch] $AllowDownload,
    [string] $OutFile
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_Common.ps1')

$AdomdVersion = '19.117.0'
$AdomdSha512 = '85D568E72F5B09A36A0F88497801BAFB1D1E9DF5DA1190ABCF7636C264F78D6BA3978B28A78D2640B338AF0BDD6941A31447E7D33D7E0D9004BA64C96C7F3562'

if (-not $IsWindows) {
    Write-Host 'Skipped: the DAX tests need Power BI Desktop, which runs on Windows only.' -ForegroundColor Yellow
    exit 0
}

$root = Get-RepoRoot
$python = Get-VenvPython -Root $root
if (-not $python) {
    Write-Host 'Run scripts/Initialize-DevEnvironment.ps1 first.' -ForegroundColor Red
    exit 2
}
if (-not $OutFile) { $OutFile = Join-Path $root 'out' 'dax-tests.json' }
$OutFile = [IO.Path]::GetFullPath($OutFile, (Get-Location).Path)

# --- ADOMD.NET ---------------------------------------------------------------------------------
$adomdDir = Join-Path $root '.tools' 'adomd' $AdomdVersion
$libDir = Join-Path $adomdDir 'lib' 'net8.0'
$clientDll = Join-Path $libDir 'Microsoft.AnalysisServices.AdomdClient.dll'
if (-not (Test-Path -LiteralPath $clientDll)) {
    if (-not $AllowDownload) {
        Write-Host "ADOMD.NET $AdomdVersion isn't in .tools/adomd/. Run again with -AllowDownload to fetch it from nuget.org." -ForegroundColor Yellow
        exit 2
    }
    $package = Join-Path $root '.tools' "adomd-$AdomdVersion.nupkg"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $package) | Out-Null
    $url = "https://www.nuget.org/api/v2/package/Microsoft.AnalysisServices.AdomdClient/$AdomdVersion"
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $package -UseBasicParsing
    $hash = (Get-FileHash -LiteralPath $package -Algorithm SHA512).Hash
    if ($hash -ne $AdomdSha512) {
        Remove-Item -LiteralPath $package
        throw "The downloaded package hash doesn't match the pinned SHA-512. Nothing was installed."
    }
    Expand-Archive -LiteralPath $package -DestinationPath $adomdDir -Force
    Remove-Item -LiteralPath $package
}
foreach ($name in 'Microsoft.AnalysisServices.Runtime.Core.dll', 'Microsoft.AnalysisServices.Runtime.Windows.dll', 'Microsoft.AnalysisServices.AdomdClient.dll') {
    Add-Type -LiteralPath (Join-Path $libDir $name)
}

# --- Find the Desktop instance ------------------------------------------------------------------
if (-not $Port) {
    $workspaceRoots = @(
        (Join-Path $env:LOCALAPPDATA 'Microsoft' 'Power BI Desktop' 'AnalysisServicesWorkspaces'),
        (Join-Path $env:USERPROFILE 'Microsoft' 'Power BI Desktop Store App' 'AnalysisServicesWorkspaces')
    ) | Where-Object { Test-Path -LiteralPath $_ }
    $portFile = $workspaceRoots |
        ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory } |
        ForEach-Object { Join-Path $_.FullName 'Data' 'msmdsrv.port.txt' } |
        Where-Object { Test-Path -LiteralPath $_ } |
        ForEach-Object { Get-Item -LiteralPath $_ } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $portFile) {
        Write-Host 'No running Power BI Desktop model found. Open fabric\ContosoPharmacy.pbip, select Refresh, and try again.' -ForegroundColor Red
        exit 1
    }
    # The port file is UTF-16; keeping only digits works whatever the encoding.
    $Port = [int] ((Get-Content -LiteralPath $portFile.FullName -Raw) -replace '\D', '')
}
Write-Host "Connecting to localhost:$Port"

# --- Run the queries ----------------------------------------------------------------------------
$queries = (& $python -m pharmacy_demo --root $root dax-queries) | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Could not read the reference DAX.' }

$connection = [Microsoft.AnalysisServices.AdomdClient.AdomdConnection]::new("Data Source=localhost:$Port")
$connection.Open()
$raw = [System.Collections.Generic.List[object]]::new()
try {
    foreach ($query in $queries) {
        $entry = [ordered]@{ question_id = $query.id; columns = @(); rows = @() }
        try {
            $command = $connection.CreateCommand()
            $command.CommandText = $query.dax
            $reader = $command.ExecuteReader()
            try {
                $entry.columns = @(0..($reader.FieldCount - 1) | ForEach-Object { $reader.GetName($_) })
                $rows = [System.Collections.Generic.List[object]]::new()
                while ($reader.Read()) {
                    $row = foreach ($i in 0..($reader.FieldCount - 1)) {
                        $value = $reader.GetValue($i)
                        if ($value -is [DBNull]) { $null }
                        elseif ($value -is [datetime]) { $value.ToString('yyyy-MM-dd') }
                        else { $value }
                    }
                    $rows.Add(@($row))
                }
                $entry.rows = $rows.ToArray()
            } finally {
                $reader.Dispose()
            }
        } catch {
            $entry.error = $_.Exception.Message
        }
        $raw.Add([pscustomobject]$entry)
    }
} finally {
    $connection.Dispose()
}

$rawFile = Join-Path (Split-Path -Parent $OutFile) 'dax-raw.json'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null
@{ questions = $raw.ToArray() } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $rawFile -Encoding utf8NoBOM
& $python -m pharmacy_demo --root $root daxcheck --input $rawFile --out $OutFile | Out-Host
exit $LASTEXITCODE

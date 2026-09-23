#Requires -Version 7.2
<#
.SYNOPSIS
    Points C:\ContosoPharmacyDemo\data at this clone's data\generated folder (Windows only).
.DESCRIPTION
    The semantic model reads the CSV files from the DataFolderPath parameter, which defaults to
    C:\ContosoPharmacyDemo\data\. This script creates that path as a directory junction to
    data\generated in your clone, so the model works wherever you cloned the repo, including paths
    with spaces. Junctions don't need administrator rights or Developer Mode.

    If the path already exists as a junction it's replaced. If it's a real folder with files in it,
    the script stops and changes nothing.
.PARAMETER Path
    Where to create the link. Default: C:\ContosoPharmacyDemo\data. If you change it, also change
    DataFolderPath in Power BI Desktop (Transform data > Edit parameters).
.PARAMETER Remove
    Remove the junction (and the parent folder if it's empty). Your data isn't touched.
.EXAMPLE
    pwsh ./scripts/Set-LocalDataLink.ps1
.EXAMPLE
    pwsh ./scripts/Set-LocalDataLink.ps1 -Remove
#>
[CmdletBinding(PositionalBinding = $false, SupportsShouldProcess)]
param(
    [string] $Path = 'C:\ContosoPharmacyDemo\data',
    [switch] $Remove
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_Common.ps1')

if (-not $IsWindows) {
    Write-Host 'Set-LocalDataLink.ps1 is for Windows, where Power BI Desktop runs. Nothing to do on this OS.' -ForegroundColor Yellow
    exit 0
}

$target = Join-Path (Get-RepoRoot) 'data' 'generated'
$item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
$isLink = $item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)

if ($Remove) {
    if (-not $item) { Write-Host "$Path doesn't exist. Nothing to remove."; exit 0 }
    if (-not $isLink) { Write-Host "$Path is a real folder, not a link. Leaving it alone." -ForegroundColor Yellow; exit 1 }
    if ($PSCmdlet.ShouldProcess($Path, 'Remove junction')) {
        # Deleting the junction itself never touches the files it points at.
        [IO.Directory]::Delete($Path)
        $parent = Split-Path -Parent $Path
        if ((Test-Path -LiteralPath $parent) -and -not (Get-ChildItem -LiteralPath $parent -Force)) {
            Remove-Item -LiteralPath $parent
        }
        Write-Host "Removed $Path"
    }
    exit 0
}

if ($item -and -not $isLink) {
    if (Get-ChildItem -LiteralPath $Path -Force) {
        Write-Host "$Path is a real folder with files in it. Move them, then run this again." -ForegroundColor Red
        exit 1
    }
    Remove-Item -LiteralPath $Path
} elseif ($isLink) {
    $current = @($item.Target)[0]
    if ($current -and ([IO.Path]::GetFullPath($current).TrimEnd('\') -ieq [IO.Path]::GetFullPath($target).TrimEnd('\'))) {
        Write-Host "$Path already points at $target"
        exit 0
    }
    if ($PSCmdlet.ShouldProcess($Path, "Replace junction to $current")) { [IO.Directory]::Delete($Path) }
}

if ($PSCmdlet.ShouldProcess($Path, "Create junction to $target")) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    New-Item -ItemType Junction -Path $Path -Target $target | Out-Null
    Write-Host "Linked $Path -> $target" -ForegroundColor Green
    Write-Host 'Open fabric\ContosoPharmacy.pbip in Power BI Desktop and select Refresh.'
}
exit 0

#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.5.0' }

# Variables set in BeforeDiscovery are consumed by -ForEach and -Skip, which the analyzer can't see.
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseDeclaredVarsMoreThanAssignments', '')]
param()

# These run each script in a child pwsh, the same way a learner does, because the scripts write
# straight to the host and call exit.

BeforeDiscovery {
    . (Join-Path $PSScriptRoot '..' '_Common.ps1')
    $root = Get-RepoRoot
    $scriptFiles = Get-ChildItem -LiteralPath (Join-Path $root 'scripts') -Recurse -Filter '*.ps1' |
        Where-Object { $_.FullName -notmatch '[\\/]tests[\\/]' -and $_.Name -notlike '_*' } |
        ForEach-Object { [System.IO.Path]::GetRelativePath($root, $_.FullName) }
    $hasVenv = [bool] (Get-VenvPython -Root $root)
}

BeforeAll {
    . (Join-Path $PSScriptRoot '..' '_Common.ps1')
    $script:RepoRoot = Get-RepoRoot
    $script:Pwsh = (Get-Process -Id $PID).Path

    function Invoke-Script {
        param([string] $Path, [string[]] $Arguments = @(), [string] $WorkingDirectory = $RepoRoot)
        Push-Location -LiteralPath $WorkingDirectory
        try {
            $output = & $Pwsh -NoProfile -NonInteractive -File $Path @Arguments 2>&1 | Out-String
            return [pscustomobject]@{ Code = $LASTEXITCODE; Output = $output }
        } finally {
            Pop-Location
        }
    }
}

Describe 'Every script' {
    It '<_> has comment-based help and disables positional binding' -ForEach $scriptFiles {
        $text = Get-Content -LiteralPath (Join-Path $RepoRoot $_) -Raw
        $text | Should -Match '\.SYNOPSIS'
        $text | Should -Match 'PositionalBinding\s*=\s*\$false'
    }

    It 'uses no Unix-only paths' {
        $hits = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot '..') -Recurse -Filter '*.ps1' |
            Where-Object { $_.FullName -notmatch '[\\/]tests[\\/]' } |
            Select-String -Pattern '(?<![\w.])/(usr|bin|opt|tmp)/|homebrew' -CaseSensitive:$false
        $hits | Should -BeNullOrEmpty
    }
}

Describe 'Test-Prerequisites.ps1' {
    It 'emits JSON with a status for every check' {
        $r = Invoke-Script -Path (Join-Path $RepoRoot 'scripts' 'Test-Prerequisites.ps1') -Arguments @('-Json')
        $checks = @($r.Output.Substring($r.Output.IndexOf('[')) | ConvertFrom-Json)
        $checks.Count | Should -BeGreaterThan 5
        $checks.Status | ForEach-Object { $_ | Should -BeIn @('PASS', 'WARN', 'FAIL', 'SKIP') }
    }
}

Describe 'Test-ModelConventions.ps1' {
    It 'rejects an unknown rule id' {
        $r = Invoke-Script -Path (Join-Path $RepoRoot 'scripts' 'Test-ModelConventions.ps1') -Arguments @('-Rule', 'C07,Z99')
        $r.Code | Should -Not -Be 0
        $r.Output | Should -Match 'Z99'
    }

    It 'accepts a comma list of rules' -Skip:(-not $hasVenv) {
        $r = Invoke-Script -Path (Join-Path $RepoRoot 'scripts' 'Test-ModelConventions.ps1') -Arguments @('-Rule', 'c07,C08', '-Json')
        $r.Output | Should -Match 'C07'
        $r.Output | Should -Match 'C08'
    }
}

Describe 'Invoke-Validation.ps1' {
    It 'rejects an unknown step' {
        $r = Invoke-Script -Path (Join-Path $RepoRoot 'scripts' 'Invoke-Validation.ps1') -Arguments @('-Only', 'nope')
        $r.Code | Should -Not -Be 0
    }
}

Describe 'Restore-LabCheckpoint.ps1' {
    BeforeAll {
        $script:Scratch = Join-Path ([System.IO.Path]::GetTempPath()) "cpdemo restore $([guid]::NewGuid())"
        New-Item -ItemType Directory -Path $Scratch | Out-Null
        foreach ($dir in 'scripts', 'lab', 'tools') {
            Copy-Item -LiteralPath (Join-Path $RepoRoot $dir) -Destination $Scratch -Recurse
        }
        Remove-Item -LiteralPath (Join-Path $Scratch 'tools' 'python' '.venv') -Recurse -Force -ErrorAction SilentlyContinue
        & git -C $Scratch init -q -b main
        & git -C $Scratch -c user.name=t -c user.email=t@example.com add -A
        & git -C $Scratch -c user.name=t -c user.email=t@example.com commit -q -m init
    }
    AfterAll { Remove-Item -LiteralPath $Scratch -Recurse -Force -ErrorAction SilentlyContinue }

    It 'lists checkpoints' {
        $r = Invoke-Script -Path (Join-Path $Scratch 'scripts' 'lab' 'Restore-LabCheckpoint.ps1') -Arguments @('-List') -WorkingDirectory $Scratch
        $r.Code | Should -Be 0
        $r.Output | Should -Match 'lab07-complete'
    }

    It 'refuses to run with uncommitted changes' {
        Add-Content -LiteralPath (Join-Path $Scratch 'lab' 'checkpoints.json') -Value ' '
        try {
            $r = Invoke-Script -Path (Join-Path $Scratch 'scripts' 'lab' 'Restore-LabCheckpoint.ps1') -Arguments @('-Checkpoint', 'lab07-complete') -WorkingDirectory $Scratch
            $r.Code | Should -Not -Be 0
            $r.Output | Should -Match 'uncommitted changes'
        } finally {
            & git -C $Scratch checkout -q -- lab/checkpoints.json
        }
    }

    It 'rejects an unknown checkpoint' {
        $r = Invoke-Script -Path (Join-Path $Scratch 'scripts' 'lab' 'Restore-LabCheckpoint.ps1') -Arguments @('-Checkpoint', 'lab99') -WorkingDirectory $Scratch
        $r.Code | Should -Not -Be 0
    }
}

#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.5.0' }

BeforeAll {
    . (Join-Path $PSScriptRoot '..' '_Common.ps1')
    . (Join-Path $PSScriptRoot '..' '_Checkpoints.ps1')
    $script:RepoRoot = Get-RepoRoot
}

Describe 'Get-RepoRoot' {
    It 'finds the folder that holds tools/python/pyproject.toml' {
        Test-Path -LiteralPath (Join-Path $RepoRoot 'tools' 'python' 'pyproject.toml') | Should -BeTrue
    }

    It 'walks up from a nested folder' {
        Get-RepoRoot -Start (Join-Path $RepoRoot 'scripts' 'lab') | Should -Be $RepoRoot
    }

    It 'throws outside a repo' {
        { Get-RepoRoot -Start ([System.IO.Path]::GetTempPath()) } | Should -Throw
    }
}

Describe 'Get-VenvPython' {
    It 'returns null when there is no venv' {
        $empty = Join-Path ([System.IO.Path]::GetTempPath()) "cpdemo-empty-$([guid]::NewGuid())"
        New-Item -ItemType Directory -Path $empty | Out-Null
        try {
            Get-VenvPython -Root $empty | Should -BeNullOrEmpty
        } finally {
            Remove-Item -LiteralPath $empty -Recurse -Force
        }
    }
}

Describe 'Get-LabCheckpointManifest' {
    It 'lists the six checkpoints in order' {
        $names = @((Get-LabCheckpointManifest -Root $RepoRoot).checkpoints.name)
        $names | Should -Be @('lab02-start', 'lab05-complete', 'lab06-complete', 'lab07-complete', 'lab08-complete', 'lab09-complete')
    }

    It 'restores only fabric and lab/samples' {
        (Get-LabCheckpointManifest -Root $RepoRoot).restore_paths | Should -Be @('fabric', 'lab/samples')
    }
}

Describe 'Initialize-CheckpointOutput' {
    BeforeEach {
        $script:Tmp = Join-Path ([System.IO.Path]::GetTempPath()) "cpdemo seed $([guid]::NewGuid())"
        New-Item -ItemType Directory -Force -Path (Join-Path $Tmp 'evaluation' 'runs'), (Join-Path $Tmp 'lab' 'samples') | Out-Null
        '{"label":"sample-baseline","notes":"n","answers":[]}' | Set-Content -LiteralPath (Join-Path $Tmp 'evaluation' 'runs' 'sample-baseline.json')
        '# Assessment' | Set-Content -LiteralPath (Join-Path $Tmp 'lab' 'samples' 'assessment.md')
    }
    AfterEach { Remove-Item -LiteralPath $Tmp -Recurse -Force }

    It 'seeds the baseline run and the assessment, relabeling the run' {
        $cp = [pscustomobject]@{ name = 'lab07-complete'; seed_baseline_run = $true; seed_assessment = $true }
        $created = @(Initialize-CheckpointOutput -Root $Tmp -Checkpoint $cp)
        $created.Count | Should -Be 2
        $run = Get-Content -LiteralPath (Join-Path $Tmp 'evaluation' 'runs' 'local-baseline.json') -Raw | ConvertFrom-Json
        $run.label | Should -Be 'local-baseline'
        Test-Path -LiteralPath (Join-Path $Tmp 'out' 'assessment.md') | Should -BeTrue
    }

    It 'keeps files that already exist' {
        'mine' | Set-Content -LiteralPath (Join-Path $Tmp 'evaluation' 'runs' 'local-baseline.json')
        $cp = [pscustomobject]@{ name = 'lab05-complete'; seed_baseline_run = $true; seed_assessment = $false }
        @(Initialize-CheckpointOutput -Root $Tmp -Checkpoint $cp).Count | Should -Be 0
        (Get-Content -LiteralPath (Join-Path $Tmp 'evaluation' 'runs' 'local-baseline.json') -Raw).Trim() | Should -Be 'mine'
    }

    It 'seeds nothing for lab02-start' {
        $cp = [pscustomobject]@{ name = 'lab02-start'; seed_baseline_run = $false; seed_assessment = $false }
        @(Initialize-CheckpointOutput -Root $Tmp -Checkpoint $cp).Count | Should -Be 0
    }
}

Describe 'Invoke-Git' {
    It 'passes -- and short flags through unchanged' {
        $out = @(Invoke-Git -Root $RepoRoot -Arguments @('log', '-1', '--format=%H', '--', 'README.md'))
        $out[0] | Should -Match '^[0-9a-f]{40}$'
    }

    It 'throws on failure unless -AllowFailure' {
        { Invoke-Git -Root $RepoRoot -Arguments @('rev-parse', '--verify', 'refs/tags/does-not-exist-xyz') } | Should -Throw
        { Invoke-Git -Root $RepoRoot -Arguments @('rev-parse', '--verify', 'refs/tags/does-not-exist-xyz') -AllowFailure } | Should -Not -Throw
    }
}

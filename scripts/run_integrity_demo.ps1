param(
    [string]$CreatedUtc = "2026-03-06T10:00:00Z",
    [string]$CoreVersion = "0.4.0",
    [string]$RulesetId = "ruleset.core.v1",
    [int]$MaxChunks = 20,
    [int]$MaxEvents = 30
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $env:PYTHON_BIN
if (-not $Python) {
    $Python = "python"
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Output "==> $Label"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$Required = @(
    "scripts/demo.py",
    "scripts/extract_ledger_dir.py",
    "scripts/self_casefile_run_id.py",
    "scripts/clonable_integrity.ps1",
    "scripts/generate_manifest.py",
    "docs/casefiles/iota_verbum_self",
    "MANIFEST.sha256"
)

foreach ($Path in $Required) {
    if (-not (Test-Path $Path)) {
        Write-Error "Required path missing: $Path"
        exit 2
    }
}

$Query = "Build a deterministic self-casefile for IOTA VERBUM documentation evidence."
$Prompt = "Produce a verified world model and sealed casefile for this repository corpus."

# Step 1
Invoke-Step -Label "Step 1/7: Run unit tests" -Action {
    & $Python -m pytest -q
}

# Step 2
Invoke-Step -Label "Step 2/7: Verify deterministic manifest" -Action {
    & $Python scripts/generate_manifest.py --verify
}

# Step 3
Invoke-Step -Label "Step 3/7: Run clonable integrity check" -Action {
    & .\scripts\clonable_integrity.ps1 `
        -CreatedUtc $CreatedUtc `
        -CoreVersion $CoreVersion `
        -RulesetId $RulesetId `
        -MaxChunks $MaxChunks `
        -MaxEvents $MaxEvents
}

# Step 4
Invoke-Step -Label "Step 4/7: Generate self-casefile demo" -Action {
    $script:RunId = & $Python scripts/self_casefile_run_id.py `
        --folder docs/casefiles/iota_verbum_self `
        --query $Query `
        --prompt $Prompt `
        --max-chunks $MaxChunks `
        --created-utc $CreatedUtc `
        --core-version $CoreVersion `
        --ruleset-id $RulesetId `
        --world true
    if ($LASTEXITCODE -ne 0 -or -not $script:RunId) {
        throw "Unable to compute run_id for self-casefile demo."
    }
    $script:RunId = $script:RunId.Trim()

    $demoOutput = @()
    & $Python scripts/demo.py `
        --folder docs/casefiles/iota_verbum_self `
        --query $Query `
        --prompt $Prompt `
        --max-chunks $MaxChunks `
        --created-utc $CreatedUtc `
        --core-version $CoreVersion `
        --ruleset-id $RulesetId `
        --world true `
        --max-events $MaxEvents `
        2>&1 | Tee-Object -Variable demoOutput | Out-Null
    if ($LASTEXITCODE -ne 0) {
        if ($demoOutput.Count -gt 0) {
            $demoOutput | Write-Output
        }
        throw "Self-casefile demo execution failed."
    }

    $tmp = [System.IO.Path]::GetTempFileName()
    try {
        ($demoOutput -join [Environment]::NewLine) | Set-Content -Path $tmp -Encoding utf8
        $script:LedgerDir = & $Python scripts/extract_ledger_dir.py $tmp
        if ($LASTEXITCODE -ne 0 -or -not $script:LedgerDir) {
            throw "Unable to parse ledger_dir from demo output."
        }
        $script:LedgerDir = $script:LedgerDir.Trim()
    }
    finally {
        Remove-Item -Force $tmp -ErrorAction SilentlyContinue
    }
}

# Step 5
Invoke-Step -Label "Step 5/7: Run deterministic replay verification" -Action {
    & $Python -m core.determinism.replay $LedgerDir --strict-manifest
}

$CasefilePath = Join-Path (Join-Path (Join-Path "outputs" "demo") $RunId) "casefile.json"
if (-not (Test-Path $CasefilePath)) {
    throw "Expected casefile not found at $CasefilePath"
}

# Step 6
Invoke-Step -Label "Step 6/7: Inspect casefile" -Action {
    & $Python -m core.casefile.inspect $CasefilePath
}

$Casefile = Get-Content $CasefilePath -Raw | ConvertFrom-Json
$ReplayCommand = "python -m core.determinism.replay $LedgerDir --strict-manifest"

# Step 7
Write-Output ""
Write-Output "IOTA VERBUM INTEGRITY DEMO COMPLETE"
Write-Output ""
Write-Output "run_id: $RunId"
Write-Output "casefile_id: $($Casefile.casefile_id)"
Write-Output "bundle_sha256: $($Casefile.hashes.bundle_sha256)"
Write-Output "world_sha256: $($Casefile.hashes.world_sha256)"
Write-Output "output_sha256: $($Casefile.hashes.output_sha256)"
Write-Output "attestation_sha256: $($Casefile.hashes.attestation_sha256)"
Write-Output "ledger_dir: $LedgerDir"
Write-Output ""
Write-Output "Replay command:"
Write-Output $ReplayCommand

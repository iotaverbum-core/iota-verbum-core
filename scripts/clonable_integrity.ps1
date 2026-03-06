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

$Required = @(
    "scripts/demo.py",
    "scripts/extract_ledger_dir.py",
    "scripts/self_casefile_run_id.py",
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

$RunId = & $Python scripts/self_casefile_run_id.py `
    --folder docs/casefiles/iota_verbum_self `
    --query $Query `
    --prompt $Prompt `
    --max-chunks $MaxChunks `
    --created-utc $CreatedUtc `
    --core-version $CoreVersion `
    --ruleset-id $RulesetId `
    --world true
if ($LASTEXITCODE -ne 0 -or -not $RunId) {
    exit 2
}
$RunDir = Join-Path (Join-Path "outputs" "demo") $RunId.Trim()
if (Test-Path $RunDir) {
    Remove-Item -Recurse -Force $RunDir
}

$DemoOutput = @()
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
    2>&1 | Tee-Object -Variable DemoOutput | Out-Null
if ($LASTEXITCODE -ne 0) {
    if ($DemoOutput.Count -gt 0) {
        $DemoOutput | Write-Output
    }
    exit $LASTEXITCODE
}

$TempDemoOutput = [System.IO.Path]::GetTempFileName()
try {
    ($DemoOutput -join [Environment]::NewLine) | Set-Content -Path $TempDemoOutput -Encoding utf8
    $LedgerDir = & $Python scripts/extract_ledger_dir.py $TempDemoOutput
    if ($LASTEXITCODE -ne 0 -or -not $LedgerDir) {
        if ($DemoOutput.Count -gt 0) {
            $DemoOutput | Write-Output
        }
        exit 2
    }
}
finally {
    Remove-Item -Force $TempDemoOutput -ErrorAction SilentlyContinue
}

$ReplayOutput = @()
& $Python -W "ignore::RuntimeWarning" -m core.determinism.replay $LedgerDir --strict-manifest `
    2>&1 | Tee-Object -Variable ReplayOutput | Out-Null
if ($LASTEXITCODE -ne 0) {
    if ($ReplayOutput.Count -gt 0) {
        $ReplayOutput | Write-Output
    }
    exit $LASTEXITCODE
}

Write-Output "CLONABLE_INTEGRITY_OK"

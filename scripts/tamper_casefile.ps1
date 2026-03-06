param(
    [Parameter(Mandatory = $true)]
    [string]$LedgerDir
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $env:PYTHON_BIN
if (-not $Python) {
    $Python = "python"
}

if (-not (Test-Path $LedgerDir -PathType Container)) {
    Write-Error "Ledger directory not found: $LedgerDir"
    exit 2
}

$TamperedLedgerDir = & $Python scripts/create_tampered_ledger_copy.py $LedgerDir
if ($LASTEXITCODE -ne 0 -or -not $TamperedLedgerDir) {
    exit 2
}

$ReplayOutput = @()
& $Python -W "ignore::RuntimeWarning" -m core.determinism.replay $TamperedLedgerDir --strict-manifest `
    2>&1 | Tee-Object -Variable ReplayOutput | Out-Null
if ($LASTEXITCODE -eq 0) {
    if ($ReplayOutput.Count -gt 0) {
        $ReplayOutput | Write-Output
    }
    Write-Error "Tampered replay unexpectedly succeeded."
    exit 1
}

Write-Output "TAMPER_DETECTED_OK"

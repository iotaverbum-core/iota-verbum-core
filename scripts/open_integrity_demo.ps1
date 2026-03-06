$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ViewerPath = Join-Path $Root "docs\proof_trace_viewer.html"

Write-Output "IOTA VERBUM Integrity Trust Loop"
Write-Output "1) .\scripts\clonable_integrity.ps1"
Write-Output "2) python -m core.casefile.inspect <casefile.json>"
Write-Output "3) python -m core.determinism.replay <ledger_dir> --strict-manifest"
Write-Output "4) .\scripts\tamper_casefile.ps1 -LedgerDir <ledger_dir>"
Write-Output ""
Write-Output "Proof Trace Viewer (read-only): $ViewerPath"
Start-Process $ViewerPath

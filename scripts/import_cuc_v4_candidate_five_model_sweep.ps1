param(
    [string]$DownloadsRoot = (Join-Path $HOME "Downloads\cuc_v4_candidate_2026_04_08"),
    [string]$OutputDir = (Join-Path $PSScriptRoot "..\cuc-results"),
    [string]$DocDir = (Join-Path $PSScriptRoot "..\cuc-docs")
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

& $pythonExe `
    (Join-Path $PSScriptRoot "import_cuc_v4_candidate_five_model_sweep.py") `
    --downloads-root $DownloadsRoot `
    --output-dir $OutputDir `
    --doc-dir $DocDir

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

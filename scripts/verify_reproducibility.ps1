$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $env:PYTHON_BIN
if (-not $Python) { $Python = "python" }

$VenvDir = Join-Path $Root ".venv-repro"
if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
& $Python -m venv $VenvDir

$Activate = Join-Path $VenvDir "Scripts\Activate.ps1"
& $Activate

python -m pip install -U pip
python -m pip install -r requirements.lock
python -m pip install -e .

pytest
python scripts\determinism_check.py

python scripts\generate_manifest.py --verify
python scripts\generate_manifest.py
python scripts\generate_manifest.py --verify

param(
    [string]$CreatedUtc = "2026-03-06T10:00:00Z",
    [string]$CoreVersion = "0.4.0",
    [string]$RulesetId = "ruleset.core.v1",
    [int]$MaxChunks = 20,
    [int]$MaxEvents = 30
)

$ErrorActionPreference = "Stop"

$query = "Build a deterministic self-casefile for IOTA VERBUM documentation evidence."
$prompt = "Produce a verified world model and sealed casefile for this repository corpus."
$folder = "docs/casefiles/iota_verbum_self"

$demoOutput = @()
& python scripts/demo.py `
    --folder $folder `
    --query $query `
    --prompt $prompt `
    --max-chunks $MaxChunks `
    --created-utc $CreatedUtc `
    --core-version $CoreVersion `
    --ruleset-id $RulesetId `
    --world true `
    --max-events $MaxEvents `
    2>&1 | Tee-Object -Variable demoOutput

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$ledgerDir = $null

foreach ($line in $demoOutput) {
    if ($line -match '^ledger_dir:\s+(.+)$') {
        $ledgerDir = $Matches[1].Trim()
        break
    }
}

if (-not $ledgerDir) {
    for ($i = 0; $i -lt $demoOutput.Count; $i++) {
        if ($demoOutput[$i] -match '^Ledger Dir\s*$') {
            for ($j = $i + 1; $j -lt $demoOutput.Count; $j++) {
                $candidate = $demoOutput[$j].Trim()
                if ($candidate) {
                    $ledgerDir = $candidate
                    break
                }
            }
            if ($ledgerDir) {
                break
            }
        }
    }
}

if (-not $ledgerDir) {
    foreach ($line in $demoOutput) {
        if ($line -match '^python -m core\.determinism\.replay\s+(\S+)') {
            $ledgerDir = $Matches[1].Trim()
            break
        }
    }
}

if (-not $ledgerDir) {
    Write-Error "Unable to parse ledger_dir from demo output."
    exit 2
}

Write-Output "== REPLAY VERIFY =="
& python -W "ignore::RuntimeWarning" -m core.determinism.replay $ledgerDir --strict-manifest
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Output "OK"

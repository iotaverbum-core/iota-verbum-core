param(
    [string]$DownloadsRoot = (Join-Path $HOME "Downloads\cuc_v4_candidate_2026_04_08")
)

$folders = @(
    "gpt_5_4",
    "claude_sonnet_4_6",
    "gemini_2_5_pro",
    "gemini_2_5_flash",
    "qwen3_next_80b",
    "deepseek_v3_2"
)

New-Item -ItemType Directory -Force -Path $DownloadsRoot | Out-Null
foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DownloadsRoot $folder) | Out-Null
}

Write-Host "Prepared CUC v4 candidate sweep folders under: $DownloadsRoot"
foreach ($folder in $folders) {
    Write-Host (" - " + (Join-Path $DownloadsRoot $folder))
}

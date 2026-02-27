# Legacy Recovery Plan

## Purpose

Provide a structured approach to locate, verify, and preserve legacy history without rewriting the core repository.

## Current Confirmed State

- This repository contains only the core baseline history.
- Legacy branches, tags, or prior history are not present here.
- v2/v3/v4 artifacts are referenced historically but not recoverable from current materials.

## Possible Places Legacy Could Exist

- Other repositories under the same org/user.
- Old local folders on developer machines.
- Backups, zip archives, or exported bundles.
- Cloud drives or shared team storage.

## Recovery Checklist (Local Commands)

1) Identify candidate directories that may be git repos:
```powershell
Get-ChildItem -Directory | ForEach-Object { if (Test-Path (Join-Path $_.FullName ".git")) { $_.FullName } }
```

2) For each candidate repo:
```powershell
git -C <path> status -sb
git -C <path> remote -v
git -C <path> branch -a
git -C <path> tag -l
git -C <path> log --oneline --decorate --graph --all
```

3) Look for v2/v3/v4 references:
```powershell
git -C <path> log --oneline --all | Select-String -Pattern "v2|v3|v4"
```

## Import Policy (If Legacy Is Recovered)

- Do NOT rewrite core history.
- Preferred: keep legacy as a separate repo.
- Alternate: store legacy under `archive/legacy/<YYYY-MM-DD>/` in a new branch or separate repo.
- Add cross-links in docs between core and legacy locations.

## Decision Log

- Until recovery, do not claim v2/v3/v4 as supported artifacts.
- `v0.1.0-core` remains the canonical baseline.

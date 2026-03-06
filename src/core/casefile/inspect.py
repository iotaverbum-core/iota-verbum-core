from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.determinism.schema_validate import validate

_ROLE_ORDER = {
    "sealed": 0,
    "derived": 1,
    "narrative": 2,
}


def _artifact_sort_key(item: dict) -> tuple[int, str]:
    role = str(item.get("role", ""))
    return (_ROLE_ORDER.get(role, 99), str(item.get("name", "")))


def render_casefile_summary(casefile: dict) -> str:
    lines: list[str] = []

    lines.append("Header")
    lines.append(f"Casefile ID: {casefile['casefile_id']}")
    lines.append(f"Verification Status: {casefile['summary']['verification_status']}")
    lines.append(f"Created UTC: {casefile['created_utc']}")
    lines.append(f"Core Version: {casefile['core_version']}")
    lines.append(f"Ruleset ID: {casefile['ruleset_id']}")
    lines.append("")

    lines.append("Hashes")
    lines.append(f"manifest_sha256: {casefile['hashes']['manifest_sha256']}")
    lines.append(f"bundle_sha256: {casefile['hashes']['bundle_sha256']}")
    lines.append(f"world_sha256: {casefile['hashes']['world_sha256']}")
    lines.append(f"output_sha256: {casefile['hashes']['output_sha256']}")
    lines.append(f"attestation_sha256: {casefile['hashes']['attestation_sha256']}")
    lines.append("")

    lines.append("Summary")
    lines.append(f"entities: {casefile['summary']['entities']}")
    lines.append(f"events: {casefile['summary']['events']}")
    lines.append(f"unknowns: {casefile['summary']['unknowns']}")
    lines.append(f"conflicts: {casefile['summary']['conflicts']}")
    lines.append(
        f"constraint_violations: {casefile['summary']['constraint_violations']}"
    )
    lines.append(f"causal_edges: {casefile['summary']['causal_edges']}")
    lines.append("")

    lines.append("Ledger")
    lines.append(f"ledger_dir: {casefile['ledger_dir']}")
    lines.append(
        "replay command: "
        f"python -m core.determinism.replay {casefile['ledger_dir']} --strict-manifest"
    )
    lines.append("")

    lines.append("Artifacts")
    lines.append("name | role | sha256 | schema")
    for artifact in sorted(casefile["artifacts"], key=_artifact_sort_key):
        schema = artifact.get("schema", "-")
        lines.append(
            f"{artifact['name']} | {artifact['role']} | {artifact['sha256']} | {schema}"
        )
    lines.append("")

    lines.append("Receipts")
    lines.append(
        f"evidence_ref_count: {casefile['receipts_summary']['evidence_ref_count']}"
    )
    lines.append(f"proof_count: {casefile['receipts_summary']['proof_count']}")
    lines.append(f"finding_count: {casefile['receipts_summary']['finding_count']}")

    return "\n".join(lines) + "\n"


def inspect_casefile(path: str | Path) -> str:
    casefile_path = Path(path)
    casefile_obj = json.loads(casefile_path.read_text(encoding="utf-8"))
    validate(casefile_obj, "schemas/casefile.schema.json")
    return render_casefile_summary(casefile_obj)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("casefile_path")
    args = parser.parse_args(argv)

    try:
        summary = inspect_casefile(args.casefile_path)
    except Exception as exc:
        print(f"Casefile inspection failed: {exc}", file=sys.stderr)
        return 1

    print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

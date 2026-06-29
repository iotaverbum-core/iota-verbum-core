"""Provenant CLI: seal, verify, diff, export decision records.

    python -m provenant seal    --input decision.json --out runs/app-001
    python -m provenant verify  runs/app-001
    python -m provenant diff     runs/app-001 runs/app-001-v2
    python -m provenant export  --tenant acme --generated-utc 2026-06-28T00:00:00Z \
        --out export/pack.json runs/app-001 runs/app-001-v2
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from provenant.diff import diff_records
from provenant.export import build_examiner_pack, write_examiner_pack
from provenant.record import seal_decision, verify_record, write_record


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cmd_seal(args) -> int:
    spec = _load(args.input)
    record = seal_decision(
        record_id=spec["record_id"],
        tenant_id=spec["tenant_id"],
        created_utc=spec["created_utc"],
        subject_ref=spec["subject_ref"],
        decision=spec["decision"],
        model=spec["model"],
        evidence=spec.get("evidence"),
        reason_codes=spec.get("reason_codes"),
        governance=spec.get("governance"),
        prior_record_sha256=spec.get("prior_record_sha256"),
    )
    result = write_record(record, Path(args.out))
    print(json.dumps(result, indent=2))
    if record["compliance_warnings"]:
        print(
            f"WARNING: {len(record['compliance_warnings'])} compliance warning(s)",
            file=sys.stderr,
        )
    return 0


def _cmd_verify(args) -> int:
    result = verify_record(Path(args.record_dir))
    print(json.dumps(result, indent=2))
    return 0 if result["verified"] else 1


def _cmd_diff(args) -> int:
    prior = _load(str(Path(args.prior) / "record.json"))
    current = _load(str(Path(args.current) / "record.json"))
    result = diff_records(prior, current)
    print(json.dumps(result, indent=2))
    return 2 if result["regression"] else 0


def _cmd_export(args) -> int:
    pack = build_examiner_pack(
        [Path(d) for d in args.record_dirs],
        tenant_id=args.tenant,
        generated_utc=args.generated_utc,
    )
    write_examiner_pack(pack, Path(args.out))
    print(json.dumps(pack["summary"], indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="provenant", description="Provenant CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_seal = sub.add_parser("seal", help="Seal a decision into a record")
    p_seal.add_argument("--input", required=True)
    p_seal.add_argument("--out", required=True)
    p_seal.set_defaults(func=_cmd_seal)

    p_verify = sub.add_parser("verify", help="Verify a sealed record directory")
    p_verify.add_argument("record_dir")
    p_verify.set_defaults(func=_cmd_verify)

    p_diff = sub.add_parser("diff", help="Diff two records for silent regression")
    p_diff.add_argument("prior")
    p_diff.add_argument("current")
    p_diff.set_defaults(func=_cmd_diff)

    p_export = sub.add_parser("export", help="Build an examiner export pack")
    p_export.add_argument("--tenant", required=True)
    p_export.add_argument("--generated-utc", required=True)
    p_export.add_argument("--out", required=True)
    p_export.add_argument("record_dirs", nargs="+")
    p_export.set_defaults(func=_cmd_export)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

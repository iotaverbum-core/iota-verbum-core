from __future__ import annotations

import argparse

from core.reasoning.world_patch import run_world_patch


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--patch", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--created-utc", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument("--ruleset-id", required=True)
    parser.add_argument("--with-diff", default="true")
    parser.add_argument("--with-constraint-diff", default="true")
    parser.add_argument("--mode", default="brief", choices=["brief", "full"])
    parser.add_argument("--max-lines", type=int, default=200)
    args = parser.parse_args(argv)

    result = run_world_patch(
        base=args.base,
        patch=args.patch,
        out_dir=args.out_dir,
        created_utc=args.created_utc,
        core_version=args.core_version,
        ruleset_id=args.ruleset_id,
        with_diff=_parse_bool(args.with_diff),
        with_constraint_diff=_parse_bool(args.with_constraint_diff),
        mode=args.mode,
        max_lines=args.max_lines,
    )
    print(
        (
            f"patch_id={result['patch']['patch_id']} "
            f"run_dir={result['run_dir']} "
            f"ledger_dir={result['result']['ledger_dir']} "
            f"verification={result['result']['verification_change']['old']}->"
            f"{result['result']['verification_change']['new']}"
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

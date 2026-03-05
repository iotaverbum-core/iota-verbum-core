from __future__ import annotations

import argparse

from core.reasoning.repair_loop import run_repair_loop


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
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--created-utc", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument("--ruleset-id", required=True)
    parser.add_argument("--approve", default="false")
    parser.add_argument("--choose", type=int, default=None)
    parser.add_argument("--strict-manifest", default="true")
    parser.add_argument("--max-lines", type=int, default=120)
    parser.add_argument("--mode", choices=["brief", "full"], default="brief")
    args = parser.parse_args(argv)

    try:
        return run_repair_loop(
            base=args.base,
            out_dir=args.out_dir,
            created_utc=args.created_utc,
            core_version=args.core_version,
            ruleset_id=args.ruleset_id,
            approve=_parse_bool(args.approve),
            choose=args.choose,
            strict_manifest=_parse_bool(args.strict_manifest),
            mode=args.mode,
            max_lines=args.max_lines,
        )
    except Exception as exc:
        print(f"Repair loop failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

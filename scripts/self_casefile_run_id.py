from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_src_to_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-chunks", required=True, type=int)
    parser.add_argument("--created-utc", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument("--ruleset-id", required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--enrich", default="")
    args = parser.parse_args(argv)

    _add_src_to_syspath()
    from proposal.cli_demo import _compute_run_id, _parse_bool

    run_id = _compute_run_id(
        folder=args.folder,
        query=args.query,
        prompt=args.prompt,
        max_chunks=args.max_chunks,
        created_utc=args.created_utc,
        core_version=args.core_version,
        ruleset_id=args.ruleset_id,
        world=_parse_bool(args.world),
        enrich=args.enrich,
    )
    print(run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path

from proposal.bundle_from_pack import build_evidence_bundle_from_pack, load_pack


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--created-utc", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument("--ruleset-id", required=True)
    parser.add_argument("--mode", default="all", choices=["all", "keyword", "topk"])
    parser.add_argument("--query", default="")
    parser.add_argument("--max-chunks", type=int, default=50)
    args = parser.parse_args(argv)

    pack = load_pack(args.pack)
    bundle_obj, bundle_bytes, bundle_sha256 = build_evidence_bundle_from_pack(
        pack,
        prompt=args.prompt,
        params={},
        created_utc=args.created_utc,
        core_version=args.core_version,
        ruleset_id=args.ruleset_id,
        mode=args.mode,
        query=args.query,
        max_chunks=args.max_chunks,
    )
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(output_path, bundle_bytes)
    print(f"{bundle_sha256} artifacts={len(bundle_obj['artifacts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

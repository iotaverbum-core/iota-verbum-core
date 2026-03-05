from __future__ import annotations

import argparse
from pathlib import Path

from proposal.evidence_pack import build_evidence_pack


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root-hint", default="")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap-chars", type=int, default=120)
    args = parser.parse_args(argv)

    pack_obj, pack_bytes = build_evidence_pack(
        args.folder,
        root_hint=args.root_hint,
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
    )
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(output_path, pack_bytes)
    print(
        f"{pack_obj['pack_sha256']} "
        f"docs={len(pack_obj['documents'])} "
        f"chunks={len(pack_obj['chunks'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from pathlib import Path

from core.files import write_bytes_deterministic
from proposal.evidence_pack import build_evidence_pack


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _write_atomic(path: Path, data: bytes) -> None:
    write_bytes_deterministic(path, data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root-hint", default="")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap-chars", type=int, default=120)
    parser.add_argument("--max-docs", type=int, default=100)
    parser.add_argument("--max-total-words", type=int, default=500000)
    parser.add_argument("--max-total-chunks", type=int, default=2000)
    parser.add_argument("--chunk-target-words", type=int, default=450)
    parser.add_argument("--chunk-overlap-words", type=int, default=75)
    parser.add_argument("--extract-structure", default="false")
    parser.add_argument("--categorize", default="false")
    args = parser.parse_args(argv)

    pack_obj, pack_bytes = build_evidence_pack(
        args.folder,
        root_hint=args.root_hint,
        max_chars=args.max_chars,
        overlap_chars=args.overlap_chars,
        max_docs=args.max_docs,
        max_total_words=args.max_total_words,
        max_total_chunks=args.max_total_chunks,
        chunk_target_words=args.chunk_target_words,
        chunk_overlap_words=args.chunk_overlap_words,
        extract_structure=_parse_bool(args.extract_structure),
        categorize=_parse_bool(args.categorize),
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

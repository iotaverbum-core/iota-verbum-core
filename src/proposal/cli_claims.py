from __future__ import annotations

import argparse
from pathlib import Path

from proposal.claim_propose import (
    dumps_claim_graph,
    load_evidence_pack,
    propose_claim_graph,
)


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    evidence_pack = load_evidence_pack(args.pack)
    claim_graph = propose_claim_graph(evidence_pack)
    claim_graph_bytes = dumps_claim_graph(claim_graph)

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(output_path, claim_graph_bytes)
    print(
        f"docs={len(evidence_pack['documents'])} "
        f"chunks={len(evidence_pack['chunks'])} "
        f"claims={len(claim_graph['claims'])} "
        f"edges={len(claim_graph['edges'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

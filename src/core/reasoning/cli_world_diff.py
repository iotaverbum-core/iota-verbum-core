from __future__ import annotations

import argparse
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.reasoning.world_diff import compute_world_diff, load_output_input
from core.reasoning.world_diff_narrative import render_world_diff_narrative


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--narrative-out")
    parser.add_argument("--mode", default="brief", choices=["brief", "full"])
    args = parser.parse_args(argv)

    diff = compute_world_diff(
        old_output=load_output_input(args.old),
        new_output=load_output_input(args.new),
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(out_path, dumps_canonical(diff))

    if args.narrative_out:
        narrative = render_world_diff_narrative(diff, mode=args.mode)
        narrative_path = Path(args.narrative_out)
        narrative_path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(narrative_path, dumps_canonical(narrative))
        print(narrative["text"], end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

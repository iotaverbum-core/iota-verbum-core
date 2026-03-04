from __future__ import annotations

import argparse
from pathlib import Path

from proposal.world_propose import (
    dumps_world_model,
    load_world_pack,
    propose_world_model,
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

    pack = load_world_pack(args.pack)
    world_model = propose_world_model(pack)
    world_bytes = dumps_world_model(world_model)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(out_path, world_bytes)
    print(
        (
            f"entities={len(world_model['entities'])} "
            f"events={len(world_model['events'])} "
            f"unknowns={len(world_model['unknowns'])} "
            f"conflicts={len(world_model['conflicts'])} "
            f"world_sha256={world_model['world_sha256']}"
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

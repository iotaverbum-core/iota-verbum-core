from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.agent.runner import run_task
from core.determinism.canonical_json import dumps_canonical


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    temp_path.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    task_obj = json.loads(Path(args.task).read_text(encoding="utf-8"))
    result = run_task(task_obj=task_obj, approve=args.approve)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_atomic(out_path, dumps_canonical(result["plan"]))

    if args.approve:
        print(
            f"Agent task {result['plan']['task_id']} completed "
            f"exit_code={result['exit_code']}"
        )
    else:
        print(
            f"Agent task {result['plan']['task_id']} requires approval "
            f"exit_code={result['exit_code']}"
        )
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())

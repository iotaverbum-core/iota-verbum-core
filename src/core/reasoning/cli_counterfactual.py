from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.reasoning.counterfactual import (
    canonicalize_counterfactual_task_file,
    load_counterfactual_task,
    run_counterfactual_task,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--mode", default="brief", choices=["brief", "full"])
    parser.add_argument("--fix-task", default="false")
    args = parser.parse_args(argv)

    try:
        task, _task_bytes = load_counterfactual_task(args.task)
    except ValueError as exc:
        if args.fix_task.strip().lower() == "true":
            task_id = canonicalize_counterfactual_task_file(args.task)
            print(f"Wrote canonical task_id: {task_id}", end="")
            return 2
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    result = run_counterfactual_task(
        task,
        out_dir=args.out_dir,
        mode_override=args.mode,
    )
    run_dir = Path(result["run_dir"])
    print(
        (
            f"task_id={task['task_id']} "
            f"run_dir={run_dir.as_posix()} "
            f"world_sha256={result['result']['counterfactual_hashes']['world_sha256']} "
            f"output_sha256={result['output_sha256']} "
            f"attestation_sha256={result['attestation_sha256']}"
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

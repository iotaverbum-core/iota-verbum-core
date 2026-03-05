import json
from pathlib import Path

import pytest

from core.agent.cli_agent import main


def _write_task(path: Path, folder: Path, task_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "task_version": "1.0",
                "task_id": task_id,
                "created_utc": "2026-03-04T12:00:00Z",
                "ruleset_id": "ruleset.core.v1",
                "core_version": "0.3.0",
                "inputs": {
                    "folder": str(folder),
                    "query": "API_KEYS",
                    "prompt": "Show timeline and conflicts",
                    "max_chunks": 5,
                },
                "steps": [
                    {
                        "step_id": "step-world",
                        "action": "RUN_DEMO_WORLD",
                        "params": {},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_cli_agent_help_exits_cleanly():
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


def test_cli_agent_requires_approval_and_writes_plan(tmp_path: Path, capsys):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n- 2026-03-01 `API_KEYS` are environment only.\n",
        encoding="utf-8",
    )
    task_path = tmp_path / "task.json"
    plan_path = tmp_path / "plan.json"
    _write_task(task_path, docs_dir, f"task-{tmp_path.name}")

    exit_code = main(["--task", str(task_path), "--out", str(plan_path)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert plan_path.exists()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["steps"][0]["status"] == "PLANNED"
    assert "requires approval exit_code=2" in captured.out

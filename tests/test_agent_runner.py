import json
from pathlib import Path

from core.agent.runner import run_task


def _task_obj(task_id: str, folder: Path) -> dict:
    return {
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
    }


def test_run_task_requires_approval_and_prints_plan(tmp_path: Path, capsys):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n- 2026-03-01 `API_KEYS` are environment only.\n",
        encoding="utf-8",
    )
    task = _task_obj(f"task-{tmp_path.name}", docs_dir)

    result = run_task(task_obj=task, approve=False)
    captured = capsys.readouterr()

    assert result["exit_code"] == 2
    assert captured.out == result["plan_text"]
    assert captured.out.startswith("Agent Plan\n")
    assert "status=PLANNED" in captured.out


def test_run_task_executes_world_demo_and_writes_step_record(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n"
        "- 2026-03-01 `API_KEYS` are environment only.\n"
        "- 2026-03-02 `API_KEYS` are never in source.\n",
        encoding="utf-8",
    )
    task = _task_obj(f"task-{tmp_path.name}", docs_dir)

    result = run_task(task_obj=task, approve=True)

    assert result["exit_code"] == 0
    step = result["plan"]["steps"][0]
    assert step["status"] == "EXECUTED"
    step_record_path = Path(
        next(
            artifact
            for artifact in step["outputs"]["artifacts"]
            if Path(artifact).name.startswith("step_record")
        )
    )
    assert step_record_path.exists()
    step_record = json.loads(step_record_path.read_text(encoding="utf-8"))
    assert step_record["status"] == "EXECUTED"
    assert step_record["action"] == "RUN_DEMO_WORLD"
    assert "Deterministic World Demo\n" in step_record["stdout_text"]
    assert step_record["receipts"]["ledger_dir"] == step["outputs"]["ledger_dir"]


def test_run_task_is_idempotent_for_identical_inputs(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Access Policy\n- 2026-03-01 `API_KEYS` are environment only.\n",
        encoding="utf-8",
    )
    task = _task_obj(f"task-{tmp_path.name}", docs_dir)

    first = run_task(task_obj=task, approve=True)
    first_step_record_path = Path(
        next(
            artifact
            for artifact in first["plan"]["steps"][0]["outputs"]["artifacts"]
            if Path(artifact).name.startswith("step_record")
        )
    )
    first_bytes = first_step_record_path.read_bytes()
    second = run_task(task_obj=task, approve=True)

    assert first["exit_code"] == 0
    assert second["exit_code"] == 0
    assert first["plan"] == second["plan"]
    second_step_record_path = Path(
        next(
            artifact
            for artifact in second["plan"]["steps"][0]["outputs"]["artifacts"]
            if Path(artifact).name.startswith("step_record")
        )
    )
    second_bytes = second_step_record_path.read_bytes()
    assert first_bytes == second_bytes

from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.replay import verify_run
from core.determinism.schema_validate import validate
from core.reasoning.world_diff import compute_world_diff, load_output_input
from core.reasoning.world_diff_narrative import render_world_diff_narrative
from proposal.cli_demo import run_demo

ALLOWLIST = {
    "RUN_DEMO_WORLD",
    "RUN_DEMO_GRAPH",
    "RUN_WORLD_DIFF",
    "REPLAY_VERIFY",
}


def _atomic_write(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    os.replace(temp_path, path)


def _write_or_verify(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"existing file mismatch: {path}")
        return path
    _atomic_write(path, data)
    return path


def _write_with_conflict_suffix(path: Path, data: bytes) -> Path:
    if not path.exists():
        return _write_or_verify(path, data)
    if path.read_bytes() == data:
        return path
    conflict_index = 1
    while True:
        candidate = path.with_name(
            f"{path.stem}__conflict_{conflict_index}{path.suffix}"
        )
        if not candidate.exists():
            return _write_or_verify(candidate, data)
        if candidate.read_bytes() == data:
            return candidate
        conflict_index += 1


def _plan_with_hash(plan: dict) -> dict:
    without_hash = {
        **plan,
        "plan_sha256": "",
    }
    plan_sha256 = sha256_bytes(dumps_canonical(without_hash))
    finalized = {
        **plan,
        "plan_sha256": plan_sha256,
    }
    validate(finalized, "schemas/agent_plan.schema.json")
    return finalized


def _canonical_params(params: dict) -> dict:
    return json.loads(dumps_canonical(params).decode("utf-8"))


def _step_output_shell() -> dict:
    return {
        "run_dir": "",
        "ledger_dir": "",
        "artifacts": [],
    }


def _build_plan(task_obj: dict) -> dict:
    plan = {
        "plan_version": "1.0",
        "task_id": task_obj["task_id"],
        "steps": [
            {
                "step_id": step["step_id"],
                "action": step["action"],
                "params": _canonical_params(step["params"]),
                "status": "PLANNED",
                "outputs": _step_output_shell(),
            }
            for step in task_obj["steps"]
        ],
        "plan_sha256": "",
    }
    return _plan_with_hash(plan)


def _render_plan_text(plan: dict) -> str:
    lines = [
        "Agent Plan",
        f"task_id: {plan['task_id']}",
        f"plan_sha256: {plan['plan_sha256']}",
    ]
    for step in plan["steps"]:
        params_text = dumps_canonical(step["params"]).decode("utf-8")
        lines.append(
            f"- {step['step_id']} {step['action']} "
            f"status={step['status']} params={params_text}"
        )
    return "\n".join(lines) + "\n"


def _task_demo_kwargs(task_obj: dict, step_params: dict, *, world: bool) -> dict:
    inputs = task_obj["inputs"]
    return {
        "folder": str(step_params.get("folder", inputs["folder"])),
        "query": str(step_params.get("query", inputs["query"])),
        "prompt": str(step_params.get("prompt", inputs["prompt"])),
        "max_chunks": int(step_params.get("max_chunks", inputs["max_chunks"])),
        "created_utc": str(step_params.get("created_utc", task_obj["created_utc"])),
        "core_version": str(step_params.get("core_version", task_obj["core_version"])),
        "ruleset_id": str(step_params.get("ruleset_id", task_obj["ruleset_id"])),
        "world": world,
        "verbosity": str(step_params.get("verbosity", "brief")),
        "show_receipts": bool(step_params.get("show_receipts", False)),
        "max_lines": int(step_params.get("max_lines", 200)),
        "diff_against": str(step_params.get("diff_against", "")),
    }


def _result_json_safe(result: dict) -> dict:
    return json.loads(dumps_canonical(result).decode("utf-8"))


def _run_demo_step(
    task_obj: dict,
    step_params: dict,
    *,
    world: bool,
) -> tuple[str, dict]:
    result = run_demo(**_task_demo_kwargs(task_obj, step_params, world=world))
    stdout_text = result["report"].replace("\r\n", "\n").replace("\r", "\n")
    return stdout_text, _result_json_safe(result)


def _write_json_artifact(path: Path, obj: dict) -> Path:
    return _write_with_conflict_suffix(path, dumps_canonical(obj))


def _run_world_diff_step(
    step_dir: Path,
    step_params: dict,
    previous_outputs: list[dict],
) -> tuple[str, dict]:
    old_path = str(step_params["old"])
    new_path = str(step_params.get("new", ""))
    if not new_path:
        for candidate in reversed(previous_outputs):
            ledger_dir = candidate["outputs"]["ledger_dir"]
            if ledger_dir:
                new_path = ledger_dir
                break
    if not new_path:
        raise ValueError(
            "RUN_WORLD_DIFF requires new or a previous step with ledger_dir"
        )

    diff = compute_world_diff(
        old_output=load_output_input(old_path),
        new_output=load_output_input(new_path),
    )
    narrative = render_world_diff_narrative(
        diff,
        mode=str(step_params.get("mode", "brief")),
    )
    diff_path = _write_json_artifact(step_dir / "world_diff.json", diff)
    narrative_path = _write_json_artifact(
        step_dir / "world_diff_narrative.json",
        narrative,
    )
    stdout_text = narrative["text"].replace("\r\n", "\n").replace("\r", "\n")
    return stdout_text, {
        "run_dir": str(step_dir),
        "ledger_dir": new_path if Path(new_path).is_dir() else "",
        "artifacts": [str(diff_path), str(narrative_path)],
        "world_diff_path": str(diff_path),
        "world_diff_narrative_path": str(narrative_path),
        "old": old_path,
        "new": new_path,
        "output_sha256": diff["new"]["output_sha256"],
        "attestation_sha256": diff["new"]["attestation_sha256"],
    }


def _replay_stdout(result: dict) -> str:
    warning_suffix = ""
    if result["warnings"]:
        warning_suffix = f" warnings={len(result['warnings'])}"
    lines = [
        "Replay verification OK:"
        f" bundle_sha256={result['bundle_sha256']}"
        f" output_sha256={result['output_sha256']}"
        f" attestation_sha256={result['attestation_sha256']}"
        f"{warning_suffix}"
    ]
    lines.extend(f"warning: {warning}" for warning in result["warnings"])
    return "\n".join(lines) + "\n"


def _run_replay_step(
    step_dir: Path,
    step_params: dict,
    previous_outputs: list[dict],
) -> tuple[str, dict]:
    ledger_dir = str(step_params.get("ledger_dir", ""))
    if not ledger_dir:
        for candidate in reversed(previous_outputs):
            previous_ledger_dir = candidate["outputs"]["ledger_dir"]
            if previous_ledger_dir:
                ledger_dir = previous_ledger_dir
                break
    if not ledger_dir:
        raise ValueError(
            "REPLAY_VERIFY requires ledger_dir or a previous step with ledger_dir"
        )
    strict_manifest = bool(step_params.get("strict_manifest", False))
    result = verify_run(ledger_dir, strict_manifest=strict_manifest)
    stdout_text = _replay_stdout(result)
    replay_result = {
        "ledger_dir": ledger_dir,
        "strict_manifest": strict_manifest,
        **result,
    }
    replay_result_path = _write_json_artifact(
        step_dir / "replay_result.json",
        replay_result,
    )
    return stdout_text, {
        "run_dir": str(step_dir),
        "ledger_dir": ledger_dir,
        "artifacts": [str(replay_result_path)],
        "replay_result_path": str(replay_result_path),
        "ok": bool(result["ok"]),
        "bundle_sha256": result["bundle_sha256"],
        "output_sha256": result["output_sha256"],
        "attestation_sha256": result["attestation_sha256"],
        "warnings": result["warnings"],
    }


def _execute_step(
    *,
    task_obj: dict,
    step: dict,
    step_dir: Path,
    previous_outputs: list[dict],
) -> tuple[str, dict]:
    action = step["action"]
    params = step["params"]
    if action not in ALLOWLIST:
        raise ValueError(f"step action not allowlisted: {action}")
    if action == "RUN_DEMO_WORLD":
        return _run_demo_step(task_obj, params, world=True)
    if action == "RUN_DEMO_GRAPH":
        return _run_demo_step(task_obj, params, world=False)
    if action == "RUN_WORLD_DIFF":
        return _run_world_diff_step(step_dir, params, previous_outputs)
    if action == "REPLAY_VERIFY":
        return _run_replay_step(step_dir, params, previous_outputs)
    raise ValueError(f"unsupported step action: {action}")


def _receipts_from_result(result: dict) -> dict:
    return {
        "ledger_dir": str(result.get("ledger_dir", "")),
        "output_sha256": str(result.get("output_sha256", "")),
        "attestation_sha256": str(result.get("attestation_sha256", "")),
    }


def _record_step(
    *,
    task_id: str,
    step: dict,
    status: str,
    stdout_text: str,
    result: dict,
    step_dir: Path,
) -> Path:
    step_record = {
        "step_record_version": "1.0",
        "task_id": task_id,
        "step_id": step["step_id"],
        "action": step["action"],
        "params": _canonical_params(step["params"]),
        "status": status,
        "stdout_text": stdout_text.replace("\r\n", "\n").replace("\r", "\n"),
        "result": _result_json_safe(result),
        "receipts": _receipts_from_result(result),
    }
    validate(step_record, "schemas/agent_step_record.schema.json")
    return _write_json_artifact(step_dir / "step_record.json", step_record)


def run_task(
    *,
    task_obj: dict,
    approve: bool,
    ledger_root: str = "data/ledger",
) -> dict:
    del ledger_root
    validate(task_obj, "schemas/agent_task.schema.json")
    plan = _build_plan(task_obj)
    plan_text = _render_plan_text(plan)
    if not approve:
        print(plan_text, end="")
        return {
            "plan": plan,
            "plan_text": plan_text,
            "exit_code": 2,
        }

    plan_work = {
        "plan_version": plan["plan_version"],
        "task_id": plan["task_id"],
        "steps": [
            json.loads(dumps_canonical(step).decode("utf-8"))
            for step in plan["steps"]
        ],
        "plan_sha256": "",
    }
    agent_root = Path("outputs") / "agent" / task_obj["task_id"]
    previous_outputs: list[dict] = []

    for index, task_step in enumerate(task_obj["steps"]):
        plan_step = plan_work["steps"][index]
        step_dir = agent_root / task_step["step_id"]
        stdout_buffer = io.StringIO()
        try:
            with redirect_stdout(stdout_buffer):
                stdout_text, result = _execute_step(
                    task_obj=task_obj,
                    step=task_step,
                    step_dir=step_dir,
                    previous_outputs=previous_outputs,
                )
            combined_stdout = stdout_buffer.getvalue() + stdout_text
            step_record_path = _record_step(
                task_id=task_obj["task_id"],
                step=task_step,
                status="EXECUTED",
                stdout_text=combined_stdout,
                result=result,
                step_dir=step_dir,
            )
            artifacts = list(result.get("artifacts", []))
            artifacts.append(str(step_record_path))
            plan_step["status"] = "EXECUTED"
            plan_step["outputs"] = {
                "run_dir": str(result.get("run_dir", step_dir)),
                "ledger_dir": str(result.get("ledger_dir", "")),
                "artifacts": sorted(artifacts),
            }
            previous_outputs.append(
                {"step": task_step, "outputs": plan_step["outputs"]}
            )
        except Exception as exc:
            failure_result = {
                "error": str(exc),
            }
            step_record_path = _record_step(
                task_id=task_obj["task_id"],
                step=task_step,
                status="FAILED",
                stdout_text=stdout_buffer.getvalue(),
                result=failure_result,
                step_dir=step_dir,
            )
            plan_step["status"] = "FAILED"
            plan_step["outputs"] = {
                "run_dir": str(step_dir),
                "ledger_dir": "",
                "artifacts": [str(step_record_path)],
            }
            for remaining_step in plan_work["steps"][index + 1 :]:
                remaining_step["status"] = "SKIPPED"
            finalized_plan = _plan_with_hash(plan_work)
            return {
                "plan": finalized_plan,
                "plan_text": _render_plan_text(finalized_plan),
                "exit_code": 1,
            }

    finalized_plan = _plan_with_hash(plan_work)
    return {
        "plan": finalized_plan,
        "plan_text": _render_plan_text(finalized_plan),
        "exit_code": 0,
    }

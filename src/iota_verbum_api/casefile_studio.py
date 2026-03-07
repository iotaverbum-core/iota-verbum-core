from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.replay import verify_run
from proposal.cli_demo import run_demo

FIXTURES_PATH = Path("data/demo_cases/fixtures.json")
OUTPUTS_DEMO_DIR = Path("outputs/demo")
UPLOADS_DIR = Path("tmp_uploads/casefile_studio")

PIPELINE_STEPS = [
    ("evidence_pack", "EvidencePack"),
    ("claim_proposer", "Claim Proposer"),
    ("claim_graph", "Claim Graph"),
    ("graph_reasoning", "Graph Reasoning"),
    ("world_model", "World Model"),
    ("narrative_renderer", "Narrative Renderer"),
    ("ledger_attestation", "Ledger + Attestation"),
    ("replay_verification", "Replay Verification"),
]

_RUNS_LOCK = threading.Lock()
_RUNS: dict[str, dict[str, Any]] = {}
_RUN_SEQ = 0


def _next_run_request_id() -> str:
    global _RUN_SEQ
    with _RUNS_LOCK:
        _RUN_SEQ += 1
        return f"studio-run-{_RUN_SEQ:06d}"


def _normalize_fixture_list(raw: dict) -> list[dict]:
    items = raw.get("items", [])
    normalized = []
    for item in items:
        fixture = {
            "id": str(item["id"]),
            "title": str(item["title"]),
            "category": str(item["category"]),
            "description": str(item["description"]),
            "folder": str(item["folder"]).replace("\\", "/"),
            "query": str(item.get("query", "")),
            "prompt": str(item.get("prompt", "")),
            "created_utc": str(item["created_utc"]),
            "core_version": str(item["core_version"]),
            "ruleset_id": str(item["ruleset_id"]),
            "max_chunks": int(item.get("max_chunks", 8)),
            "max_events": int(item.get("max_events", 30)),
        }
        normalized.append(fixture)
    return sorted(normalized, key=lambda item: item["id"])


def load_fixtures() -> list[dict]:
    if not FIXTURES_PATH.exists():
        raise HTTPException(status_code=500, detail="fixture_registry_missing")
    raw = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return _normalize_fixture_list(raw)


def _fixture_by_id(fixture_id: str) -> dict:
    fixtures = load_fixtures()
    for item in fixtures:
        if item["id"] == fixture_id:
            return item
    raise HTTPException(status_code=404, detail="fixture_not_found")


def _to_posix(path: Path) -> str:
    return path.resolve().as_posix()


def _resolve_run_dir(run_id: str) -> Path:
    run_dir = OUTPUTS_DEMO_DIR / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run_not_found")
    return run_dir


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"missing_artifact:{path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _sorted_evidence_refs(receipts: dict) -> list[dict]:
    refs = receipts.get("evidence_refs", [])
    return sorted(
        refs,
        key=lambda item: (
            item["source_id"],
            item["chunk_id"],
            item["offset_start"],
            item["offset_end"],
            item["text_sha256"],
        ),
    )


def _sorted_findings(receipts: dict) -> list[dict]:
    findings = receipts.get("findings", [])
    return sorted(
        findings,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )


def _sorted_proofs(receipts: dict) -> list[dict]:
    proofs = receipts.get("proofs", [])
    return sorted(
        proofs,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )


def _time_sort_key(event: dict) -> tuple[int, str, str]:
    time_ref = event.get("time", {"kind": "unknown"})
    if time_ref.get("kind") == "unknown":
        return (1, "", event.get("event_id", ""))
    return (0, str(time_ref.get("value", "")), event.get("event_id", ""))


def _run_workspace(run_id: str) -> dict:
    run_dir = _resolve_run_dir(run_id)
    casefile = _load_json(run_dir / "casefile.json")
    sealed_output = _load_json(run_dir / "sealed_output.json")
    world_model = sealed_output.get("world_model", {})
    verification = sealed_output.get("verification_result", {})
    receipts = verification.get("receipts", {})
    return {
        "run_dir": run_dir,
        "run_id": run_dir.name,
        "casefile": casefile,
        "sealed_output": sealed_output,
        "world_model": world_model,
        "verification_result": verification,
        "receipts": receipts,
    }


def _artifact_map(workspace: dict) -> dict[str, Path]:
    run_dir: Path = workspace["run_dir"]
    casefile = workspace["casefile"]
    ledger_dir = Path(casefile["ledger_dir"])
    if not ledger_dir.is_absolute():
        ledger_dir = Path.cwd() / ledger_dir
    return {
        "casefile.json": run_dir / "casefile.json",
        "sealed_output.json": run_dir / "sealed_output.json",
        "world_model.json": run_dir / "world_model.json",
        "evidence_pack.json": run_dir / "evidence_pack.json",
        "evidence_bundle.json": run_dir / "evidence_bundle.json",
        "attestation.json": run_dir / "attestation.json",
        "ledger_bundle.json": ledger_dir / "bundle.json",
        "ledger_output.json": ledger_dir / "output.json",
        "ledger_attestation.json": ledger_dir / "attestation.json",
    }


def _step_state(current_stage: str, done: bool, failed: bool) -> list[dict]:
    steps = []
    stage_ids = [step_id for step_id, _label in PIPELINE_STEPS]
    try:
        current_index = stage_ids.index(current_stage)
    except ValueError:
        current_index = 0
    for index, (step_id, label) in enumerate(PIPELINE_STEPS):
        if failed and step_id == current_stage:
            status = "failed"
        elif done:
            status = "completed"
        elif index < current_index:
            status = "completed"
        elif index == current_index:
            status = "in_progress"
        else:
            status = "pending"
        steps.append({"id": step_id, "label": label, "status": status})
    return steps


def _update_run(run_request_id: str, **updates: Any) -> None:
    with _RUNS_LOCK:
        run = _RUNS.get(run_request_id)
        if run is None:
            return
        run.update(updates)


def _launch_run(run_request_id: str, run_kwargs: dict[str, Any]) -> None:
    _update_run(
        run_request_id,
        status="running",
        current_stage="evidence_pack",
        steps=_step_state("evidence_pack", done=False, failed=False),
    )

    def _progress_hook(stage_id: str, _message: str) -> None:
        _update_run(
            run_request_id,
            current_stage=stage_id,
            steps=_step_state(stage_id, done=False, failed=False),
        )

    try:
        result = run_demo(progress_hook=_progress_hook, **run_kwargs)
        run_dir = Path(result["run_dir"])
        _update_run(
            run_request_id,
            status="completed",
            current_stage="replay_verification",
            steps=_step_state("replay_verification", done=True, failed=False),
            run_id=run_dir.name,
            run_dir=_to_posix(run_dir),
            casefile_id=result["casefile"]["casefile_id"],
            casefile=result["casefile"],
            hashes=result["casefile"]["hashes"],
            replay_command=(
                "python -m core.determinism.replay "
                f"{result['ledger_dir_rel']} --strict-manifest"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        _update_run(
            run_request_id,
            status="failed",
            error=str(exc),
            traceback=traceback.format_exc(),
            steps=_step_state("replay_verification", done=False, failed=True),
        )

def _start_run(run_kwargs: dict[str, Any], source: dict[str, str]) -> dict:
    run_request_id = _next_run_request_id()
    with _RUNS_LOCK:
        _RUNS[run_request_id] = {
            "run_request_id": run_request_id,
            "status": "queued",
            "source": source,
            "current_stage": "evidence_pack",
            "steps": _step_state("evidence_pack", done=False, failed=False),
        }
    thread = threading.Thread(
        target=_launch_run,
        args=(run_request_id, run_kwargs),
        daemon=True,
    )
    thread.start()
    return {"run_request_id": run_request_id}


def _safe_filename(name: str, index: int) -> str:
    clean = "".join(
        ch for ch in (name or f"upload_{index}.txt") if ch.isalnum() or ch in "._-"
    ).strip(".")
    if not clean:
        clean = f"upload_{index}.txt"
    if "." not in clean:
        clean = f"{clean}.txt"
    return clean


def _stage_uploads(files: list[UploadFile]) -> str:
    staged_items: list[tuple[str, bytes]] = []
    for index, upload in enumerate(files):
        filename = _safe_filename(upload.filename or "", index)
        suffix = Path(filename).suffix.lower()
        if suffix not in {".md", ".txt"}:
            raise HTTPException(status_code=400, detail="unsupported_file_type")
        raw = upload.file.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="file_not_utf8") from exc
        staged_items.append((filename, text.replace("\r\n", "\n").encode("utf-8")))

    if not staged_items:
        raise HTTPException(status_code=400, detail="no_files_uploaded")

    staged_items.sort(key=lambda item: item[0])
    preimage = json.dumps(
        [
            {
                "name": filename,
                "sha256": sha256_bytes(content),
            }
            for filename, content in staged_items
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    upload_id = sha256_bytes(preimage)
    folder = UPLOADS_DIR / upload_id
    folder.mkdir(parents=True, exist_ok=True)
    for filename, content in staged_items:
        path = folder / filename
        if path.exists():
            if path.read_bytes() != content:
                raise HTTPException(status_code=409, detail="upload_content_conflict")
        else:
            path.write_bytes(content)
    return folder.as_posix()


router = APIRouter(tags=["casefile-studio"])


@router.get("/api/health")
def api_health() -> dict:
    return {
        "status": "ok",
        "product": "Casefile Studio",
        "pipeline": [item[1] for item in PIPELINE_STEPS],
    }


@router.get("/api/fixtures")
def api_fixtures() -> dict:
    return {"items": load_fixtures()}


@router.post("/api/runs/sample")
def api_run_sample(payload: dict) -> dict:
    fixture_id = str(payload.get("fixture_id", ""))
    fixture = _fixture_by_id(fixture_id)
    run_kwargs = {
        "folder": fixture["folder"],
        "query": fixture["query"],
        "prompt": fixture["prompt"],
        "max_chunks": fixture["max_chunks"],
        "created_utc": fixture["created_utc"],
        "core_version": fixture["core_version"],
        "ruleset_id": fixture["ruleset_id"],
        "world": True,
        "verbosity": "brief",
        "show_receipts": True,
        "max_events": fixture["max_events"],
        "enrich": "",
    }
    started = _start_run(run_kwargs, source={"kind": "fixture", "id": fixture_id})
    return {**started, "fixture_id": fixture_id}


@router.post("/api/runs/upload")
def api_run_upload(
    files: list[UploadFile] = File(default=[]),
    query: str = Form(default=""),
    prompt: str = Form(default="Build a deterministic casefile for this evidence."),
    created_utc: str = Form(default="2026-03-05T00:00:00Z"),
    core_version: str = Form(default="0.4.0"),
    ruleset_id: str = Form(default="ruleset.core.v1"),
    max_chunks: int = Form(default=8),
    max_events: int = Form(default=30),
) -> dict:
    folder = _stage_uploads(files)
    run_kwargs = {
        "folder": folder,
        "query": query,
        "prompt": prompt,
        "max_chunks": max_chunks,
        "created_utc": created_utc,
        "core_version": core_version,
        "ruleset_id": ruleset_id,
        "world": True,
        "verbosity": "brief",
        "show_receipts": True,
        "max_events": max_events,
        "enrich": "",
    }
    started = _start_run(
        run_kwargs,
        source={"kind": "upload", "id": f"upload:{sha256_text(folder)}"},
    )
    return {**started, "folder": folder}


@router.get("/api/runs/{run_request_id}")
def api_run_status(run_request_id: str) -> dict:
    with _RUNS_LOCK:
        run = _RUNS.get(run_request_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run_request_not_found")
    return run


@router.get("/api/runs/{run_id}/summary")
def api_run_summary(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    casefile = workspace["casefile"]
    sealed_output = workspace["sealed_output"]
    world_narrative = (
        sealed_output.get("world_narrative_v2", {}).get("text")
        or sealed_output.get("world_narrative", {}).get("text")
        or ""
    )
    causal_narrative = sealed_output.get("causal_narrative_v2", {}).get("text", "")
    return {
        "run_id": workspace["run_id"],
        "casefile_id": casefile["casefile_id"],
        "summary": casefile["summary"],
        "hashes": casefile["hashes"],
        "ledger_dir": casefile["ledger_dir"],
        "narratives": {
            "world": world_narrative,
            "causal": causal_narrative,
        },
        "replay_command": (
            "python -m core.determinism.replay "
            f"{casefile['ledger_dir']} --strict-manifest"
        ),
    }


@router.get("/api/runs/{run_id}/timeline")
def api_run_timeline(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    world_model = workspace["world_model"]
    entities = {item["entity_id"]: item["name"] for item in world_model.get("entities", [])}
    events = sorted(world_model.get("events", []), key=_time_sort_key)
    items = []
    for event in events:
        items.append(
            {
                "event_id": event["event_id"],
                "type": event["type"],
                "time": event["time"],
                "action": event["action"],
                "objects": [
                    {"entity_id": object_id, "name": entities.get(object_id, object_id)}
                    for object_id in event.get("objects", [])
                ],
                "evidence_count": len(event.get("evidence", [])),
            }
        )
    return {"items": items}


@router.get("/api/runs/{run_id}/contradictions")
def api_run_contradictions(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    conflicts = workspace["world_model"].get("conflicts", [])
    ordered = sorted(
        conflicts,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )
    return {"items": ordered}


@router.get("/api/runs/{run_id}/unknowns")
def api_run_unknowns(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    world_unknowns = workspace["world_model"].get("unknowns", [])
    verification_unknowns = workspace["verification_result"].get("required_info", [])
    ordered_world = sorted(
        world_unknowns,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )
    ordered_required = sorted(
        verification_unknowns,
        key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
    )
    return {
        "world_unknowns": ordered_world,
        "required_info": ordered_required,
    }


@router.get("/api/runs/{run_id}/receipts")
def api_run_receipts(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    receipts = workspace["receipts"]
    return {
        "bundle_sha256": receipts.get("bundle_sha256", ""),
        "output_sha256": receipts.get("output_sha256", ""),
        "attestation_sha256": receipts.get("attestation_sha256", ""),
        "ruleset_sha256": receipts.get("ruleset_sha256", ""),
        "evidence_refs": _sorted_evidence_refs(receipts),
        "proofs": _sorted_proofs(receipts),
        "findings": _sorted_findings(receipts),
    }


@router.get("/api/runs/{run_id}/artifacts")
def api_run_artifacts(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    mapping = _artifact_map(workspace)
    items = []
    for name, path in sorted(mapping.items()):
        if path.exists():
            items.append(
                {
                    "name": name,
                    "download_url": f"/api/runs/{run_id}/artifacts/{name}",
                    "bytes": path.stat().st_size,
                }
            )
    return {"items": items}


@router.get("/api/runs/{run_id}/artifacts/{artifact_name}")
def api_download_artifact(run_id: str, artifact_name: str):
    workspace = _run_workspace(run_id)
    mapping = _artifact_map(workspace)
    path = mapping.get(artifact_name)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="artifact_not_found")
    return FileResponse(path, filename=artifact_name)


@router.post("/api/runs/{run_id}/replay-verify")
def api_replay_verify(run_id: str, payload: dict | None = None) -> dict:
    del payload
    workspace = _run_workspace(run_id)
    ledger_dir = workspace["casefile"]["ledger_dir"]
    try:
        result = verify_run(ledger_dir, strict_manifest=True)
        return {
            "status": "VERIFIED_OK",
            "ledger_dir": ledger_dir,
            "verification": result,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "VERIFIED_FAIL",
            "ledger_dir": ledger_dir,
            "error": str(exc),
        }

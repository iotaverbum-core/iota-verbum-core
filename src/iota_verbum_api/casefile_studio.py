from __future__ import annotations

import json
import os
import threading
import traceback
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.replay import verify_run
from proposal.cli_demo import run_demo

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


def _candidate_repo_roots() -> list[Path]:
    module_path = Path(__file__).resolve()
    candidates: list[Path] = []
    repo_root_hint = os.environ.get("IOTA_VERBUM_REPO_ROOT")
    if repo_root_hint:
        candidates.append(Path(repo_root_hint))
    candidates.append(Path.cwd())
    candidates.extend(module_path.parents)

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = resolved.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(resolved)
    return unique_roots


def _resolve_fixtures_path() -> tuple[Path, Path] | None:
    for repo_root in _candidate_repo_roots():
        fixtures_path = repo_root / "data" / "demo_cases" / "fixtures.json"
        if fixtures_path.exists():
            return fixtures_path, repo_root
    return None


def _normalize_fixture_list(raw: dict, repo_root: Path) -> list[dict]:
    items = raw.get("items", [])
    normalized = []
    for item in items:
        fixture = {
            "id": str(item["id"]),
            "title": str(item["title"]),
            "featured_rank": int(item.get("featured_rank", 999)),
            "category": str(item["category"]),
            "description": str(item["description"]),
            "folder": str((repo_root / str(item["folder"])).resolve().as_posix()),
            "query": str(item.get("query", "")),
            "prompt": str(item.get("prompt", "")),
            "created_utc": str(item["created_utc"]),
            "core_version": str(item["core_version"]),
            "ruleset_id": str(item["ruleset_id"]),
            "max_chunks": int(item.get("max_chunks", 8)),
            "max_events": int(item.get("max_events", 30)),
        }
        normalized.append(fixture)
    return sorted(normalized, key=lambda item: (item["featured_rank"], item["id"]))


def load_fixtures() -> list[dict]:
    resolved = _resolve_fixtures_path()
    if resolved is None:
        raise HTTPException(status_code=500, detail="fixture_registry_missing")
    fixtures_path, repo_root = resolved
    raw = json.loads(fixtures_path.read_text(encoding="utf-8"))
    return _normalize_fixture_list(raw, repo_root=repo_root)


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
    evidence_pack = _load_json(run_dir / "evidence_pack.json")
    world_model = sealed_output.get("world_model", {})
    verification = sealed_output.get("verification_result", {})
    receipts = verification.get("receipts", {})
    return {
        "run_dir": run_dir,
        "run_id": run_dir.name,
        "casefile": casefile,
        "sealed_output": sealed_output,
        "evidence_pack": evidence_pack,
        "world_model": world_model,
        "verification_result": verification,
        "receipts": receipts,
    }


def _json_sort_key(item: dict) -> str:
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def _entity_name_map(world_model: dict) -> dict[str, str]:
    return {
        str(item.get("entity_id", "")): str(item.get("name", ""))
        for item in world_model.get("entities", [])
        if item.get("entity_id")
    }


def _canonical_hypotheses(sealed_output: dict) -> list[dict]:
    payload = (
        sealed_output.get("hypothesis_competition")
        or sealed_output.get("hypotheses")
        or {}
    )
    hypotheses = payload.get("hypotheses", []) if isinstance(payload, dict) else []
    return sorted(
        hypotheses,
        key=lambda item: (
            -float(item.get("confidence_score", 0)),
            str(item.get("hypothesis_id", "")),
        ),
    )


def _adjudication_by_hypothesis_id(sealed_output: dict) -> dict[str, dict]:
    adjudication = sealed_output.get("adjudication") or {}
    ranked = adjudication.get("ranked_final_assessment", [])
    output = {}
    for item in ranked:
        hypothesis_id = str(item.get("hypothesis_id", ""))
        if hypothesis_id:
            output[hypothesis_id] = item
    return output


def _graph_payload(workspace: dict) -> dict:
    world_model = workspace["world_model"]
    entity_name_by_id = _entity_name_map(world_model)
    entities = sorted(
        world_model.get("entities", []),
        key=lambda item: str(item.get("entity_id", "")),
    )
    events = sorted(world_model.get("events", []), key=_time_sort_key)

    nodes = [
        {
            "id": entity["entity_id"],
            "kind": "entity",
            "label": entity.get("name", entity["entity_id"]),
            "entity_type": entity.get("type", "entity"),
            "unknown": False,
            "meta": entity,
        }
        for entity in entities
    ]
    for event in events:
        nodes.append(
            {
                "id": event["event_id"],
                "kind": "event",
                "label": event.get("action", event["event_id"]),
                "event_type": event.get("type", "event"),
                "time": event.get("time", {"kind": "unknown"}),
                "confidence": float(event.get("confidence", 0.0) or 0.0),
                "unknown": event.get("time", {}).get("kind") == "unknown",
                "meta": event,
            }
        )

    edges = []
    for event in events:
        event_id = event["event_id"]
        actor = event.get("actor")
        if actor:
            edges.append(
                {
                    "id": f"edge:{event_id}:actor:{actor}",
                    "source": actor,
                    "target": event_id,
                    "relation": "actor_of",
                    "confidence": float(event.get("confidence", 0.0) or 0.0),
                    "contradiction": False,
                }
            )
        for object_id in sorted(event.get("objects", [])):
            edges.append(
                {
                    "id": f"edge:{event_id}:object:{object_id}",
                    "source": event_id,
                    "target": object_id,
                    "relation": "involves",
                    "confidence": float(event.get("confidence", 0.0) or 0.0),
                    "contradiction": False,
                }
            )

    for index, conflict in enumerate(
        sorted(world_model.get("conflicts", []), key=_json_sort_key)
    ):
        ref = conflict.get("ref", {})
        for event_id in sorted(ref.get("event_ids", [])):
            entity_id = ref.get("entity_id", "")
            if event_id and entity_id:
                edges.append(
                    {
                        "id": f"edge:conflict:{index}:{event_id}:{entity_id}",
                        "source": event_id,
                        "target": entity_id,
                        "relation": "contradiction_link",
                        "confidence": 0.0,
                        "contradiction": True,
                        "reason": conflict.get("reason", ""),
                    }
                )

    facets = {
        "entity_types": sorted(
            {str(item.get("type", "entity")) for item in entities if item}
        ),
        "event_types": sorted(
            {str(item.get("type", "event")) for item in events if item}
        ),
        "relation_types": sorted({edge["relation"] for edge in edges}),
    }

    return {
        "nodes": sorted(nodes, key=lambda item: (item["kind"], item["id"])),
        "edges": sorted(edges, key=lambda item: item["id"]),
        "facets": facets,
        "entity_name_by_id": entity_name_by_id,
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


def _completed_with_replay_pending() -> list[dict]:
    steps = []
    for step_id, label in PIPELINE_STEPS:
        status = "completed"
        if step_id == "replay_verification":
            status = "pending"
        steps.append({"id": step_id, "label": label, "status": status})
    return steps


def _steps_with_replay_status(replay_status: str) -> list[dict]:
    steps = []
    for step_id, label in PIPELINE_STEPS:
        status = "completed"
        if step_id == "replay_verification":
            if replay_status == "VERIFIED_OK":
                status = "completed"
            elif replay_status == "VERIFIED_FAIL":
                status = "failed"
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
            current_stage="ledger_attestation",
            steps=_completed_with_replay_pending(),
            run_id=run_dir.name,
            run_dir=_to_posix(run_dir),
            casefile_id=result["casefile"]["casefile_id"],
            casefile=result["casefile"],
            hashes=result["casefile"]["hashes"],
            replay_status="NOT_RUN",
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


def _update_replay_state_for_run(run_id: str, replay_status: str, detail: dict) -> None:
    with _RUNS_LOCK:
        for run_request_id, run in _RUNS.items():
            if run.get("run_id") != run_id:
                continue
            _RUNS[run_request_id] = {
                **run,
                "replay_status": replay_status,
                "replay_detail": detail,
                "steps": _steps_with_replay_status(replay_status),
            }


def _tracked_run_by_run_id(run_id: str) -> dict | None:
    with _RUNS_LOCK:
        for run in _RUNS.values():
            if run.get("run_id") == run_id:
                return run
    return None


def _authoritative_replay_status(ledger_dir: str) -> tuple[str, dict]:
    try:
        verification = verify_run(ledger_dir, strict_manifest=True)
        return "VERIFIED_OK", {"verification": verification}
    except Exception as exc:  # noqa: BLE001
        return "VERIFIED_FAIL", {"error": str(exc)}


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
    pack_sha256 = workspace["evidence_pack"].get("pack_sha256", "")
    replay_status, replay_detail = _authoritative_replay_status(casefile["ledger_dir"])
    world_narrative = (
        sealed_output.get("world_narrative_v2", {}).get("text")
        or sealed_output.get("world_narrative", {}).get("text")
        or ""
    )
    causal_narrative = sealed_output.get("causal_narrative_v2", {}).get("text", "")
    return {
        "run_id": workspace["run_id"],
        "casefile_id": casefile["casefile_id"],
        "casefile": casefile,
        "summary": casefile["summary"],
        "hashes": casefile["hashes"],
        "integrity": {
            "pack_sha256": pack_sha256,
            "manifest_sha256": casefile["hashes"]["manifest_sha256"],
            "bundle_sha256": casefile["hashes"]["bundle_sha256"],
            "world_sha256": casefile["hashes"]["world_sha256"],
            "output_sha256": casefile["hashes"]["output_sha256"],
            "attestation_sha256": casefile["hashes"]["attestation_sha256"],
            "replay_status": replay_status,
            "replay_detail": replay_detail,
        },
        "ledger_dir": casefile["ledger_dir"],
        "narratives": {
            "world": world_narrative,
            "causal": causal_narrative,
        },
        "verification_scope": (
            "Verification status refers to deterministic ruleset evaluation for "
            "the target claim/world assertions; replay verification separately "
            "attests sealed artifact integrity."
        ),
        "replay_command": (
            "python -m core.determinism.replay "
            f"{casefile['ledger_dir']} --strict-manifest"
        ),
    }


@router.get("/api/runs/{run_id}/casefile")
def api_run_casefile(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    return workspace["casefile"]


@router.get("/api/runs")
def api_runs_list() -> dict:
    items = []
    if OUTPUTS_DEMO_DIR.exists():
        for run_dir in sorted(
            path for path in OUTPUTS_DEMO_DIR.iterdir() if path.is_dir()
        ):
            casefile_path = run_dir / "casefile.json"
            if not casefile_path.exists():
                continue
            casefile = _load_json(casefile_path)
            items.append(
                {
                    "run_id": run_dir.name,
                    "casefile_id": casefile.get("casefile_id", ""),
                    "created_utc": casefile.get("created_utc", ""),
                    "graph_version": casefile.get("casefile_version", "1.0"),
                }
            )
    return {"items": items}


@router.get("/api/runs/{run_id}/overview")
def api_run_overview(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    casefile = workspace["casefile"]
    summary = casefile.get("summary", {})
    sealed_output = workspace["sealed_output"]
    world_narrative = (
        sealed_output.get("world_narrative_v2", {}).get("text")
        or sealed_output.get("world_narrative", {}).get("text")
        or ""
    )
    headline = (
        world_narrative.split("\n")[0] if world_narrative else "No narrative available."
    )
    hypotheses = _canonical_hypotheses(sealed_output)
    return {
        "case_id": casefile.get("casefile_id", ""),
        "run_id": workspace["run_id"],
        "graph_version": casefile.get("casefile_version", "1.0"),
        "manifest_hash": casefile.get("hashes", {}).get("manifest_sha256", ""),
        "ledger_hash": casefile.get("hashes", {}).get("bundle_sha256", ""),
        "pipeline_status": "completed",
        "metrics": {
            "entity_count": int(summary.get("entities", 0)),
            "event_count": int(summary.get("events", 0)),
            "relation_count": int(summary.get("causal_edges", 0)),
            "unknown_count": int(summary.get("unknowns", 0)),
            "contradiction_count": int(summary.get("conflicts", 0)),
            "hypothesis_count": len(hypotheses),
            "verification_status": summary.get("verification_status", "UNKNOWN"),
        },
        "headline": headline,
        "updated_utc": casefile.get("created_utc", ""),
        "schema_versions": {
            "ruleset_id": casefile.get("ruleset_id", ""),
            "core_version": casefile.get("core_version", ""),
        },
    }


@router.get("/api/runs/{run_id}/graph")
def api_run_graph(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    payload = _graph_payload(workspace)
    return {
        "nodes": payload["nodes"],
        "edges": payload["edges"],
        "facets": payload["facets"],
    }


@router.get("/api/runs/{run_id}/nodes/{node_id}")
def api_run_node_detail(run_id: str, node_id: str) -> dict:
    workspace = _run_workspace(run_id)
    graph = _graph_payload(workspace)
    node = next((item for item in graph["nodes"] if item["id"] == node_id), None)
    if node is None:
        raise HTTPException(status_code=404, detail="node_not_found")
    linked_edges = [
        edge
        for edge in graph["edges"]
        if edge["source"] == node_id or edge["target"] == node_id
    ]
    hypotheses = _canonical_hypotheses(workspace["sealed_output"])
    related_hypotheses = [
        item
        for item in hypotheses
        if node_id in item.get("supporting_evidence", [])
        or node_id in item.get("contradicting_evidence", [])
    ]
    contradictions = [
        item
        for item in sorted(
            workspace["world_model"].get("conflicts", []), key=_json_sort_key
        )
        if node_id in item.get("ref", {}).get("event_ids", [])
        or node_id == item.get("ref", {}).get("entity_id")
    ]
    return {
        "node": node,
        "edges": sorted(linked_edges, key=lambda item: item["id"]),
        "related_hypotheses": related_hypotheses,
        "contradictions": contradictions,
    }


@router.get("/api/runs/{run_id}/hypotheses")
def api_run_hypotheses(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    sealed_output = workspace["sealed_output"]
    hypotheses = _canonical_hypotheses(sealed_output)
    adjudication = _adjudication_by_hypothesis_id(sealed_output)
    items = []
    for index, hypothesis in enumerate(hypotheses):
        hid = str(hypothesis.get("hypothesis_id", ""))
        adjudication_item = adjudication.get(hid, {})
        items.append(
            {
                "hypothesis_id": hid,
                "title": hypothesis.get("title", hid),
                "narrative_type": hypothesis.get("type", "generic"),
                "confidence_score": float(
                    hypothesis.get("confidence_score", 0.0) or 0.0
                ),
                "causal_plausibility": float(
                    hypothesis.get("causal_plausibility", 0.0) or 0.0
                ),
                "temporal_fit": float(hypothesis.get("temporal_fit", 0.0) or 0.0),
                "source_reliability": float(
                    hypothesis.get("source_reliability", 0.0) or 0.0
                ),
                "support_count": len(hypothesis.get("supporting_evidence", [])),
                "contradiction_count": len(
                    hypothesis.get("contradicting_evidence", [])
                ),
                "missing_evidence_count": len(hypothesis.get("missing_evidence", [])),
                "adjudication_status": adjudication_item.get(
                    "status", "viable" if index == 0 else "weakened"
                ),
                "rank": int(adjudication_item.get("rank", index + 1)),
                "final_score": float(
                    adjudication_item.get(
                        "final_score", hypothesis.get("confidence_score", 0.0)
                    )
                    or 0.0
                ),
                "rationale": hypothesis.get("rationale", ""),
                "supporting_evidence": sorted(
                    hypothesis.get("supporting_evidence", [])
                ),
                "contradicting_evidence": sorted(
                    hypothesis.get("contradicting_evidence", [])
                ),
                "missing_evidence": sorted(hypothesis.get("missing_evidence", [])),
            }
        )
    return {
        "items": sorted(items, key=lambda item: (item["rank"], item["hypothesis_id"]))
    }


@router.get("/api/runs/{run_id}/evidence")
def api_run_evidence(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    receipts = workspace["receipts"]
    refs = _sorted_evidence_refs(receipts)
    hypotheses = _canonical_hypotheses(workspace["sealed_output"])
    supported_by_ref = {}
    contradicted_by_ref = {}
    for hypothesis in hypotheses:
        for ref in hypothesis.get("supporting_evidence", []):
            supported_by_ref.setdefault(ref, []).append(
                hypothesis.get("hypothesis_id", "")
            )
        for ref in hypothesis.get("contradicting_evidence", []):
            contradicted_by_ref.setdefault(ref, []).append(
                hypothesis.get("hypothesis_id", "")
            )
    items = []
    for ref in refs:
        ref_id = ":".join(
            [
                ref["source_id"],
                ref["chunk_id"],
                str(ref["offset_start"]),
                str(ref["offset_end"]),
            ]
        )
        items.append(
            {
                "evidence_id": ref_id,
                "source_id": ref["source_id"],
                "chunk_id": ref["chunk_id"],
                "offset_start": ref["offset_start"],
                "offset_end": ref["offset_end"],
                "text_sha256": ref["text_sha256"],
                "supports_hypotheses": sorted(
                    supported_by_ref.get(ref["chunk_id"], [])
                ),
                "contradicts_hypotheses": sorted(
                    contradicted_by_ref.get(ref["chunk_id"], [])
                ),
            }
        )
    return {"items": items}


@router.get("/api/runs/{run_id}/narrative")
def api_run_narrative(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    sealed_output = workspace["sealed_output"]
    world_narrative = sealed_output.get("world_narrative_v2", {})
    text = world_narrative.get("text", "")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    turning_points = [line for line in lines if "turn" in line.lower()][:8]
    unresolved = [
        line for line in lines if "unknown" in line.lower() or "missing" in line.lower()
    ][:8]
    world_model = workspace["world_model"]
    principal_actors = sorted(
        {
            event.get("actor", "")
            for event in world_model.get("events", [])
            if event.get("actor")
        }
    )
    return {
        "narrative_type": "world_narrative_v2",
        "headline": lines[0] if lines else "No narrative available.",
        "sequence": lines[:20],
        "principal_actors": principal_actors,
        "turning_points": turning_points,
        "unresolved_tensions": unresolved,
        "confidence_posture": workspace["casefile"]
        .get("summary", {})
        .get("verification_status", "UNKNOWN"),
        "summary_text": text,
    }


@router.get("/api/runs/{run_id}/diff")
def api_run_diff(run_id: str, against_run_id: str = "") -> dict:
    workspace = _run_workspace(run_id)
    if not against_run_id:
        return {
            "current_run_id": run_id,
            "baseline_run_id": "",
            "available": False,
            "message": "Provide against_run_id to compute world diff.",
            "summary": {},
            "details": {},
        }
    baseline = _run_workspace(against_run_id)
    current_world = workspace["world_model"]
    baseline_world = baseline["world_model"]
    current_entities = {
        item.get("entity_id", "") for item in current_world.get("entities", [])
    }
    baseline_entities = {
        item.get("entity_id", "") for item in baseline_world.get("entities", [])
    }
    current_events = {
        item.get("event_id", "") for item in current_world.get("events", [])
    }
    baseline_events = {
        item.get("event_id", "") for item in baseline_world.get("events", [])
    }
    return {
        "current_run_id": run_id,
        "baseline_run_id": against_run_id,
        "available": True,
        "summary": {
            "new_entities": len(current_entities - baseline_entities),
            "new_events": len(current_events - baseline_events),
            "resolved_unknowns": max(
                len(baseline_world.get("unknowns", []))
                - len(current_world.get("unknowns", [])),
                0,
            ),
            "new_contradictions": max(
                len(current_world.get("conflicts", []))
                - len(baseline_world.get("conflicts", [])),
                0,
            ),
            "removed_contradictions": max(
                len(baseline_world.get("conflicts", []))
                - len(current_world.get("conflicts", [])),
                0,
            ),
        },
        "details": {
            "new_entity_ids": sorted(current_entities - baseline_entities),
            "new_event_ids": sorted(current_events - baseline_events),
            "current_unknowns": sorted(
                current_world.get("unknowns", []), key=_json_sort_key
            ),
            "current_contradictions": sorted(
                current_world.get("conflicts", []), key=_json_sort_key
            ),
        },
    }


@router.get("/api/runs/{run_id}/timeline")
def api_run_timeline(run_id: str) -> dict:
    workspace = _run_workspace(run_id)
    world_model = workspace["world_model"]
    entities = {
        item["entity_id"]: item["name"] for item in world_model.get("entities", [])
    }
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
        response = {
            "status": "VERIFIED_OK",
            "ledger_dir": ledger_dir,
            "verification": result,
        }
        _update_replay_state_for_run(run_id, "VERIFIED_OK", response)
        return response
    except Exception as exc:  # noqa: BLE001
        response = {
            "status": "VERIFIED_FAIL",
            "ledger_dir": ledger_dir,
            "error": str(exc),
        }
        _update_replay_state_for_run(run_id, "VERIFIED_FAIL", response)
        return response

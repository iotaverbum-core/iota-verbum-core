import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

import iota_verbum_api.casefile_studio as studio
from core.reasoning.verifier import RulesetResolutionError
from iota_verbum_api.app import app


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_workspace(base: Path, run_id: str) -> Path:
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    casefile = {
        "casefile_version": "1.0",
        "casefile_id": "case:" + ("1" * 64),
        "created_utc": "2026-03-05T00:00:00Z",
        "core_version": "0.4.0",
        "ruleset_id": "ruleset.core.v1",
        "query": "x",
        "prompt": "y",
        "hashes": {
            "manifest_sha256": "2" * 64,
            "bundle_sha256": "3" * 64,
            "world_sha256": "4" * 64,
            "output_sha256": "5" * 64,
            "attestation_sha256": "6" * 64,
        },
        "ledger_dir": str((run_dir / "ledger" / ("3" * 64)).as_posix()),
        "summary": {
            "entities": 1,
            "events": 2,
            "unknowns": 1,
            "conflicts": 1,
            "verification_status": "VERIFIED_NEEDS_INFO",
            "constraint_violations": 0,
            "causal_edges": 1,
        },
        "artifacts": [
            {"name": "attestation.json", "role": "sealed", "sha256": "6" * 64},
            {"name": "bundle.json", "role": "sealed", "sha256": "3" * 64},
            {"name": "output.json", "role": "sealed", "sha256": "5" * 64},
            {"name": "casefile.json", "role": "derived", "sha256": "7" * 64},
        ],
        "receipts_summary": {
            "evidence_ref_count": 1,
            "proof_count": 1,
            "finding_count": 1,
        },
    }
    sealed_output = {
        "world_model": {
            "entities": [{"entity_id": "entity:a", "name": "TOKEN"}],
            "events": [
                {
                    "event_id": "event:2",
                    "type": "Leak",
                    "time": {"kind": "unknown"},
                    "action": "Unknown leak action",
                    "objects": ["entity:a"],
                    "evidence": [],
                },
                {
                    "event_id": "event:1",
                    "type": "Config",
                    "time": {"kind": "date", "value": "2026-02-01"},
                    "action": "TOKEN environment only",
                    "objects": ["entity:a"],
                    "evidence": [
                        {
                            "source_id": "doc:1",
                            "chunk_id": "chunk:1",
                            "offset_start": 0,
                            "offset_end": 1,
                            "text_sha256": "a" * 64,
                        }
                    ],
                },
            ],
            "conflicts": [
                {
                    "kind": "state_conflict",
                    "ref": {
                        "entity_id": "entity:a",
                        "event_ids": ["event:1", "event:2"],
                        "key": "TOKEN",
                        "values": ["env-only", "never-in-repo"],
                    },
                    "reason": "TOKEN has conflicting states: env-only, never-in-repo",
                }
            ],
            "unknowns": [{"kind": "missing_actor", "ref": {"event_id": "event:1"}}],
        },
        "verification_result": {
            "required_info": [{"kind": "missing_time", "ref": {"event_id": "event:2"}}],
            "receipts": {
                "bundle_sha256": "3" * 64,
                "output_sha256": "5" * 64,
                "attestation_sha256": "6" * 64,
                "ruleset_sha256": "8" * 64,
                "evidence_refs": [
                    {
                        "source_id": "doc:1",
                        "chunk_id": "chunk:1",
                        "offset_start": 0,
                        "offset_end": 1,
                        "text_sha256": "a" * 64,
                    }
                ],
                "proofs": [{"rule": "demo"}],
                "findings": [{"code": "CYCLE_TEMPORAL_CONSTRAINT"}],
            },
        },
        "world_narrative_v2": {
            "text": (
                "World narrative text\n"
                "Turning point: scope narrowed\n"
                "Unknown actor remains"
            )
        },
        "causal_narrative_v2": {"text": "Causal narrative text"},
        "hypothesis_competition": {
            "hypotheses": [
                {
                    "hypothesis_id": "hyp:1",
                    "title": "Insider misuse",
                    "confidence_score": 0.7,
                    "supporting_evidence": ["chunk:1"],
                    "contradicting_evidence": [],
                    "missing_evidence": ["chunk:2"],
                },
                {
                    "hypothesis_id": "hyp:2",
                    "title": "External compromise",
                    "confidence_score": 0.4,
                    "supporting_evidence": [],
                    "contradicting_evidence": ["chunk:1"],
                    "missing_evidence": [],
                },
            ]
        },
        "adjudication": {
            "ranked_final_assessment": [
                {
                    "hypothesis_id": "hyp:1",
                    "rank": 1,
                    "status": "leading",
                    "final_score": 0.7,
                },
                {
                    "hypothesis_id": "hyp:2",
                    "rank": 2,
                    "status": "weakened",
                    "final_score": 0.4,
                },
            ]
        },
    }
    _write_json(run_dir / "casefile.json", casefile)
    _write_json(run_dir / "sealed_output.json", sealed_output)
    _write_json(run_dir / "world_model.json", sealed_output["world_model"])
    _write_json(run_dir / "evidence_pack.json", {"k": "v"})
    _write_json(run_dir / "evidence_bundle.json", {"k": "v"})
    _write_json(run_dir / "attestation.json", {"k": "v"})
    ledger_dir = run_dir / "ledger" / ("3" * 64)
    _write_json(ledger_dir / "bundle.json", {"k": "v"})
    _write_json(ledger_dir / "output.json", {"k": "v"})
    _write_json(ledger_dir / "attestation.json", {"k": "v"})
    return run_dir


def test_fixtures_endpoint_is_sorted_and_stable():
    with TestClient(app) as client:
        response = client.get("/api/fixtures")
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) >= 3
        expected = sorted(
            items,
            key=lambda item: (item.get("featured_rank", 999), item["id"]),
        )
        assert [item["id"] for item in items] == [item["id"] for item in expected]


def test_fixtures_endpoint_is_not_cwd_relative(monkeypatch):
    cwd_probe = Path(".repro_check") / "fixture_cwd_probe"
    cwd_probe.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(cwd_probe)
    with TestClient(app) as client:
        response = client.get("/api/fixtures")
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 3


def test_fixtures_endpoint_resolves_first_available_repo_root(
    monkeypatch, tmp_path: Path
):
    missing_root = tmp_path / "missing-root"
    missing_root.mkdir(parents=True, exist_ok=True)
    repo_root = tmp_path / "repo-root"
    fixtures_path = repo_root / "data" / "demo_cases" / "fixtures.json"
    _write_json(
        fixtures_path,
        {
            "items": [
                {
                    "id": "fixture:smoke",
                    "title": "Smoke Fixture",
                    "featured_rank": 1,
                    "category": "test",
                    "description": "Fixture discovery regression check.",
                    "folder": "data/demo_cases/timeline_breach_chain",
                    "query": "smoke",
                    "prompt": "smoke",
                    "created_utc": "2026-03-05T00:00:00Z",
                    "core_version": "0.4.0",
                    "ruleset_id": "ruleset.core.v1",
                    "max_chunks": 8,
                    "max_events": 30,
                }
            ]
        },
    )
    monkeypatch.setattr(
        studio, "_candidate_repo_roots", lambda: [missing_root, repo_root]
    )
    with TestClient(app) as client:
        response = client.get("/api/fixtures")
        assert response.status_code == 200
        items = response.json()["items"]
        assert [item["id"] for item in items] == ["fixture:smoke"]
        assert items[0]["folder"] == str(
            (repo_root / "data" / "demo_cases" / "timeline_breach_chain")
            .resolve()
            .as_posix()
        )


def test_v1_demo_returns_fixture_gallery_payload():
    with TestClient(app) as client:
        response = client.get("/v1/demo")
        assert response.status_code == 200
        payload = response.json()
        assert "fixtures" in payload
        assert "pipeline" in payload
        assert len(payload["fixtures"]) >= 3


def test_workspace_endpoints_are_available_and_ordered(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(studio, "OUTPUTS_DEMO_DIR", tmp_path)
    _seed_workspace(tmp_path, "run-alpha")

    with TestClient(app) as client:
        summary = client.get("/api/runs/run-alpha/summary")
        assert summary.status_code == 200
        assert summary.json()["casefile_id"].startswith("case:")
        assert summary.json()["casefile"]["casefile_version"] == "1.0"
        assert summary.json()["integrity"]["pack_sha256"] == ""
        assert "verification_scope" in summary.json()

        casefile = client.get("/api/runs/run-alpha/casefile")
        assert casefile.status_code == 200
        assert casefile.json()["casefile_id"].startswith("case:")

        timeline = client.get("/api/runs/run-alpha/timeline")
        assert timeline.status_code == 200
        timeline_items = timeline.json()["items"]
        assert timeline_items[0]["event_id"] == "event:1"

        contradictions = client.get("/api/runs/run-alpha/contradictions")
        assert contradictions.status_code == 200
        assert contradictions.json()["items"][0]["kind"] == "state_conflict"

        unknowns = client.get("/api/runs/run-alpha/unknowns")
        assert unknowns.status_code == 200
        assert len(unknowns.json()["world_unknowns"]) == 1
        assert len(unknowns.json()["required_info"]) == 1

        receipts = client.get("/api/runs/run-alpha/receipts")
        assert receipts.status_code == 200
        assert receipts.json()["bundle_sha256"] == "3" * 64

        artifacts = client.get("/api/runs/run-alpha/artifacts")
        assert artifacts.status_code == 200
        names = [item["name"] for item in artifacts.json()["items"]]
        assert "casefile.json" in names
        download = client.get("/api/runs/run-alpha/artifacts/casefile.json")
        assert download.status_code == 200


def test_replay_endpoint_reports_pass_and_fail(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(studio, "OUTPUTS_DEMO_DIR", tmp_path)
    _seed_workspace(tmp_path, "run-beta")
    monkeypatch.setattr(
        studio,
        "verify_run_deterministic",
        lambda *_args, **_kwargs: {
            "ok": True,
            "status": "verified_ok",
            "reason": "",
            "replay_target": "",
            "run_id": "",
            "sub_step": "completed",
            "empty_collection": "",
            "bundle_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "attestation_sha256": "c" * 64,
            "warnings": [],
        },
    )
    with TestClient(app) as client:
        passed = client.post("/api/runs/run-beta/replay-verify", json={})
        assert passed.status_code == 200
        assert passed.json()["status"] == "VERIFIED_OK"
        status = client.get("/api/runs/run-beta")
        assert status.status_code == 404

    monkeypatch.setattr(
        studio,
        "verify_run_deterministic",
        lambda *_args, **_kwargs: {
            "ok": False,
            "status": "failed_deterministically",
            "reason": "no comparable replay artifacts found",
            "replay_target": "",
            "run_id": "",
            "sub_step": "artifact_discovery",
            "empty_collection": "comparable_artifacts",
            "bundle_sha256": "",
            "output_sha256": "",
            "attestation_sha256": "",
            "warnings": [],
        },
    )
    with TestClient(app) as client:
        failed = client.post("/api/runs/run-beta/replay-verify", json={})
        assert failed.status_code == 200
        assert failed.json()["status"] == "VERIFIED_FAIL"
        assert failed.json()["error"] == "no comparable replay artifacts found"
        assert failed.json()["verification"]["status"] == "failed_deterministically"

    monkeypatch.setattr(
        studio,
        "verify_run_deterministic",
        lambda *_args, **_kwargs: {
            "ok": False,
            "status": "skipped",
            "reason": "no comparable replay artifacts found",
            "replay_target": "",
            "run_id": "",
            "sub_step": "artifact_discovery",
            "empty_collection": "comparable_artifacts",
            "bundle_sha256": "",
            "output_sha256": "",
            "attestation_sha256": "",
            "warnings": [],
        },
    )
    with TestClient(app) as client:
        skipped = client.post("/api/runs/run-beta/replay-verify", json={})
        assert skipped.status_code == 200
        assert skipped.json()["status"] == "VERIFIED_SKIPPED"
        assert skipped.json()["error"] == "no comparable replay artifacts found"


def test_sample_run_endpoint_reports_progress(monkeypatch):
    def _fake_run_demo(**_kwargs):
        return {
            "run_dir": "outputs/demo/fake-run",
            "casefile": {
                "casefile_id": "case:" + ("9" * 64),
                "hashes": {
                    "manifest_sha256": "1" * 64,
                    "bundle_sha256": "2" * 64,
                    "world_sha256": "3" * 64,
                    "output_sha256": "4" * 64,
                    "attestation_sha256": "5" * 64,
                },
            },
            "ledger_dir_rel": "outputs/demo/fake-run/ledger/" + ("2" * 64),
        }

    monkeypatch.setattr(studio, "run_demo", _fake_run_demo)
    with TestClient(app) as client:
        start = client.post(
            "/api/runs/sample",
            json={"fixture_id": "timeline_breach_chain"},
        )
        assert start.status_code == 200
        req_id = start.json()["run_request_id"]

        final = {}
        for _ in range(10):
            status = client.get(f"/api/runs/{req_id}")
            assert status.status_code == 200
            final = status.json()
            if final["status"] == "completed":
                break
            time.sleep(0.1)
        assert final["status"] == "completed"
        assert final["run_id"] == "fake-run"
        assert final["replay_status"] == "NOT_RUN"


def test_sample_run_failure_maps_empty_sequence_error(monkeypatch):
    def _failing_run_demo(**_kwargs):
        raise ValueError("min() arg is an empty sequence")

    monkeypatch.setattr(studio, "run_demo", _failing_run_demo)
    with TestClient(app) as client:
        start = client.post(
            "/api/runs/sample",
            json={"fixture_id": "timeline_breach_chain"},
        )
        assert start.status_code == 200
        req_id = start.json()["run_request_id"]

        final = {}
        for _ in range(10):
            status = client.get(f"/api/runs/{req_id}")
            assert status.status_code == 200
            final = status.json()
            if final["status"] == "failed":
                break
            time.sleep(0.1)

    assert final["status"] == "failed"
    assert "min() arg is an empty sequence" not in final["error"]
    assert "expected collection was empty" in final["error"]
    assert final["error_detail"]["raw_error"] == "min() arg is an empty sequence"


def test_sample_run_failure_maps_missing_ruleset_error(monkeypatch):
    def _failing_run_demo(**_kwargs):
        raise RulesetResolutionError(
            requested_ruleset="ruleset.core.v1",
            search_paths=["package:core.rulesets/ruleset.core.v1.json"],
            run_id="run-sample",
        )

    monkeypatch.setattr(studio, "run_demo", _failing_run_demo)
    with TestClient(app) as client:
        start = client.post(
            "/api/runs/sample",
            json={"fixture_id": "timeline_breach_chain"},
        )
        assert start.status_code == 200
        req_id = start.json()["run_request_id"]

        final = {}
        for _ in range(10):
            status = client.get(f"/api/runs/{req_id}")
            assert status.status_code == 200
            final = status.json()
            if final["status"] == "failed":
                break
            time.sleep(0.1)

    assert final["status"] == "failed"
    assert "requested ruleset 'ruleset.core.v1' was not found" in final["error"]
    assert final["error_detail"]["raw_error"].startswith(
        "ruleset 'ruleset.core.v1' could not be resolved"
    )
    assert final["error_detail"]["structured_error"]["error"] == "ruleset_not_found"


def test_investigation_endpoints(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(studio, "OUTPUTS_DEMO_DIR", tmp_path)
    _seed_workspace(tmp_path, "run-gamma")

    with TestClient(app) as client:
        runs = client.get("/api/runs")
        assert runs.status_code == 200
        assert runs.json()["items"][0]["run_id"] == "run-gamma"

        overview = client.get("/api/runs/run-gamma/overview")
        assert overview.status_code == 200
        assert overview.json()["metrics"]["hypothesis_count"] == 2

        graph = client.get("/api/runs/run-gamma/graph")
        assert graph.status_code == 200
        assert len(graph.json()["nodes"]) >= 3

        node = client.get("/api/runs/run-gamma/nodes/entity:a")
        assert node.status_code == 200

        hypotheses = client.get("/api/runs/run-gamma/hypotheses")
        assert hypotheses.status_code == 200
        assert hypotheses.json()["items"][0]["hypothesis_id"] == "hyp:1"

        evidence = client.get("/api/runs/run-gamma/evidence")
        assert evidence.status_code == 200
        assert evidence.json()["items"][0]["supports_hypotheses"] == ["hyp:1"]

        narrative = client.get("/api/runs/run-gamma/narrative")
        assert narrative.status_code == 200
        assert "turning_points" in narrative.json()

        diff = client.get("/api/runs/run-gamma/diff")
        assert diff.status_code == 200
        assert diff.json()["available"] is False

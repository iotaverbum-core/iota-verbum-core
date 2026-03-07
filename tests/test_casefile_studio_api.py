import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

import iota_verbum_api.casefile_studio as studio
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
        "world_narrative_v2": {"text": "World narrative text"},
        "causal_narrative_v2": {"text": "Causal narrative text"},
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
        "verify_run",
        lambda *_args, **_kwargs: {
            "ok": True,
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

    def _fail(*_args, **_kwargs):
        raise ValueError("manifest mismatch")

    monkeypatch.setattr(studio, "verify_run", _fail)
    with TestClient(app) as client:
        failed = client.post("/api/runs/run-beta/replay-verify", json={})
        assert failed.status_code == 200
        assert failed.json()["status"] == "VERIFIED_FAIL"


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

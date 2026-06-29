"""API tests for the Provenant decision endpoints.

Covers seal/verify/diff/export over HTTP, tenant isolation, tamper detection,
and byte-for-byte parity between the API and the deterministic ``provenant``
core.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from iota_verbum_api.app import app
from provenant.record import seal_decision, write_record

CREATED = "2026-06-28T12:00:00Z"


def _headers(api_key: str = "demo-key") -> dict[str, str]:
    return {"X-API-Key": api_key}


def _seal_payload(record_id="app-001", subject="application-001", with_reasons=True):
    return {
        "record_id": record_id,
        "created_utc": CREATED,
        "subject_ref": subject,
        "decision": {"outcome": "DENY", "score": 0.31},
        "model": {"name": "underwriter-llm", "version": "2026-05-01"},
        "evidence": [{"ref": "doc:paystub", "sha256": "a" * 64}],
        "reason_codes": (
            [{"code": "R01", "text": "DTI too high", "evidence_ref": "doc:paystub"}]
            if with_reasons
            else []
        ),
        "governance": {"adverse_action_required": True},
    }


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("PROVENANT_STORAGE_DIR", str(tmp_path / "provenant"))
    return tmp_path


def test_seal_and_verify():
    with TestClient(app) as client:
        seal = client.post("/v1/decisions", json=_seal_payload(), headers=_headers())
        assert seal.status_code == 200
        body = seal.json()
        assert body["record_sha256"] and body["content_sha256"]
        assert body["verify_url"] == "/v1/decisions/app-001/verify"

        verify = client.get(body["verify_url"], headers=_headers())
        assert verify.status_code == 200
        assert verify.json()["verified"] is True


def test_seal_flags_missing_reason_codes():
    with TestClient(app) as client:
        seal = client.post(
            "/v1/decisions",
            json=_seal_payload(with_reasons=False),
            headers=_headers(),
        )
        codes = [w["code"] for w in seal.json()["compliance_warnings"]]
        assert "ADVERSE_ACTION_NO_REASONS" in codes


def test_verify_detects_tampering(_isolated_storage):
    with TestClient(app) as client:
        client.post("/v1/decisions", json=_seal_payload(), headers=_headers())
        record_path = (
            _isolated_storage / "provenant" / "tenant-demo" / "app-001" / "record.json"
        )
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["decision"]["outcome"] = "APPROVE"
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

        verify = client.get("/v1/decisions/app-001/verify", headers=_headers())
        assert verify.status_code == 200
        assert verify.json()["verified"] is False


def test_diff_detects_regression():
    with TestClient(app) as client:
        client.post(
            "/v1/decisions",
            json=_seal_payload(record_id="v1", subject="application-77"),
            headers=_headers(),
        )
        v2 = _seal_payload(record_id="v2", subject="application-77")
        v2["decision"] = {"outcome": "APPROVE", "score": 0.62}
        v2["model"] = {"name": "underwriter-llm", "version": "2026-06-01"}
        client.post("/v1/decisions", json=v2, headers=_headers())

        diff = client.post(
            "/v1/decisions/diff",
            json={"prior_record_id": "v1", "current_record_id": "v2"},
            headers=_headers(),
        )
        assert diff.status_code == 200
        body = diff.json()
        assert body["regression"] is True
        assert body["severity"] == "high"


def test_export_summarises_records():
    with TestClient(app) as client:
        client.post(
            "/v1/decisions",
            json=_seal_payload(record_id="a", subject="application-1"),
            headers=_headers(),
        )
        client.post(
            "/v1/decisions",
            json=_seal_payload(
                record_id="b", subject="application-2", with_reasons=False
            ),
            headers=_headers(),
        )
        export = client.post(
            "/v1/exports",
            json={"generated_utc": CREATED},
            headers=_headers(),
        )
        assert export.status_code == 200
        summary = export.json()["summary"]
        assert summary["record_count"] == 2
        assert summary["adverse_action"]["coverage"] == 0.5


def test_cross_tenant_isolation():
    with TestClient(app) as client:
        client.post("/v1/decisions", json=_seal_payload(), headers=_headers("demo-key"))
        # other-key maps to tenant-other; must not see tenant-demo's record.
        verify = client.get(
            "/v1/decisions/app-001/verify", headers=_headers("other-key")
        )
        assert verify.status_code == 404


def test_invalid_record_id_rejected():
    with TestClient(app) as client:
        payload = _seal_payload(record_id="../evil")
        seal = client.post("/v1/decisions", json=payload, headers=_headers())
        assert seal.status_code == 400


def test_requires_authentication():
    with TestClient(app) as client:
        seal = client.post("/v1/decisions", json=_seal_payload())
        assert seal.status_code == 401


def test_api_matches_core_byte_for_byte(tmp_path):
    """The API seal must produce the same record bytes as the provenant core."""
    payload = _seal_payload(record_id="parity-1", subject="application-parity")
    with TestClient(app) as client:
        api = client.post("/v1/decisions", json=payload, headers=_headers()).json()

    record = seal_decision(
        record_id="parity-1",
        tenant_id="tenant-demo",  # demo-key maps to tenant-demo
        created_utc=payload["created_utc"],
        subject_ref=payload["subject_ref"],
        decision=payload["decision"],
        model=payload["model"],
        evidence=payload["evidence"],
        reason_codes=payload["reason_codes"],
        governance=payload["governance"],
    )
    core = write_record(record, tmp_path / "core")
    assert api["record_sha256"] == core["record_sha256"]
    assert api["content_sha256"] == core["content_sha256"]

from datetime import timedelta
import importlib
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

app_module = importlib.import_module("iota_verbum_api.app")
from iota_verbum_api.app import app
from iota_verbum_api.db.models import AuditLog, DocumentInput
from iota_verbum_api.db.session import new_session
from iota_verbum_api.services.pdf import ExtractionFailure
from iota_verbum_api.services.retention import enforce_retention_policy
from iota_verbum_api.utils import now_utc


def _headers(api_key: str = "demo-key") -> dict[str, str]:
    return {"X-API-Key": api_key}


def test_health_and_status_endpoints():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        payload = health.json()
        assert payload["version"] == "v0.3.0-production"
        assert payload["storage"] == "postgresql"
        assert payload["pdf_parsing"] == "active"

        status_response = client.get("/v1/status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "operational"


def test_full_json_flow_and_verify():
    text = Path("tests/fixtures/nda_fr.txt").read_text(encoding="utf-8")
    with TestClient(app) as client:
        analyse = client.post(
            "/v1/analyse",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"text": text, "domain": "nda"},
        )
        assert analyse.status_code == 200
        body = analyse.json()
        record_id = body["record_id"]
        assert body["language_detected"] == "fr"

        verify = client.get(f"/v1/verify/{record_id}", headers=_headers())
        assert verify.status_code == 200
        verify_body = verify.json()
        assert verify_body["hash_match"] is True
        assert verify_body["verified_count"] == 1
        assert any(item["event"] == "verify" for item in verify_body["record"]["audit_log"])


def test_hash_mismatch_case():
    text = Path("tests/fixtures/nda_es.txt").read_text(encoding="utf-8")
    with TestClient(app) as client:
        analyse = client.post(
            "/v1/analyse",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"text": text, "domain": "nda"},
        )
        record_id = analyse.json()["record_id"]

    with new_session() as db:
        stored = db.scalar(
            select(DocumentInput).where(DocumentInput.record_id == record_id)
        )
        stored.raw_text = "tampered text"
        db.commit()

    with TestClient(app) as client:
        verify = client.get(f"/v1/verify/{record_id}", headers=_headers())
        assert verify.status_code == 200
        assert verify.json()["hash_match"] is False


def test_auth_failure_is_logged():
    with TestClient(app) as client:
        response = client.post(
            "/v1/analyse",
            headers={"Content-Type": "application/json"},
            json={"text": "secret", "domain": "nda"},
        )
        assert response.status_code == 401

    with new_session() as db:
        failure = db.scalar(
            select(AuditLog).where(AuditLog.event_type == "auth.failure")
        )
        assert failure is not None
        assert failure.api_key_hash != ""


def test_tenant_isolation_for_audit_and_verify():
    text = Path("tests/fixtures/nda_de.txt").read_text(encoding="utf-8")
    with TestClient(app) as client:
        analyse = client.post(
            "/v1/analyse",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"text": text, "domain": "nda"},
        )
        record_id = analyse.json()["record_id"]

        forbidden = client.get(f"/v1/verify/{record_id}", headers=_headers("other-key"))
        assert forbidden.status_code == 404

        own_audit = client.get("/v1/audit", headers=_headers())
        other_audit = client.get("/v1/audit", headers=_headers("other-key"))
        assert own_audit.status_code == 200
        assert other_audit.status_code == 200
        assert all(item["record_id"] != record_id for item in other_audit.json()["items"])


def test_pdf_upload_uses_pdfplumber_path(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "extract_text_pdfplumber",
        lambda _pdf_bytes: (
            "Confidential Information means technical and business information. "
            "The recipient shall keep the information confidential. "
            "The term of this agreement is twenty four months. "
            "Exceptions apply when disclosure is required by law. "
            "The recipient must return or destroy all materials. "
            "This agreement is governed by the laws of Delaware. "
            "The parties submit to exclusive jurisdiction in Wilmington.",
            {"page_count": 1, "producer": "stub", "creation_date": "2026-01-15", "extraction_method": "pdfplumber"},
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/analyse",
            headers=_headers(),
            files={"document": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
            data={"domain": "nda"},
        )
        assert response.status_code == 200
        assert response.json()["input_format"] == "pdf"
        assert response.json()["pdf_metadata"]["extraction_method"] == "pdfplumber"


def test_pdf_upload_uses_ocr_fallback(monkeypatch):
    def _fail(_pdf_bytes):
        raise ExtractionFailure("force fallback")

    monkeypatch.setattr(app_module, "extract_text_pdfplumber", _fail)
    monkeypatch.setattr(
        app_module,
        "extract_text_ocr",
        lambda _pdf_bytes: (
            "Confidential Information includes designs and forecasts. "
            "The recipient must keep all confidential information secret. "
            "The duration of the agreement is twelve months. "
            "Exceptions exist for lawful disclosures. "
            "The recipient shall destroy all copies after use. "
            "This agreement is governed by California law. "
            "Jurisdiction lies in San Francisco.",
            {"dpi": 300, "language": "eng", "page_count": 1, "confidence_scores": {98: 7}, "extraction_method": "ocr"},
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/analyse",
            headers=_headers(),
            files={"document": ("scan.pdf", b"%PDF-1.4", "application/pdf")},
            data={"domain": "nda"},
        )
        assert response.status_code == 200
        assert response.json()["pdf_metadata"]["extraction_method"] == "ocr"


def test_retention_policy_purges_document_inputs_and_logs_event(monkeypatch):
    text = Path("tests/fixtures/nda_fr.txt").read_text(encoding="utf-8")
    with TestClient(app) as client:
        analyse = client.post(
            "/v1/analyse",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"text": text, "domain": "nda"},
        )
        record_id = analyse.json()["record_id"]

    with new_session() as db:
        document = db.scalar(
            select(DocumentInput).where(DocumentInput.record_id == record_id)
        )
        document.created_at = now_utc() - timedelta(days=400)
        db.commit()

    purged = __import__("asyncio").run(enforce_retention_policy())
    assert purged >= 1

    with new_session() as db:
        document = db.scalar(
            select(DocumentInput).where(DocumentInput.record_id == record_id)
        )
        purge_event = db.scalar(
            select(AuditLog).where(AuditLog.event_type == "retention.purge")
        )
        assert document is None
        assert purge_event is not None

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from iota_verbum_api.config import settings
from iota_verbum_api.constants import (
    API_VERSION,
    DETERMINISM_CONTRACT,
    DOMAINS_AVAILABLE,
    LANGUAGES_SUPPORTED,
    NEUROSYMBOLIC_BOUNDARY,
    VERSION,
)
from iota_verbum_api.db.migrations import run_migrations
from iota_verbum_api.db.models import AuditLog
from iota_verbum_api.db.session import get_db, new_session
from iota_verbum_api.rate_limit import InMemoryRateLimiter
from iota_verbum_api.runtime import RuntimeState
from iota_verbum_api.schemas import AnalyseJsonRequest
from iota_verbum_api.security import AuthContext, authenticate_api_key
from iota_verbum_api.services.audit import create_audit_entry
from iota_verbum_api.services.extraction import UnsupportedDomainLanguage, extract_symbolic
from iota_verbum_api.services.language import detect_language
from iota_verbum_api.services.pdf import (
    ExtractionFailure,
    clean_extracted_text,
    extract_text_ocr,
    extract_text_pdfplumber,
)
from iota_verbum_api.services.retention import retention_loop
from iota_verbum_api.services.storage import (
    append_record_audit_log,
    load_document_input,
    load_record,
    next_record_id,
    write_provenance_record,
)
from iota_verbum_api.utils import hash_sensitive, isoformat_utc, now_utc, sha256_text


rate_limiter = InMemoryRateLimiter(settings.rate_limit_per_minute)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    state = RuntimeState(started_at=now_utc())
    app.state.runtime = state
    with new_session() as db:
        db.add(
            create_audit_entry(
                event_type="system.migration",
                tenant_id=None,
                api_key_hash="",
                endpoint="/system/migration",
                method="STARTUP",
                request_id="startup-migration",
                ip_address_hash="",
                response_status=200,
                processing_time_ms=0,
                record_id=None,
                error_code=None,
                neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            )
        )
        db.add(
            create_audit_entry(
                event_type="system.startup",
                tenant_id=None,
                api_key_hash="",
                endpoint="/system/startup",
                method="STARTUP",
                request_id="startup",
                ip_address_hash="",
                response_status=200,
                processing_time_ms=0,
                record_id=None,
                error_code=None,
                neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            )
        )
        db.commit()
    state.retention_task = asyncio.create_task(retention_loop())
    try:
        yield
    finally:
        if state.retention_task:
            state.retention_task.cancel()


app = FastAPI(title="IOTA VERBUM CORE", version=VERSION, lifespan=lifespan)


@app.middleware("http")
async def audit_and_rate_limit(request: Request, call_next):
    start = time.perf_counter()
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    x_api_key = request.headers.get("x-api-key")
    tenant_id = settings.api_keys.get(x_api_key) if x_api_key else None
    api_key_hash = hash_sensitive(x_api_key)
    ip_address_hash = hash_sensitive(request.client.host if request.client else "")

    public_paths = {"/health", "/v1/status", "/docs", "/openapi.json", "/v1/demo"}
    requires_auth = request.url.path not in public_paths
    if requires_auth:
        if not x_api_key or not tenant_id:
            response = JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "authentication_failed"},
            )
            with new_session() as db:
                db.add(
                    create_audit_entry(
                        event_type="auth.failure",
                        tenant_id=None,
                        api_key_hash=api_key_hash,
                        endpoint=request.url.path,
                        method=request.method,
                        request_id=request_id,
                        ip_address_hash=ip_address_hash,
                        response_status=response.status_code,
                        processing_time_ms=int((time.perf_counter() - start) * 1000),
                        record_id=None,
                        error_code="authentication_failed",
                        neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
                    )
                )
                db.commit()
            return response
        if not rate_limiter.allow(f"{tenant_id}:{request.url.path}"):
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"error": "rate_limit_triggered"},
            )
            with new_session() as db:
                db.add(
                    create_audit_entry(
                        event_type="rate_limit.triggered",
                        tenant_id=tenant_id,
                        api_key_hash=api_key_hash,
                        endpoint=request.url.path,
                        method=request.method,
                        request_id=request_id,
                        ip_address_hash=ip_address_hash,
                        response_status=response.status_code,
                        processing_time_ms=int((time.perf_counter() - start) * 1000),
                        record_id=None,
                        error_code="rate_limit_triggered",
                        neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
                    )
                )
                db.commit()
            return response

    response = await call_next(request)

    event_type_map = {
        "/health": "api.health",
        "/v1/status": "api.health",
        "/v1/audit": "api.audit",
    }
    if request.url.path not in {"/v1/analyse"} and not request.url.path.startswith("/v1/verify/"):
        with new_session() as db:
            if tenant_id:
                db.add(
                    create_audit_entry(
                        event_type="auth.success",
                        tenant_id=tenant_id,
                        api_key_hash=api_key_hash,
                        endpoint=request.url.path,
                        method=request.method,
                        request_id=request_id,
                        ip_address_hash=ip_address_hash,
                        response_status=response.status_code,
                        processing_time_ms=int((time.perf_counter() - start) * 1000),
                        record_id=None,
                        error_code=None,
                        neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
                    )
                )
            db.add(
                create_audit_entry(
                    event_type=event_type_map.get(request.url.path, "api.request"),
                    tenant_id=tenant_id,
                    api_key_hash=api_key_hash,
                    endpoint=request.url.path,
                    method=request.method,
                    request_id=request_id,
                    ip_address_hash=ip_address_hash,
                    response_status=response.status_code,
                    processing_time_ms=int((time.perf_counter() - start) * 1000),
                    record_id=None,
                    error_code=None if response.status_code < 400 else "request_failed",
                    neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
                )
            )
            db.commit()
    return response


def _health_payload(request: Request) -> dict:
    runtime = request.app.state.runtime
    return {
        "status": "healthy",
        "version": VERSION,
        "api_version": API_VERSION,
        "neurosymbolic_boundary": NEUROSYMBOLIC_BOUNDARY,
        "determinism_contract": DETERMINISM_CONTRACT,
        "storage": "postgresql",
        "pdf_parsing": "active",
        "languages_supported": LANGUAGES_SUPPORTED,
        "domains_available": DOMAINS_AVAILABLE,
        "soc2_controls": "active",
        "uptime_seconds": int((now_utc() - runtime.started_at).total_seconds()),
        "timestamp": isoformat_utc(now_utc()),
    }


@app.get("/health")
def health(request: Request):
    return _health_payload(request)


@app.get("/v1/status")
def status_endpoint(request: Request):
    runtime = request.app.state.runtime
    components = runtime.component_status
    overall = (
        "operational"
        if all(value == "operational" for value in components.values())
        else "degraded"
    )
    return {
        "status": overall,
        "version": VERSION,
        "components": components,
        "uptime_seconds": int((now_utc() - runtime.started_at).total_seconds()),
        "last_successful_db_write": isoformat_utc(runtime.last_successful_db_write),
        "last_successful_analysis": isoformat_utc(runtime.last_successful_analysis),
    }


@app.get("/v1/demo", response_class=HTMLResponse)
def demo():
    return """
    <html><body>
    <h1>IOTA VERBUM CORE Demo</h1>
    <p>PDF and plain text supported.</p>
    <form action="/v1/analyse" method="post" enctype="multipart/form-data">
      <input type="text" name="domain" value="nda" />
      <input type="file" name="document" accept=".pdf,.txt" />
      <button type="submit">Analyse</button>
    </form>
    </body></html>
    """


async def _extract_request_payload(
    request: Request, document: UploadFile | None
) -> tuple[str, str, str, dict | None]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = AnalyseJsonRequest.model_validate(await request.json())
        return payload.domain, clean_extracted_text(payload.text), "text", None

    if document is None:
        raise HTTPException(status_code=400, detail={"error": "document_required"})

    form = await request.form()
    domain = str(form.get("domain") or "")
    raw_bytes = await document.read()
    filename = (document.filename or "").lower()
    if filename.endswith(".pdf") or document.content_type == "application/pdf":
        try:
            raw_text, metadata = extract_text_pdfplumber(raw_bytes)
        except ExtractionFailure:
            raw_text, metadata = extract_text_ocr(raw_bytes)
        return domain, clean_extracted_text(raw_text), "pdf", metadata

    return domain, clean_extracted_text(raw_bytes.decode("utf-8")), "text", None


@app.post("/v1/analyse")
async def analyse(
    request: Request,
    response: Response,
    document: UploadFile | None = File(default=None),
    auth: AuthContext = Depends(authenticate_api_key),
    db: Session = Depends(get_db),
):
    start = time.perf_counter()
    request_id = request.state.request_id
    ip_address_hash = hash_sensitive(request.client.host if request.client else "")

    try:
        domain, clean_text, input_format, pdf_metadata = await _extract_request_payload(
            request, document
        )
        language, _, language_metadata = detect_language(clean_text)
        bundle = extract_symbolic(domain, language, clean_text)
        record_id = next_record_id(sha256_text(clean_text))
        record = write_provenance_record(
            db,
            record_id=record_id,
            tenant_id=auth.tenant_id,
            domain=domain,
            language_detected=language,
            extraction_result=bundle.result,
            governance_metadata=bundle.result["governance_metadata"],
            neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            raw_text=clean_text,
            input_format=input_format,
            pdf_metadata=pdf_metadata,
            language_detection_metadata=language_metadata,
            extraction_language=bundle.extraction_language,
            rule_set_version=bundle.rule_set_version,
        )
        db.add(
            create_audit_entry(
                event_type="auth.success",
                tenant_id=auth.tenant_id,
                api_key_hash=auth.api_key_hash,
                endpoint="/v1/analyse",
                method=request.method,
                request_id=request_id,
                ip_address_hash=ip_address_hash,
                response_status=200,
                processing_time_ms=0,
                record_id=record_id,
                error_code=None,
                neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            )
        )
        db.add(
            create_audit_entry(
                event_type="storage.write",
                tenant_id=auth.tenant_id,
                api_key_hash=auth.api_key_hash,
                endpoint="/v1/analyse",
                method=request.method,
                request_id=request_id,
                ip_address_hash=ip_address_hash,
                response_status=200,
                processing_time_ms=0,
                record_id=record_id,
                error_code=None,
                neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            )
        )
        db.add(
            create_audit_entry(
                event_type="api.analyse",
                tenant_id=auth.tenant_id,
                api_key_hash=auth.api_key_hash,
                endpoint="/v1/analyse",
                method=request.method,
                request_id=request_id,
                ip_address_hash=ip_address_hash,
                response_status=200,
                processing_time_ms=int((time.perf_counter() - start) * 1000),
                record_id=record_id,
                error_code=None,
                neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
            )
        )
        db.commit()
        db.refresh(record)
    except (UnsupportedDomainLanguage, ExtractionFailure, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        raise HTTPException(
            status_code=503, detail={"error": "provenance_write_failed"}
        )

    request.app.state.runtime.last_successful_db_write = now_utc()
    request.app.state.runtime.last_successful_analysis = now_utc()
    response.status_code = 200
    return {
        "record_id": record.record_id,
        "document_hash": record.document_hash,
        "input_format": record.input_format,
        "pdf_metadata": record.pdf_metadata,
        "language_detected": record.language_detected,
        "language_detection_metadata": record.language_detection_metadata,
        "extraction_language": record.extraction_language,
        "rule_set_version": record.rule_set_version,
        "governance_metadata": record.governance_metadata,
        "neurosymbolic_boundary": record.neurosymbolic_boundary,
        "result": record.extraction_result,
    }


@app.get("/v1/verify/{record_id}")
def verify_record(
    record_id: str,
    request: Request,
    auth: AuthContext = Depends(authenticate_api_key),
    db: Session = Depends(get_db),
):
    start = time.perf_counter()
    request_id = request.state.request_id
    ip_address_hash = hash_sensitive(request.client.host if request.client else "")

    record = load_record(db, record_id, auth.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "record_not_found"})
    document_input = load_document_input(db, record_id, auth.tenant_id)
    if document_input is None:
        raise HTTPException(
            status_code=404, detail={"error": "document_input_not_found"}
        )

    recomputed_hash = sha256_text(document_input.raw_text)
    hash_match = recomputed_hash == record.document_hash
    record.verified_count += 1
    record.audit_log = append_record_audit_log(
        record.audit_log, event="verify", tenant_id=auth.tenant_id
    )
    db.add(
        create_audit_entry(
            event_type="auth.success",
            tenant_id=auth.tenant_id,
            api_key_hash=auth.api_key_hash,
            endpoint=f"/v1/verify/{record_id}",
            method=request.method,
            request_id=request_id,
            ip_address_hash=ip_address_hash,
            response_status=200,
            processing_time_ms=0,
            record_id=record_id,
            error_code=None,
            neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
        )
    )
    db.add(
        create_audit_entry(
            event_type="storage.read",
            tenant_id=auth.tenant_id,
            api_key_hash=auth.api_key_hash,
            endpoint=f"/v1/verify/{record_id}",
            method=request.method,
            request_id=request_id,
            ip_address_hash=ip_address_hash,
            response_status=200,
            processing_time_ms=0,
            record_id=record_id,
            error_code=None,
            neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
        )
    )
    db.add(
        create_audit_entry(
            event_type="api.verify",
            tenant_id=auth.tenant_id,
            api_key_hash=auth.api_key_hash,
            endpoint=f"/v1/verify/{record_id}",
            method=request.method,
            request_id=request_id,
            ip_address_hash=ip_address_hash,
            response_status=200,
            processing_time_ms=int((time.perf_counter() - start) * 1000),
            record_id=record_id,
            error_code=None,
            neurosymbolic_boundary=NEUROSYMBOLIC_BOUNDARY,
        )
    )
    db.commit()
    return {
        "record": {
            "record_id": record.record_id,
            "document_hash": record.document_hash,
            "tenant_id": record.tenant_id,
            "domain": record.domain,
            "language_detected": record.language_detected,
            "created_at": isoformat_utc(record.created_at),
            "audit_log": record.audit_log,
        },
        "hash_match": hash_match,
        "verified_count": record.verified_count,
        "governance_metadata": record.governance_metadata,
    }


@app.get("/v1/audit")
def audit_log_endpoint(
    limit: int = 50,
    offset: int = 0,
    auth: AuthContext = Depends(authenticate_api_key),
    db: Session = Depends(get_db),
):
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == auth.tenant_id)
        .order_by(AuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = db.scalars(stmt).all()
    return {
        "tenant_id": auth.tenant_id,
        "items": [
            {
                "timestamp": isoformat_utc(row.timestamp),
                "event_type": row.event_type,
                "endpoint": row.endpoint,
                "method": row.method,
                "response_status": row.response_status,
                "record_id": row.record_id,
                "error_code": row.error_code,
                "request_id": row.request_id,
            }
            for row in rows
        ],
    }

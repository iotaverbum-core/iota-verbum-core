from __future__ import annotations

from pydantic import BaseModel


class AnalyseJsonRequest(BaseModel):
    text: str
    domain: str


class CasefileGenerateRequest(BaseModel):
    folder: str
    query: str = ""
    prompt: str = ""
    max_chunks: int = 5
    max_events: int = 30
    created_utc: str
    core_version: str
    ruleset_id: str
    verbosity: str = "brief"
    show_receipts: bool = False
    enrich_path: str = ""


class CasefileVerifyRequest(BaseModel):
    ledger_dir: str
    strict_manifest: bool = True


class DecisionSealRequest(BaseModel):
    record_id: str
    created_utc: str
    subject_ref: str
    decision: dict
    model: dict
    evidence: list[dict] | None = None
    reason_codes: list[dict] | None = None
    governance: dict | None = None
    prior_record_sha256: str | None = None


class DecisionDiffRequest(BaseModel):
    prior_record_id: str
    current_record_id: str


class ExaminerPackRequest(BaseModel):
    generated_utc: str
    record_ids: list[str] | None = None

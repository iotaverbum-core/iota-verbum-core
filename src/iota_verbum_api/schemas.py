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

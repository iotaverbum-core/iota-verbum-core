from __future__ import annotations

import os
from dataclasses import dataclass


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+pysqlite:///./iota_verbum.db")
    api_keys_raw: str = os.getenv("API_KEYS", "demo-key:tenant-demo")
    retention_days_document_input: int = int(
        os.getenv("RETENTION_DAYS_DOCUMENT_INPUT", "90")
    )
    retention_days_provenance_record: int = int(
        os.getenv("RETENTION_DAYS_PROVENANCE_RECORD", "2555")
    )
    retention_days_audit_log: int = int(os.getenv("RETENTION_DAYS_AUDIT_LOG", "2555"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    @property
    def api_keys(self) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for entry in _split_csv(self.api_keys_raw):
            if ":" not in entry:
                continue
            key_name, tenant_id = entry.split(":", 1)
            pairs[key_name.strip()] = tenant_id.strip()
        return pairs


settings = Settings()


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RuntimeState:
    started_at: datetime
    last_successful_db_write: datetime | None = None
    last_successful_analysis: datetime | None = None
    retention_task: object | None = None
    component_status: dict[str, str] = field(
        default_factory=lambda: {
            "api": "operational",
            "database": "operational",
            "pdf_parsing": "operational",
            "language_detection": "operational",
        }
    )


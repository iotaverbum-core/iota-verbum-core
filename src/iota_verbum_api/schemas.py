from __future__ import annotations

from pydantic import BaseModel


class AnalyseJsonRequest(BaseModel):
    text: str
    domain: str


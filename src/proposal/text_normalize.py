from __future__ import annotations

import unicodedata


def normalize_text(s: str) -> str:
    normalized = unicodedata.normalize("NFC", s)
    return normalized.replace("\r\n", "\n").replace("\r", "\n")

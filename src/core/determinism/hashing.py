from __future__ import annotations

import hashlib
import unicodedata


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    return normalized.replace("\r\n", "\n").replace("\r", "\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(_normalize_text(text).encode("utf-8"))

from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes


def hash_artifact(obj: dict) -> str:
    return sha256_bytes(dumps_canonical(obj))

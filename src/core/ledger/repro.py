from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical


def reproducible(first: dict, second: dict) -> bool:
    return dumps_canonical(first) == dumps_canonical(second)

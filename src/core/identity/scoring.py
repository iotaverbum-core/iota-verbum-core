from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def to_confidence(hits: int, total: int) -> str:
    if total <= 0:
        return "0.000"
    score = (Decimal(hits) / Decimal(total)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    return format(score, "f")

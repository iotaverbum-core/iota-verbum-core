from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def score_ratio(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.000"
    return format(
        (Decimal(numerator) / Decimal(denominator)).quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        ),
        "f",
    )

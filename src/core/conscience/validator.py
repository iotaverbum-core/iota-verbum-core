from __future__ import annotations

import re
from typing import Any


class LLMValidator:
    def validate(
        self, llm_output: str, ground_truth: dict, strict_mode: bool = True
    ) -> dict:
        checks = {
            "invented_facts": self._check_invented_facts(llm_output, ground_truth),
            "numbers": self._check_numbers(llm_output, ground_truth),
            "forbidden_topics": self._check_forbidden_topics(llm_output, ground_truth),
            "citations": self._check_citations(llm_output, ground_truth),
        }
        passes = all(checks[name]["pass"] for name in checks)
        severity = _severity(checks, strict_mode)
        return {"passes": passes, "checks": checks, "severity": severity}

    def _check_invented_facts(self, llm_output: str, ground_truth: dict) -> dict:
        facts_map = ground_truth.get("facts_map", {})
        claims = _extract_claims(llm_output)
        invented = []
        for key, value in claims.items():
            if key not in facts_map:
                invented.append({"key": key, "value": value, "reason": "unknown_key"})
                continue
            expected = facts_map[key]
            if isinstance(expected, (int, float)) or isinstance(value, (int, float)):
                continue
            if str(expected).lower() != str(value).lower():
                invented.append({"key": key, "value": value, "expected": expected})
        return {"pass": len(invented) == 0, "invented": invented}

    def _check_numbers(self, llm_output: str, ground_truth: dict) -> dict:
        facts_map = ground_truth.get("facts_map", {})
        claims = _extract_claims(llm_output)
        mismatches = []
        for key, value in claims.items():
            if key not in facts_map:
                continue
            expected = facts_map[key]
            if not _is_number(value) or not _is_number(expected):
                continue
            if abs(float(value) - float(expected)) > 1e-6:
                mismatches.append({"key": key, "value": value, "expected": expected})
        return {"pass": len(mismatches) == 0, "mismatches": mismatches}

    def _check_forbidden_topics(self, llm_output: str, ground_truth: dict) -> dict:
        forbidden = ground_truth.get("constraints", {}).get("CANNOT_invent", [])
        violations = []
        lowered = llm_output.lower()
        for item in forbidden:
            if item and str(item).lower() in lowered:
                violations.append(item)
        return {"pass": len(violations) == 0, "violations": violations}

    def _check_citations(self, llm_output: str, ground_truth: dict) -> dict:
        required = set(ground_truth.get("constraints", {}).get("MUST_cite", []))
        cited = set(_extract_citations(llm_output))
        missing = sorted(required - cited)
        extra = sorted(cited - required)
        return {
            "pass": len(missing) == 0,
            "missing": missing,
            "extra": extra,
        }


def _extract_claims(text: str) -> dict[str, Any]:
    claims: dict[str, Any] = {}
    pattern = re.compile(
        r"(?P<key>[A-Za-z_][A-Za-z0-9_.\[\]-]*)\s*(?:=|:)\s*(?P<val>[^,\n;]+)"
    )
    for match in pattern.finditer(text):
        key = match.group("key").strip()
        raw_val = match.group("val").strip().strip('"').strip("'")
        claims[key] = _parse_value(raw_val)
    return claims


def _extract_citations(text: str) -> list[str]:
    pattern = re.compile(r"(?:evidence|cite)\s*[:#]\s*([A-Za-z0-9_-]+)", re.IGNORECASE)
    return [m.group(1) for m in pattern.finditer(text)]


def _parse_value(value: str) -> Any:
    if _is_number(value):
        return float(value) if "." in str(value) else int(float(value))
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def _is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _severity(checks: dict, strict_mode: bool) -> str:
    if all(check["pass"] for check in checks.values()):
        return "low"
    if not strict_mode:
        return "medium"
    if not checks["invented_facts"]["pass"] or not checks["numbers"]["pass"]:
        return "high"
    return "medium"

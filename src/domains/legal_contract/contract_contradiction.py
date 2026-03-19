from __future__ import annotations

import re
from collections import OrderedDict

_MODAL_PREFIXES = (
    "may ",
    "shall ",
    "must ",
    "will ",
    "agrees to ",
    "is required to ",
    "is prohibited from ",
    "grants ",
    "grant ",
    "has the right to ",
)

_PARTY_PREFIX_CONNECTORS = (
    "subject to the terms of this agreement, ",
    "subject to this agreement, ",
    "upon termination, ",
    "if applicable, ",
)

_VAGUE_TERMS = (
    "reasonable",
    "reasonably",
    "material",
    "materially",
    "promptly",
    "timely",
    "as soon as practicable",
)

_RISK_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_contract_analysis(extracted: dict) -> OrderedDict:
    contradictions = detect_contradictions(extracted)
    ambiguities = detect_ambiguities(extracted)
    risk_registry = build_risk_registry(contradictions, ambiguities)
    executive_summary = build_executive_summary(
        contradictions=contradictions,
        ambiguities=ambiguities,
        risk_registry=risk_registry,
    )

    analysis = OrderedDict()
    analysis["executive_summary"] = executive_summary
    analysis["contradictions"] = contradictions
    analysis["ambiguities"] = ambiguities
    analysis["risk_registry"] = risk_registry
    return analysis


def detect_contradictions(extracted: dict) -> list[dict]:
    rights = extracted.get("rights", [])
    prohibitions = extracted.get("prohibitions", [])
    obligations = extracted.get("obligations", [])
    contradictions: list[dict] = []

    for right in rights:
        right_action = canonical_action(right.get("action", ""))
        if not right_action:
            continue
        for prohibition in prohibitions:
            if right["party"] != prohibition["party"]:
                continue
            if right_action != canonical_action(prohibition.get("action", "")):
                continue
            contradictions.append(
                _build_contradiction(
                    contradiction_type="RIGHT_PROHIBITION",
                    left=right,
                    right=prohibition,
                    beneficiary=right["party"],
                )
            )

    for index, obligation in enumerate(obligations):
        obligation_action = canonical_action(obligation.get("action", ""))
        if not obligation_action:
            continue
        for other in obligations[index + 1 :]:
            if obligation["party"] != other["party"]:
                continue
            if obligation_action != canonical_action(other.get("action", "")):
                continue
            if obligation.get("polarity") == other.get("polarity"):
                continue
            contradictions.append(
                _build_contradiction(
                    contradiction_type="OBLIGATION_CONFLICT",
                    left=obligation,
                    right=other,
                    beneficiary=obligation["party"],
                )
            )

    contradictions.sort(
        key=lambda item: (
            item["severity"],
            item["party"],
            item["action"],
            item["left_clause_offset"],
            item["right_clause_offset"],
        )
    )
    return _dedupe_contradictions(contradictions)


def detect_ambiguities(extracted: dict) -> list[dict]:
    clauses = (
        list(extracted.get("obligations", []))
        + list(extracted.get("rights", []))
        + list(extracted.get("prohibitions", []))
    )
    ambiguities: list[dict] = []
    seen_keys: set[tuple[str, int, str]] = set()
    for clause in clauses:
        lowered = clause.get("text", "").lower()
        for term in _VAGUE_TERMS:
            pattern = rf"\b{term}\b" if " " not in term else re.escape(term)
            if not re.search(pattern, lowered):
                continue
            key = (clause.get("party", ""), clause.get("offset", -1), term)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ambiguities.append(
                {
                    "ambiguity_id": (
                        f"ambiguity:{clause.get('offset', 0)}:{term.replace(' ', '_')}"
                    ),
                    "party": clause.get("party"),
                    "term": term,
                    "text": clause.get("text"),
                    "offset": clause.get("offset"),
                    "risk_level": (
                        "medium" if term in {"material", "materially"} else "low"
                    ),
                }
            )
    ambiguities.sort(key=lambda item: (item["offset"], item["term"], item["party"]))
    return ambiguities


def build_risk_registry(
    contradictions: list[dict], ambiguities: list[dict]
) -> list[dict]:
    registry: list[dict] = []
    for index, contradiction in enumerate(contradictions, start=1):
        registry.append(
            {
                "risk_id": f"risk:{index:03d}",
                "risk_type": "contradiction",
                "severity": contradiction["severity"],
                "title": contradiction["title"],
                "party": contradiction["party"],
                "action": contradiction["action"],
                "beneficiary": contradiction["beneficiary"],
                "evidence_offsets": [
                    contradiction["left_clause_offset"],
                    contradiction["right_clause_offset"],
                ],
            }
        )

    base = len(registry)
    for index, ambiguity in enumerate(ambiguities, start=1):
        registry.append(
            {
                "risk_id": f"risk:{base + index:03d}",
                "risk_type": "ambiguity",
                "severity": ambiguity["risk_level"],
                "title": f"Ambiguous qualifier: {ambiguity['term']}",
                "party": ambiguity["party"],
                "action": None,
                "beneficiary": None,
                "evidence_offsets": [ambiguity["offset"]],
            }
        )

    registry.sort(
        key=lambda item: (
            _RISK_ORDER[item["severity"]],
            item["risk_type"],
            item["party"] or "",
            item["title"],
        )
    )
    return registry


def build_executive_summary(
    *,
    contradictions: list[dict],
    ambiguities: list[dict],
    risk_registry: list[dict],
) -> OrderedDict:
    summary = OrderedDict()
    summary["risk_score"] = min(100, len(contradictions) * 35 + len(ambiguities) * 10)
    summary["contradiction_count"] = len(contradictions)
    summary["ambiguity_count"] = len(ambiguities)
    summary["highest_severity"] = (
        risk_registry[0]["severity"] if risk_registry else "low"
    )
    summary["headline"] = _build_headline(contradictions, ambiguities)
    return summary


def normalize_action(text: str, party_name: str | None = None) -> str:
    lowered = " ".join(text.lower().split())
    for connector in _PARTY_PREFIX_CONNECTORS:
        if lowered.startswith(connector):
            lowered = lowered[len(connector) :]
            break
    if party_name:
        party_lower = party_name.lower()
        if lowered.startswith(party_lower + " "):
            lowered = lowered[len(party_lower) + 1 :]
    prefix_index = None
    prefix_value = None
    for prefix in _MODAL_PREFIXES:
        index = lowered.find(prefix)
        if index == -1:
            continue
        if prefix_index is None or index < prefix_index:
            prefix_index = index
            prefix_value = prefix
    if prefix_index is not None and prefix_value is not None:
        lowered = lowered[prefix_index + len(prefix_value) :]
    if prefix_value in {"grant ", "grants "} and " right to " in lowered:
        lowered = lowered.split(" right to ", 1)[1]
    lowered = lowered.strip(" .,;:")
    return lowered


def canonical_action(action: str) -> str:
    normalized = action.strip().lower()
    if normalized.startswith("not "):
        return normalized[4:]
    return normalized


def _build_contradiction(
    *,
    contradiction_type: str,
    left: dict,
    right: dict,
    beneficiary: str,
) -> dict:
    action = left.get("action") or right.get("action") or ""
    return {
        "contradiction_id": (
            f"contradiction:{left['offset']}:{right['offset']}:{contradiction_type.lower()}"
        ),
        "contradiction_type": contradiction_type,
        "title": _title_for(contradiction_type, left["party"], action),
        "description": (
            (
                f"{left['party']} is both permitted and restricted with "
                f"respect to '{action}'."
            )
            if contradiction_type == "RIGHT_PROHIBITION"
            else f"{left['party']} is assigned conflicting obligations for '{action}'."
        ),
        "party": left["party"],
        "beneficiary": beneficiary,
        "action": action,
        "severity": "high",
        "left_clause_text": left["text"],
        "left_clause_offset": left["offset"],
        "right_clause_text": right["text"],
        "right_clause_offset": right["offset"],
    }


def _title_for(contradiction_type: str, party: str, action: str) -> str:
    if contradiction_type == "RIGHT_PROHIBITION":
        return f"Right/prohibition conflict for {party}"
    return f"Obligation conflict for {party}: {action}"


def _build_headline(contradictions: list[dict], ambiguities: list[dict]) -> str:
    if contradictions:
        return (
            "Detected "
            f"{len(contradictions)} contradiction(s) requiring clause harmonization."
        )
    if ambiguities:
        return (
            "No direct contradictions detected; "
            f"{len(ambiguities)} ambiguity signal(s) remain."
        )
    return "No direct contradictions or ambiguity signals detected."


def _dedupe_contradictions(contradictions: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for contradiction in contradictions:
        key = (
            contradiction["contradiction_type"],
            contradiction["party"],
            contradiction["beneficiary"],
            contradiction["action"],
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(contradiction)
    return deduped

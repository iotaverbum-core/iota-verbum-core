from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationIssue:
    family: str
    ids: tuple[str, ...] = ()
    detail: str = ""

    @property
    def reason(self) -> str:
        if self.ids:
            return f"{self.family}:{','.join(self.ids)}"
        if self.detail:
            return f"{self.family}:{self.detail}"
        return self.family


@dataclass(frozen=True)
class DeltaVerificationResult:
    accepted: bool
    issues: tuple[VerificationIssue, ...]

    @property
    def reasons(self) -> list[str]:
        return [issue.reason for issue in self.issues]

    @property
    def reason_families(self) -> list[str]:
        return _unique(issue.family for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reasons": self.reasons,
            "reason_families": self.reason_families,
        }


def verify_revision_delta(
    proposal: Any,
    gold_delta: Mapping[str, Any],
) -> DeltaVerificationResult:
    payload = _as_payload(proposal)
    issues: list[VerificationIssue] = []

    required_fields = (
        ("changed_states", _gold_item_ids(gold_delta, "changed_states")),
        ("changed_edges", _gold_item_ids(gold_delta, "changed_edges")),
        ("changed_events", _gold_item_ids(gold_delta, "changed_events")),
        ("new_unknowns", _gold_item_ids(gold_delta, "new_unknowns")),
        ("resolved_unknowns", _gold_item_ids(gold_delta, "resolved_unknowns")),
    )
    for field_name, required_ids in required_fields:
        proposed_ids = _change_ids(payload.get(field_name, []))
        _append_missing_issue(
            issues,
            f"missing_{field_name}",
            required_ids - proposed_ids,
        )

    required_scenarios = _gold_scenario_ids(gold_delta)
    proposed_scenarios = _scenario_ids(payload.get("scenario_rank_changes", []))
    _append_missing_issue(
        issues,
        "missing_scenario_rank_changes",
        required_scenarios - proposed_scenarios,
    )

    touched_ids = set().union(
        *(
            _change_ids(payload.get(field_name, []))
            for field_name, _ in required_fields
        ),
        proposed_scenarios,
    )
    forbidden_revisions = _string_set(gold_delta.get("forbidden_revisions", []))
    _append_missing_issue(
        issues,
        "forbidden_revision_touched",
        forbidden_revisions & touched_ids,
    )

    required_preserved = _string_set(gold_delta.get("preserved_items", []))
    proposed_preserved = _string_set(payload.get("preserved_items", []))
    _append_missing_issue(
        issues,
        "missing_preserved_items",
        required_preserved - proposed_preserved,
    )

    expected_artifact = str(gold_delta.get("named_evidence_artifact", ""))
    proposed_artifact = str(payload.get("named_evidence_artifact", ""))
    if expected_artifact and proposed_artifact != expected_artifact:
        issues.append(
            VerificationIssue(
                family="named_evidence_artifact_mismatch",
                detail=f"{proposed_artifact}!={expected_artifact}",
            )
        )

    return DeltaVerificationResult(accepted=not issues, issues=tuple(issues))


def _as_payload(proposal: Any) -> Mapping[str, Any]:
    if isinstance(proposal, Mapping):
        return proposal
    if hasattr(proposal, "model_dump"):
        payload = proposal.model_dump(mode="json")
        if isinstance(payload, Mapping):
            return payload
    raise TypeError("proposal must be a mapping or expose model_dump(mode='json').")


def _gold_item_ids(gold_delta: Mapping[str, Any], field_name: str) -> set[str]:
    return _change_ids(gold_delta.get(field_name, []))


def _gold_scenario_ids(gold_delta: Mapping[str, Any]) -> set[str]:
    return _scenario_ids(gold_delta.get("scenario_rank_changes", []))


def _change_ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {
        str(item["id"])
        for item in items
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    }


def _scenario_ids(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {
        str(item["scenario_id"])
        for item in items
        if isinstance(item, Mapping) and isinstance(item.get("scenario_id"), str)
    }


def _string_set(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item) for item in items if isinstance(item, str)}


def _append_missing_issue(
    issues: list[VerificationIssue],
    family: str,
    ids: set[str],
) -> None:
    if ids:
        issues.append(VerificationIssue(family=family, ids=tuple(sorted(ids))))


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


__all__ = [
    "DeltaVerificationResult",
    "VerificationIssue",
    "verify_revision_delta",
]

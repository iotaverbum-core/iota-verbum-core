from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.phase3_revision_engine.types import (
    DependencyTrace,
    FailureFamily,
    FailureSymptom,
)


def _hash_obj(payload: dict[str, Any]) -> str:
    return sha256_bytes(dumps_canonical(payload))


def _sorted_tuple(values: set[str] | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value}))


def _claim_ids(graph: Mapping[str, Any]) -> tuple[str, ...]:
    ids: set[str] = set()
    for key in ("claim_ids", "prior_claim_ids", "trigger_claim_ids"):
        ids.update(str(value) for value in graph.get(key, []) if isinstance(value, str))
    for claim in graph.get("claims", []):
        if isinstance(claim, Mapping) and isinstance(claim.get("claim_id"), str):
            ids.add(claim["claim_id"])
    return _sorted_tuple(ids)


def _preserved_claim_ids(
    prior_graph: Mapping[str, Any],
    verifier_context: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    ids: set[str] = set()
    ids.update(
        str(value)
        for value in prior_graph.get("preserved_claim_ids", [])
        if isinstance(value, str)
    )
    if verifier_context is not None:
        for key in ("forbidden_revision_ids", "missing_preserved_ids"):
            ids.update(
                str(value)
                for value in verifier_context.get(key, [])
                if isinstance(value, str)
            )
    return _sorted_tuple(ids)


def _trigger_claim_ids(trigger_graph: Mapping[str, Any]) -> tuple[str, ...]:
    return _claim_ids(trigger_graph)


def _evidence_ids(graph: Mapping[str, Any]) -> tuple[str, ...]:
    ids: set[str] = set()
    ids.update(str(value) for value in graph.get("evidence_ids", []) if value)
    for edge in graph.get("support_edges", []):
        if isinstance(edge, Mapping):
            source_id = edge.get("from_id") or edge.get("source_id")
            if isinstance(source_id, str):
                ids.add(source_id)
            continue
        if isinstance(edge, Sequence) and not isinstance(edge, str) and edge:
            first = edge[0]
            if isinstance(first, str):
                ids.add(first)
    for claim in graph.get("claims", []):
        if not isinstance(claim, Mapping):
            continue
        for grounding in claim.get("groundings", []):
            if isinstance(grounding, Mapping):
                grounding_id = grounding.get("grounding_id")
                if isinstance(grounding_id, str):
                    ids.add(grounding_id)
        for evidence in claim.get("evidence", []):
            if isinstance(evidence, Mapping):
                source_id = evidence.get("source_id")
                if isinstance(source_id, str):
                    ids.add(source_id)
    return _sorted_tuple(ids)


def _claim_grounding_ids(
    *,
    target_claim_id: str | None,
    trigger_graph: Mapping[str, Any],
) -> tuple[str, ...]:
    if target_claim_id is None:
        return ()

    ids: set[str] = set()
    for edge in trigger_graph.get("support_edges", []):
        if isinstance(edge, Mapping):
            edge_type = str(edge.get("type") or edge.get("edge_type") or "")
            to_id = edge.get("to_id") or edge.get("target_id")
            from_id = edge.get("from_id") or edge.get("source_id")
            if to_id == target_claim_id and edge_type in {"grounds", "supports"}:
                if isinstance(from_id, str):
                    ids.add(from_id)
        elif isinstance(edge, Sequence) and not isinstance(edge, str):
            if len(edge) >= 3 and edge[1] == target_claim_id:
                if edge[2] in {"grounds", "supports"} and isinstance(edge[0], str):
                    ids.add(edge[0])

    for claim in trigger_graph.get("claims", []):
        if not isinstance(claim, Mapping) or claim.get("claim_id") != target_claim_id:
            continue
        for grounding in claim.get("groundings", []):
            if isinstance(grounding, Mapping):
                grounding_id = grounding.get("grounding_id")
                if isinstance(grounding_id, str):
                    ids.add(grounding_id)
        for evidence in claim.get("evidence", []):
            if isinstance(evidence, Mapping):
                source_id = evidence.get("source_id")
                if isinstance(source_id, str):
                    ids.add(source_id)

    return _sorted_tuple(ids)


def _operation_id(operation: Mapping[str, Any], symptom: FailureSymptom) -> str:
    return str(
        operation.get("target_operation_id")
        or operation.get("operation_id")
        or symptom.candidate_id
    )


def _operation_claim_id(operation: Mapping[str, Any]) -> str | None:
    for key in ("target_claim_id", "target_prior_claim_id", "source_trigger_claim_id"):
        value = operation.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _grounding_target_claim_id(
    operation: Mapping[str, Any],
    trigger_graph: Mapping[str, Any],
) -> str | None:
    source_trigger_claim_id = operation.get("source_trigger_claim_id")
    if isinstance(source_trigger_claim_id, str) and source_trigger_claim_id:
        return source_trigger_claim_id

    trigger_ids = _trigger_claim_ids(trigger_graph)
    operation_target = _operation_claim_id(operation)
    if operation_target in trigger_ids:
        return operation_target
    if len(trigger_ids) == 1:
        return trigger_ids[0]
    return operation_target


def trace_dependency(
    *,
    family: FailureFamily,
    symptom: FailureSymptom,
    prior_graph: Mapping[str, Any],
    trigger_graph: Mapping[str, Any],
    operation: Mapping[str, Any],
    verifier_context: Mapping[str, Any] | None = None,
) -> DependencyTrace:
    prior_claim_ids = _claim_ids(prior_graph)
    trigger_claim_ids = _trigger_claim_ids(trigger_graph)
    checked_evidence_ids = _evidence_ids(trigger_graph)
    preservation_constraints = _preserved_claim_ids(prior_graph, verifier_context)
    target_operation_id = _operation_id(operation, symptom)

    target_claim_id: str | None = None
    grounding_evidence_ids: tuple[str, ...] = ()
    halt_reason: str | None = None

    graph_claim_ids = set(prior_claim_ids).union(trigger_claim_ids)
    if family is FailureFamily.SCHEMA_VIOLATION:
        target_claim_id = None
    elif family is FailureFamily.GROUNDING_GAP:
        target_claim_id = _grounding_target_claim_id(operation, trigger_graph)
        grounding_evidence_ids = _claim_grounding_ids(
            target_claim_id=target_claim_id,
            trigger_graph=trigger_graph,
        )
        if not grounding_evidence_ids:
            halt_reason = "ungroundable_repair"
    elif family is FailureFamily.PRESERVATION_BREACH:
        target_claim_id = _operation_claim_id(operation)
        if symptom.code == "forbidden_revision_touched":
            if target_claim_id not in set(preservation_constraints):
                halt_reason = "ambiguous_dependency_trace"
        elif not preservation_constraints:
            halt_reason = "ambiguous_dependency_trace"
    else:
        target_claim_id = _operation_claim_id(operation)
        if target_claim_id is not None and target_claim_id not in graph_claim_ids:
            halt_reason = "ambiguous_dependency_trace"

    trace_preimage = {
        "family": family.value,
        "source_rejection_id": symptom.source_rejection_id,
        "target_operation_id": target_operation_id,
        "target_claim_id": target_claim_id,
        "grounding_evidence_ids": list(grounding_evidence_ids),
        "preservation_constraints": list(preservation_constraints),
        "halt_reason": halt_reason,
        "checked_prior_claim_ids": list(prior_claim_ids),
        "checked_trigger_claim_ids": list(trigger_claim_ids),
        "checked_evidence_ids": list(checked_evidence_ids),
    }
    return DependencyTrace(
        trace_id="phase3-diagnostic-trace:" + _hash_obj(trace_preimage),
        family=family,
        source_rejection_id=symptom.source_rejection_id,
        target_operation_id=target_operation_id,
        target_claim_id=target_claim_id,
        grounding_evidence_ids=grounding_evidence_ids,
        preservation_constraints=preservation_constraints,
        halt_reason=halt_reason,
        checked_prior_claim_ids=prior_claim_ids,
        checked_trigger_claim_ids=trigger_claim_ids,
        checked_evidence_ids=checked_evidence_ids,
    )


__all__ = ["trace_dependency"]

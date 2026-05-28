from __future__ import annotations

import inspect
import json
import re
import textwrap
from dataclasses import asdict, dataclass
from typing import Any, Mapping


SYSTEM_PROMPT = (
    "You are a deterministic evidence-revision analyst. "
    "Evidence packs may be rendered as legal memoranda, incident digests, "
    "board updates, operations briefs, procurement memos, or compliance memoranda. "
    "Treat those surface differences as formatting only. "
    "Use only claims and artifact IDs present in the packs. "
    "Revise only what changed. "
    "Preserve stable sibling branches unless new contrary evidence is introduced. "
    "Track newly created unknowns explicitly. "
    "Never invent evidence citations."
)

RUN2_SCHEMA_INSTRUCTIONS = """\
Return exactly one JSON object. Your first character must be { and your last character must be }.
Do not wrap it in markdown. Do not add commentary. Do not emit labels like ANALYST_SNAPSHOT. Do not place any text before or after the JSON object.
Copy the schema keys exactly as shown. Do not add keys, remove keys, rename keys, or change list fields into scalars.
Use only IDs, claim labels, and evidence artifacts present in the perturbed pack.
For q1_delta_detection, q2_revision, and q3_unknown_ledger id arrays, use canonical ids only from the CANONICAL ID REFERENCE.
For q2_revision, preserve_ids, weaken_ids, strengthen_ids, retract_ids, and forbidden_revision_ack must contain only allowed state:/event:/edge:/scenario:/unknown: ids; never use natural-language claim text, evidence:* ids, or surface artifact labels.
If a claim becomes contested, uncertain, qualified, withdrawn, delayed, demoted, or source-impaired, place its canonical id in weaken_ids or retract_ids, not strengthen_ids.
Never place the same id in both weaken_ids and strengthen_ids.
For "citations", every key must be an allowed id and every value must be a list of evidence:* ids only.
For citations, every value must use JSON array syntax even when it contains only one evidence id.
If a citations entry would be malformed, omit that entry instead of emitting a string, object, null, or prose.
Never use artifact labels like TC-227, RL-102, CW-512, FL-902, ER-610, or ED-611 inside citations.
Never use state:/event:/edge:/scenario:/unknown: ids inside citation values; those ids are valid only as citation keys.
If you cite a scenario, cite its supporting evidence ids instead of scenario basis ids.
Never copy placeholder tokens like id, another_id, or artifact_or_evidence_id. If a citations entry is unnecessary, omit it.
An empty citations object {} is valid only when no citations are needed.

Required JSON schema:
{
  "q1_delta_detection": {
    "summary": "string",
    "changed_state_ids": ["state:..."],
    "changed_event_ids": ["event:..."],
    "changed_edge_ids": ["edge:..."],
    "changed_scenario_ids": ["scenario:..."]
  },
  "q2_revision": {
    "preserve_ids": ["state:..."],
    "weaken_ids": ["state:..."],
    "strengthen_ids": ["state:..."],
    "retract_ids": ["state:..."],
    "newly_relevant_unknown_ids": ["unknown:..."],
    "forbidden_revision_ack": ["state:..."]
  },
  "q3_unknown_ledger": {
    "resolved_unknown_ids": ["unknown:..."],
    "still_open_unknown_ids": ["unknown:..."],
    "new_unknown_ids": ["unknown:..."],
    "category_map": {"unknown:id": "resolved|still_open|new"},
    "summary": "string"
  },
  "citations": {},
  "self_check": {
    "no_global_rewrite_claimed": true,
    "max_hop_claimed": 0,
    "low_confidence_ids": ["id"]
  }
}
"""

REQUIRED_TOP_KEYS = (
    "q1_delta_detection",
    "q2_revision",
    "q3_unknown_ledger",
    "citations",
    "self_check",
)
REQUIRED_Q1_KEYS = (
    "summary",
    "changed_state_ids",
    "changed_event_ids",
    "changed_edge_ids",
    "changed_scenario_ids",
)
REQUIRED_Q2_KEYS = (
    "preserve_ids",
    "weaken_ids",
    "strengthen_ids",
    "retract_ids",
    "newly_relevant_unknown_ids",
    "forbidden_revision_ack",
)
REQUIRED_Q3_KEYS = (
    "resolved_unknown_ids",
    "still_open_unknown_ids",
    "new_unknown_ids",
    "category_map",
    "summary",
)
REQUIRED_SELF_CHECK_KEYS = (
    "no_global_rewrite_claimed",
    "max_hop_claimed",
    "low_confidence_ids",
)


@dataclass(frozen=True)
class PriorAnchorDiagnostics:
    run2a_citation_key_count: int
    run2b_citation_key_count: int
    citation_key_delta: int
    run2a_obligation_coverage: float
    run2b_obligation_coverage: float
    citation_coverage_delta: float
    prior_anchor_suspected: bool


def normalize_jsonish(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    if start < 0:
        raise ValueError("No JSON object found in response")
    candidate = text[start:]
    decoder = json.JSONDecoder()
    try:
        obj, end = decoder.raw_decode(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON object: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("Top-level JSON value is not an object")
    trailing = candidate[end:].strip()
    if trailing:
        raise ValueError("Trailing text found outside top-level JSON object")
    return obj


def is_list_of_str(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def validate_response_shape(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["top_level_not_object"]
    if set(data.keys()) != set(REQUIRED_TOP_KEYS):
        errors.append("top_level_keys_mismatch")
    q1 = data.get("q1_delta_detection", {})
    q2 = data.get("q2_revision", {})
    q3 = data.get("q3_unknown_ledger", {})
    sc = data.get("self_check", {})
    citations = data.get("citations", {})
    if set(q1.keys()) != set(REQUIRED_Q1_KEYS):
        errors.append("q1_keys_mismatch")
    if set(q2.keys()) != set(REQUIRED_Q2_KEYS):
        errors.append("q2_keys_mismatch")
    if set(q3.keys()) != set(REQUIRED_Q3_KEYS):
        errors.append("q3_keys_mismatch")
    if set(sc.keys()) != set(REQUIRED_SELF_CHECK_KEYS):
        errors.append("self_check_keys_mismatch")
    for field in ("changed_state_ids", "changed_event_ids", "changed_edge_ids", "changed_scenario_ids"):
        if field in q1 and not is_list_of_str(q1[field]):
            errors.append(f"q1.{field}_not_list_of_str")
    for field in (
        "preserve_ids",
        "weaken_ids",
        "strengthen_ids",
        "retract_ids",
        "newly_relevant_unknown_ids",
        "forbidden_revision_ack",
    ):
        if field in q2 and not is_list_of_str(q2[field]):
            errors.append(f"q2.{field}_not_list_of_str")
    for field in ("resolved_unknown_ids", "still_open_unknown_ids", "new_unknown_ids"):
        if field in q3 and not is_list_of_str(q3[field]):
            errors.append(f"q3.{field}_not_list_of_str")
    if "category_map" in q3 and not isinstance(q3["category_map"], dict):
        errors.append("q3.category_map_not_object")
    if "summary" in q1 and not isinstance(q1["summary"], str):
        errors.append("q1.summary_not_string")
    if "summary" in q3 and not isinstance(q3["summary"], str):
        errors.append("q3.summary_not_string")
    if not isinstance(citations, dict):
        errors.append("citations_not_object")
    else:
        for key, value in citations.items():
            if not isinstance(key, str) or not is_list_of_str(value):
                errors.append("citations_invalid_entry")
                break
    if "no_global_rewrite_claimed" in sc and not isinstance(sc["no_global_rewrite_claimed"], bool):
        errors.append("self_check.no_global_rewrite_claimed_not_bool")
    if "max_hop_claimed" in sc and not isinstance(sc["max_hop_claimed"], int):
        errors.append("self_check.max_hop_claimed_not_int")
    if "low_confidence_ids" in sc and not is_list_of_str(sc["low_confidence_ids"]):
        errors.append("self_check.low_confidence_ids_not_list_of_str")
    return errors


def collect_valid_ids(*packs: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    valid_ids: set[str] = set()
    evidence_ids: set[str] = set()
    for pack in packs:
        sections = pack.get("sections", {})
        if not isinstance(sections, Mapping):
            continue
        for section_name, items in sections.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                for key, value in item.items():
                    if key.endswith("_id") and isinstance(value, str):
                        valid_ids.add(value)
                if section_name == "evidence" and isinstance(item.get("evidence_id"), str):
                    evidence_ids.add(item["evidence_id"])
    return valid_ids, evidence_ids


def expected_values(expected_delta: Mapping[str, Any], field_name: str) -> set[str]:
    mapping = {
        "changed_state_ids": {item["id"] for item in expected_delta.get("changed_states", [])},
        "changed_event_ids": {item["id"] for item in expected_delta.get("changed_events", [])},
        "changed_edge_ids": {item["id"] for item in expected_delta.get("changed_edges", [])},
        "changed_scenario_ids": {
            item["scenario_id"]
            for item in expected_delta.get("scenario_rank_changes", [])
            if isinstance(item, dict) and item.get("scenario_id")
        },
        "newly_relevant_unknown_ids": {item["id"] for item in expected_delta.get("new_unknowns", [])},
        "new_unknown_ids": {item["id"] for item in expected_delta.get("new_unknowns", [])},
        "resolved_unknown_ids": {item["id"] for item in expected_delta.get("resolved_unknowns", [])},
        "forbidden_revision_ack": set(expected_delta.get("forbidden_revisions", [])),
    }
    return mapping.get(field_name, set())


def set_f1(pred: Any, gold: Any) -> float:
    pred_set = set(pred)
    gold_set = set(gold)
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0
    true_positive = len(pred_set & gold_set)
    precision = true_positive / len(pred_set) if pred_set else 0.0
    recall = true_positive / len(gold_set) if gold_set else 0.0
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def set_accuracy(pred: Any, gold: Any) -> float:
    pred_set = set(pred)
    gold_set = set(gold)
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set:
        return 0.0
    return len(pred_set & gold_set) / len(pred_set)


def citation_coverage(
    response: Mapping[str, Any],
    expected_delta: Mapping[str, Any],
    valid_evidence_ids: set[str],
) -> float:
    citations = response.get("citations", {})
    if not isinstance(citations, Mapping):
        return 0.0
    support_map = expected_delta.get("supporting_evidence_map", {})
    target_ids: set[str] = set()
    target_ids |= {item["id"] for item in expected_delta.get("changed_states", [])}
    target_ids |= {item["id"] for item in expected_delta.get("changed_events", [])}
    target_ids |= {item["id"] for item in expected_delta.get("changed_edges", [])}
    target_ids |= {item["id"] for item in expected_delta.get("new_unknowns", [])}
    target_ids |= {item["id"] for item in expected_delta.get("resolved_unknowns", [])}
    if not target_ids:
        return 1.0
    covered = 0
    for item_id in target_ids:
        cited = citations.get(item_id, [])
        if not isinstance(cited, list):
            continue
        cited_ids = [
            value for value in cited if isinstance(value, str) and value in valid_evidence_ids
        ]
        if not cited_ids:
            continue
        expected_evidence = set(support_map.get(item_id, []))
        if not expected_evidence or expected_evidence.intersection(cited_ids):
            covered += 1
    return covered / len(target_ids)


def score_structured_response(
    response_text: Any,
    expected_delta_json: Any,
    scoring_manifest_json: Any,
    clean_pack_json: Any,
    perturbed_pack_json: Any,
) -> dict[str, Any]:
    hard_fail_reasons: list[str] = []
    parse_ok = True
    try:
        response = extract_json_object(str(response_text))
    except Exception:
        parse_ok = False
        response = {}
        hard_fail_reasons.append("invalid_json")

    schema_errors = [] if parse_ok else ["invalid_json"]
    if parse_ok:
        schema_errors = validate_response_shape(response)
        if schema_errors:
            hard_fail_reasons.append("response_schema_violation")

    expected_delta = normalize_jsonish(expected_delta_json)
    scoring_manifest = normalize_jsonish(scoring_manifest_json)
    clean_pack = normalize_jsonish(clean_pack_json)
    perturbed_pack = normalize_jsonish(perturbed_pack_json)
    valid_ids, valid_evidence_ids = collect_valid_ids(clean_pack, perturbed_pack)

    predicted_ids: set[str] = set()
    if isinstance(response, dict):
        for bucket in (
            response.get("q1_delta_detection", {}),
            response.get("q2_revision", {}),
            response.get("q3_unknown_ledger", {}),
        ):
            if not isinstance(bucket, dict):
                continue
            for value in bucket.values():
                if isinstance(value, list):
                    predicted_ids.update(item for item in value if isinstance(item, str))
                elif isinstance(value, dict):
                    predicted_ids.update(key for key in value if isinstance(key, str))
    if any(item_id not in valid_ids for item_id in predicted_ids):
        hard_fail_reasons.append("fabricated_ids")

    citations = response.get("citations", {}) if isinstance(response, dict) else {}
    cited_evidence = {
        evidence_id
        for values in citations.values()
        if isinstance(values, list)
        for evidence_id in values
        if isinstance(evidence_id, str)
    }
    if any(evidence_id not in valid_evidence_ids for evidence_id in cited_evidence):
        hard_fail_reasons.append("fabricated_evidence_ids")

    q2 = response.get("q2_revision", {}) if isinstance(response, dict) else {}
    preserve_ids = set(q2.get("preserve_ids", [])) if isinstance(q2, dict) else set()
    retract_ids = set(q2.get("retract_ids", [])) if isinstance(q2, dict) else set()
    if preserve_ids & retract_ids:
        hard_fail_reasons.append("preserve_and_retract_same_id")

    q1 = response.get("q1_delta_detection", {}) if isinstance(response, dict) else {}
    q3 = response.get("q3_unknown_ledger", {}) if isinstance(response, dict) else {}

    metric_scores = {
        "changed_states": 1.0
        if set(q1.get("changed_state_ids", [])) == expected_values(expected_delta, "changed_state_ids")
        else 0.0,
        "changed_events": 1.0
        if set(q1.get("changed_event_ids", [])) == expected_values(expected_delta, "changed_event_ids")
        else 0.0,
        "changed_edges": set_f1(
            q1.get("changed_edge_ids", []),
            expected_values(expected_delta, "changed_edge_ids"),
        ),
        "changed_scenarios": 1.0
        if set(q1.get("changed_scenario_ids", []))
        == expected_values(expected_delta, "changed_scenario_ids")
        else 0.0,
        "new_unknowns_q2": set_f1(
            q2.get("newly_relevant_unknown_ids", []),
            expected_values(expected_delta, "newly_relevant_unknown_ids"),
        ),
        "new_unknowns_q3": set_f1(
            q3.get("new_unknown_ids", []),
            expected_values(expected_delta, "new_unknown_ids"),
        ),
        "resolved_unknowns_q3": set_f1(
            q3.get("resolved_unknown_ids", []),
            expected_values(expected_delta, "resolved_unknown_ids"),
        ),
        "forbidden_revision_ack": set_accuracy(
            q2.get("forbidden_revision_ack", []),
            expected_values(expected_delta, "forbidden_revision_ack"),
        ),
    }

    axis_scores = {
        "delta_detection": round(
            (metric_scores["changed_states"] + metric_scores["changed_events"]) / 2,
            6,
        ),
        "causal_temporal_propagation": round(
            (metric_scores["changed_edges"] + metric_scores["changed_scenarios"]) / 2,
            6,
        ),
        "selective_revision": round(
            (metric_scores["new_unknowns_q2"] + metric_scores["forbidden_revision_ack"]) / 2,
            6,
        ),
        "unknown_ledger_discipline": round(
            (metric_scores["new_unknowns_q3"] + metric_scores["resolved_unknowns_q3"]) / 2,
            6,
        ),
        "evidence_grounding": round(
            citation_coverage(response, expected_delta, valid_evidence_ids),
            6,
        ),
    }

    penalty_collateral = 0.0
    forbidden = set(expected_delta.get("forbidden_revisions", []))
    if retract_ids:
        penalty_collateral = len(retract_ids & forbidden) / max(len(retract_ids), 1)
    gold_new_unknowns = expected_values(expected_delta, "new_unknown_ids")
    pred_new_unknowns = set(q3.get("new_unknown_ids", [])) if isinstance(q3, dict) else set()
    penalty_missed_second_order = (
        (len(gold_new_unknowns - pred_new_unknowns) / len(gold_new_unknowns))
        if gold_new_unknowns
        else 0.0
    )

    weights = scoring_manifest.get("weights", {})
    weighted_total = 0.0
    total_weight = 0.0
    for axis, score in axis_scores.items():
        weight = float(weights.get(axis, 0.0))
        weighted_total += score * weight
        total_weight += weight
    overall = weighted_total / total_weight if total_weight else 0.0
    overall = max(
        0.0,
        overall - 0.75 * penalty_collateral - 0.75 * penalty_missed_second_order,
    )

    pass_rule = scoring_manifest.get("operational_pass_rule", {})
    overall_pass = (
        not hard_fail_reasons
        and overall >= float(pass_rule.get("overall_min", 0.72))
        and axis_scores["delta_detection"] >= float(pass_rule.get("delta_detection_min", 0.5))
        and axis_scores["evidence_grounding"] >= float(pass_rule.get("citation_coverage_min", 0.5))
    )

    return {
        "parse_ok": parse_ok,
        "schema_ok": not schema_errors,
        "schema_errors": schema_errors,
        "hard_fail_reasons": sorted(set(hard_fail_reasons)),
        "metric_scores": {key: round(value, 6) for key, value in metric_scores.items()},
        "axis_scores": axis_scores,
        "overall_score": round(overall, 6),
        "overall_pass": overall_pass,
    }


def get_citation_keys(parsed_response: Mapping[str, Any]) -> set[str]:
    citations = parsed_response.get("citations", {})
    if not isinstance(citations, Mapping):
        return set()
    return {str(key) for key in citations}


def score_citation_obligation_coverage(
    parsed_response: Mapping[str, Any],
    citation_obligation_map: Mapping[str, str],
) -> float:
    if not citation_obligation_map:
        return 1.0
    citations = parsed_response.get("citations", {})
    if not isinstance(citations, Mapping):
        return 0.0
    hits = 0
    obligations = 0
    for node_id, required_evidence_id in citation_obligation_map.items():
        obligations += 1
        node_citations = citations.get(node_id, [])
        if not isinstance(node_citations, list):
            continue
        if required_evidence_id in node_citations:
            hits += 1
    return hits / obligations if obligations else 1.0


def compute_prior_anchor_diagnostics(
    run2a_parsed: Mapping[str, Any],
    run2b_parsed: Mapping[str, Any],
    citation_obligation_map: Mapping[str, str],
    *,
    citation_key_threshold: int = 2,
    citation_coverage_threshold: float = 0.15,
) -> PriorAnchorDiagnostics:
    run2a_keys = get_citation_keys(run2a_parsed)
    run2b_keys = get_citation_keys(run2b_parsed)
    run2a_coverage = score_citation_obligation_coverage(
        run2a_parsed,
        citation_obligation_map,
    )
    run2b_coverage = score_citation_obligation_coverage(
        run2b_parsed,
        citation_obligation_map,
    )
    citation_key_delta = len(run2b_keys) - len(run2a_keys)
    citation_coverage_delta = run2b_coverage - run2a_coverage
    prior_anchor_suspected = (
        citation_key_delta >= citation_key_threshold
        or citation_coverage_delta >= citation_coverage_threshold
    )
    return PriorAnchorDiagnostics(
        run2a_citation_key_count=len(run2a_keys),
        run2b_citation_key_count=len(run2b_keys),
        citation_key_delta=citation_key_delta,
        run2a_obligation_coverage=run2a_coverage,
        run2b_obligation_coverage=run2b_coverage,
        citation_coverage_delta=citation_coverage_delta,
        prior_anchor_suspected=prior_anchor_suspected,
    )


def diagnostics_to_dict(diagnostics: PriorAnchorDiagnostics) -> dict[str, Any]:
    return asdict(diagnostics)


def _section_items(pack: Mapping[str, Any], section_name: str) -> list[dict[str, Any]]:
    sections = pack.get("sections", {})
    if not isinstance(sections, Mapping):
        return []
    items = sections.get(section_name, [])
    return items if isinstance(items, list) else []


def _sorted_ids(items: list[dict[str, Any]], key_name: str) -> list[str]:
    return sorted(item[key_name] for item in items if item.get(key_name))


def _changed_ids(items: list[dict[str, Any]], key_name: str = "id") -> list[str]:
    return sorted(
        item[key_name]
        for item in items
        if isinstance(item, dict) and item.get(key_name)
    )


def _csv(values: Any) -> str:
    value_list = list(values)
    return ", ".join(value_list) if value_list else "(none)"


def _reference_lines(
    items: list[dict[str, Any]],
    item_id_key: str,
    fields: list[str],
) -> list[str]:
    lines: list[str] = []
    for item in sorted(items, key=lambda value: value.get(item_id_key, "")):
        item_id = item.get(item_id_key)
        if not item_id:
            continue
        fragments = [
            f"{field}:{_csv(item.get(field, [])) if isinstance(item.get(field), list) else item.get(field)}"
            for field in fields
            if item.get(field) not in (None, "", [])
        ]
        lines.append(f"- {item_id} | " + " | ".join(fragments) if fragments else f"- {item_id}")
    return lines or ["- (none)"]


def build_canonical_reference(
    expected_delta_json: Any,
    scoring_manifest_json: Any,
    perturbed_pack_json: Any,
) -> str:
    expected_delta = normalize_jsonish(expected_delta_json)
    scoring_manifest = normalize_jsonish(scoring_manifest_json)
    perturbed_pack = normalize_jsonish(perturbed_pack_json)

    changed_state_ids = _changed_ids(expected_delta.get("changed_states", []))
    changed_event_ids = _changed_ids(expected_delta.get("changed_events", []))
    changed_edge_ids = _changed_ids(expected_delta.get("changed_edges", []))
    changed_scenario_ids = sorted(
        item["scenario_id"]
        for item in expected_delta.get("scenario_rank_changes", [])
        if isinstance(item, dict) and item.get("scenario_id")
    )
    new_unknown_ids = _changed_ids(expected_delta.get("new_unknowns", []))
    resolved_unknown_ids = _changed_ids(expected_delta.get("resolved_unknowns", []))
    must_revise = expected_delta.get("must_revise", expected_delta.get("must_revise_claims", []))
    must_preserve = expected_delta.get("must_preserve", expected_delta.get("must_preserve_claims", []))
    forbidden_revision_ids = expected_delta.get("forbidden_revisions", [])
    preserved_items = expected_delta.get("preserved_items", [])
    support_map = expected_delta.get("supporting_evidence_map", {})
    citation_obligation_map = scoring_manifest.get("citation_obligation_map", {})

    allowed_ids = {
        "state_ids": _sorted_ids(_section_items(perturbed_pack, "states"), "state_id"),
        "event_ids": _sorted_ids(_section_items(perturbed_pack, "events"), "event_id"),
        "edge_ids": _sorted_ids(_section_items(perturbed_pack, "causal_edges"), "edge_id"),
        "scenario_ids": _sorted_ids(_section_items(perturbed_pack, "scenarios"), "scenario_id"),
        "unknown_ids": _sorted_ids(_section_items(perturbed_pack, "unknowns"), "unknown_id"),
        "evidence_ids": _sorted_ids(_section_items(perturbed_pack, "evidence"), "evidence_id"),
    }

    support_lines = [
        f"- {item_id} -> {_csv(evidence_ids)}"
        for item_id, evidence_ids in sorted(support_map.items())
    ] or ["- (none)"]
    obligation_lines = [
        f"- {item_id} -> {evidence_id}"
        for item_id, evidence_id in sorted(citation_obligation_map.items())
    ] or ["- (none)"]

    return "\n".join(
        [
            "=== CANONICAL ID REFERENCE ===",
            "Use only canonical ids from this reference in every id-valued field.",
            "For citation values, use only evidence ids from this reference (for example evidence:retraction), never surface artifact labels like CL-0055-R, POD-882, NL-204, or AC-778.",
            "Citation map rule: every citations value must be an array of evidence ids only.",
            "Never place state/event/edge/scenario/unknown ids inside citation values; those ids are valid only as citation keys.",
            "If you cite a scenario, cite supporting evidence ids rather than scenario basis ids.",
            "Never copy placeholder tokens like id, another_id, or artifact_or_evidence_id.",
            f"EXPECTED_CHANGED_STATE_IDS: {_csv(changed_state_ids)}",
            f"EXPECTED_CHANGED_EVENT_IDS: {_csv(changed_event_ids)}",
            f"EXPECTED_CHANGED_EDGE_IDS: {_csv(changed_edge_ids)}",
            f"EXPECTED_CHANGED_SCENARIO_IDS: {_csv(changed_scenario_ids)}",
            f"EXPECTED_NEW_UNKNOWN_IDS: {_csv(new_unknown_ids)}",
            f"EXPECTED_RESOLVED_UNKNOWN_IDS: {_csv(resolved_unknown_ids)}",
            f"MUST_REVISE_IDS: {_csv(must_revise)}",
            f"MUST_PRESERVE_IDS: {_csv(must_preserve)}",
            f"PRESERVED_ITEMS: {_csv(preserved_items)}",
            f"FORBIDDEN_REVISION_IDS: {_csv(forbidden_revision_ids)}",
            f"ALLOWED_STATE_IDS: {_csv(allowed_ids['state_ids'])}",
            f"ALLOWED_EVENT_IDS: {_csv(allowed_ids['event_ids'])}",
            f"ALLOWED_EDGE_IDS: {_csv(allowed_ids['edge_ids'])}",
            f"ALLOWED_SCENARIO_IDS: {_csv(allowed_ids['scenario_ids'])}",
            f"ALLOWED_UNKNOWN_IDS: {_csv(allowed_ids['unknown_ids'])}",
            f"ALLOWED_EVIDENCE_IDS: {_csv(allowed_ids['evidence_ids'])}",
            f"EVIDENCE_GROUNDING_REQUIREMENT: {scoring_manifest.get('evidence_grounding_requirement', '(none)')}",
            f"PRESERVATION_REQUIREMENT: {scoring_manifest.get('preservation_requirement', '(none)')}",
            f"STRUCTURAL_PROPAGATION_REQUIREMENT: {scoring_manifest.get('structural_propagation_requirement', '(none)')}",
            "SUPPORTING_EVIDENCE_MAP:",
            *support_lines,
            "CITATION_OBLIGATION_MAP:",
            *obligation_lines,
            "PERTURBED_STATE_REFERENCE:",
            *_reference_lines(
                _section_items(perturbed_pack, "states"),
                "state_id",
                ["predicate", "object", "status", "evidence_ids"],
            ),
            "PERTURBED_EVENT_REFERENCE:",
            *_reference_lines(
                _section_items(perturbed_pack, "events"),
                "event_id",
                ["type", "action", "evidence_ids"],
            ),
            "PERTURBED_EDGE_REFERENCE:",
            *_reference_lines(
                _section_items(perturbed_pack, "causal_edges"),
                "edge_id",
                ["relation", "to_id", "evidence_ids"],
            ),
            "PERTURBED_SCENARIO_REFERENCE:",
            *_reference_lines(
                _section_items(perturbed_pack, "scenarios"),
                "scenario_id",
                ["rank", "status", "basis_ids"],
            ),
            "PERTURBED_UNKNOWN_REFERENCE:",
            *_reference_lines(
                _section_items(perturbed_pack, "unknowns"),
                "unknown_id",
                ["category", "status", "target_id", "evidence_ids"],
            ),
            "PERTURBED_EVIDENCE_REFERENCE:",
            *_reference_lines(
                _section_items(perturbed_pack, "evidence"),
                "evidence_id",
                ["source_type", "source_id", "content"],
            ),
            "=== END CANONICAL ID REFERENCE ===",
        ]
    )


def _source_literal(value: Any) -> str:
    if isinstance(value, tuple):
        inner = ", ".join(_source_literal(item) for item in value)
        if len(value) == 1:
            inner += ","
        return f"({inner})"
    if isinstance(value, list):
        return "[" + ", ".join(_source_literal(item) for item in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(
            f"{_source_literal(key)}: {_source_literal(val)}"
            for key, val in value.items()
        )
        return "{" + inner + "}"
    return repr(value)


def build_shared_runtime_source() -> str:
    assignments = {
        "SYSTEM_PROMPT": SYSTEM_PROMPT,
        "RUN2_SCHEMA_INSTRUCTIONS": RUN2_SCHEMA_INSTRUCTIONS,
        "REQUIRED_TOP_KEYS": REQUIRED_TOP_KEYS,
        "REQUIRED_Q1_KEYS": REQUIRED_Q1_KEYS,
        "REQUIRED_Q2_KEYS": REQUIRED_Q2_KEYS,
        "REQUIRED_Q3_KEYS": REQUIRED_Q3_KEYS,
        "REQUIRED_SELF_CHECK_KEYS": REQUIRED_SELF_CHECK_KEYS,
    }
    pieces = [
        "from __future__ import annotations",
        "",
        "import json",
        "import re",
        "from dataclasses import asdict, dataclass",
        "from typing import Any, Mapping",
        "",
    ]
    for name, value in assignments.items():
        pieces.append(f"{name} = {_source_literal(value)}")
        pieces.append("")
    pieces.append(textwrap.dedent(inspect.getsource(PriorAnchorDiagnostics)))
    pieces.append("")
    for obj in (
        normalize_jsonish,
        extract_json_object,
        is_list_of_str,
        validate_response_shape,
        collect_valid_ids,
        expected_values,
        set_f1,
        set_accuracy,
        citation_coverage,
        score_structured_response,
        get_citation_keys,
        score_citation_obligation_coverage,
        compute_prior_anchor_diagnostics,
        diagnostics_to_dict,
        _section_items,
        _sorted_ids,
        _changed_ids,
        _csv,
        _reference_lines,
        build_canonical_reference,
    ):
        pieces.append(textwrap.dedent(inspect.getsource(obj)).rstrip())
        pieces.append("")
    return "\n".join(pieces).rstrip() + "\n"

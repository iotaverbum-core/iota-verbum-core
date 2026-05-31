from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "rulesets" / "phase3_diagnostic_matrix.v1.json"
DOCTRINE_PATH = ROOT / "rulesets" / "phase3_diagnostic_doctrine.v1.json"
CONTRACT_PATH = ROOT / "schemas" / "phase3_diagnostic_loop.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _classifier_family_for_code(doctrine: dict[str, Any], code: str) -> str:
    families = {row["family"]: row for row in doctrine["failure_families"]}
    for family_name in doctrine["determinism_policy"]["classifier_precedence"]:
        classifier = families[family_name]["classifier"]
        codes = set(classifier["canonical_codes"])
        codes.update(classifier.get("compatibility_aliases", []))
        if code in codes:
            return family_name
    return "UNSUPPORTED"


def _graph_id_universe(row: dict[str, Any]) -> set[str]:
    graph = row["graph"]
    return set(graph["prior_claim_ids"]).union(
        graph["trigger_claim_ids"],
        graph["evidence_ids"],
        graph["preserved_claim_ids"],
    )


def _expected_ids(row: dict[str, Any]) -> set[str]:
    expected = row["expected"]
    trace = expected["trace"]
    ids = set(trace["grounding_evidence_ids"])
    ids.update(trace["preserve_claim_ids"])
    if trace["target_claim_id"] is not None:
        ids.add(trace["target_claim_id"])

    repair = expected["repair"]
    if repair is not None:
        ids.update(repair["grounding_evidence_ids"])
        ids.update(repair["preservation_constraints"])
    return ids


def test_classifier_doctrine_is_deterministic_for_matrix_rows() -> None:
    matrix = _load_json(MATRIX_PATH)
    doctrine = _load_json(DOCTRINE_PATH)

    for row in matrix["rows"]:
        code = row["symptom"]["code"]
        first = _classifier_family_for_code(doctrine, code)
        second = _classifier_family_for_code(doctrine, code)

        assert first == second
        assert first == row["expected"]["classification"]


def test_traces_and_repairs_never_invent_graph_ids() -> None:
    matrix = _load_json(MATRIX_PATH)

    for row in matrix["rows"]:
        outside_graph = _expected_ids(row) - _graph_id_universe(row)
        assert outside_graph == set(), row["row_id"]


def test_repair_instructions_never_drop_preservation_constraints() -> None:
    matrix = _load_json(MATRIX_PATH)

    for row in matrix["rows"]:
        repair = row["expected"]["repair"]
        if repair is None:
            continue

        preserved = set(row["graph"]["preserved_claim_ids"])
        constraints = set(repair["preservation_constraints"])
        assert preserved <= constraints, row["row_id"]


def test_contract_requires_repair_instruction_before_retry_proposer_call() -> None:
    doctrine = _load_json(DOCTRINE_PATH)
    contract = _load_json(CONTRACT_PATH)

    repair_schema = contract["$defs"]["RepairInstruction"]
    result_schema = contract["$defs"]["DiagnosticLoopResult"]
    repaired_branch = result_schema["allOf"][0]["then"]["properties"]

    assert (
        doctrine["scope"]["initial_proposer_call_requires_repair_instruction"]
        is False
    )
    assert (
        doctrine["scope"]["repair_instruction_candidate_kind"]
        == "repair_instruction"
    )
    assert (
        repair_schema["properties"]["candidate_kind"]["const"]
        == "repair_instruction"
    )
    assert repaired_branch["proposer_call_permitted"]["const"] is True
    assert repaired_branch["budget_consumed"]["const"] is False
    assert repaired_branch["ledger_advanced"]["const"] is False


def test_budget_exhaustion_halts_without_ledger_advance() -> None:
    doctrine = _load_json(DOCTRINE_PATH)
    contract = _load_json(CONTRACT_PATH)

    result_schema = contract["$defs"]["DiagnosticLoopResult"]
    halt_branch = result_schema["allOf"][1]["then"]["properties"]

    assert "budget_exhausted" in doctrine["halt_reasons"]
    assert doctrine["scope"]["ledger_advance_allowed_before_acceptance"] is False
    assert halt_branch["repair_instruction"]["type"] == "null"
    assert halt_branch["proposer_call_permitted"]["const"] is False
    assert halt_branch["ledger_advanced"]["const"] is False


def test_doctrine_digest_seals_exact_matrix_hash() -> None:
    doctrine = _load_json(DOCTRINE_PATH)
    matrix_hash = hashlib.sha256(MATRIX_PATH.read_bytes()).hexdigest()

    assert doctrine["source_matrix"]["sha256"] == matrix_hash

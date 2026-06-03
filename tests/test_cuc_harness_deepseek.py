from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from core.cuc_harness.deepseek_proposer import (
    DeepSeekProposer,
    RevisionDelta,
    SealedFailureArtifact,
    _normalize_revision_delta_payload,
)
from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.ledger import write_run

CASE_ID = "CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
SOURCE_CASE_ID = "CUCV4-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT"
FIXTURE_DIR = Path("benchmark/kaggle/fixtures") / SOURCE_CASE_ID
EVIDENCE_BUNDLE_PATH = Path("tests/fixtures/evidence_bundle_example.json")


@pytest.mark.timeout(30)
def test_deepseek_proposer_on_simple_cuc_case(tmp_path: Path) -> None:
    clean_pack = _read_json(FIXTURE_DIR / "clean_pack.json")
    perturbed_pack = _read_json(FIXTURE_DIR / "perturbed_pack.json")
    gold_delta = _read_json(FIXTURE_DIR / "expected_delta.json")

    fake_client = _FakeDeepSeekClient(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(gold_delta, sort_keys=True),
                    }
                }
            ]
        }
    )

    with patch(
        "core.cuc_harness.deepseek_proposer.httpx.Client",
        side_effect=AssertionError("tests must not open live HTTP clients"),
    ):
        proposer = DeepSeekProposer(api_key="test-key", client=fake_client)
        proposal = proposer.propose(
            clean_pack,
            perturbed_pack,
            case_id=CASE_ID,
            strict_copy=False,
        )

    json_valid = isinstance(proposal, RevisionDelta)
    proposal_payload = proposal.model_dump(mode="json")
    print("DEEPSEEK_PROPOSER_OUTPUT=")
    print(json.dumps(proposal_payload, indent=2, sort_keys=True))

    verifier_accepted = False
    verifier_reasons: list[str] = []
    ledger_committed = False
    commit_outcome = "not_committed"

    if json_valid:
        _save_delta_if_requested(proposal)
        verifier_accepted, verifier_reasons = _verify_against_gold(
            proposal,
            gold_delta,
        )
        print(
            "DEEPSEEK_VERIFIER "
            f"status={'accepted' if verifier_accepted else 'rejected'} "
            f"reasons={json.dumps(verifier_reasons, sort_keys=True)}"
        )
        if verifier_accepted:
            run_dir = _commit_delta(tmp_path, proposal)
            ledger_committed = run_dir.is_dir()
            commit_outcome = str(run_dir)
    else:
        failure = proposal
        assert isinstance(failure, SealedFailureArtifact)
        verifier_reasons = [failure.error_type]
        print(
            "DEEPSEEK_VERIFIER "
            "status=rejected "
            f"reasons={json.dumps(verifier_reasons, sort_keys=True)}"
        )

    print(f"DEEPSEEK_COMMIT outcome={commit_outcome}")
    print(
        "DEEPSEEK_SUMMARY "
        f"json_valid={json_valid} "
        f"verifier_accepted={verifier_accepted} "
        f"ledger_committed={ledger_committed}"
    )
    assert json_valid, "DeepSeek proposer did not return a valid RevisionDelta."
    assert len(fake_client.requests) == 1


def test_normalizes_bare_unknown_ids_from_model_output() -> None:
    payload = {
        "schema_version": "1.0.0",
        "changed_edges": [],
        "changed_events": [],
        "changed_states": [],
        "forbidden_revisions": [],
        "new_conflicts": [],
        "new_unknowns": [],
        "preserved_items": [],
        "pruned_conflicts": [],
        "resolved_unknowns": ["unknown:primary"],
        "scenario_rank_changes": [],
        "supporting_evidence_map": {},
        "must_preserve_claims": [],
        "must_revise_claims": [],
        "named_evidence_artifact": "evidence:corroboration",
        "preservation_notes": "preserve",
        "revision_notes": "revise",
        "structural_invariant": "invariant",
    }

    normalized = _normalize_revision_delta_payload(payload)
    delta = RevisionDelta.model_validate(normalized)

    assert delta.resolved_unknowns[0].id == "unknown:primary"
    assert delta.resolved_unknowns[0].change_type == "resolved"
    assert delta.resolved_unknowns[0].source_op_ids == []


def test_normalizes_scenario_rank_aliases_from_model_output() -> None:
    payload = {
        "schema_version": "1.0.0",
        "changed_edges": [],
        "changed_events": [],
        "changed_states": [],
        "forbidden_revisions": [],
        "new_conflicts": [],
        "new_unknowns": [],
        "preserved_items": [],
        "pruned_conflicts": [],
        "resolved_unknowns": [],
        "scenario_rank_changes": [
            {
                "id": "scenario:primary",
                "old_rank": 1,
                "new_rank": 2,
            }
        ],
        "supporting_evidence_map": {},
        "must_preserve_claims": [],
        "must_revise_claims": [],
        "named_evidence_artifact": "evidence:primary",
        "preservation_notes": "preserve",
        "revision_notes": "revise",
        "structural_invariant": "invariant",
    }

    normalized = _normalize_revision_delta_payload(payload)

    assert normalized["scenario_rank_changes"] == [
        {
            "scenario_id": "scenario:primary",
            "before_rank": 1,
            "after_rank": 2,
        }
    ]


def test_preserved_items_include_forbidden_revisions_from_model_output() -> None:
    payload = {
        "schema_version": "1.0.0",
        "changed_edges": [],
        "changed_events": [],
        "changed_states": [],
        "forbidden_revisions": [
            "state:secondary",
            "edge:secondary_support",
            "unknown:secondary",
        ],
        "new_conflicts": [],
        "new_unknowns": [],
        "preserved_items": ["state:secondary"],
        "pruned_conflicts": [],
        "resolved_unknowns": [],
        "scenario_rank_changes": [],
        "supporting_evidence_map": {},
        "must_preserve_claims": [],
        "must_revise_claims": [],
        "named_evidence_artifact": "evidence:primary",
        "preservation_notes": "preserve",
        "revision_notes": "revise",
        "structural_invariant": "invariant",
    }

    normalized = _normalize_revision_delta_payload(payload)

    assert normalized["preserved_items"] == [
        "state:secondary",
        "edge:secondary_support",
        "unknown:secondary",
    ]


def test_normalizes_omitted_empty_revision_lists_from_model_output() -> None:
    payload = {
        "schema_version": "1.0.0",
        "changed_edges": [],
        "changed_events": [],
        "changed_states": [],
        "forbidden_revisions": [],
        "new_unknowns": [],
        "preserved_items": [],
        "resolved_unknowns": [],
        "scenario_rank_changes": [],
        "supporting_evidence_map": {},
        "must_preserve_claims": [],
        "must_revise_claims": [],
        "named_evidence_artifact": "evidence:primary",
        "preservation_notes": "preserve",
        "revision_notes": "revise",
        "structural_invariant": "invariant",
    }

    normalized = _normalize_revision_delta_payload(payload)
    delta = RevisionDelta.model_validate(normalized)

    assert delta.new_conflicts == []
    assert delta.pruned_conflicts == []


def test_explicit_empty_fallback_disables_default_fallback() -> None:
    proposer = DeepSeekProposer(api_key="test", fallback_model="")

    assert proposer.fallback_model == ""


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_against_gold(
    proposal: RevisionDelta,
    gold_delta: dict[str, Any],
) -> tuple[bool, list[str]]:
    payload = proposal.model_dump(mode="json")
    reasons: list[str] = []

    required_changed_states = _ids(gold_delta["changed_states"])
    required_changed_edges = _ids(gold_delta["changed_edges"])
    required_resolved_unknowns = _ids(gold_delta["resolved_unknowns"])

    proposed_changed_states = _ids(payload["changed_states"])
    proposed_changed_edges = _ids(payload["changed_edges"])
    proposed_resolved_unknowns = _ids(payload["resolved_unknowns"])

    _append_missing(
        reasons,
        "missing_changed_states",
        required_changed_states - proposed_changed_states,
    )
    _append_missing(
        reasons,
        "missing_changed_edges",
        required_changed_edges - proposed_changed_edges,
    )
    _append_missing(
        reasons,
        "missing_resolved_unknowns",
        required_resolved_unknowns - proposed_resolved_unknowns,
    )

    forbidden_revisions = set(gold_delta["forbidden_revisions"])
    touched_ids = set().union(
        proposed_changed_states,
        proposed_changed_edges,
        _ids(payload["changed_events"]),
        _ids(payload["new_unknowns"]),
        proposed_resolved_unknowns,
    )
    collateral = forbidden_revisions & touched_ids
    _append_missing(reasons, "forbidden_revision_touched", collateral)

    required_preserved = set(gold_delta["preserved_items"])
    missing_preserved = required_preserved - set(payload["preserved_items"])
    _append_missing(reasons, "missing_preserved_items", missing_preserved)

    expected_artifact = gold_delta["named_evidence_artifact"]
    if payload["named_evidence_artifact"] != expected_artifact:
        reasons.append(
            "named_evidence_artifact_mismatch:"
            f"{payload['named_evidence_artifact']}!={expected_artifact}"
        )

    return not reasons, reasons


def _ids(items: list[dict[str, Any]]) -> set[str]:
    return {
        str(item["id"])
        for item in items
        if isinstance(item, dict) and "id" in item
    }


def _append_missing(reasons: list[str], label: str, values: set[str]) -> None:
    if values:
        reasons.append(f"{label}:{','.join(sorted(values))}")


def _commit_delta(tmp_path: Path, proposal: RevisionDelta) -> Path:
    evidence_bundle = _read_json(EVIDENCE_BUNDLE_PATH)
    output_obj = {
        "case_id": CASE_ID,
        "delta": proposal.model_dump(mode="json"),
        "verifier_status": "accepted",
    }
    sealed = finalize(
        evidence_bundle,
        output_obj,
        manifest_sha256="2" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.cuc_harness.deepseek.v1",
        created_utc="2026-05-24T00:00:00Z",
    )
    return write_run(ledger_root=str(tmp_path / "ledger"), **sealed)


def _save_delta_if_requested(proposal: RevisionDelta) -> None:
    output_path = os.getenv("DEEPSEEK_DELTA_OUTPUT_PATH")
    if not output_path:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(dumps_canonical(proposal.model_dump(mode="json")))


class _FakeDeepSeekResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeDeepSeekClient:
    def __init__(self, response_payload: dict[str, Any]) -> None:
        self.response_payload = response_payload
        self.requests: list[dict[str, Any]] = []

    def post(
        self,
        endpoint: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
    ) -> _FakeDeepSeekResponse:
        self.requests.append(
            {
                "endpoint": endpoint,
                "headers": dict(headers),
                "json": dict(json),
            }
        )
        return _FakeDeepSeekResponse(self.response_payload)

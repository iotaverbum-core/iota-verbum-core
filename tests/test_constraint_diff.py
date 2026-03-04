import json
from pathlib import Path

from core.reasoning.constraint_diff import compute_constraint_diff

FIXTURES = Path("tests/fixtures")


def _evidence(chunk_id: str, text_sha256: str) -> dict:
    return {
        "source_id": "doc:1",
        "chunk_id": chunk_id,
        "offset_start": 0,
        "offset_end": 10,
        "text_sha256": text_sha256,
    }


def _violation(
    *,
    violation_type: str,
    events: list[str],
    entities: list[str],
    reason: str,
    evidence: list[dict],
) -> dict:
    return {
        "type": violation_type,
        "events": events,
        "entities": entities,
        "reason": reason,
        "evidence": evidence,
    }


def _wrapped_output(
    *,
    world_sha256: str,
    output_sha256: str,
    attestation_sha256: str,
    verification_status: str,
    violations: list[dict],
) -> dict:
    return {
        "output": {
            "world_model": {
                "world_version": "1.0",
                "world_sha256": world_sha256,
                "entities": [],
                "events": [],
                "relations": [],
                "unknowns": [],
                "conflicts": [],
            },
            "constraint_report": {
                "version": "1.0",
                "violations": violations,
                "counts": {
                    "policy": sum(
                        1
                        for violation in violations
                        if violation["type"] == "POLICY_CONFLICT"
                    ),
                    "temporal": sum(
                        1
                        for violation in violations
                        if violation["type"] == "TEMPORAL_CONFLICT"
                    ),
                    "causal": sum(
                        1
                        for violation in violations
                        if violation["type"] == "CAUSAL_CONFLICT"
                    ),
                    "state": sum(
                        1
                        for violation in violations
                        if violation["type"] == "STATE_CONFLICT"
                    ),
                },
            },
            "verification_result": {
                "verification_version": "1.0",
                "ruleset_id": "ruleset.core.v1",
                "target_claim_id": "world:test",
                "status": verification_status,
                "reasons": [],
                "required_info": [],
                "receipts": {
                    "bundle_sha256": "bundle",
                    "output_sha256": output_sha256,
                    "attestation_sha256": attestation_sha256,
                    "ruleset_sha256": "ruleset",
                    "evidence_refs": [],
                    "proofs": [],
                    "findings": [],
                },
            },
        },
        "__meta__": {
            "output_sha256": output_sha256,
            "attestation_sha256": attestation_sha256,
        },
    }


def _old_output() -> dict:
    return _wrapped_output(
        world_sha256="old-world",
        output_sha256="old-output",
        attestation_sha256="old-attestation",
        verification_status="VERIFIED_OK",
        violations=[
            _violation(
                violation_type="POLICY_CONFLICT",
                events=[
                    "event:1111111111111111111111111111111111111111111111111111111111111111",
                    "event:2222222222222222222222222222222222222222222222222222222222222222",
                ],
                entities=[
                    "entity:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ],
                reason="policy forbids source exposure",
                evidence=[
                    _evidence(
                        "chunk:1",
                        "1111111111111111111111111111111111111111111111111111111111111111",
                    )
                ],
            ),
            _violation(
                violation_type="TEMPORAL_CONFLICT",
                events=[
                    "event:3333333333333333333333333333333333333333333333333333333333333333",
                    "event:4444444444444444444444444444444444444444444444444444444444444444",
                ],
                entities=[
                    "entity:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ],
                reason="old temporal reason",
                evidence=[
                    _evidence(
                        "chunk:2",
                        "2222222222222222222222222222222222222222222222222222222222222222",
                    )
                ],
            ),
            _violation(
                violation_type="STATE_CONFLICT",
                events=[
                    "event:5555555555555555555555555555555555555555555555555555555555555555",
                    "event:6666666666666666666666666666666666666666666666666666666666666666",
                ],
                entities=[
                    "entity:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                ],
                reason="entity has contradictory state values",
                evidence=[
                    _evidence(
                        "chunk:3",
                        "3333333333333333333333333333333333333333333333333333333333333333",
                    )
                ],
            ),
        ],
    )


def _new_output() -> dict:
    return _wrapped_output(
        world_sha256="new-world",
        output_sha256="new-output",
        attestation_sha256="new-attestation",
        verification_status="VERIFIED_FAIL",
        violations=[
            _violation(
                violation_type="POLICY_CONFLICT",
                events=[
                    "event:1111111111111111111111111111111111111111111111111111111111111111",
                    "event:2222222222222222222222222222222222222222222222222222222222222222",
                ],
                entities=[
                    "entity:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ],
                reason="policy forbids source exposure",
                evidence=[
                    _evidence(
                        "chunk:1",
                        "1111111111111111111111111111111111111111111111111111111111111111",
                    )
                ],
            ),
            _violation(
                violation_type="TEMPORAL_CONFLICT",
                events=[
                    "event:3333333333333333333333333333333333333333333333333333333333333333",
                    "event:4444444444444444444444444444444444444444444444444444444444444444",
                ],
                entities=[
                    "entity:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ],
                reason="new temporal reason",
                evidence=[
                    _evidence(
                        "chunk:4",
                        "4444444444444444444444444444444444444444444444444444444444444444",
                    )
                ],
            ),
            _violation(
                violation_type="CAUSAL_CONFLICT",
                events=[
                    "event:7777777777777777777777777777777777777777777777777777777777777777",
                    "event:8888888888888888888888888888888888888888888888888888888888888888",
                ],
                entities=[
                    "entity:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
                ],
                reason="new causal violation",
                evidence=[
                    _evidence(
                        "chunk:5",
                        "5555555555555555555555555555555555555555555555555555555555555555",
                    )
                ],
            ),
        ],
    )


def test_compute_constraint_diff_is_deterministic_and_matches_fixture():
    first = compute_constraint_diff(old_output=_old_output(), new_output=_new_output())
    second = compute_constraint_diff(old_output=_old_output(), new_output=_new_output())
    expected = json.loads(
        (FIXTURES / "constraint_diff_expected.json").read_text(encoding="utf-8")
    )

    assert first == second
    assert first == expected


def test_compute_constraint_diff_matches_changed_violations_by_identity():
    diff = compute_constraint_diff(old_output=_old_output(), new_output=_new_output())

    assert diff["counts"] == {
        "old_total": 3,
        "new_total": 3,
        "added": 1,
        "removed": 1,
        "changed": 1,
    }
    assert diff["violations"]["changed"][0]["old"]["reason"] == "old temporal reason"
    assert diff["violations"]["changed"][0]["new"]["reason"] == "new temporal reason"

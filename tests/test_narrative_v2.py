import json
from pathlib import Path

from core.reasoning.narrative_v2 import render_narrative_v2

FIXTURES = Path("tests/fixtures")


def _support_tree() -> dict:
    return {
        "support_tree_version": "1.0",
        "target_claim_id": "C",
        "nodes": [
            {
                "claim_id": "A",
                "claim": {
                    "claim_id": "A",
                    "subject": "Alpha",
                    "predicate": "supports",
                    "object": "Beta",
                    "polarity": "affirm",
                    "modality": "assert",
                    "qualifiers": {},
                    "evidence": [
                        {
                            "source_id": "source-a",
                            "chunk_id": "chunk-a",
                            "offset_start": 0,
                            "offset_end": 10,
                            "text_sha256": "1" * 64,
                        }
                    ],
                },
            },
            {
                "claim_id": "B",
                "claim": {
                    "claim_id": "B",
                    "subject": "Beta",
                    "predicate": "supports",
                    "object": "Gamma",
                    "polarity": "affirm",
                    "modality": "assert",
                    "qualifiers": {},
                    "evidence": [
                        {
                            "source_id": "source-b",
                            "chunk_id": "chunk-b",
                            "offset_start": 11,
                            "offset_end": 21,
                            "text_sha256": "1" * 64,
                        }
                    ],
                },
            },
            {
                "claim_id": "C",
                "claim": {
                    "claim_id": "C",
                    "subject": "Gamma",
                    "predicate": "supports",
                    "object": "Delta",
                    "polarity": "affirm",
                    "modality": "assert",
                    "qualifiers": {},
                    "evidence": [
                        {
                            "source_id": "source-c",
                            "chunk_id": "chunk-c",
                            "offset_start": 22,
                            "offset_end": 32,
                            "text_sha256": "1" * 64,
                        }
                    ],
                },
            },
        ],
        "edges": [
            {
                "from_id": "A",
                "to_id": "B",
                "type": "supports",
                "derived": False,
                "proof": None,
            },
            {
                "from_id": "A",
                "to_id": "C",
                "type": "supports",
                "derived": True,
                "proof": [
                    {"from_id": "A", "to_id": "B", "type": "supports"},
                    {"from_id": "B", "to_id": "C", "type": "supports"},
                ],
            },
            {
                "from_id": "B",
                "to_id": "C",
                "type": "supports",
                "derived": False,
                "proof": None,
            },
        ],
    }


def _verification_result() -> dict:
    return {
        "verification_version": "1.0",
        "ruleset_id": "ruleset.core.v1",
        "target_claim_id": "C",
        "status": "VERIFIED_OK",
        "reasons": [],
        "required_info": [],
        "receipts": {
            "bundle_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "attestation_sha256": "",
            "ruleset_sha256": "c" * 64,
            "evidence_refs": [
                {
                    "source_id": "source-a",
                    "chunk_id": "chunk-a",
                    "offset_start": 0,
                    "offset_end": 10,
                    "text_sha256": "1" * 64,
                },
                {
                    "source_id": "source-b",
                    "chunk_id": "chunk-b",
                    "offset_start": 11,
                    "offset_end": 21,
                    "text_sha256": "1" * 64,
                },
                {
                    "source_id": "source-c",
                    "chunk_id": "chunk-c",
                    "offset_start": 22,
                    "offset_end": 32,
                    "text_sha256": "1" * 64,
                },
            ],
            "proofs": [
                {
                    "from_id": "A",
                    "to_id": "C",
                    "type": "supports",
                    "proof": [
                        {"from_id": "A", "to_id": "B", "type": "supports"},
                        {"from_id": "B", "to_id": "C", "type": "supports"},
                    ],
                }
            ],
            "findings": [],
        },
    }


def test_render_narrative_v2_brief_is_stable_and_bounded():
    first = render_narrative_v2(
        support_tree=_support_tree(),
        findings={"findings_version": "1.0", "duplicates": [], "contradictions": []},
        verification_result=_verification_result(),
        mode="brief",
        show_receipts=False,
        max_lines=40,
    )
    second = render_narrative_v2(
        support_tree=_support_tree(),
        findings={"findings_version": "1.0", "duplicates": [], "contradictions": []},
        verification_result=_verification_result(),
        mode="brief",
        show_receipts=False,
        max_lines=40,
    )

    assert first == second
    assert len(first["text"].splitlines()) <= 40
    expected = (FIXTURES / "narrative_v2_expected.txt").read_text(encoding="utf-8")
    assert first["text"] == expected


def test_render_narrative_v2_full_with_receipts_expands_deterministically():
    brief = render_narrative_v2(
        support_tree=_support_tree(),
        findings={"findings_version": "1.0", "duplicates": [], "contradictions": []},
        verification_result=_verification_result(),
        mode="brief",
        show_receipts=False,
        max_lines=40,
    )
    full = render_narrative_v2(
        support_tree=_support_tree(),
        findings={"findings_version": "1.0", "duplicates": [], "contradictions": []},
        verification_result=_verification_result(),
        mode="full",
        show_receipts=True,
        max_lines=80,
    )

    assert len(full["text"].splitlines()) > len(brief["text"].splitlines())
    assert "evidence: " in full["text"]
    assert json.loads(json.dumps(full)) == full

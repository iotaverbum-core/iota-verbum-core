import json
from pathlib import Path

from core.reasoning.run_graph import run_graph_reasoning

FIXTURES = Path("tests/fixtures")


def _bundle() -> dict:
    return json.loads(
        (FIXTURES / "evidence_bundle_example.json").read_text(encoding="utf-8")
    )


def _graph() -> dict:
    return json.loads(
        (FIXTURES / "claim_graph_closure_example.json").read_text(encoding="utf-8")
    )


def test_rendered_narrative_is_stable_and_has_receipts():
    result = run_graph_reasoning(
        _bundle(),
        _graph(),
        manifest_sha256="1" * 64,
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:05:00Z",
        target_claim_id="C",
    )
    output = json.loads(result["output_bytes"].decode("utf-8"))
    narrative = output["narrative"]

    assert narrative["narrative_version"] == "1.0"
    assert [paragraph["pid"] for paragraph in narrative["paragraphs"]] == [
        "01-claim",
        "02-support",
        "03-conflicts",
        "04-receipts-summary",
    ]
    assert narrative["paragraphs"][0]["receipts"] == [
        {
            "kind": "evidence",
                "ref": {
                    "source_id": "source-c",
                    "chunk_id": "chunk-c",
                    "offset_start": 22,
                    "offset_end": 32,
                    "text_sha256": (
                        "29d3d204d9e3016293b45f0fdcec99bc58cefaf13efb7d60943456c946f29505"
                    ),
                },
            }
        ]
    assert any(
        receipt["kind"] == "proof"
        and receipt["ref"]["from_id"] == "A"
        and receipt["ref"]["to_id"] == "C"
        and len(receipt["ref"]["proof"]) == 2
        for receipt in narrative["paragraphs"][1]["receipts"]
    )
    expected_text = (FIXTURES / "narrative_expected.txt").read_text(encoding="utf-8")
    assert narrative["text"] == expected_text

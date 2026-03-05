from __future__ import annotations

import re

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _sort_receipts(receipts: list[dict]) -> list[dict]:
    return sorted(
        receipts,
        key=lambda receipt: (
            receipt["kind"],
            dumps_canonical(receipt["ref"]).decode("utf-8"),
        ),
    )


def _evidence_receipts(claim: dict) -> list[dict]:
    return _sort_receipts(
        [
            {"kind": "evidence", "ref": evidence_ref}
            for evidence_ref in claim["evidence"]
        ]
    )


def render_narrative(
    *,
    support_tree: dict,
    findings: dict,
    verification_result: dict | None = None,
) -> dict:
    validate(support_tree, "schemas/support_tree.schema.json")
    validate(findings, "schemas/graph_findings.schema.json")

    claims_by_id = {
        node["claim_id"]: node["claim"]
        for node in support_tree["nodes"]
    }
    target_claim = claims_by_id[support_tree["target_claim_id"]]

    claim_body = _normalize_text(
        (
            f"{target_claim['claim_id']}: "
            f"{target_claim['subject']} "
            f"{target_claim['predicate']} "
            f"{target_claim['object']} "
            f"[polarity={target_claim['polarity']}, "
            f"modality={target_claim['modality']}]"
        )
    )
    paragraph_claim = {
        "pid": "01-claim",
        "title": "Claim",
        "body": claim_body,
        "receipts": _evidence_receipts(target_claim),
    }

    support_lines = []
    support_receipts = []
    for edge in support_tree["edges"]:
        edge_mode = "derived" if edge["derived"] else "primitive"
        support_lines.append(
            f"{edge['from_id']} -> {edge['to_id']} ({edge['type']}) [{edge_mode}]"
        )
        support_receipts.extend(_evidence_receipts(claims_by_id[edge["from_id"]]))
        if edge["derived"]:
            support_receipts.append(
                {
                    "kind": "proof",
                    "ref": {
                        "from_id": edge["from_id"],
                        "to_id": edge["to_id"],
                        "type": edge["type"],
                        "proof": edge["proof"],
                    },
                }
            )
    paragraph_support = {
        "pid": "02-support",
        "title": "Support",
        "body": _normalize_text("\n".join(support_lines)) if support_lines else "None.",
        "receipts": _sort_receipts(support_receipts),
    }

    contradiction_receipts = []
    contradiction_lines = []
    for contradiction in findings["contradictions"]:
        if support_tree["target_claim_id"] not in {
            contradiction["claim_a"],
            contradiction["claim_b"],
        }:
            continue
        contradiction_lines.append(
            f"{contradiction['claim_a']} vs {contradiction['claim_b']}: "
            f"{contradiction['reason']}"
        )
        contradiction_receipts.append(
            {
                "kind": "finding",
                "ref": {
                    "finding_type": "contradiction",
                    "claim_a": contradiction["claim_a"],
                    "claim_b": contradiction["claim_b"],
                    "reason": contradiction["reason"],
                },
            }
        )
    paragraph_conflicts = {
        "pid": "03-conflicts",
        "title": "Conflicts",
        "body": _normalize_text("\n".join(contradiction_lines))
        if contradiction_lines
        else "None.",
        "receipts": _sort_receipts(contradiction_receipts),
    }

    evidence_count = sum(
        len(node["claim"]["evidence"])
        for node in support_tree["nodes"]
    )
    proof_count = sum(1 for edge in support_tree["edges"] if edge["derived"])
    conflict_count = len(contradiction_lines)
    paragraph_receipts = {
        "pid": "04-receipts-summary",
        "title": "Receipts",
        "body": (
            f"#claims={len(support_tree['nodes'])}, "
            f"#edges={len(support_tree['edges'])}, "
            f"#evidence_refs={evidence_count}, "
            f"#proofs={proof_count}, "
            f"#conflicts={conflict_count}"
        ),
        "receipts": [],
    }

    verification_paragraph = None
    if verification_result is not None:
        reason_lines = [
            f"- {reason['code']}: {reason['message']}"
            for reason in verification_result["reasons"]
        ]
        info_lines = [
            f"- {item['kind']}: {dumps_canonical(item['ref']).decode('utf-8')}"
            for item in verification_result["required_info"]
        ]
        verification_body_lines = [
            f"Status: {verification_result['status']}",
            "Reasons:",
            "\n".join(reason_lines) if reason_lines else "None.",
            "Required Info:",
            "\n".join(info_lines) if info_lines else "None.",
        ]
        verification_paragraph = {
            "pid": "05-verification",
            "title": "Verification",
            "body": "\n".join(verification_body_lines),
            "receipts": [],
        }

    paragraphs = [
        paragraph_claim,
        paragraph_support,
        paragraph_conflicts,
        paragraph_receipts,
    ]
    if verification_paragraph is not None:
        paragraphs.append(verification_paragraph)
    paragraphs = sorted(paragraphs, key=lambda paragraph: paragraph["pid"])
    text = "\n\n".join(
        f"{paragraph['title']}\n{paragraph['body']}"
        for paragraph in paragraphs
    ).replace("\r\n", "\n").replace("\r", "\n") + "\n"

    narrative = {
        "narrative_version": "1.0",
        "target_claim_id": support_tree["target_claim_id"],
        "text": text,
        "paragraphs": paragraphs,
    }
    validate(narrative, "schemas/narrative.schema.json")
    return narrative

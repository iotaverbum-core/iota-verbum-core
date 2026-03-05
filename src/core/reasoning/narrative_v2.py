from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _compact_ref(kind: str, ref: dict) -> str:
    if "event_id" in ref and len(ref) == 1:
        return f"{kind} (event_id={ref['event_id']})"
    return f"{kind} ({_truncate(dumps_canonical(ref).decode('utf-8'))})"


def _line_budget(sections: list[dict], max_lines: int) -> list[dict]:
    if max_lines <= 0:
        return [{"title": section["title"], "lines": []} for section in sections]
    structural_lines = max(0, (2 * len(sections)) - 1)
    remaining = max(0, max_lines - structural_lines)
    bounded_sections = []
    for section in sections:
        if remaining <= 0:
            bounded_sections.append({"title": section["title"], "lines": []})
            continue
        lines = section["lines"][:remaining]
        bounded_sections.append({"title": section["title"], "lines": lines})
        remaining -= len(lines)
    return bounded_sections


def _render_text(sections: list[dict]) -> str:
    def _section_text(section: dict) -> str:
        body = "\n".join(section["lines"]) if section["lines"] else "None."
        return f"{section['title']}\n{body}"

    return (
        "\n\n".join(_section_text(section) for section in sections)
        + "\n"
    )


def _summarize_refs(
    *,
    evidence_refs: list[dict],
    proofs: list[dict],
    findings: list[dict],
) -> dict:
    return {
        "evidence_ref_count": len(evidence_refs),
        "proof_count": len(proofs),
        "finding_count": len(findings),
        "top_evidence_refs": [
            f"{ref['source_id']}|{ref['chunk_id']}" for ref in evidence_refs[:5]
        ],
        "top_proofs": [
            f"{proof['from_id']}->{proof['to_id']}:{proof['type']}"
            for proof in proofs[:5]
        ],
        "top_findings": [
            (
                f"{finding.get('finding_type', 'contradiction')}:"
                f"{finding.get('claim_a', '')}:{finding.get('claim_b', '')}"
            )
            for finding in findings[:5]
        ],
    }


def render_narrative_v2(
    *,
    support_tree: dict,
    findings: dict,
    verification_result: dict,
    mode: str = "brief",
    show_receipts: bool = False,
    max_lines: int = 200,
) -> dict:
    validate(support_tree, "schemas/support_tree.schema.json")
    validate(findings, "schemas/graph_findings.schema.json")
    validate(verification_result, "schemas/verification_result.schema.json")

    claims_by_id = {node["claim_id"]: node["claim"] for node in support_tree["nodes"]}

    verification_lines = [f"Status: {verification_result['status']}"]
    reason_lines = (
        [f"- {reason['code']}" for reason in verification_result["reasons"]]
        if mode == "brief"
        else [
            f"- {reason['code']}: {reason['message']}"
            for reason in verification_result["reasons"]
        ]
    )
    required_info_lines = (
        [
            "- " + _compact_ref(item["kind"], item["ref"])
            for item in verification_result["required_info"]
        ]
        if mode == "brief"
        else [
            f"- {item['kind']}: {dumps_canonical(item['ref']).decode('utf-8')}"
            for item in verification_result["required_info"]
        ]
    )
    verification_lines.extend(reason_lines or ["Reasons: none"])
    verification_lines.extend(required_info_lines or ["Required Info: none"])

    support_claim_ids = sorted(
        {
            edge["from_id"]
            for edge in support_tree["edges"]
        }
    )
    know_ids = [support_tree["target_claim_id"], *support_claim_ids]
    if mode == "brief":
        know_ids = know_ids[:7]
    know_lines = []
    for claim_id in know_ids:
        claim = claims_by_id[claim_id]
        know_lines.append(
            f"- {claim_id}: {claim['subject']} {claim['predicate']} {claim['object']} "
            f"[evidence={len(claim['evidence'])}]"
        )

    unknown_lines = (
        [
            "- " + _compact_ref(item["kind"], item["ref"])
            for item in verification_result["required_info"][:10]
        ]
        if mode == "brief"
        else [
            f"- {item['kind']}: {dumps_canonical(item['ref']).decode('utf-8')}"
            for item in verification_result["required_info"]
        ]
    )

    contradiction_lines = []
    for contradiction in findings["contradictions"]:
        if support_tree["target_claim_id"] not in {
            contradiction["claim_a"],
            contradiction["claim_b"],
        }:
            continue
        if mode == "brief":
            contradiction_lines.append(
                f"- contradiction: {contradiction['reason']}"
            )
        else:
            contradiction_lines.append(
                "- contradiction: "
                + dumps_canonical(contradiction).decode("utf-8")
            )

    receipts = verification_result["receipts"]
    receipts_lines = [
        f"Counts: evidence_refs={len(receipts['evidence_refs'])}, "
        f"proofs={len(receipts['proofs'])}, findings={len(receipts['findings'])}"
    ]
    if mode == "brief" and not show_receipts:
        receipts_lines.extend(
            [
                "Top evidence refs: "
                + (", ".join(
                    f"{ref['source_id']}|{ref['chunk_id']}"
                    for ref in receipts["evidence_refs"][:5]
                ) or "none"),
                "Run with --show-receipts true for full receipts",
            ]
        )
    else:
        expanded_items = []
        for evidence_ref in receipts["evidence_refs"]:
            expanded_items.append(
                "evidence: " + dumps_canonical(evidence_ref).decode("utf-8")
            )
        for proof in receipts["proofs"]:
            expanded_items.append("proof: " + dumps_canonical(proof).decode("utf-8"))
        for finding in receipts["findings"]:
            expanded_items.append(
                "finding: " + dumps_canonical(finding).decode("utf-8")
            )
        receipts_lines.extend(expanded_items[: max(0, max_lines)])

    sections = [
        {"title": "Verification", "lines": verification_lines},
        {"title": "What we know", "lines": know_lines},
        {"title": "What we don't know yet", "lines": unknown_lines},
        {"title": "Conflicts", "lines": contradiction_lines},
        {"title": "Receipts", "lines": receipts_lines},
    ]
    bounded_sections = _line_budget(sections, max_lines)
    narrative_v2 = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded_sections),
        "sections": bounded_sections,
        "receipts_summary": _summarize_refs(
            evidence_refs=receipts["evidence_refs"],
            proofs=sorted(receipts["proofs"], key=_sort_key),
            findings=sorted(receipts["findings"], key=_sort_key),
        ),
        "target_claim_id": support_tree["target_claim_id"],
    }
    validate(narrative_v2, "schemas/narrative_v2.schema.json")
    return narrative_v2

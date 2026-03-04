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
        lines = section["lines"][:remaining]
        bounded_sections.append({"title": section["title"], "lines": lines})
        remaining -= len(lines)
        if remaining < 0:
            remaining = 0
    return bounded_sections


def _render_text(sections: list[dict]) -> str:
    def _section_text(section: dict) -> str:
        body = "\n".join(section["lines"]) if section["lines"] else "None."
        return f"{section['title']}\n{body}"

    return (
        "\n\n".join(_section_text(section) for section in sections)
        + "\n"
    )


def _time_sort_key(event: dict) -> tuple[int, str, str]:
    if event["time"]["kind"] == "unknown":
        return (1, "", event["event_id"])
    return (0, event["time"]["value"], event["event_id"])


def render_world_narrative_v2(
    *,
    world_model: dict,
    verification_result: dict,
    mode: str = "brief",
    show_receipts: bool = False,
    max_lines: int = 200,
) -> dict:
    validate(world_model, "schemas/world_model.schema.json")
    validate(verification_result, "schemas/verification_result.schema.json")

    verification_lines = [f"Status: {verification_result['status']}"]
    verification_lines.extend(
        [f"- {reason['code']}" for reason in verification_result["reasons"]]
        if mode == "brief"
        else [
            f"- {reason['code']}: {reason['message']}"
            for reason in verification_result["reasons"]
        ]
    )
    if not verification_result["reasons"]:
        verification_lines.append("Reasons: none")
    verification_lines.extend(
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
    if not verification_result["required_info"]:
        verification_lines.append("Required Info: none")

    events = sorted(world_model["events"], key=_time_sort_key)
    if mode == "brief":
        events = events[:7]
    know_lines = [
        f"- [{event['time'].get('value', 'unknown')}] "
        f"{event['type']}: {event['action']} "
        f"[evidence={len(event['evidence'])}]"
        for event in events
    ]

    unknowns = sorted(
        world_model["unknowns"],
        key=lambda item: (item["kind"], dumps_canonical(item["ref"]).decode("utf-8")),
    )
    if mode == "brief":
        unknowns = unknowns[:10]
    unknown_lines = [
        (
            "- " + _compact_ref(item["kind"], item["ref"])
            if mode == "brief"
            else f"- {item['kind']}: {dumps_canonical(item['ref']).decode('utf-8')}"
        )
        for item in unknowns
    ]

    conflicts = world_model["conflicts"]
    conflict_lines = [
        (
            f"- {conflict['kind']}: {conflict['reason']}"
            if mode == "brief"
            else f"- {conflict['kind']}: {dumps_canonical(conflict).decode('utf-8')}"
        )
        for conflict in conflicts
    ]

    receipts = verification_result["receipts"]
    receipts_lines = [
        f"Counts: evidence_refs={len(receipts['evidence_refs'])}, "
        f"proofs={len(receipts['proofs'])}, findings={len(receipts['findings'])}"
    ]
    if mode == "brief" and not show_receipts:
        receipts_lines.extend(
            [
                "Top evidence refs: "
                + (
                    ", ".join(
                        f"{ref['source_id']}|{ref['chunk_id']}"
                        for ref in receipts["evidence_refs"][:5]
                    )
                    or "none"
                ),
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
        {"title": "Conflicts", "lines": conflict_lines},
        {"title": "Receipts", "lines": receipts_lines},
    ]
    bounded_sections = _line_budget(sections, max_lines)
    narrative_v2 = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded_sections),
        "sections": bounded_sections,
        "receipts_summary": {
            "evidence_ref_count": len(receipts["evidence_refs"]),
            "proof_count": len(receipts["proofs"]),
            "finding_count": len(receipts["findings"]),
            "top_evidence_refs": [
                f"{ref['source_id']}|{ref['chunk_id']}"
                for ref in receipts["evidence_refs"][:5]
            ],
            "top_proofs": [
                (
                    f"{proof.get('from_id', '')}"
                    f"->{proof.get('to_id', '')}:{proof.get('type', '')}"
                )
                for proof in sorted(receipts["proofs"], key=_sort_key)[:5]
            ],
            "top_findings": [
                _sort_key(finding)
                for finding in sorted(receipts["findings"], key=_sort_key)[:5]
            ],
        },
        "world_sha256": world_model["world_sha256"],
    }
    validate(narrative_v2, "schemas/world_narrative_v2.schema.json")
    return narrative_v2

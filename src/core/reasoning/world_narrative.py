from __future__ import annotations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.schema_validate import validate


def _sort_receipts(receipts: list[dict]) -> list[dict]:
    return sorted(
        receipts,
        key=lambda receipt: (
            receipt["kind"],
            dumps_canonical(receipt["ref"]).decode("utf-8"),
        ),
    )


def _time_label(event: dict) -> str:
    if event["time"]["kind"] == "unknown":
        return "unknown"
    return event["time"]["value"]


def _event_line(event: dict) -> str:
    return (
        f"- [{_time_label(event)}] {event['type']}: {event['action']} "
        f"(event_id={event['event_id']})"
    )


def render_world_narrative(
    world_model: dict,
    verification_result: dict | None = None,
) -> dict:
    validate(world_model, "schemas/world_model.schema.json")

    summary = {
        "pid": "01-summary",
        "title": "Summary",
        "body": (
            f"Entities={len(world_model['entities'])}; "
            f"Events={len(world_model['events'])}; "
            f"Unknowns={len(world_model['unknowns'])}; "
            f"Conflicts={len(world_model['conflicts'])}."
        ),
        "receipts": [],
    }

    timeline_lines = []
    timeline_receipts = []
    for event in world_model["events"]:
        timeline_lines.append(_event_line(event))
        for evidence_ref in event["evidence"]:
            timeline_receipts.append({"kind": "evidence", "ref": evidence_ref})
    timeline = {
        "pid": "02-timeline",
        "title": "Timeline",
        "body": "\n".join(timeline_lines) if timeline_lines else "None.",
        "receipts": _sort_receipts(timeline_receipts),
    }

    unknown_lines = [
        f"- {unknown['kind']}: {dumps_canonical(unknown['ref']).decode('utf-8')}"
        for unknown in world_model["unknowns"]
    ]
    unknowns = {
        "pid": "03-unknowns",
        "title": "Unknowns",
        "body": "\n".join(unknown_lines) if unknown_lines else "None.",
        "receipts": [],
    }

    conflict_lines = []
    conflict_receipts = []
    for conflict in world_model["conflicts"]:
        conflict_lines.append(
            f"- {conflict['kind']}: {conflict['reason']} "
            f"(ref={dumps_canonical(conflict['ref']).decode('utf-8')})"
        )
        conflict_receipts.append({"kind": "conflict", "ref": conflict})
    conflicts = {
        "pid": "04-conflicts",
        "title": "Conflicts",
        "body": "\n".join(conflict_lines) if conflict_lines else "None.",
        "receipts": _sort_receipts(conflict_receipts),
    }

    verification = None
    if verification_result is not None:
        reason_lines = [
            f"- {reason['code']}: {reason['message']}"
            for reason in verification_result["reasons"]
        ]
        info_lines = [
            f"- {item['kind']}: {dumps_canonical(item['ref']).decode('utf-8')}"
            for item in verification_result["required_info"]
        ]
        verification = {
            "pid": "05-verification",
            "title": "Verification",
            "body": "\n".join(
                [
                    f"Status: {verification_result['status']}",
                    "Reasons:",
                    "\n".join(reason_lines) if reason_lines else "None.",
                    "Required Info:",
                    "\n".join(info_lines) if info_lines else "None.",
                ]
            ),
            "receipts": [],
        }

    paragraphs = [summary, timeline, unknowns, conflicts]
    if verification is not None:
        paragraphs.append(verification)
    paragraphs = sorted(paragraphs, key=lambda paragraph: paragraph["pid"])
    text = (
        "\n\n".join(
            f"{paragraph['title']}\n{paragraph['body']}"
            for paragraph in paragraphs
        )
        + "\n"
    )

    narrative = {
        "narrative_version": "1.0",
        "world_sha256": world_model["world_sha256"],
        "text": text,
        "paragraphs": paragraphs,
    }
    validate(narrative, "schemas/world_narrative.schema.json")
    return narrative

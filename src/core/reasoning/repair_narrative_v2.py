from __future__ import annotations

from core.determinism.schema_validate import validate


def _line_budget(sections: list[dict], max_lines: int) -> list[dict]:
    structural_lines = max(0, (2 * len(sections)) - 1)
    remaining = max(0, max_lines - structural_lines)
    bounded: list[dict] = []
    for section in sections:
        lines = section["lines"][:remaining]
        bounded.append({"title": section["title"], "lines": lines})
        remaining -= len(lines)
        if remaining < 0:
            remaining = 0
    return bounded


def _render_text(sections: list[dict]) -> str:
    def _section_text(section: dict) -> str:
        body = "\n".join(section["lines"]) if section["lines"] else "None."
        return f"{section['title']}\n{body}"

    return "\n\n".join(_section_text(section) for section in sections) + "\n"


def render_repair_narrative_v2(
    plan: dict,
    record: dict | None,
    *,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    validate(plan, "schemas/repair_plan.schema.json")
    if record is not None:
        validate(record, "schemas/repair_run_record.schema.json")

    summary_lines = [
        f"Plan: {plan['plan_id']}",
        f"Base verification: {plan['status']}",
        f"Action count: {len(plan['actions'])}",
    ]
    proposed_lines = [
        (
            f"- p{action['priority']} {action['risk']} "
            f"{action['kind']} :: {action['goal']}"
        )
        for action in plan["actions"]
    ]

    selected_lines: list[str] = []
    result_lines: list[str] = []
    replay_lines: list[str] = []
    planned_trigger_reasons = sum(
        len(action["receipts"]["trigger_reasons"]) for action in plan["actions"]
    )
    planned_event_refs = sum(
        len(action["receipts"]["event_ids"]) for action in plan["actions"]
    )
    receipt_lines = [
        f"planned_actions: {len(plan['actions'])}",
        f"planned_trigger_reasons: {planned_trigger_reasons}",
        f"planned_event_refs: {planned_event_refs}",
    ]
    selected_action_id = ""
    verification_old = plan["status"]
    verification_new = plan["status"]
    replay_ok = None

    if record is not None:
        selected_action_id = record["selected_action_id"]
        selected_lines.append(selected_action_id)
        verification_old = record["verification"]["old"]
        verification_new = record["verification"]["new"]
        result_lines.extend(
            [
                f"Verification: {verification_old} -> {verification_new}",
                f"Ledger: {record['new']['ledger_dir']}",
            ]
        )
        replay_ok = record["replay"]["ok"]
        replay_lines.extend(
            [
                f"strict_manifest: {str(record['replay']['strict_manifest']).lower()}",
                f"ok: {str(record['replay']['ok']).lower()}",
            ]
        )
        receipt_lines.extend(
            [
                "selected_trigger_reasons: "
                + str(
                    len(
                        record["receipts"]["action_receipts"]["trigger_reasons"]
                    )
                ),
                "selected_event_refs: "
                + str(len(record["receipts"]["action_receipts"]["event_ids"])),
                "selected_entity_refs: "
                + str(len(record["receipts"]["action_receipts"]["entity_ids"])),
            ]
        )

    sections = [
        {"title": "Summary", "lines": summary_lines},
        {"title": "Proposed actions", "lines": proposed_lines},
        {"title": "Selected action", "lines": selected_lines},
        {"title": "Result", "lines": result_lines},
        {"title": "Replay", "lines": replay_lines},
        {"title": "Receipts", "lines": receipt_lines},
    ]
    bounded = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded).replace("\r\n", "\n").replace("\r", "\n"),
        "sections": bounded,
        "summary": {
            "plan_id": plan["plan_id"],
            "base_verification": plan["status"],
            "action_count": len(plan["actions"]),
            "selected_action_id": selected_action_id or None,
            "verification_old": verification_old,
            "verification_new": verification_new,
            "replay_ok": replay_ok,
        },
    }
    validate(narrative, "schemas/repair_narrative_v2.schema.json")
    return narrative

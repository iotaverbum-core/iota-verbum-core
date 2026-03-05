from __future__ import annotations

from core.determinism.schema_validate import validate


def _line_budget(sections: list[dict], max_lines: int) -> list[dict]:
    structural_lines = max(0, (2 * len(sections)) - 1)
    remaining = max(0, max_lines - structural_lines)
    bounded = []
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


def _top_targets(patch_obj: dict, limit: int = 5) -> list[str]:
    targets = []
    for op in patch_obj["ops"]:
        target = op["target"]
        if "entity_id" in target:
            targets.append(target["entity_id"])
        elif "event_id" in target:
            targets.append(target["event_id"])
        elif "relation_key" in target:
            key = target["relation_key"]
            targets.append(f"{key['type']}:{key['from_id']}->{key['to_id']}")
    return sorted(set(targets))[:limit]


def render_world_patch_narrative_v2(
    patch_obj: dict,
    patch_result_obj: dict,
    *,
    mode: str = "brief",
    max_lines: int = 200,
) -> dict:
    validate(patch_obj, "schemas/world_patch.schema.json")
    validate(patch_result_obj, "schemas/world_patch_result.schema.json")

    counts: dict[str, int] = {}
    for op in patch_obj["ops"]:
        counts[op["op"]] = counts.get(op["op"], 0) + 1
    count_lines = [f"- {op_name}: {counts[op_name]}" for op_name in sorted(counts)]
    top_targets = _top_targets(patch_obj)
    target_lines = [f"- {item}" for item in top_targets]
    verification_lines = [
        f"Patch: {patch_obj['patch_id']}",
        (
            "Verification: "
            f"{patch_result_obj['verification_change']['old']} -> "
            f"{patch_result_obj['verification_change']['new']}"
        ),
        f"Base world_sha256: {patch_result_obj['base']['world_sha256']}",
        f"New world_sha256: {patch_result_obj['new']['world_sha256']}",
    ]
    diff_lines = []
    if "world_diff" in patch_result_obj:
        diff = patch_result_obj["world_diff"]
        diff_lines.extend(
            [
                "World diff:"
                + (
                    f" entities +{len(diff['entities']['added'])}"
                    f"/-{len(diff['entities']['removed'])},"
                )
                + (
                    f" events +{len(diff['events']['added'])}"
                    f"/-{len(diff['events']['removed'])},"
                )
                + f" changed_events={len(diff['events']['changed'])}",
            ]
        )
    if "constraint_diff" in patch_result_obj:
        constraint = patch_result_obj["constraint_diff"]
        diff_lines.extend(
            [
                "Constraint diff:"
                + f" old_total={constraint['counts']['old_total']},"
                + f" new_total={constraint['counts']['new_total']},"
                + f" added={constraint['counts']['added']},"
                + f" removed={constraint['counts']['removed']},"
                + f" changed={constraint['counts']['changed']}",
            ]
        )
    receipt_lines = [
        f"patch_sha256: {patch_result_obj['receipts']['patch_sha256']}",
        f"op_count: {patch_result_obj['receipts']['op_count']}",
        f"ledger_dir: {patch_result_obj['ledger_dir']}",
    ]
    if mode == "full":
        receipt_lines.extend([f"- {op['op_id']} {op['op']}" for op in patch_obj["ops"]])

    sections = [
        {"title": "Summary", "lines": verification_lines},
        {"title": "Operation counts", "lines": count_lines},
        {"title": "Top affected ids", "lines": target_lines},
        {"title": "Diff summary", "lines": diff_lines},
        {"title": "Receipts", "lines": receipt_lines},
    ]
    bounded = _line_budget(sections, max_lines)
    narrative = {
        "narrative_version": "2.0",
        "mode": mode,
        "text": _render_text(bounded).replace("\r\n", "\n").replace("\r", "\n"),
        "sections": bounded,
        "summary": {
            "patch_id": patch_obj["patch_id"],
            "op_count": len(patch_obj["ops"]),
            "verification_old": patch_result_obj["verification_change"]["old"],
            "verification_new": patch_result_obj["verification_change"]["new"],
            "top_targets": top_targets,
        },
    }
    validate(narrative, "schemas/world_patch_narrative_v2.schema.json")
    return narrative

from pathlib import Path

from proposal.bundle_from_pack import build_evidence_bundle_from_pack
from proposal.evidence_pack import build_evidence_pack
from proposal.world_propose import (
    normalize_query_tokens,
    propose_world_model,
    propose_world_model_from_artifacts,
    score_event,
)


def test_world_model_from_artifacts_stays_focused_to_bundle_selection(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    for index in range(50):
        if index in {7, 21, 44}:
            (docs_dir / f"relevant_{index}.md").write_text(
                "# Access Control\n"
                f"- access control item {index} uses `API_KEYS`.\n",
                encoding="utf-8",
            )
        else:
            (docs_dir / f"noise_{index}.md").write_text(
                "# General Notes\n"
                f"- unrelated note {index}.\n",
                encoding="utf-8",
            )

    pack_obj, _ = build_evidence_pack(
        str(docs_dir),
        root_hint="docs",
        max_chars=400,
        overlap_chars=0,
    )
    bundle_obj, _bundle_bytes, _bundle_sha256 = build_evidence_bundle_from_pack(
        pack_obj,
        prompt="Focus on access control",
        params={"mode": "keyword", "query": "access control", "max_chunks": 3},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="keyword",
        query="access control",
        max_chunks=3,
    )

    full_world = propose_world_model(pack_obj)
    focused_world = propose_world_model_from_artifacts(
        pack_obj,
        bundle_obj["artifacts"],
        query="access control",
    )

    assert len(bundle_obj["artifacts"]) == 3
    assert len(focused_world["events"]) <= 3
    assert len(full_world["events"]) > len(focused_world["events"])
    assert len(focused_world["events"]) == len(
        {event["event_id"] for event in focused_world["events"]}
    )
    focused_chunk_ids = {
        artifact["chunk_id"]
        for artifact in bundle_obj["artifacts"]
    }
    assert focused_chunk_ids
    assert {
        evidence_ref["chunk_id"]
        for event in focused_world["events"]
        for evidence_ref in event["evidence"]
    } <= focused_chunk_ids


def test_world_filtering_excludes_unrelated_lines_deterministically(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "notes.md").write_text(
        "# Checklist\n"
        "- rotate meeting chairs\n"
        "- access control review uses `API_KEYS`\n"
        "- buy groceries\n"
        "- credential reset planned\n",
        encoding="utf-8",
    )

    pack_obj, _ = build_evidence_pack(
        str(docs_dir),
        root_hint="docs",
        max_chars=400,
        overlap_chars=0,
    )
    bundle_obj, _bundle_bytes, _bundle_sha256 = build_evidence_bundle_from_pack(
        pack_obj,
        prompt="Focus on access control",
        params={"mode": "all", "query": "access control", "max_chunks": 10},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="all",
        query="access control",
        max_chunks=10,
    )

    world = propose_world_model_from_artifacts(
        pack_obj,
        bundle_obj["artifacts"],
        query="access control",
    )

    assert sorted(event["action"] for event in world["events"]) == [
        "access control review uses `API_KEYS`",
        "credential reset planned",
    ]


def test_world_focus_scoring_is_deterministic_and_bounded(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    lines = []
    for index in range(12):
        lines.append(f"- access control review {index} keeps `API_KEYS` guarded\n")
    lines.append("- API_KEYS are environment only\n")
    lines.append("- API_KEYS are never in source\n")
    (docs_dir / "focus.md").write_text(
        "# Access Policy\n" + "".join(lines),
        encoding="utf-8",
    )

    pack_obj, _ = build_evidence_pack(
        str(docs_dir),
        root_hint="docs",
        max_chars=4000,
        overlap_chars=0,
    )
    bundle_obj, _bundle_bytes, _bundle_sha256 = build_evidence_bundle_from_pack(
        pack_obj,
        prompt="Focus on access control",
        params={"mode": "all", "query": "access control", "max_chunks": 5},
        created_utc="2026-03-01T12:00:00Z",
        core_version="0.3.0",
        ruleset_id="ruleset.core.v1",
        mode="all",
        query="access control",
        max_chunks=5,
    )

    first = propose_world_model_from_artifacts(
        pack_obj,
        bundle_obj["artifacts"],
        query="access control",
        max_chunks=5,
        max_events=10,
    )
    second = propose_world_model_from_artifacts(
        pack_obj,
        bundle_obj["artifacts"],
        query="access control",
        max_chunks=5,
        max_events=10,
    )

    assert first == second
    assert len(first["events"]) > 10
    assert len(first["events"]) <= 12
    assert "API_KEYS are environment only" in {
        event["action"] for event in first["events"]
    }
    assert "API_KEYS are never in source" in {
        event["action"] for event in first["events"]
    }


def test_world_focus_score_event_prefers_query_token_matches():
    query_tokens = normalize_query_tokens("access control")
    stronger = {
        "event_id": "event:" + ("1" * 64),
        "type": "Access",
        "time": {"kind": "unknown"},
        "actors": [],
        "objects": ["entity:" + ("a" * 64)],
        "action": "access control review uses `API_KEYS`",
        "state": None,
        "evidence": [],
        "_entity_label_tokens": ["access", "control"],
    }
    weaker = {
        "event_id": "event:" + ("2" * 64),
        "type": "Other",
        "time": {"kind": "unknown"},
        "actors": [],
        "objects": [],
        "action": "general note",
        "state": None,
        "evidence": [],
        "_entity_label_tokens": [],
    }

    assert score_event(stronger, query_tokens) > score_event(weaker, query_tokens)

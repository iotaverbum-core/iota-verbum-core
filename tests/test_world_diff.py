from core.diff import compute_world_diff_v2
from core.engine import run_narrative_intelligence_v2
from proposal.evidence_pack import build_evidence_pack


def _run(text: str, tmp_path, name: str):
    docs = tmp_path / name
    docs.mkdir()
    (docs / "case.txt").write_text(text, encoding="utf-8")
    pack, _ = build_evidence_pack(str(docs), root_hint="docs")
    return run_narrative_intelligence_v2(pack, {"mode": "deterministic"})


def test_world_diff_detects_new_event(tmp_path):
    old = _run("2026-01-01 transfer approved.\n", tmp_path, "a")
    new = _run(
        "2026-01-01 transfer approved.\n2026-01-02 fraud escalated.\n", tmp_path, "b"
    )
    diff = compute_world_diff_v2(old, new)
    assert diff["diff_report"]["newly_introduced_events"]

"""Tests for the Provenant Phase 1 demo.

Protects the product promise: the demo runs end to end on bundled data, finds
the planted compliance gap and silent regressions, renders the customer-facing
report, is deterministic, and fails clearly on bad input.
"""

from __future__ import annotations

import json
from pathlib import Path

from provenant.demo import main, run_demo


def test_demo_runs_and_finds_planted_signals(tmp_path: Path):
    result = run_demo(out_dir=tmp_path / "out")
    h = result["headline"]
    assert h["records_sealed"] == 12
    assert h["records_verified"] == 12
    assert h["all_verified"] is True
    # Exactly one true compliance gap (a denial with no reason codes) and two
    # silently flipped decisions across the model change.
    assert h["compliance_gaps"] == 1
    assert h["silent_regressions"] == 2


def test_demo_writes_all_artifacts(tmp_path: Path):
    result = run_demo(out_dir=tmp_path / "out")
    for key in ("examiner_pack", "audit_report_md", "audit_report_html"):
        assert Path(result[key]).exists()
    report = Path(result["audit_report_md"]).read_text(encoding="utf-8")
    assert "Provenant Audit-Ready Report" in report
    assert "ADVERSE_ACTION_NO_REASONS" in report  # the planted compliance gap
    assert "application-1001" in report  # a silently flipped decision
    html = Path(result["audit_report_html"]).read_text(encoding="utf-8")
    assert "<table>" in html and "Silent regressions" in html


def test_demo_is_deterministic(tmp_path: Path):
    first = run_demo(out_dir=tmp_path / "a")
    second = run_demo(out_dir=tmp_path / "b")
    assert first["pack_sha256"] == second["pack_sha256"]
    for name in ("audit_report.md", "audit_report.html", "examiner_pack.json"):
        assert (tmp_path / "a" / name).read_bytes() == (
            tmp_path / "b" / name
        ).read_bytes()


def test_demo_cli_exit_zero(tmp_path: Path):
    assert main(["--out", str(tmp_path / "out")]) == 0


def test_demo_rejects_invalid_portfolio(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"tenant_id": "x", "snapshots": []}), encoding="utf-8")
    assert main(["--portfolio", str(bad), "--out", str(tmp_path / "out")]) == 2

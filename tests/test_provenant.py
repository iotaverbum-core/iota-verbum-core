"""Tests for the Provenant decision-record MVP core.

Covers the four product primitives end to end: seal (deterministic +
compliance check), verify (tamper-evidence), diff (silent-regression
detection), and export (deterministic examiner pack).
"""

from __future__ import annotations

import json
from pathlib import Path

from provenant import (
    build_examiner_pack,
    diff_records,
    seal_decision,
    verify_record,
    write_record,
)
from provenant.cli import main as cli_main

CREATED = "2026-06-28T12:00:00Z"


def _deny_record(record_id="app-001", subject="application-001", with_reasons=True):
    return seal_decision(
        record_id=record_id,
        tenant_id="lender-acme",
        created_utc=CREATED,
        subject_ref=subject,
        decision={"outcome": "DENY", "score": 0.31},
        model={"name": "underwriter-llm", "version": "2026-05-01"},
        evidence=[{"ref": "doc:paystub", "sha256": "a" * 64}],
        reason_codes=(
            [
                {
                    "code": "R01",
                    "text": "Debt-to-income ratio above policy threshold",
                    "regulation": "ECOA / Reg B",
                    "evidence_ref": "doc:paystub",
                }
            ]
            if with_reasons
            else []
        ),
        governance={"audit_ready": True, "adverse_action_required": True},
    )


def test_seal_is_deterministic(tmp_path: Path):
    a = write_record(_deny_record(), tmp_path / "a")
    b = write_record(_deny_record(), tmp_path / "b")
    assert a["record_sha256"] == b["record_sha256"]
    assert a["content_sha256"] == b["content_sha256"]
    assert (tmp_path / "a" / "record.json").read_bytes() == (
        tmp_path / "b" / "record.json"
    ).read_bytes()


def test_verify_passes_for_untampered_record(tmp_path: Path):
    write_record(_deny_record(), tmp_path / "rec")
    result = verify_record(tmp_path / "rec")
    assert result["verified"] is True
    assert result["file_match"] and result["content_match"]


def test_verify_detects_tampering(tmp_path: Path):
    write_record(_deny_record(), tmp_path / "rec")
    record_path = tmp_path / "rec" / "record.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["decision"]["outcome"] = "APPROVE"  # flip the decision after sealing
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    result = verify_record(tmp_path / "rec")
    assert result["verified"] is False
    # Content hash no longer matches the sealed content hash.
    assert result["content_match"] is False


def test_compliance_flags_adverse_action_without_reasons(tmp_path: Path):
    record = _deny_record(with_reasons=False)
    warnings = record["compliance_warnings"]
    assert any(w["code"] == "ADVERSE_ACTION_NO_REASONS" for w in warnings)

    # And a compliant denial produces no adverse-action warning.
    ok = _deny_record(with_reasons=True)
    assert not any(
        w["code"] == "ADVERSE_ACTION_NO_REASONS" for w in ok["compliance_warnings"]
    )


def test_diff_detects_silent_regression():
    prior = _deny_record(record_id="app-001-v1")
    current = seal_decision(
        record_id="app-001-v2",
        tenant_id="lender-acme",
        created_utc=CREATED,
        subject_ref="application-001",  # same subject
        decision={"outcome": "APPROVE", "score": 0.62},  # flipped
        model={"name": "underwriter-llm", "version": "2026-06-01"},  # new model
    )
    result = diff_records(prior, current)
    assert result["regression"] is True
    assert result["severity"] == "high"
    assert result["outcome_changed"] is True
    assert result["model_changed"] is True
    assert result["score_delta"] == 0.31


def test_diff_no_regression_when_outcome_stable():
    prior = _deny_record(record_id="v1")
    current = _deny_record(record_id="v2")
    result = diff_records(prior, current)
    assert result["regression"] is False
    assert result["severity"] == "none"


def test_examiner_pack_is_deterministic_and_summarises(tmp_path: Path):
    write_record(_deny_record(record_id="a", subject="application-001"), tmp_path / "a")
    write_record(
        _deny_record(record_id="b", subject="application-002", with_reasons=False),
        tmp_path / "b",
    )

    pack1 = build_examiner_pack(
        [tmp_path / "a", tmp_path / "b"],
        tenant_id="lender-acme",
        generated_utc=CREATED,
    )
    pack2 = build_examiner_pack(
        [tmp_path / "b", tmp_path / "a"],  # order-independent
        tenant_id="lender-acme",
        generated_utc=CREATED,
    )
    assert pack1["pack_sha256"] == pack2["pack_sha256"]
    assert pack1["summary"]["record_count"] == 2
    assert pack1["summary"]["verified_count"] == 2
    assert pack1["summary"]["adverse_action"]["adverse_decisions"] == 2
    assert pack1["summary"]["adverse_action"]["with_reason_codes"] == 1
    assert pack1["summary"]["adverse_action"]["coverage"] == 0.5
    assert pack1["summary"]["compliance_warning_count"] >= 1


def test_cli_seal_verify_diff_export(tmp_path: Path):
    spec = {
        "record_id": "app-100",
        "tenant_id": "lender-acme",
        "created_utc": CREATED,
        "subject_ref": "application-100",
        "decision": {"outcome": "DENY", "score": 0.4},
        "model": {"name": "underwriter-llm", "version": "2026-05-01"},
        "reason_codes": [{"code": "R02", "text": "Insufficient credit history"}],
        "governance": {"adverse_action_required": True},
    }
    spec_path = tmp_path / "decision.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    rec_dir = tmp_path / "runs" / "app-100"
    assert cli_main(["seal", "--input", str(spec_path), "--out", str(rec_dir)]) == 0
    assert cli_main(["verify", str(rec_dir)]) == 0

    pack_path = tmp_path / "pack.json"
    assert (
        cli_main(
            [
                "export",
                "--tenant",
                "lender-acme",
                "--generated-utc",
                CREATED,
                "--out",
                str(pack_path),
                str(rec_dir),
            ]
        )
        == 0
    )
    assert pack_path.exists()

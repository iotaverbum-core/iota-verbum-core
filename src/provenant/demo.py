"""Provenant Phase 1 demo: a complete, sellable input -> report path.

Runs the full Provenant story on a bundled sample lending portfolio:

    seal each decision -> verify chain of custody -> diff model v1 vs v2
    -> flag compliance gaps -> render a customer-facing audit report.

It is deterministic and offline. Run it with::

    python -m provenant.demo            # writes to outputs/provenant_demo
    ./scripts/provenant_demo.sh
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.attestation import canonicalize_json
from provenant.diff import diff_records
from provenant.export import build_examiner_pack, write_examiner_pack
from provenant.record import (
    ADVERSE_OUTCOMES,
    seal_decision,
    verify_record,
    write_record,
)
from provenant.report import build_report_model, render_html, render_markdown

BUNDLED_PORTFOLIO = Path(__file__).resolve().parent / "sample_data" / "portfolio.json"
DEFAULT_OUT = Path("outputs/provenant_demo")


def _validate_portfolio(portfolio: dict) -> None:
    snapshots = portfolio.get("snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise ValueError("portfolio must contain a non-empty 'snapshots' list")
    for snap in snapshots:
        if not snap.get("decisions"):
            raise ValueError(
                f"snapshot '{snap.get('label')}' has no decisions"
            )
        if "model" not in snap or "created_utc" not in snap:
            raise ValueError(
                f"snapshot '{snap.get('label')}' missing model/created_utc"
            )


def run_demo(
    portfolio_path: Path | None = None,
    out_dir: Path | None = None,
    generated_utc: str | None = None,
) -> dict:
    """Run the demo end to end and write artifacts. Returns a result summary."""
    portfolio_path = Path(portfolio_path or BUNDLED_PORTFOLIO)
    out_dir = Path(out_dir or DEFAULT_OUT)
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    _validate_portfolio(portfolio)

    tenant_id = portfolio.get("tenant_id", "demo-tenant")
    generated_utc = generated_utc or portfolio.get(
        "generated_utc", "1970-01-01T00:00:00Z"
    )
    records_dir = out_dir / "records"

    records_summary: list[dict] = []
    record_dirs: list[Path] = []
    sealed_by_subject: dict[str, dict[str, dict]] = {}
    models_compared: list[str] = []

    for snap in portfolio["snapshots"]:
        label = snap["label"]
        models_compared.append(snap["model"].get("version", label))
        for decision in snap["decisions"]:
            subject = decision["subject_ref"]
            record_id = f"{label}-{subject}"
            outcome = str(decision["decision"].get("outcome", "")).upper()
            record = seal_decision(
                record_id=record_id,
                tenant_id=tenant_id,
                created_utc=snap["created_utc"],
                subject_ref=subject,
                decision=decision["decision"],
                model=snap["model"],
                evidence=decision.get("evidence"),
                reason_codes=decision.get("reason_codes"),
                governance={
                    "audit_ready": True,
                    # Adverse-action notice is only required for adverse outcomes.
                    "adverse_action_required": outcome in ADVERSE_OUTCOMES,
                },
            )
            record_dir = records_dir / record_id
            written = write_record(record, record_dir)
            verification = verify_record(record_dir)
            record_dirs.append(record_dir)
            sealed_by_subject.setdefault(subject, {})[label] = record
            records_summary.append(
                {
                    "record_id": record_id,
                    "subject_ref": subject,
                    "outcome": record["decision"].get("outcome"),
                    "record_sha256": written["record_sha256"],
                    "verified": verification["verified"],
                    "compliance_warnings": record["compliance_warnings"],
                }
            )

    # Diff the first two snapshots per subject (v1 -> v2).
    labels = [snap["label"] for snap in portfolio["snapshots"]]
    diffs: list[dict] = []
    if len(labels) >= 2:
        prior_label, current_label = labels[0], labels[1]
        for subject, by_label in sorted(sealed_by_subject.items()):
            if prior_label in by_label and current_label in by_label:
                diffs.append(
                    diff_records(by_label[prior_label], by_label[current_label])
                )

    pack = build_examiner_pack(
        record_dirs, tenant_id=tenant_id, generated_utc=generated_utc
    )

    model = build_report_model(
        tenant_id=tenant_id,
        generated_utc=generated_utc,
        models_compared=models_compared,
        records=records_summary,
        diffs=diffs,
        verified_count=pack["summary"]["verified_count"],
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    pack_path = out_dir / "examiner_pack.json"
    md_path = out_dir / "audit_report.md"
    html_path = out_dir / "audit_report.html"
    write_examiner_pack(pack, pack_path)
    md_path.write_text(render_markdown(model), encoding="utf-8", newline="\n")
    html_path.write_text(render_html(model), encoding="utf-8", newline="\n")
    (out_dir / "report_model.json").write_bytes(canonicalize_json(model))

    return {
        "out_dir": str(out_dir),
        "examiner_pack": str(pack_path),
        "audit_report_md": str(md_path),
        "audit_report_html": str(html_path),
        "headline": model["headline"],
        "pack_sha256": pack["pack_sha256"],
    }


def _print_summary(result: dict) -> None:
    h = result["headline"]
    print("Provenant demo complete.\n")
    print(f"  Decisions sealed:     {h['records_sealed']}")
    print(
        f"  Independently verified: {h['records_verified']}"
        f"  ({'all verified' if h['all_verified'] else 'VERIFICATION FAILED'})"
    )
    print(f"  Compliance gaps:      {h['compliance_gaps']}")
    print(f"  Silent regressions:   {h['silent_regressions']}")
    print("\nArtifacts a founder can show on a sales call:")
    print(f"  Report (HTML):  {result['audit_report_html']}")
    print(f"  Report (MD):    {result['audit_report_md']}")
    print(f"  Examiner pack:  {result['examiner_pack']}")
    print(f"\n  pack_sha256:    {result['pack_sha256']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="provenant.demo", description="Run the Provenant Phase 1 demo"
    )
    parser.add_argument("--portfolio", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--generated-utc", default=None)
    args = parser.parse_args(argv)

    try:
        result = run_demo(
            portfolio_path=args.portfolio,
            out_dir=args.out,
            generated_utc=args.generated_utc,
        )
    except (ValueError, KeyError) as exc:
        print(f"error: invalid portfolio input: {exc}", file=sys.stderr)
        return 2

    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

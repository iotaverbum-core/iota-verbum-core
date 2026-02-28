import json
from pathlib import Path

from deterministic_ai import main as run_pipeline
from scripts.generate_provenance_report import main as generate_report
from scripts.view_provenance import format_cli_report


def _build_sample_outputs(base: Path) -> tuple[Path, Path, Path]:
    out_dir = base / "sample"
    run_pipeline(
        [
            "--domain",
            "legal_contract",
            "--input-ref",
            "sample_contract",
            "--input-file",
            "data/legal_contract_sample/sample_contract.txt",
            "--timestamp",
            "2026-02-28T14:32:00Z",
            "--commit-ref",
            "e20fbd8",
            "--repo-tag",
            "v0.2.0-legal-domain",
            "--out",
            str(out_dir),
        ]
    )
    return (
        out_dir / "provenance.json",
        Path("data/legal_contract_sample/sample_contract.txt"),
        out_dir / "output.json",
    )


def test_cli_report_is_deterministic(tmp_path: Path):
    record_path, input_path, output_path = _build_sample_outputs(tmp_path)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    report_a = format_cli_report(record, record_path, input_path, output_path)
    report_b = format_cli_report(record, record_path, input_path, output_path)
    assert report_a == report_b
    assert "Status:        VERIFIED OK" in report_a


def test_html_report_is_deterministic(tmp_path: Path):
    record_path, _, _ = _build_sample_outputs(tmp_path)
    out_a = tmp_path / "report_a.html"
    out_b = tmp_path / "report_b.html"
    generate_report(["--record", str(record_path), "--out", str(out_a)])
    generate_report(["--record", str(record_path), "--out", str(out_b)])
    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")

from __future__ import annotations

from pathlib import Path


def test_integrity_docs_and_scripts_exist() -> None:
    required_paths = [
        "docs/INTEGRITY_PATH.md",
        "docs/CLONABLE_INTEGRITY.md",
        "docs/PROOF_TRACE_VIEWER.md",
        "docs/proof_trace_viewer.html",
        "scripts/clonable_integrity.ps1",
        "scripts/tamper_casefile.ps1",
    ]
    for path in required_paths:
        assert Path(path).is_file(), f"Missing required path: {path}"


def test_readme_references_trust_loop_entry_points() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "clonable_integrity.ps1" in readme
    assert "proof_trace_viewer.html" in readme
    assert "python -m core.casefile.inspect" in readme
    assert "python -m core.determinism.replay" in readme

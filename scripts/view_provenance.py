from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.attestation import sha256_bytes
from deterministic_ai import REPO_ROOT
from scripts.generate_manifest import build_manifest_text

BANNER = "=" * 51


def _load_record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _record_input_path(record: dict) -> Path | None:
    input_meta = record.get("input_meta") or {}
    input_file = input_meta.get("input_file")
    if not input_file:
        return None
    return REPO_ROOT / Path(input_file)


def _verify_manifest() -> bool:
    manifest_path = REPO_ROOT / "MANIFEST.sha256"
    if not manifest_path.exists():
        return False
    return manifest_path.read_text(encoding="utf-8") == build_manifest_text()


def _verify_hash(path: Path | None, expected: str | None) -> bool | None:
    if path is None or not path.exists() or not expected:
        return None
    return sha256_bytes(path.read_bytes()) == expected


def _status_text(
    ok: bool | None, yes_text: str, no_text: str, unknown_text: str
) -> str:
    if ok is True:
        return yes_text
    if ok is False:
        return no_text
    return unknown_text


def _repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def build_summary(
    record: dict, input_path: Path | None, output_path: Path | None
) -> dict:
    input_ok = _verify_hash(input_path, record.get("input_sha256"))
    output_ok = _verify_hash(output_path, record.get("output_sha256"))
    manifest_ok = _verify_manifest()
    provenance_meta = record.get("provenance_meta") or {}
    verified = input_ok is True and output_ok is True and manifest_ok is True
    return {
        "domain": record.get("domain", "unknown"),
        "timestamp": provenance_meta.get("timestamp", "unknown"),
        "commit_ref": provenance_meta.get("commit_ref", "unknown"),
        "repo_tag": provenance_meta.get("repo_tag", "unknown"),
        "input_ok": input_ok,
        "output_ok": output_ok,
        "manifest_ok": manifest_ok,
        "status": "VERIFIED OK" if verified else "CHECK REQUIRED",
    }


def format_cli_report(
    record: dict,
    record_path: Path,
    input_path: Path | None,
    output_path: Path | None,
) -> str:
    summary = build_summary(record, input_path, output_path)
    lines = [
        BANNER,
        " IOTA VERBUM CORE - Provenance Record",
        BANNER,
        f" Domain:        {summary['domain']}",
        f" Timestamp:     {summary['timestamp']}",
        f" Status:        {summary['status']}",
        "",
        " INPUT",
        f"   Document:    {input_path.name if input_path else 'unknown'}",
        f"   Hash:        sha256:{record.get('input_sha256', 'unknown')}",
        "   Verified:    "
        + _status_text(
            summary["input_ok"],
            "YES - hash matches file on disk",
            "NO - hash mismatch",
            "UNKNOWN - file unavailable",
        ),
        "",
        " CODE STATE",
        f"   Commit:      {summary['commit_ref']}",
        f"   Tag:         {summary['repo_tag']}",
        "   Manifest:    "
        + _status_text(
            summary["manifest_ok"],
            "CURRENT - no drift detected",
            "STALE - drift detected",
            "UNKNOWN - manifest unavailable",
        ),
        "",
        " OUTPUT",
        f"   Artifact:    {output_path.name if output_path else 'output.json'}",
        f"   Hash:        sha256:{record.get('output_sha256', 'unknown')}",
        "   Verified:    "
        + _status_text(
            summary["output_ok"],
            "YES - output hash matches record",
            "NO - output hash mismatch",
            "UNKNOWN - output unavailable",
        ),
        "",
        " VERIFICATION COMMAND",
        "   python scripts/view_provenance.py --verify",
        f"     --record {record_path.as_posix()}",
    ]
    if input_path:
        lines.append(f"     --input {_repo_rel(input_path)}")
    if output_path:
        lines.append(f"     --output {output_path.as_posix()}")
    lines.append(BANNER)
    return "\n".join(lines) + "\n"


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_html_report(
    record: dict,
    record_path: Path,
    input_path: Path | None,
    output_path: Path | None,
) -> str:
    summary = build_summary(record, input_path, output_path)
    command_lines = [
        "python scripts/view_provenance.py --verify",
        f"--record {record_path.as_posix()}",
    ]
    if input_path:
        command_lines.append(f"--input {_repo_rel(input_path)}")
    if output_path:
        command_lines.append(f"--output {output_path.as_posix()}")
    command_text = " \\\n".join(command_lines)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>IOTA VERBUM CORE Provenance Report</title>
<style>
body {{
  background: #f5f1e8;
  color: #172026;
  font-family: Georgia, "Times New Roman", serif;
  margin: 0;
  padding: 32px;
}}
.report {{
  background: #fffdf7;
  border: 2px solid #172026;
  margin: 0 auto;
  max-width: 860px;
  padding: 32px;
}}
h1 {{
  font-size: 28px;
  margin: 0 0 12px;
}}
h2 {{
  border-top: 1px solid #172026;
  font-size: 16px;
  margin: 24px 0 12px;
  padding-top: 16px;
}}
dl {{
  display: grid;
  gap: 8px 16px;
  grid-template-columns: 160px 1fr;
  margin: 0;
}}
dt {{
  font-weight: 700;
}}
dd {{
  margin: 0;
}}
pre {{
  background: #efe7d6;
  padding: 16px;
  white-space: pre-wrap;
}}
</style>
</head>
<body>
<div class="report">
<h1>IOTA VERBUM CORE Provenance Record</h1>
<dl>
<dt>Domain</dt><dd>{_html_escape(summary["domain"])}</dd>
<dt>Timestamp</dt><dd>{_html_escape(summary["timestamp"])}</dd>
<dt>Status</dt><dd>{_html_escape(summary["status"])}</dd>
</dl>
<h2>Input</h2>
<dl>
<dt>Document</dt><dd>{_html_escape(input_path.name if input_path else "unknown")}</dd>
<dt>Hash</dt><dd>{_html_escape("sha256:" + record.get("input_sha256", "unknown"))}</dd>
<dt>Verified</dt><dd>{
        _html_escape(
            _status_text(
                summary["input_ok"],
                "YES - hash matches file on disk",
                "NO - hash mismatch",
                "UNKNOWN - file unavailable",
            )
        )
    }</dd>
</dl>
<h2>Code State</h2>
<dl>
<dt>Commit</dt><dd>{_html_escape(summary["commit_ref"])}</dd>
<dt>Tag</dt><dd>{_html_escape(summary["repo_tag"])}</dd>
<dt>Manifest</dt><dd>{
        _html_escape(
            _status_text(
                summary["manifest_ok"],
                "CURRENT - no drift detected",
                "STALE - drift detected",
                "UNKNOWN - manifest unavailable",
            )
        )
    }</dd>
</dl>
<h2>Output</h2>
<dl>
<dt>Artifact</dt><dd>{
        _html_escape(output_path.name if output_path else "output.json")
    }</dd>
<dt>Hash</dt><dd>{_html_escape("sha256:" + record.get("output_sha256", "unknown"))}</dd>
<dt>Verified</dt><dd>{
        _html_escape(
            _status_text(
                summary["output_ok"],
                "YES - output hash matches record",
                "NO - output hash mismatch",
                "UNKNOWN - output unavailable",
            )
        )
    }</dd>
</dl>
<h2>Verification Command</h2>
<pre>{_html_escape(command_text)}</pre>
</div>
</body>
</html>
"""
    return html.replace("\r\n", "\n").replace("\r", "\n")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="View and verify provenance records.")
    parser.add_argument("--record", required=True)
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)

    record_path = Path(args.record)
    record = _load_record(record_path)
    input_path = Path(args.input) if args.input else _record_input_path(record)
    output_path = (
        Path(args.output) if args.output else record_path.parent / "output.json"
    )
    report = format_cli_report(record, record_path, input_path, output_path)
    print(report, end="")

    if (
        args.verify
        and build_summary(record, input_path, output_path)["status"] != "VERIFIED OK"
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

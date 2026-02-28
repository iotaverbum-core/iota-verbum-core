from __future__ import annotations

import argparse
from pathlib import Path

from core.attestation import write_text
from scripts.view_provenance import (
    _load_record,
    _record_input_path,
    generate_html_report,
)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Generate a deterministic HTML provenance report."
    )
    parser.add_argument("--record", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--input")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    record_path = Path(args.record)
    record = _load_record(record_path)
    input_path = Path(args.input) if args.input else _record_input_path(record)
    output_path = (
        Path(args.output) if args.output else record_path.parent / "output.json"
    )
    write_text(
        Path(args.out),
        generate_html_report(record, record_path, input_path, output_path),
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_src_to_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="-")
    args = parser.parse_args(argv)

    _add_src_to_syspath()
    from core.determinism.integrity import extract_ledger_dir_from_output

    ledger_dir = extract_ledger_dir_from_output(_read_text(args.path))
    if not ledger_dir:
        print("Unable to parse ledger_dir from demo output.", file=sys.stderr)
        return 2

    print(ledger_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

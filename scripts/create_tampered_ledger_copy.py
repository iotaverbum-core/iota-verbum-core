from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_src_to_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger_dir")
    args = parser.parse_args(argv)

    _add_src_to_syspath()
    from core.determinism.integrity import create_tampered_ledger_copy

    tampered = create_tampered_ledger_copy(Path(args.ledger_dir))
    print(tampered.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

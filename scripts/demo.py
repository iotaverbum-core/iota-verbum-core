from __future__ import annotations

import sys
from pathlib import Path


def _add_src_to_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    sys.path.insert(0, str(src))


def main() -> int:
    _add_src_to_syspath()
    from proposal.cli_demo import main as demo_main

    return demo_main()


if __name__ == "__main__":
    raise SystemExit(main())

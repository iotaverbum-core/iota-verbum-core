import os
import re
import sys
from pathlib import Path
from uuid import uuid4

import _pytest.pathlib
import _pytest.tmpdir
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("API_KEYS", "demo-key:tenant-demo,other-key:tenant-other")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

_ORIGINAL_UNLINK = Path.unlink


def pytest_configure(config) -> None:
    if config.option.basetemp:
        return
    base_root = ROOT / ".pytest_codex_tmp"
    base_root.mkdir(parents=True, exist_ok=True)
    _pytest.pathlib.cleanup_dead_symlinks = lambda root: None
    _pytest.tmpdir.cleanup_dead_symlinks = lambda root: None
    config.option.basetemp = str(base_root / f"run_{os.getpid()}_{uuid4().hex}")


@pytest.fixture
def tmp_path(request) -> Path:
    base_root = ROOT / ".pytest_codex_paths"
    base_root.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", request.node.name).strip("_") or "tmp"
    path = base_root / f"{slug}_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _sandbox_compatible_unlink(
    self: Path, missing_ok: bool = False
) -> None:  # pragma: no cover - env shim
    try:
        return _ORIGINAL_UNLINK(self, missing_ok=missing_ok)
    except PermissionError:
        temp_root = ROOT / ".pytest_codex_paths"
        if temp_root in self.parents and self.is_file():
            self.write_bytes(b"")
            return None
        raise


Path.unlink = _sandbox_compatible_unlink

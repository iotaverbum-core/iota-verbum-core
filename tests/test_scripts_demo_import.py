import subprocess
import sys
from pathlib import Path


def test_scripts_demo_exports_main_symbol():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "demo.py"
    namespace: dict[str, object] = {}

    exec(script_path.read_text(encoding="utf-8"), namespace)

    assert "main" in namespace
    assert callable(namespace["main"])


def test_scripts_demo_help_returns_zero():
    completed = subprocess.run(
        [sys.executable, "scripts/demo.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "usage:" in completed.stdout.lower()

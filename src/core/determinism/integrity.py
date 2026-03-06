from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

_INLINE_LEDGER_RE = re.compile(r"^\s*ledger_dir:\s*(.+?)\s*$", re.IGNORECASE)
_REPLAY_COMMAND_RE = re.compile(
    r"^\s*python(?:\d+(?:\.\d+)*)?\s+-m\s+core\.determinism\.replay\s+(\S+)"
)


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) < 2:
        return value
    if (value[0] == "'" and value[-1] == "'") or (
        value[0] == '"' and value[-1] == '"'
    ):
        return value[1:-1]
    return value


def _new_tamper_root(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(20):
        candidate = base_dir / f"ledger_tamper_{uuid4().hex}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("unable to allocate tamper root directory")


def extract_ledger_dir_from_output(report_text: str) -> str | None:
    lines = report_text.splitlines()

    for line in lines:
        match = _INLINE_LEDGER_RE.match(line)
        if match:
            return _strip_wrapping_quotes(match.group(1).strip())

    for index, line in enumerate(lines):
        if line.strip().lower() != "ledger dir":
            continue
        for candidate in lines[index + 1 :]:
            candidate = candidate.strip()
            if candidate:
                return _strip_wrapping_quotes(candidate)

    for line in lines:
        match = _REPLAY_COMMAND_RE.match(line.strip())
        if match:
            return _strip_wrapping_quotes(match.group(1).strip())

    return None


def create_tampered_ledger_copy(
    ledger_dir: Path, *, tamper_root: Path | None = None
) -> Path:
    source_dir = ledger_dir.resolve()
    if not source_dir.is_dir():
        raise ValueError(f"ledger_dir not found: {source_dir.as_posix()}")

    required_files = ("bundle.json", "output.json", "attestation.json")
    for filename in required_files:
        if not (source_dir / filename).is_file():
            raise ValueError(
                "ledger_dir missing required file: "
                f"{(source_dir / filename).as_posix()}"
            )

    auto_tamper_root = tamper_root is None
    if auto_tamper_root:
        repo_root = Path(__file__).resolve().parents[3]
        tamper_base = repo_root / "tmp_tamper"
        tamper_root = _new_tamper_root(tamper_base)
    else:
        tamper_root = tamper_root.resolve()
        tamper_root.mkdir(parents=True, exist_ok=True)

    tampered_ledger_dir = tamper_root / source_dir.name
    try:
        shutil.copytree(source_dir, tampered_ledger_dir)
    except PermissionError:
        if not auto_tamper_root:
            raise
        repo_root = Path(__file__).resolve().parents[3]
        tamper_base = repo_root / "tmp_tamper"
        tamper_root = _new_tamper_root(tamper_base)
        tampered_ledger_dir = tamper_root / source_dir.name
        shutil.copytree(source_dir, tampered_ledger_dir)

    # Deterministic tamper: append one LF byte to output.json.
    with (tampered_ledger_dir / "output.json").open("ab") as handle:
        handle.write(b"\n")

    return tampered_ledger_dir

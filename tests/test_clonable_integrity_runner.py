from __future__ import annotations

from core.determinism.integrity import extract_ledger_dir_from_output


def test_extract_ledger_dir_from_inline_field() -> None:
    text = "ledger_dir: outputs/demo/run/ledger/abc123\n"
    assert extract_ledger_dir_from_output(text) == "outputs/demo/run/ledger/abc123"


def test_extract_ledger_dir_from_ledger_dir_block() -> None:
    text = "World Narrative\n...\nLedger Dir\noutputs/demo/run/ledger/def456\n"
    assert extract_ledger_dir_from_output(text) == "outputs/demo/run/ledger/def456"


def test_extract_ledger_dir_from_replay_command_fallback() -> None:
    text = (
        "Replay Command\n"
        "python -m core.determinism.replay outputs/demo/run/ledger/ghi789 "
        "--strict-manifest\n"
    )
    assert extract_ledger_dir_from_output(text) == "outputs/demo/run/ledger/ghi789"

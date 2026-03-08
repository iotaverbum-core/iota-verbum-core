from __future__ import annotations

import json

from core.determinism import schema_validate


def test_validate_evidence_pack_schema_from_unrelated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    try:
        schema_validate.validate({}, "schemas/evidence_pack.schema.json")
    except ValueError as exc:
        assert "required property" in str(exc)
    else:
        raise AssertionError("Expected schema validation failure for empty evidence pack")


def test_schema_text_loads_from_packaged_resource(monkeypatch):
    monkeypatch.setattr(
        schema_validate,
        "_iter_schema_path_candidates",
        lambda _schema_path: iter(()),
    )

    raw_schema = json.loads(
        schema_validate._read_schema_text("schemas/evidence_pack.schema.json")
    )

    assert raw_schema["$id"].endswith("/schemas/evidence_pack.schema.json")

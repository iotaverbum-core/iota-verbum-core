import json
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes
from core.reasoning.cli_repair import main as cli_main
from core.reasoning.repair_narrative_v2 import render_repair_narrative_v2
from core.reasoning.repair_plan import compute_repair_plan

FIXTURES = Path("tests/fixtures")
_TEXTS = {
    "chunk:1": "Policy says API_KEYS are never in source.",
    "chunk:2": "Config keeps API_KEYS environment only.",
    "chunk:3": "API_KEYS access review pending actor and time.",
}
_OFFSETS = {
    "chunk:1": (0, 39),
    "chunk:2": (40, 79),
    "chunk:3": (80, 119),
}


def _fixture_base_output() -> dict:
    return json.loads((FIXTURES / "repair_base_needs_info.json").read_text("utf-8"))


def _write_base_source(tmp_path: Path, output_obj: dict) -> Path:
    evidence = {}
    for event in output_obj["world_model"]["events"]:
        for ref in event["evidence"]:
            evidence[ref["chunk_id"]] = ref["text_sha256"]

    bundle = {
        "bundle_version": "1.0",
        "created_utc": "2026-03-01T12:00:00Z",
        "inputs": {
            "prompt": "repair fixture",
            "params": {
                "query": "API_KEYS",
                "max_chunks": 5,
            },
        },
        "artifacts": [
            {
                "source_id": "doc:1",
                "chunk_id": chunk_id,
                "offset_start": _OFFSETS[chunk_id][0],
                "offset_end": _OFFSETS[chunk_id][1],
                "text": _TEXTS[chunk_id],
                "text_sha256": evidence[chunk_id],
            }
            for chunk_id in sorted(evidence)
        ],
        "toolchain": {
            "core_version": "0.4.0",
            "parser_versions": {},
            "schema_versions": {
                "attestation_record": "1.0",
                "evidence_bundle": "1.0",
                "evidence_pack": "1.0",
            },
        },
        "policy": {
            "ruleset_id": "ruleset.core.v1",
        },
    }
    manifest_sha256 = sha256_bytes(Path("MANIFEST.sha256").read_bytes())
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    sealed = finalize(
        bundle,
        output_obj,
        manifest_sha256=manifest_sha256,
        core_version="0.4.0",
        ruleset_id="ruleset.core.v1",
        created_utc="2026-03-01T12:00:00Z",
    )
    (base_dir / "output.json").write_bytes(sealed["output_bytes"])
    (base_dir / "attestation.json").write_bytes(sealed["attestation_bytes"])
    (base_dir / "evidence_bundle.json").write_bytes(sealed["bundle_bytes"])
    return base_dir / "output.json"


def _plan_for_fixture(output_obj: dict) -> dict:
    return compute_repair_plan(
        {
            "output": output_obj,
            "__meta__": {
                "output_sha256": "0" * 64,
                "attestation_sha256": "",
            },
        },
        "ruleset.core.v1",
    )


def test_repair_plan_deterministic():
    fixture = _fixture_base_output()
    first = _plan_for_fixture(fixture)
    second = _plan_for_fixture(fixture)

    first_bytes = dumps_canonical(first)
    second_bytes = dumps_canonical(second)
    expected_bytes = (FIXTURES / "repair_plan_expected.json").read_bytes()
    expected_narrative = (FIXTURES / "repair_narrative_expected.txt").read_text(
        encoding="utf-8"
    )

    assert first_bytes == second_bytes
    assert first_bytes == expected_bytes

    narrative = render_repair_narrative_v2(first, None, max_lines=120)
    assert narrative["text"] == expected_narrative
    assert "\r" not in narrative["text"]


def test_cli_repair_requires_approval(tmp_path: Path):
    base_output = _fixture_base_output()
    base_output["repair_hints"] = {
        "enrichment_path": str((tmp_path / "world_enrich.json").as_posix())
    }
    base_output_path = _write_base_source(tmp_path, base_output)

    exit_code = cli_main(
        [
            "--base",
            str(base_output_path.as_posix()),
            "--out-dir",
            str((tmp_path / "out").as_posix()),
            "--created-utc",
            "2026-03-05T00:00:00Z",
            "--core-version",
            "0.4.0",
            "--ruleset-id",
            "ruleset.core.v1",
            "--approve",
            "false",
            "--strict-manifest",
            "true",
            "--max-lines",
            "80",
        ]
    )
    assert exit_code == 2

    out_root = tmp_path / "out"
    run_dirs = [item for item in out_root.iterdir() if item.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "repair_plan.json").exists()
    assert (run_dir / "repair_narrative_v2.txt").exists()


def test_cli_repair_apply_enrichment_happy_path(tmp_path: Path):
    base_output = _fixture_base_output()
    enrichment_path = tmp_path / "world_enrich_example.json"
    base_output["repair_hints"] = {"enrichment_path": str(enrichment_path.as_posix())}
    base_output_path = _write_base_source(tmp_path, base_output)

    plan = _plan_for_fixture(base_output)
    enrichment_action = next(
        action for action in plan["actions"] if action["kind"] == "ADD_WORLD_ENRICHMENT"
    )
    missing_items = []
    for missing in enrichment_action["inputs"]["missing"]:
        value = None
        if missing["kind"] == "missing_actor":
            value = ["secops"]
        elif missing["kind"] == "missing_object":
            value = [
                "entity:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ]
        elif missing["kind"] == "missing_time":
            value = {"kind": "date", "value": "2026-03-03"}
        missing_items.append({**missing, "value": value})
    enrichment_template = {"version": "1.0", "missing": missing_items}
    enrichment_path.write_text(
        json.dumps(enrichment_template, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
        newline="\n",
    )

    exit_code = cli_main(
        [
            "--base",
            str(base_output_path.as_posix()),
            "--out-dir",
            str((tmp_path / "out").as_posix()),
            "--created-utc",
            "2026-03-05T00:00:00Z",
            "--core-version",
            "0.4.0",
            "--ruleset-id",
            "ruleset.core.v1",
            "--approve",
            "true",
            "--strict-manifest",
            "true",
            "--max-lines",
            "120",
        ]
    )
    assert exit_code == 0

    out_root = tmp_path / "out"
    run_dirs = [item for item in out_root.iterdir() if item.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    for filename in [
        "repair_plan.json",
        "repair_run_record.json",
        "repair_narrative_v2.json",
        "repair_narrative_v2.txt",
        "world_diff.json",
        "constraint_diff.json",
        "output.json",
        "attestation.json",
    ]:
        assert (run_dir / filename).exists()

    record = json.loads(
        (run_dir / "repair_run_record.json").read_text(encoding="utf-8")
    )
    assert record["replay"]["ok"] is True
    assert record["replay"]["strict_manifest"] is True
    assert record["verification"]["old"] == "VERIFIED_NEEDS_INFO"
    assert record["diffs"]["world_diff_present"] is True
    assert record["new"]["output_sha256"] != record["base"]["output_sha256"]

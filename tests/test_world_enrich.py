from pathlib import Path

from proposal.world_enrich import apply_world_enrichment, load_world_enrichment

FIXTURES = Path("tests/fixtures")


def _world_model() -> dict:
    return {
        "world_version": "1.0",
        "world_sha256": "a" * 64,
        "entities": [
            {
                "entity_id": "entity:" + ("a" * 64),
                "type": "Secret",
                "name": "API_KEYS",
                "aliases": [],
            }
        ],
        "events": [
            {
                "event_id": "event:" + ("1" * 64),
                "type": "Config",
                "time": {"kind": "unknown"},
                "actors": [],
                "objects": [],
                "action": "keys are environment only",
                "state": None,
                "evidence": [],
            },
            {
                "event_id": "event:" + ("2" * 64),
                "type": "PolicyChange",
                "time": {"kind": "date", "value": "2026-03-02"},
                "actors": ["release"],
                "objects": ["entity:" + ("a" * 64)],
                "action": "keys are never in source",
                "state": None,
                "evidence": [],
            },
        ],
        "relations": [],
        "unknowns": [],
        "conflicts": [],
    }


def test_load_world_enrichment_normalizes_and_is_deterministic():
    path = FIXTURES / "world_enrichment_example.json"
    first = load_world_enrichment(path)
    second = load_world_enrichment(path)

    assert first == second
    assert first["events"][0]["actors"] == ["ops", "secops"]
    assert first["events"][0]["objects"] == [
        "API_KEYS",
        "entity:" + ("a" * 64),
    ]


def test_apply_world_enrichment_merges_union_sorts_and_ignores_unknown_event():
    world_model = _world_model()
    enrichment = load_world_enrichment(FIXTURES / "world_enrichment_example.json")

    first = apply_world_enrichment(world_model, enrichment)
    second = apply_world_enrichment(world_model, enrichment)

    assert first == second
    assert first["events"][0]["actors"] == ["ops", "secops"]
    assert first["events"][0]["objects"] == [
        "API_KEYS",
        "entity:" + ("a" * 64),
    ]
    assert first["events"][0]["time"] == {"kind": "date", "value": "2026-03-01"}
    assert all(
        item["ref"].get("event_id") != "event:" + ("f" * 64)
        for item in first["unknowns"] + first["conflicts"]
    )


def test_apply_world_enrichment_keeps_existing_time_and_adds_conflict():
    world_model = _world_model()
    enrichment = {
        "version": "1.0",
        "events": [
            {
                "event_id": "event:" + ("2" * 64),
                "time": {"kind": "date", "value": "2026-03-03"},
            }
        ],
    }

    enriched = apply_world_enrichment(world_model, enrichment)

    assert enriched["events"][1]["time"] == {"kind": "date", "value": "2026-03-02"}
    assert {
        "kind": "ordering_conflict",
        "ref": {
            "event_id": "event:" + ("2" * 64),
            "source": "world_enrichment",
            "existing_time": {"kind": "date", "value": "2026-03-02"},
            "enrichment_time": {"kind": "date", "value": "2026-03-03"},
        },
        "reason": "enrichment time conflicts with existing event time",
    } in enriched["conflicts"]

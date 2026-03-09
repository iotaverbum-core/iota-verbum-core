from __future__ import annotations

import re
from typing import Any

from core.determinism.hashing import sha256_text
from core.determinism.schema_validate import validate

_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_WORD_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]{2,}\b")
_EVENT_HINTS = (
    "approved",
    "transferred",
    "reported",
    "blocked",
    "restored",
    "escalated",
    "failed",
    "paid",
)


def _ordered_chunks(evidence_pack: dict[str, Any]) -> list[dict[str, Any]]:
    docs = {doc["doc_id"]: doc for doc in evidence_pack.get("documents", [])}
    return sorted(
        evidence_pack.get("chunks", []),
        key=lambda c: (
            docs.get(c["doc_id"], {}).get("relpath", ""),
            c["doc_id"],
            c.get("index", 0),
            c["chunk_id"],
        ),
    )


def _ref(chunk: dict[str, Any], start: int, end: int) -> dict[str, Any]:
    return {
        "source_id": chunk["doc_id"],
        "chunk_id": chunk["chunk_id"],
        "offset_start": chunk["offset_start"] + start,
        "offset_end": chunk["offset_start"] + end,
        "text_sha256": chunk["text_sha256"],
    }


def extract_semantic_artifacts(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    entities: dict[str, dict[str, Any]] = {}
    events: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    temporal_anchors: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    source_references: list[dict[str, Any]] = []

    for chunk in _ordered_chunks(evidence_pack):
        text = chunk["text"]
        for m in _WORD_RE.finditer(text):
            surface = m.group(0)
            key = surface.lower()
            entity = entities.setdefault(
                key,
                {
                    "entity_id": f"sem_entity:{sha256_text(key)}",
                    "label": "Unknown",
                    "canonical_name": surface,
                    "mentions": [],
                },
            )
            entity["mentions"].append(
                {
                    "surface": surface,
                    "span": [m.start(), m.end()],
                    "source_ref": _ref(chunk, m.start(), m.end()),
                }
            )

        for m in _DATE_RE.finditer(text):
            anchor_seed = f"{chunk['chunk_id']}:{m.group(0)}:{m.start()}"
            temporal_anchors.append(
                {
                    "anchor_id": f"time:{sha256_text(anchor_seed)}",
                    "value": m.group(0),
                    "kind": "date",
                    "source_ref": _ref(chunk, m.start(), m.end()),
                }
            )

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for idx, line in enumerate(lines):
            line_lower = line.lower()
            if any(hint in line_lower for hint in _EVENT_HINTS):
                event_seed = f"{chunk['chunk_id']}:{idx}:{line}"
                event_id = f"sem_event:{sha256_text(event_seed)}"
                events.append(
                    {
                        "event_id": event_id,
                        "description": line,
                        "temporal_anchor": next(
                            (
                                a["anchor_id"]
                                for a in temporal_anchors
                                if a["source_ref"]["chunk_id"] == chunk["chunk_id"]
                                and a["value"] in line
                            ),
                            None,
                        ),
                        "source_ref": _ref(
                            chunk,
                            text.find(line),
                            text.find(line) + len(line),
                        ),
                    }
                )
            if any(
                token in line_lower
                for token in ("must", "should", "never", "required", "shall")
            ):
                claim_seed = f"{chunk['chunk_id']}:{idx}:{line}"
                claim_id = f"claim:{sha256_text(claim_seed)}"
                polarity = "negative" if "never" in line_lower else "positive"
                claims.append(
                    {
                        "claim_id": claim_id,
                        "text": line,
                        "polarity": polarity,
                        "source_ref": _ref(
                            chunk,
                            text.find(line),
                            text.find(line) + len(line),
                        ),
                    }
                )

    ordered_entities = sorted(entities.values(), key=lambda e: e["entity_id"])
    for entity in ordered_entities:
        entity["mentions"] = sorted(
            entity["mentions"],
            key=lambda m: (m["source_ref"]["source_id"], m["span"][0], m["span"][1]),
        )

    if ordered_entities and events:
        for event in sorted(events, key=lambda e: e["event_id"]):
            actor = ordered_entities[0]["entity_id"]
            relation_id = f"rel:{sha256_text(actor + '|' + event['event_id'])}"
            relations.append(
                {
                    "relation_id": relation_id,
                    "from_id": actor,
                    "to_id": event["event_id"],
                    "type": "participates_in",
                    "source_ref": event["source_ref"],
                }
            )

    source_references = sorted(
        [
            *{
                (
                    r["source_id"],
                    r["chunk_id"],
                    r["offset_start"],
                    r["offset_end"],
                    r["text_sha256"],
                ): r
                for r in [c["source_ref"] for c in claims]
                + [e["source_ref"] for e in events]
            }.values()
        ],
        key=lambda r: (
            r["source_id"],
            r["chunk_id"],
            r["offset_start"],
            r["offset_end"],
        ),
    )

    result = {
        "schema_version": "2.0",
        "entities": ordered_entities,
        "events": sorted(events, key=lambda e: e["event_id"]),
        "relations": sorted(relations, key=lambda r: r["relation_id"]),
        "temporal_anchors": sorted(temporal_anchors, key=lambda t: t["anchor_id"]),
        "claims": sorted(claims, key=lambda c: c["claim_id"]),
        "source_references": source_references,
        "extraction_provenance": {
            "extractor": "core.semantic.pipeline.extract_semantic_artifacts",
            "evidence_pack_sha256": evidence_pack.get("pack_sha256", ""),
            "deterministic_mode": True,
        },
    }
    validate(result, "schemas/semantic_extraction.schema.json")
    return result

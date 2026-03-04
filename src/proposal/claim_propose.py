from __future__ import annotations

import json
import re
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_text
from core.determinism.schema_validate import validate
from proposal.text_normalize import normalize_text

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$")
_BULLET_RE = re.compile(r"^(?:[-*]|\d+\.)\s+(.*)$")


def load_evidence_pack(path: str) -> dict:
    pack = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(pack, "schemas/evidence_pack.schema.json")
    return pack


def _claim_id(
    subject: str,
    predicate: str,
    obj: str,
    polarity: str,
    modality: str,
) -> str:
    fingerprint_source = "|".join(
        [
            normalize_text(subject),
            normalize_text(predicate),
            normalize_text(obj),
            polarity,
            modality,
        ]
    )
    return "claim:" + sha256_text(fingerprint_source)


def propose_claim_graph(evidence_pack: dict) -> dict:
    validate(evidence_pack, "schemas/evidence_pack.schema.json")

    claims = []
    for document in evidence_pack["documents"]:
        document_chunks = [
            chunk
            for chunk in evidence_pack["chunks"]
            if chunk["doc_id"] == document["doc_id"]
        ]
        document_chunks.sort(key=lambda chunk: (chunk["index"], chunk["chunk_id"]))

        for chunk in document_chunks:
            current_heading = "Document"
            line_order = 0
            for raw_line in normalize_text(chunk["text"]).split("\n"):
                heading_match = _HEADING_RE.match(raw_line)
                if heading_match:
                    current_heading = heading_match.group(2).strip() or "Document"
                    continue

                bullet_match = _BULLET_RE.match(raw_line)
                if bullet_match is None:
                    continue

                object_text = bullet_match.group(1).strip()
                if not object_text:
                    continue

                claim = {
                    "claim_id": _claim_id(
                        current_heading,
                        "states",
                        object_text,
                        "affirm",
                        "assert",
                    ),
                    "subject": current_heading,
                    "predicate": "states",
                    "object": object_text,
                    "polarity": "affirm",
                    "modality": "assert",
                    "qualifiers": {
                        "relpath": document["relpath"],
                        "chunk_index": chunk["index"],
                        "line_order": line_order,
                    },
                    "evidence": [
                        {
                            "source_id": document["doc_id"],
                            "chunk_id": chunk["chunk_id"],
                            "offset_start": chunk["offset_start"],
                            "offset_end": chunk["offset_end"],
                            "text_sha256": chunk["text_sha256"],
                        }
                    ],
                    "_sort_key": (
                        document["relpath"],
                        document["doc_id"],
                        chunk["index"],
                        line_order,
                    ),
                }
                claims.append(claim)
                line_order += 1

    claims.sort(key=lambda claim: claim["_sort_key"])
    for claim in claims:
        del claim["_sort_key"]
        validate(claim, "schemas/claim.schema.json")
        for evidence_ref in claim["evidence"]:
            validate(evidence_ref, "schemas/evidence_ref.schema.json")

    subject_groups: dict[str, list[dict]] = {}
    for claim in claims:
        subject_groups.setdefault(normalize_text(claim["subject"]), []).append(claim)

    edges = []
    for subject in sorted(subject_groups):
        ordered_claims = sorted(
            subject_groups[subject],
            key=lambda claim: (
                claim["qualifiers"]["relpath"],
                claim["qualifiers"]["chunk_index"],
                claim["qualifiers"]["line_order"],
                claim["claim_id"],
            ),
        )
        for earlier, later in zip(ordered_claims[:50], ordered_claims[1:51]):
            edges.append(
                {
                    "from_id": earlier["claim_id"],
                    "to_id": later["claim_id"],
                    "type": "supports",
                }
            )

    graph = {
        "graph_version": "1.0",
        "claims": claims,
        "edges": sorted(
            edges,
            key=lambda edge: (edge["type"], edge["from_id"], edge["to_id"]),
        ),
    }
    validate(graph, "schemas/claim_graph.schema.json")
    return graph


def dumps_claim_graph(graph: dict) -> bytes:
    return dumps_canonical(graph)

from __future__ import annotations

import json
import re
from pathlib import Path

from core.determinism.bundle import build_evidence_bundle
from core.determinism.hashing import sha256_text
from core.determinism.schema_validate import validate
from proposal.text_normalize import normalize_text


def load_pack(path: str) -> dict:
    pack = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(pack, "schemas/evidence_pack.schema.json")
    return pack


def _query_terms(query: str) -> list[str]:
    normalized = normalize_text(query).lower()
    return [term for term in re.split(r"\s+", normalized) if term]


def select_chunks(
    pack: dict,
    *,
    mode: str,
    query: str,
    max_chunks: int,
) -> list[dict]:
    validate(pack, "schemas/evidence_pack.schema.json")
    if max_chunks < 0:
        raise ValueError("max_chunks must be non-negative")

    docs_by_id = {
        document["doc_id"]: document
        for document in pack["documents"]
    }
    ordered_chunks = sorted(
        pack["chunks"],
        key=lambda chunk: (
            docs_by_id[chunk["doc_id"]]["relpath"],
            chunk["doc_id"],
            chunk["index"],
            chunk["chunk_id"],
        ),
    )
    if mode == "all":
        selected = ordered_chunks
    else:
        terms = _query_terms(query)
        if not terms:
            selected = []
        elif mode == "keyword":
            selected = [
                chunk
                for chunk in ordered_chunks
                if all(term in normalize_text(chunk["text"]).lower() for term in terms)
            ]
        elif mode == "topk":
            scored = []
            for chunk in ordered_chunks:
                normalized_text = normalize_text(chunk["text"]).lower()
                score = sum(normalized_text.count(term) for term in terms)
                if score > 0:
                    scored.append(
                        (
                            -score,
                            docs_by_id[chunk["doc_id"]]["relpath"],
                            chunk["doc_id"],
                            chunk["index"],
                            chunk["chunk_id"],
                            chunk,
                        )
                    )
            scored.sort()
            selected = [item[-1] for item in scored]
        else:
            raise ValueError(f"unsupported selection mode: {mode}")

    if max_chunks == 0:
        return []
    return selected[:max_chunks]


def build_evidence_bundle_from_pack(
    pack: dict,
    *,
    prompt: str,
    params: dict,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    mode: str = "all",
    query: str = "",
    max_chunks: int = 50,
) -> tuple[dict, bytes, str]:
    selected_chunks = select_chunks(
        pack,
        mode=mode,
        query=query,
        max_chunks=max_chunks,
    )
    artifacts = sorted(
        [
            {
                "source_id": chunk["doc_id"],
                "chunk_id": chunk["chunk_id"],
                "offset_start": chunk["offset_start"],
                "offset_end": chunk["offset_end"],
                "text": chunk["text"],
                "text_sha256": chunk["text_sha256"],
            }
            for chunk in selected_chunks
        ],
        key=lambda artifact: (
            artifact["source_id"],
            artifact["chunk_id"],
            artifact["offset_start"],
        ),
    )
    for artifact in artifacts:
        if sha256_text(artifact["text"]) != artifact["text_sha256"]:
            raise ValueError("artifact text_sha256 does not match artifact text")

    bundle_obj = {
        "bundle_version": "1.0",
        "created_utc": created_utc,
        "inputs": {
            "prompt": prompt,
            "params": params,
        },
        "artifacts": artifacts,
        "toolchain": {
            "core_version": core_version,
            "parser_versions": {},
            "schema_versions": {
                "attestation_record": "1.0",
                "evidence_bundle": "1.0",
                "evidence_pack": "1.0",
            },
        },
        "policy": {
            "ruleset_id": ruleset_id,
        },
    }
    bundle_bytes, bundle_sha256 = build_evidence_bundle(bundle_obj)
    return bundle_obj, bundle_bytes, bundle_sha256

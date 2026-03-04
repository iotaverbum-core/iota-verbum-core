from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from itertools import combinations

from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate


def normalize_text(s: str) -> str:
    normalized = unicodedata.normalize("NFC", s)
    collapsed = re.sub(r"\s+", " ", normalized.strip())
    return collapsed.lower()


def claim_fingerprint(claim: dict) -> str:
    fingerprint_input = {
        "subject": normalize_text(claim["subject"]),
        "predicate": normalize_text(claim["predicate"]),
        "object": normalize_text(claim["object"]),
        "polarity": claim["polarity"],
        "modality": claim["modality"],
    }
    return sha256_bytes(dumps_canonical(fingerprint_input))


def build_claim_graph(graph_obj: dict) -> dict:
    validate(graph_obj, "schemas/claim_graph.schema.json")
    return graph_obj


def _proposition_key(claim: dict) -> tuple[str, str, str]:
    return (
        normalize_text(claim["subject"]),
        normalize_text(claim["predicate"]),
        normalize_text(claim["object"]),
    )


def find_duplicates_and_contradictions(graph_obj: dict) -> dict:
    graph = build_claim_graph(graph_obj)
    fingerprint_groups: dict[str, list[dict]] = defaultdict(list)
    proposition_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)

    for claim in graph["claims"]:
        fingerprint_groups[claim_fingerprint(claim)].append(claim)
        proposition_groups[_proposition_key(claim)].append(claim)

    duplicates = []
    for claims in fingerprint_groups.values():
        ordered_claims = sorted(claims, key=lambda claim: claim["claim_id"])
        for claim_a, claim_b in combinations(ordered_claims, 2):
            duplicates.append(
                {
                    "claim_a": claim_a["claim_id"],
                    "claim_b": claim_b["claim_id"],
                    "reason": "matching normalized proposition fingerprint",
                }
            )

    contradictions = []
    for claims in proposition_groups.values():
        affirm_claims = sorted(
            (claim for claim in claims if claim["polarity"] == "affirm"),
            key=lambda claim: claim["claim_id"],
        )
        deny_claims = sorted(
            (claim for claim in claims if claim["polarity"] == "deny"),
            key=lambda claim: claim["claim_id"],
        )
        for claim_a in affirm_claims:
            for claim_b in deny_claims:
                contradictions.append(
                    {
                        "claim_a": claim_a["claim_id"],
                        "claim_b": claim_b["claim_id"],
                        "reason": "opposite polarity for same normalized proposition",
                    }
                )

    findings = {
        "findings_version": "1.0",
        "duplicates": sorted(
            duplicates,
            key=lambda item: (item["claim_a"], item["claim_b"], item["reason"]),
        ),
        "contradictions": sorted(
            contradictions,
            key=lambda item: (item["claim_a"], item["claim_b"], item["reason"]),
        ),
    }
    validate(findings, "schemas/graph_findings.schema.json")
    return findings

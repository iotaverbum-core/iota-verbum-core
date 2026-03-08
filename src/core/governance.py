from __future__ import annotations

# Governance metadata mappings — always rule-based, never inferred.
# These values map to EU AI Act and NIST AI RMF framework categories.

GOVERNANCE_METADATA = {
    "legal_contract": {
        "eu_ai_act_article": "Article 13 — Transparency obligations",
        "nist_rmf_function": "GOVERN",
        "risk_tier": "high",
        "audit_ready": True,
    },
    "nda": {
        "eu_ai_act_article": "Article 13 — Transparency obligations",
        "nist_rmf_function": "MEASURE",
        "risk_tier": "medium",
        "audit_ready": True,
    },
}


def build_neurosymbolic_boundary(domain: str) -> dict:
    return {
        "symbolic_components_used": [
            f"{domain}_extractor_v1",
            "schema_validator_v1",
            "governance_mapper_v1",
        ],
        "neural_components_used": [],
        "neural_override_count": 0,
        "symbolic_confidence": "high",
        "boundary_version": "1.0",
    }


def build_audit_controls(
    *,
    actor_id: str,
    added_at_utc: str,
    run_config: dict,
    schema_version: str,
    code_version: str,
    commit_hash: str,
    approval_hooks: list[str] | None = None,
) -> dict:
    return {
        "actor_id": actor_id,
        "evidence_added_at_utc": added_at_utc,
        "run_configuration": run_config,
        "schema_version": schema_version,
        "code_version": code_version,
        "commit_hash": commit_hash,
        "approval_hooks": sorted(approval_hooks or []),
    }

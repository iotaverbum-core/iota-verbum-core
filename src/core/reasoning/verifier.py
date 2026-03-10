from __future__ import annotations

import json
import logging
import os
from importlib.resources import files
from pathlib import Path

from core.determinism.bundle import build_evidence_bundle
from core.determinism.canonical_json import dumps_canonical
from core.determinism.hashing import sha256_bytes
from core.determinism.schema_validate import validate

_SECURITY_RELEVANT_EVENT_TYPES = {
    "Access",
    "Config",
    "Deployment",
    "Leak",
    "PolicyChange",
}
LOGGER = logging.getLogger(__name__)


class RulesetResolutionError(ValueError):
    def __init__(
        self,
        *,
        requested_ruleset: str,
        search_paths: list[str],
        run_id: str = "",
        sub_step: str = "ruleset_resolution",
    ):
        self.requested_ruleset = requested_ruleset
        self.search_paths = search_paths
        self.run_id = run_id
        self.sub_step = sub_step
        message = (
            f"ruleset '{requested_ruleset}' could not be resolved via deterministic "
            "search paths"
        )
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": "ruleset_not_found",
            "reason": "requested ruleset could not be resolved",
            "requested_ruleset": self.requested_ruleset,
            "search_paths": self.search_paths,
            "run_id": self.run_id,
            "sub_step": self.sub_step,
        }


def _sort_key(obj: dict) -> str:
    return dumps_canonical(obj).decode("utf-8")


def _ruleset_filename(ruleset_id: str) -> str:
    if ruleset_id.endswith(".json"):
        return Path(ruleset_id).name
    return f"{ruleset_id}.json"


def _record_candidate(
    *,
    requested_ruleset: str,
    run_id: str,
    candidate: str,
    exists: bool,
    search_paths: list[str],
) -> None:
    search_paths.append(candidate)
    LOGGER.info(
        "Ruleset resolution candidate requested_ruleset=%s run_id=%s "
        "sub_step=ruleset_resolution resolved_path=%s exists=%s",
        requested_ruleset,
        run_id or "unknown",
        candidate,
        exists,
    )


def _package_ruleset_bytes(filename: str) -> tuple[bytes, str] | None:
    try:
        package_root = files("core.rulesets")
    except ModuleNotFoundError:
        return None
    candidate = package_root.joinpath(filename)
    if candidate.is_file():
        return candidate.read_bytes(), f"package:core.rulesets/{filename}"
    return None


def _fallback_ruleset_paths(filename: str) -> list[Path]:
    candidate_roots = []
    configured_dir = os.environ.get("IOTA_VERBUM_RULESETS_DIR", "").strip()
    if configured_dir:
        candidate_roots.append(Path(configured_dir))
    candidate_roots.append(Path.cwd())

    module_path = Path(__file__).resolve()
    candidate_roots.extend(module_path.parents)

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in candidate_roots:
        resolved = root.resolve()
        key = resolved.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(resolved)
    return [root / "rulesets" / filename for root in unique_roots]


def load_ruleset(ruleset_id: str, *, run_id: str = "") -> tuple[dict, str]:
    requested_ruleset = str(ruleset_id).strip()
    search_paths: list[str] = []

    explicit_path = Path(requested_ruleset)
    explicit_candidate = explicit_path.resolve(strict=False).as_posix()
    explicit_exists = explicit_path.exists() and explicit_path.is_file()
    _record_candidate(
        requested_ruleset=requested_ruleset,
        run_id=run_id,
        candidate=explicit_candidate,
        exists=explicit_exists,
        search_paths=search_paths,
    )
    if explicit_exists:
        ruleset_bytes = explicit_path.read_bytes()
    else:
        ruleset_bytes = b""

    if not ruleset_bytes:
        filename = _ruleset_filename(requested_ruleset)
        package_candidate = f"package:core.rulesets/{filename}"
        packaged = _package_ruleset_bytes(filename)
        _record_candidate(
            requested_ruleset=requested_ruleset,
            run_id=run_id,
            candidate=package_candidate,
            exists=packaged is not None,
            search_paths=search_paths,
        )
        if packaged is not None:
            ruleset_bytes, _source = packaged

    if not ruleset_bytes:
        filename = _ruleset_filename(requested_ruleset)
        for path in _fallback_ruleset_paths(filename):
            candidate = path.resolve(strict=False).as_posix()
            exists = path.exists() and path.is_file()
            _record_candidate(
                requested_ruleset=requested_ruleset,
                run_id=run_id,
                candidate=candidate,
                exists=exists,
                search_paths=search_paths,
            )
            if exists:
                ruleset_bytes = path.read_bytes()
                break

    if not ruleset_bytes:
        raise RulesetResolutionError(
            requested_ruleset=requested_ruleset,
            search_paths=search_paths,
            run_id=run_id,
        )

    ruleset_obj = json.loads(ruleset_bytes.decode("utf-8"))
    validate(ruleset_obj, "schemas/ruleset.schema.json")
    return ruleset_obj, sha256_bytes(dumps_canonical(ruleset_obj))


def _sort_evidence_refs(evidence_refs: list[dict]) -> list[dict]:
    unique_refs = {
        (
            evidence_ref["source_id"],
            evidence_ref["chunk_id"],
            evidence_ref["offset_start"],
            evidence_ref["offset_end"],
            evidence_ref["text_sha256"],
        ): evidence_ref
        for evidence_ref in evidence_refs
    }
    return [unique_refs[key] for key in sorted(unique_refs)]


def _dedupe_reasons(reasons: list[dict]) -> list[dict]:
    unique_reasons = {
        (reason["code"], _sort_key(reason["ref"])): reason
        for reason in reasons
    }
    return [
        unique_reasons[key]
        for key in sorted(unique_reasons, key=lambda item: (item[0], item[1]))
    ]


def _dedupe_required_info(required_info: list[dict]) -> list[dict]:
    unique_items = {
        (item["kind"], _sort_key(item["ref"])): item
        for item in required_info
    }
    return [
        unique_items[key]
        for key in sorted(unique_items, key=lambda item: (item[0], item[1]))
    ]


def _relevant_findings(sealed_output_obj: dict, target_claim_id: str) -> list[dict]:
    findings = sealed_output_obj.get("findings", {})
    contradictions = findings.get("contradictions", [])
    return sorted(
        [
            contradiction
            for contradiction in contradictions
            if target_claim_id
            in {contradiction["claim_a"], contradiction["claim_b"]}
        ],
        key=lambda item: (item["claim_a"], item["claim_b"], item["reason"]),
    )


def _support_tree_evidence_refs(sealed_output_obj: dict) -> list[dict]:
    support_tree = sealed_output_obj.get("support_tree")
    if support_tree is None:
        return []
    evidence_refs = []
    for node in support_tree["nodes"]:
        evidence_refs.extend(node["claim"]["evidence"])
    return _sort_evidence_refs(evidence_refs)


def _support_tree_proofs(sealed_output_obj: dict) -> list[dict]:
    support_tree = sealed_output_obj.get("support_tree")
    if support_tree is None:
        return []
    proofs = [
        {
            "from_id": edge["from_id"],
            "to_id": edge["to_id"],
            "type": edge["type"],
            "proof": edge["proof"],
        }
        for edge in support_tree["edges"]
        if edge["derived"]
    ]
    return sorted(proofs, key=_sort_key)


def _world_evidence_refs(sealed_output_obj: dict) -> list[dict]:
    world_model = sealed_output_obj.get("world_model")
    if world_model is None:
        return []
    evidence_refs = []
    for event in world_model["events"]:
        evidence_refs.extend(event["evidence"])
    return _sort_evidence_refs(evidence_refs)


def _world_security_required_info(
    sealed_output_obj: dict,
    *,
    security_keywords: list[str],
    unknown_kinds_for_security: list[str],
) -> list[dict]:
    world_model = sealed_output_obj.get("world_model")
    if world_model is None:
        return []

    security_event_ids = {
        event["event_id"]
        for event in world_model["events"]
        if any(keyword in event["action"].lower() for keyword in security_keywords)
    }
    required_info = [
        unknown
        for unknown in world_model["unknowns"]
        if unknown["kind"] in set(unknown_kinds_for_security)
        and unknown["ref"].get("event_id") in security_event_ids
    ]
    return sorted(
        required_info,
        key=lambda item: (item["kind"], _sort_key(item["ref"])),
    )


def _causal_findings(sealed_output_obj: dict) -> list[dict]:
    causal_graph = sealed_output_obj.get("causal_graph")
    if causal_graph is None:
        return []
    return sorted(
        causal_graph.get("findings", []),
        key=lambda finding: (
            finding["code"],
            tuple(finding["event_ids"]),
            _sort_key(finding.get("details", {})),
        ),
    )


def _causal_security_required_info(
    sealed_output_obj: dict,
    *,
    security_event_types: set[str],
) -> list[dict]:
    world_model = sealed_output_obj.get("world_model")
    causal_graph = sealed_output_obj.get("causal_graph")
    if world_model is None or causal_graph is None:
        return []

    event_type_by_id = {
        event["event_id"]: event["type"]
        for event in world_model["events"]
    }
    required_info = []
    for finding in causal_graph.get("findings", []):
        if finding["code"] != "UNKNOWN_BLOCKS_CAUSAL":
            continue
        missing_kinds = sorted(finding.get("details", {}).get("missing_kinds", []))
        for event_id in sorted(finding["event_ids"]):
            if event_type_by_id.get(event_id) not in security_event_types:
                continue
            for missing_kind in missing_kinds:
                if missing_kind not in {
                    "missing_actor",
                    "missing_object",
                    "missing_time",
                }:
                    continue
                required_info.append(
                    {
                        "kind": missing_kind,
                        "ref": {"event_id": event_id},
                    }
                )
    return _dedupe_required_info(required_info)


def _constraint_violations(sealed_output_obj: dict) -> list[dict]:
    constraint_report = sealed_output_obj.get("constraint_report")
    if constraint_report is None:
        return []
    validate(constraint_report, "schemas/constraint_report.schema.json")
    return sorted(
        constraint_report["violations"],
        key=lambda item: (
            item["type"],
            tuple(item["events"]),
            tuple(item["entities"]),
            item["reason"],
            _sort_key({"evidence": item["evidence"]}),
        ),
    )


def verify_claim(
    *,
    ruleset_id: str,
    target_claim_id: str,
    evidence_bundle_obj: dict,
    sealed_output_obj: dict,
    strict_manifest: bool = False,
    run_id: str = "",
) -> dict:
    del strict_manifest
    validate(evidence_bundle_obj, "schemas/evidence_bundle.schema.json")
    ruleset_obj, ruleset_sha256 = load_ruleset(ruleset_id, run_id=run_id)

    _bundle_bytes, bundle_sha256 = build_evidence_bundle(evidence_bundle_obj)
    output_sha256 = sha256_bytes(dumps_canonical(sealed_output_obj))

    support_tree = sealed_output_obj.get("support_tree")
    support_tree_evidence_refs = _support_tree_evidence_refs(sealed_output_obj)
    evidence_refs = _sort_evidence_refs(
        support_tree_evidence_refs + _world_evidence_refs(sealed_output_obj)
    )
    proofs = _support_tree_proofs(sealed_output_obj)
    findings = _relevant_findings(sealed_output_obj, target_claim_id)
    causal_findings = _causal_findings(sealed_output_obj)
    constraint_violations = _constraint_violations(sealed_output_obj)
    artifact_scope = {
        (artifact["source_id"], artifact["chunk_id"])
        for artifact in evidence_bundle_obj["artifacts"]
    }

    reasons = []
    required_info = []
    for rule in ruleset_obj["rules"]:
        if not rule["enabled"]:
            continue

        if rule["rule_id"] == "RULE_CONTRADICTION":
            for finding in findings:
                reasons.append(
                    {
                        "code": "RULE_CONTRADICTION",
                        "message": "target claim is involved in a contradiction",
                        "ref": finding,
                    }
                )
            continue

        if rule["rule_id"] == "RULE_MIN_EVIDENCE":
            min_evidence_count = int(rule["params"].get("min_evidence_count", 1))
            if (
                support_tree is not None
                and len(support_tree_evidence_refs) < min_evidence_count
            ):
                reason_ref = {
                    "target_claim_id": target_claim_id,
                    "min_evidence_count": min_evidence_count,
                }
                reasons.append(
                    {
                        "code": "RULE_MIN_EVIDENCE",
                        "message": "target claim has insufficient supporting evidence",
                        "ref": reason_ref,
                    }
                )
                required_info.append(
                    {
                        "kind": "missing_evidence",
                        "ref": reason_ref,
                    }
                )
            continue

        if rule["rule_id"] == "RULE_WORLD_UNKNOWNS_SECURITY":
            world_required_info = _world_security_required_info(
                sealed_output_obj,
                security_keywords=list(rule["params"]["security_keywords"]),
                unknown_kinds_for_security=list(
                    rule["params"]["unknown_kinds_for_security"]
                ),
            )
            for item in world_required_info:
                reasons.append(
                    {
                        "code": "RULE_WORLD_UNKNOWNS_SECURITY",
                        "message": (
                            "security-relevant world event is missing "
                            "required context"
                        ),
                        "ref": item["ref"],
                    }
                )
                required_info.append(item)
            continue

        if rule["rule_id"] == "RULE_CAUSAL_TEMPORAL_CYCLE":
            for finding in causal_findings:
                if finding["code"] != "CYCLE_TEMPORAL_CONSTRAINT":
                    continue
                reasons.append(
                    {
                        "code": "RULE_CAUSAL_TEMPORAL_CYCLE",
                        "message": "causal temporal constraints contain a cycle",
                        "ref": {"event_ids": finding["event_ids"]},
                    }
                )
            continue

        if rule["rule_id"] == "RULE_CAUSAL_NEEDS_INFO":
            security_event_types = set(
                rule["params"].get(
                    "security_event_types",
                    sorted(_SECURITY_RELEVANT_EVENT_TYPES),
                )
            )
            causal_required_info = _causal_security_required_info(
                sealed_output_obj,
                security_event_types=security_event_types,
            )
            for item in causal_required_info:
                reasons.append(
                    {
                        "code": "RULE_CAUSAL_NEEDS_INFO",
                        "message": (
                            "security-relevant causal inference is blocked by "
                            "missing required context"
                        ),
                        "ref": item["ref"],
                    }
                )
                required_info.append(item)
            continue

        if rule["rule_id"] == "RULE_SCOPE":
            if not bool(rule["params"].get("fail_on_scope_mismatch", True)):
                continue
            for evidence_ref in evidence_refs:
                if (
                    evidence_ref["source_id"],
                    evidence_ref["chunk_id"],
                ) in artifact_scope:
                    continue
                reasons.append(
                    {
                        "code": "RULE_SCOPE",
                        "message": (
                            "verification receipts reference evidence outside "
                            "the bundle scope"
                        ),
                        "ref": evidence_ref,
                    }
                )

    for violation in constraint_violations:
        reasons.append(
            {
                "code": "RULE_CONSTRAINT_VIOLATION",
                "message": "constraint reasoning found a logically invalid world state",
                "ref": {
                    "type": violation["type"],
                    "events": violation["events"],
                    "entities": violation["entities"],
                },
            }
        )

    reasons = _dedupe_reasons(reasons)
    required_info = _dedupe_required_info(required_info)

    if any(
        reason["code"]
        in {
            "RULE_CONTRADICTION",
            "RULE_SCOPE",
            "RULE_CAUSAL_TEMPORAL_CYCLE",
            "RULE_CONSTRAINT_VIOLATION",
        }
        for reason in reasons
    ):
        status = "VERIFIED_FAIL"
    elif reasons:
        status = "VERIFIED_NEEDS_INFO"
    else:
        status = "VERIFIED_OK"

    verification_result = {
        "verification_version": "1.0",
        "ruleset_id": ruleset_obj["ruleset_id"],
        "target_claim_id": target_claim_id,
        "status": status,
        "reasons": reasons,
        "required_info": required_info,
        "receipts": {
            "bundle_sha256": bundle_sha256,
            "output_sha256": output_sha256,
            "attestation_sha256": "",
            "ruleset_sha256": ruleset_sha256,
            "evidence_refs": evidence_refs,
            "proofs": proofs,
            "findings": sorted(
                findings + causal_findings + constraint_violations,
                key=_sort_key,
            ),
        },
    }
    validate(verification_result, "schemas/verification_result.schema.json")
    return verification_result

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core import attestation, templates
from domains.biblical_text.extractors import BiblicalTextExtractors
from domains.clinical_records.extractors import ClinicalRecordsExtractors
from domains.credit_scoring.extractors import CreditScoringExtractors

DOMAIN_REGISTRY = {
    "biblical_text": {
        "extractor": BiblicalTextExtractors(),
        "templates": Path("domains/biblical_text/templates"),
    },
    "credit_scoring": {
        "extractor": CreditScoringExtractors(),
        "templates": Path("domains/credit_scoring/templates"),
    },
    "clinical_records": {
        "extractor": ClinicalRecordsExtractors(),
        "templates": Path("domains/clinical_records/templates"),
    },
}

EXPECTED_FIELDS = {
    "credit_scoring": [
        "applicant_id",
        "income_monthly",
        "debt_monthly",
        "credit_score",
        "delinquencies_12mo",
        "employment_months",
        "collateral",
        "co_signer",
    ],
    "clinical_records": [
        "patient_id",
        "chief_complaint",
        "encounter_date",
        "vitals.blood_pressure_systolic",
        "vitals.blood_pressure_diastolic",
        "vitals.heart_rate",
        "vitals.temperature",
        "vitals.o2_saturation",
        "history.age",
        "history.family_hypertension",
    ],
    "biblical_text": [
        "speaker_identity",
        "exact_time",
        "exact_location",
    ],
}


class GroundTruthExtractor:
    def __init__(self, domain: str):
        if domain not in DOMAIN_REGISTRY:
            raise ValueError(f"unknown domain: {domain}")
        self.domain = domain
        self.extractor = DOMAIN_REGISTRY[domain]["extractor"]
        self.template_dir = DOMAIN_REGISTRY[domain]["templates"]

    def extract(
        self,
        input_data: Any,
        input_ref: str | None = None,
        context: dict | None = None,
    ) -> dict:
        context = context or {}
        resolved_ref = input_ref or self._default_ref(input_data)
        normalized = self.extractor.normalize_input(input_data)
        extracted = self.extractor.extract(normalized, context)
        evidence_map = self.extractor.build_evidence_map(extracted, normalized)

        deterministic_output, template_meta = self._render_deterministic(
            resolved_ref, input_data, normalized, extracted, evidence_map, context
        )

        facts_pairs = _flatten_facts(extracted)
        facts_list = [f"{k}={_format_value(v)}" for k, v in facts_pairs]
        facts_map = {k: v for k, v in facts_pairs}
        evidence_ids = _collect_evidence_ids(evidence_map)
        cannot_invent = _missing_fields(self.domain, normalized)

        ground_truth = {
            "domain": self.domain,
            "input_ref": resolved_ref,
            "facts": facts_list,
            "facts_map": facts_map,
            "constraints": {
                "MUST_include": facts_list,
                "CANNOT_invent": cannot_invent,
                "MUST_cite": evidence_ids,
                "max_words": 200,
            },
            "evidence_map": evidence_map,
            "deterministic_output": deterministic_output,
            "template": template_meta,
        }
        ground_truth_sha = attestation.compute_sha256(
            attestation.canonicalize_json(ground_truth)
        )
        ground_truth["attestation_sha256"] = ground_truth_sha
        return ground_truth

    def _render_deterministic(
        self,
        input_ref: str,
        input_data: Any,
        normalized: Any,
        extracted: dict,
        evidence_map: dict,
        context: dict,
    ) -> tuple[dict, dict]:
        try:
            fallback = self.extractor.template_fallback(input_ref, context, normalized)
            template = templates.load_template(
                input_ref, self.template_dir, chain=fallback
            )
            render_context = self.extractor.build_context(
                input_ref, input_data, normalized, extracted, evidence_map, context
            )
            rendered = templates.resolve_placeholders(template, render_context)
            output = self.extractor.render_output(
                input_ref,
                input_data,
                normalized,
                extracted,
                evidence_map,
                rendered,
                context,
            )
            meta = {
                "template_path": template.get("_template_path"),
                "template_sha256": template.get("_template_sha256"),
            }
            return output, meta
        except Exception as exc:
            return {"error": f"template_render_failed: {exc}"}, {}

    def _default_ref(self, input_data: Any) -> str:
        if isinstance(input_data, dict):
            for key in ("ref", "id", "applicant_id", "patient_id"):
                value = input_data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return "generic"


def _flatten_facts(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    facts: list[tuple[str, Any]] = []

    if isinstance(data, dict):
        for key in sorted(data.keys()):
            value = data[key]
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            facts.extend(_flatten_facts(value, next_prefix))
        return facts

    if isinstance(data, list):
        for idx, value in enumerate(data):
            next_prefix = f"{prefix}[{idx}]"
            facts.extend(_flatten_facts(value, next_prefix))
        return facts

    facts.append((prefix, data))
    return facts


def _format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=True)
    return str(value)


def _collect_evidence_ids(evidence_map: dict) -> list[str]:
    ids: list[str] = []
    for value in evidence_map.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    ids.append(item["id"])
        elif isinstance(value, dict) and isinstance(value.get("id"), str):
            ids.append(value["id"])
    return ids


def _missing_fields(domain: str, normalized_input: Any) -> list[str]:
    fields = EXPECTED_FIELDS.get(domain, [])
    missing: list[str] = []
    if not fields:
        return missing
    if not isinstance(normalized_input, dict):
        return fields

    for field in fields:
        if "." in field:
            base, rest = field.split(".", 1)
            parent = normalized_input.get(base, {})
            if not isinstance(parent, dict) or parent.get(rest) in (None, "", []):
                missing.append(field)
        else:
            if normalized_input.get(field) in (None, "", []):
                missing.append(field)
    return missing

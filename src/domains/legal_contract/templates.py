from __future__ import annotations

from collections import OrderedDict

from domains.legal_contract.schema_ref import SCHEMA_VERSION


def build_output(
    parties: list[dict],
    effective_date: str | None,
    term: dict,
    obligations: list[dict],
    rights: list[dict],
    prohibitions: list[dict],
    defined_terms: dict,
    governing_law: dict,
    termination_conditions: list[str],
    conditional_triggers: list[dict],
    analysis: dict,
    risk_report: dict,
    extraction_warnings: list[str],
    review_findings: list[dict],
    review_summary: dict,
) -> dict:
    extraction = OrderedDict()
    extraction["parties"] = parties
    extraction["effective_date"] = effective_date
    extraction["term"] = term
    extraction["obligations"] = obligations
    extraction["rights"] = rights
    extraction["prohibitions"] = prohibitions
    extraction["defined_terms"] = defined_terms
    extraction["governing_law"] = governing_law
    extraction["termination_conditions"] = termination_conditions
    extraction["conditional_triggers"] = conditional_triggers
    extraction["analysis"] = analysis
    extraction["risk_report"] = risk_report
    extraction["extraction_warnings"] = extraction_warnings

    output = OrderedDict()
    output["domain"] = "legal_contract"
    output["schema_version"] = SCHEMA_VERSION
    output["extraction"] = extraction
    output["review_findings"] = review_findings
    output["review_summary"] = review_summary
    return output

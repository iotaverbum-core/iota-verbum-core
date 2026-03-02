from __future__ import annotations

from collections import OrderedDict

from domains.legal_contract.schema_ref import SCHEMA_VERSION


def build_output(
    parties: list[dict],
    effective_date: str | None,
    term: dict,
    obligations: list[dict],
    defined_terms: dict,
    governing_law: dict,
    termination_conditions: list[str],
    extraction_warnings: list[str],
) -> dict:
    extraction = OrderedDict()
    extraction["parties"] = parties
    extraction["effective_date"] = effective_date
    extraction["term"] = term
    extraction["obligations"] = obligations
    extraction["defined_terms"] = defined_terms
    extraction["governing_law"] = governing_law
    extraction["termination_conditions"] = termination_conditions
    extraction["extraction_warnings"] = extraction_warnings

    output = OrderedDict()
    output["domain"] = "legal_contract"
    output["schema_version"] = SCHEMA_VERSION
    output["extraction"] = extraction
    return output

from __future__ import annotations

from collections import OrderedDict

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_review_summary(*, domain: str, extraction: dict) -> OrderedDict:
    findings = build_review_findings(domain=domain, extraction=extraction)
    if domain == "legal_contract":
        return _build_legal_contract_summary(findings)
    if domain == "nda":
        return _build_nda_summary(findings, extraction)
    return _build_generic_summary(findings)


def build_review_findings(*, domain: str, extraction: dict) -> list[OrderedDict]:
    if domain == "legal_contract":
        return _build_legal_contract_findings(extraction)
    if domain == "nda":
        return _build_nda_findings(extraction)
    return _build_generic_findings(extraction)


def _build_legal_contract_summary(findings: list[OrderedDict]) -> OrderedDict:
    review_required = any(finding["review_required"] for finding in findings)
    has_contradictions = any(
        finding["finding_class"] == "contradiction" for finding in findings
    )
    has_ambiguities = any(
        finding["finding_class"] == "ambiguity" for finding in findings
    )
    warning_count = sum(
        1 for finding in findings if finding["finding_class"] == "warning"
    )
    headline = next(
        (
            finding["summary"]
            for finding in findings
            if finding["finding_class"] in {"contradiction", "ambiguity"}
        ),
        "Legal contract extraction completed.",
    )
    summary = OrderedDict()
    summary["status"] = "review_required" if review_required else "ready_for_review"
    summary["priority"] = (
        "high"
        if has_contradictions
        else "medium" if has_ambiguities or warning_count else "low"
    )
    summary["headline"] = headline
    summary["finding_count"] = sum(
        1 for finding in findings if finding["finding_class"] != "warning"
    )
    summary["warning_count"] = warning_count
    summary["requires_human_review"] = review_required
    return summary


def _build_nda_summary(findings: list[OrderedDict], extraction: dict) -> OrderedDict:
    clause_findings = [
        finding for finding in findings if finding["finding_class"] == "clause_detected"
    ]
    warning_count = sum(
        1 for finding in findings if finding["finding_class"] == "warning"
    )
    language = extraction.get("language", "").upper() or "UNKNOWN"
    summary = OrderedDict()
    summary["status"] = "ready_for_review" if clause_findings else "review_required"
    summary["priority"] = "low" if clause_findings else "medium"
    summary["headline"] = (
        f"Extracted {len(clause_findings)} clause(s) from {language} NDA."
        if clause_findings
        else f"No clauses extracted from {language} NDA; review required."
    )
    summary["finding_count"] = len(clause_findings)
    summary["warning_count"] = warning_count
    summary["requires_human_review"] = not clause_findings
    return summary


def _build_generic_summary(findings: list[OrderedDict]) -> OrderedDict:
    summary = OrderedDict()
    summary["status"] = "ready_for_review"
    summary["priority"] = "low"
    summary["headline"] = "Extraction completed."
    summary["finding_count"] = len(findings)
    summary["warning_count"] = sum(
        1 for finding in findings if finding["finding_class"] == "warning"
    )
    summary["requires_human_review"] = False
    return summary


def _build_legal_contract_findings(extraction: dict) -> list[OrderedDict]:
    analysis = extraction.get("analysis", {})
    findings: list[OrderedDict] = []

    for contradiction in analysis.get("contradictions", []):
        finding = OrderedDict()
        finding["finding_id"] = contradiction["contradiction_id"]
        finding["finding_class"] = "contradiction"
        finding["category"] = "contract_consistency"
        finding["severity"] = contradiction["severity"]
        finding["title"] = contradiction["title"]
        finding["summary"] = contradiction["description"]
        finding["source_path"] = "extraction.analysis.contradictions"
        finding["evidence_offsets"] = [
            contradiction["left_clause_offset"],
            contradiction["right_clause_offset"],
        ]
        finding["review_required"] = True
        finding["related_party"] = contradiction["party"]
        finding["related_action"] = contradiction["action"]
        finding["details"] = OrderedDict(
            [
                ("beneficiary", contradiction["beneficiary"]),
                ("contradiction_type", contradiction["contradiction_type"]),
                ("left_clause_text", contradiction["left_clause_text"]),
                ("right_clause_text", contradiction["right_clause_text"]),
            ]
        )
        findings.append(finding)

    for ambiguity in analysis.get("ambiguities", []):
        finding = OrderedDict()
        finding["finding_id"] = ambiguity["ambiguity_id"]
        finding["finding_class"] = "ambiguity"
        finding["category"] = "contract_clarity"
        finding["severity"] = ambiguity["risk_level"]
        finding["title"] = f"Ambiguous qualifier: {ambiguity['term']}"
        finding["summary"] = (
            f"Ambiguous term '{ambiguity['term']}' appears in a clause for "
            f"{ambiguity['party']}."
        )
        finding["source_path"] = "extraction.analysis.ambiguities"
        finding["evidence_offsets"] = [ambiguity["offset"]]
        finding["review_required"] = False
        finding["related_party"] = ambiguity["party"]
        finding["related_action"] = None
        finding["details"] = OrderedDict(
            [("term", ambiguity["term"]), ("text", ambiguity["text"])]
        )
        findings.append(finding)

    for warning in extraction.get("extraction_warnings", []):
        finding = OrderedDict()
        finding["finding_id"] = f"warning:{warning}"
        finding["finding_class"] = "warning"
        finding["category"] = "extraction_completeness"
        finding["severity"] = (
            "high" if warning.startswith("structured_error:") else "medium"
        )
        finding["title"] = warning.replace("_", " ")
        finding["summary"] = f"Extraction warning: {warning.replace('_', ' ')}."
        finding["source_path"] = "extraction.extraction_warnings"
        finding["evidence_offsets"] = []
        finding["review_required"] = True
        finding["related_party"] = None
        finding["related_action"] = None
        finding["details"] = OrderedDict([("warning_code", warning)])
        findings.append(finding)

    return _sort_findings(findings)


def _build_nda_findings(extraction: dict) -> list[OrderedDict]:
    findings: list[OrderedDict] = []
    for clause in extraction.get("clauses", []):
        finding = OrderedDict()
        finding["finding_id"] = clause["rule_id"]
        finding["finding_class"] = "clause_detected"
        finding["category"] = "nda_clause_coverage"
        finding["severity"] = "low"
        finding["title"] = f"Detected {clause['clause_type_en']} clause"
        finding["summary"] = (
            f"Symbolic extraction matched the {clause['clause_type_en']} clause."
        )
        finding["source_path"] = "extraction.clauses"
        finding["evidence_offsets"] = []
        finding["review_required"] = False
        finding["related_party"] = None
        finding["related_action"] = None
        finding["details"] = OrderedDict(
            [
                ("clause_type", clause["clause_type"]),
                ("clause_type_en", clause["clause_type_en"]),
                ("extracted_text", clause["extracted_text"]),
                ("extraction_method", clause["extraction_method"]),
                ("language", extraction.get("language")),
                ("rule_id", clause["rule_id"]),
            ]
        )
        findings.append(finding)

    if not findings:
        finding = OrderedDict()
        finding["finding_id"] = "warning:no_clauses_detected"
        finding["finding_class"] = "warning"
        finding["category"] = "extraction_completeness"
        finding["severity"] = "medium"
        finding["title"] = "No clauses detected"
        finding["summary"] = "No NDA clauses were extracted; review required."
        finding["source_path"] = "extraction.clauses"
        finding["evidence_offsets"] = []
        finding["review_required"] = True
        finding["related_party"] = None
        finding["related_action"] = None
        finding["details"] = OrderedDict([("language", extraction.get("language"))])
        findings.append(finding)

    return _sort_findings(findings)


def _build_generic_findings(extraction: dict) -> list[OrderedDict]:
    findings: list[OrderedDict] = []
    for warning in extraction.get("warnings", []):
        finding = OrderedDict()
        finding["finding_id"] = f"warning:{warning}"
        finding["finding_class"] = "warning"
        finding["category"] = "generic"
        finding["severity"] = "medium"
        finding["title"] = warning
        finding["summary"] = warning
        finding["source_path"] = "warnings"
        finding["evidence_offsets"] = []
        finding["review_required"] = False
        finding["related_party"] = None
        finding["related_action"] = None
        finding["details"] = OrderedDict()
        findings.append(finding)
    return _sort_findings(findings)


def _sort_findings(findings: list[OrderedDict]) -> list[OrderedDict]:
    return sorted(
        findings,
        key=lambda finding: (
            _SEVERITY_ORDER[finding["severity"]],
            finding["finding_class"],
            finding["finding_id"],
        ),
    )

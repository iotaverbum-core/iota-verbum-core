from __future__ import annotations

from dataclasses import dataclass

from core.governance import GOVERNANCE_METADATA
from core.review_summary import build_review_findings
from domains.legal_contract.extractor import LegalContractExtractors
from domains.legal_contract.schema_ref import SCHEMA_VERSION
from iota_verbum_api.constants import NEUROSYMBOLIC_BOUNDARY
from iota_verbum_api.domains.nda.rules import RULE_SETS


class UnsupportedDomainLanguage(Exception):
    pass


@dataclass(frozen=True)
class ExtractionBundle:
    result: dict
    extraction_language: str
    rule_set_version: str


LEGAL_CONTRACT_EXTRACTOR = LegalContractExtractors()


def extract_symbolic(domain: str, language: str, text: str) -> ExtractionBundle:
    if domain == "legal_contract":
        if language != "en":
            raise UnsupportedDomainLanguage("legal_contract_supports_english_only")
        extracted = LEGAL_CONTRACT_EXTRACTOR.extract(
            LEGAL_CONTRACT_EXTRACTOR.normalize_input(text),
            {},
        )
        result = {
            "domain": domain,
            "schema_version": SCHEMA_VERSION,
            "extraction": extracted,
            "review_findings": extracted["review_findings"],
            "review_summary": extracted["review_summary"],
            "governance_metadata": GOVERNANCE_METADATA[domain],
            "neurosymbolic_boundary": NEUROSYMBOLIC_BOUNDARY,
        }
        return ExtractionBundle(
            result=result,
            extraction_language="en",
            rule_set_version=f"en-legal_contract-v{SCHEMA_VERSION}",
        )

    if domain == "nda":
        rules = RULE_SETS.get(language)
        if not rules:
            raise UnsupportedDomainLanguage("unsupported_language")
        result = rules.extract(text)
        if "review_findings" not in result:
            result["review_findings"] = build_review_findings(
                domain=domain,
                extraction=result["extraction"],
            )
        result["governance_metadata"] = GOVERNANCE_METADATA[domain]
        result["neurosymbolic_boundary"] = NEUROSYMBOLIC_BOUNDARY
        return ExtractionBundle(
            result=result,
            extraction_language=language,
            rule_set_version=rules.version,
        )

    raise UnsupportedDomainLanguage("unsupported_domain")

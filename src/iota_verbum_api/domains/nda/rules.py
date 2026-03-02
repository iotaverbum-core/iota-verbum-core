from __future__ import annotations

import re
from dataclasses import dataclass

from iota_verbum_api.utils import normalize_text

CLAUSE_TRANSLATIONS = {
    "confidentiality_obligations": "confidentiality obligations",
    "term_duration": "term/duration",
    "exceptions": "exceptions",
    "return_or_destruction": "return/destruction",
    "governing_law": "governing law",
    "jurisdiction": "jurisdiction",
    "definition_of_confidential_information": "definition of confidential information",
}


@dataclass(frozen=True)
class RuleDefinition:
    clause_type: str
    clause_type_en: str
    rule_id: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class LanguageRuleSet:
    language: str
    domain: str
    version: str
    rules: tuple[RuleDefinition, ...]

    def extract(self, text: str) -> dict:
        normalized = normalize_text(text)
        clauses = []
        for rule in self.rules:
            sentence = _extract_matching_sentence(normalized, rule.patterns)
            if not sentence:
                continue
            clauses.append(
                {
                    "clause_type": rule.clause_type,
                    "clause_type_en": rule.clause_type_en,
                    "extracted_text": sentence,
                    "confidence": 0.99,
                    "extraction_method": "symbolic",
                    "rule_id": rule.rule_id,
                }
            )
        return {
            "domain": self.domain,
            "schema_version": "1.0",
            "extraction": {
                "clauses": clauses,
                "language": self.language,
                "rule_set_version": self.version,
            },
        }


def _extract_matching_sentence(text: str, patterns: tuple[str, ...]) -> str | None:
    sentences = re.split(r"(?<=[.!?])\s+|\n\n+", text)
    for sentence in sentences:
        candidate = sentence.strip()
        lowered = candidate.lower()
        if all(re.search(pattern, lowered) for pattern in patterns):
            return candidate
    return None


RULE_SETS = {
    "en": LanguageRuleSet(
        language="en",
        domain="nda",
        version="en-nda-v1.0",
        rules=(
            RuleDefinition(
                "confidentiality_obligations",
                CLAUSE_TRANSLATIONS["confidentiality_obligations"],
                "en.nda.confidentiality",
                (r"confidential", r"(shall|must|agree)"),
            ),
            RuleDefinition(
                "term_duration",
                CLAUSE_TRANSLATIONS["term_duration"],
                "en.nda.term",
                (r"(term|duration)",),
            ),
            RuleDefinition(
                "exceptions",
                CLAUSE_TRANSLATIONS["exceptions"],
                "en.nda.exceptions",
                (r"exception",),
            ),
            RuleDefinition(
                "return_or_destruction",
                CLAUSE_TRANSLATIONS["return_or_destruction"],
                "en.nda.return",
                (r"(return|destroy)",),
            ),
            RuleDefinition(
                "governing_law",
                CLAUSE_TRANSLATIONS["governing_law"],
                "en.nda.law",
                (r"governed by",),
            ),
            RuleDefinition(
                "jurisdiction",
                CLAUSE_TRANSLATIONS["jurisdiction"],
                "en.nda.jurisdiction",
                (r"jurisdiction",),
            ),
            RuleDefinition(
                "definition_of_confidential_information",
                CLAUSE_TRANSLATIONS["definition_of_confidential_information"],
                "en.nda.definition",
                (r"confidential information", r"means|includes"),
            ),
        ),
    ),
    "fr": LanguageRuleSet(
        language="fr",
        domain="nda",
        version="fr-nda-v1.0",
        rules=(
            RuleDefinition(
                "confidentialite",
                CLAUSE_TRANSLATIONS["confidentiality_obligations"],
                "fr.nda.confidentialite",
                (r"confidenti", r"(doit|s'engage|obligation)"),
            ),
            RuleDefinition(
                "duree",
                CLAUSE_TRANSLATIONS["term_duration"],
                "fr.nda.duree",
                (r"(dur[ée]e|terme)",),
            ),
            RuleDefinition(
                "exceptions",
                CLAUSE_TRANSLATIONS["exceptions"],
                "fr.nda.exceptions",
                (r"exception",),
            ),
            RuleDefinition(
                "restitution",
                CLAUSE_TRANSLATIONS["return_or_destruction"],
                "fr.nda.restitution",
                (r"(restituer|d[ée]truire|retourner)",),
            ),
            RuleDefinition(
                "loi_applicable",
                CLAUSE_TRANSLATIONS["governing_law"],
                "fr.nda.loi",
                (r"loi applicable|r[ée]gie par",),
            ),
            RuleDefinition(
                "juridiction",
                CLAUSE_TRANSLATIONS["jurisdiction"],
                "fr.nda.juridiction",
                (r"juridiction|tribunaux comp[ée]tents",),
            ),
            RuleDefinition(
                "definition_information_confidentielle",
                CLAUSE_TRANSLATIONS["definition_of_confidential_information"],
                "fr.nda.definition",
                (r"information confidentielle", r"(d[ée]signe|s'entend|signifie)"),
            ),
        ),
    ),
    "de": LanguageRuleSet(
        language="de",
        domain="nda",
        version="de-nda-v1.0",
        rules=(
            RuleDefinition(
                "vertraulichkeitspflichten",
                CLAUSE_TRANSLATIONS["confidentiality_obligations"],
                "de.nda.vertraulichkeit",
                (r"vertraulich", r"(muss|verpflichtet|pflicht)"),
            ),
            RuleDefinition(
                "laufzeit",
                CLAUSE_TRANSLATIONS["term_duration"],
                "de.nda.laufzeit",
                (r"laufzeit|dauer",),
            ),
            RuleDefinition(
                "ausnahmen",
                CLAUSE_TRANSLATIONS["exceptions"],
                "de.nda.ausnahmen",
                (r"ausnahmen?",),
            ),
            RuleDefinition(
                "rueckgabe",
                CLAUSE_TRANSLATIONS["return_or_destruction"],
                "de.nda.rueckgabe",
                (r"(zur[üu]ckgeben|vernichten)",),
            ),
            RuleDefinition(
                "anwendbares_recht",
                CLAUSE_TRANSLATIONS["governing_law"],
                "de.nda.recht",
                (r"(gilt .* recht|geltet .* recht|anwendbares recht)",),
            ),
            RuleDefinition(
                "gerichtsstand",
                CLAUSE_TRANSLATIONS["jurisdiction"],
                "de.nda.gerichtsstand",
                (r"gerichtsstand|zust[äa]ndige gerichte",),
            ),
            RuleDefinition(
                "definition_vertrauliche_informationen",
                CLAUSE_TRANSLATIONS["definition_of_confidential_information"],
                "de.nda.definition",
                (r"vertrauliche informationen", r"(bedeutet|umfasst|sind)"),
            ),
        ),
    ),
    "es": LanguageRuleSet(
        language="es",
        domain="nda",
        version="es-nda-v1.0",
        rules=(
            RuleDefinition(
                "obligaciones_confidencialidad",
                CLAUSE_TRANSLATIONS["confidentiality_obligations"],
                "es.nda.confidencialidad",
                (r"confidencial", r"(deber[aá]|obligaci[oó]n|se compromete)"),
            ),
            RuleDefinition(
                "vigencia",
                CLAUSE_TRANSLATIONS["term_duration"],
                "es.nda.vigencia",
                (r"vigencia|duraci[oó]n",),
            ),
            RuleDefinition(
                "excepciones",
                CLAUSE_TRANSLATIONS["exceptions"],
                "es.nda.excepciones",
                (r"excepciones?",),
            ),
            RuleDefinition(
                "devolucion",
                CLAUSE_TRANSLATIONS["return_or_destruction"],
                "es.nda.devolucion",
                (r"(devolver|destruir)",),
            ),
            RuleDefinition(
                "ley_aplicable",
                CLAUSE_TRANSLATIONS["governing_law"],
                "es.nda.ley",
                (r"ley aplicable|regir[aá]",),
            ),
            RuleDefinition(
                "jurisdiccion",
                CLAUSE_TRANSLATIONS["jurisdiction"],
                "es.nda.jurisdiccion",
                (r"jurisdicci[oó]n|tribunales competentes",),
            ),
            RuleDefinition(
                "definicion_informacion_confidencial",
                CLAUSE_TRANSLATIONS["definition_of_confidential_information"],
                "es.nda.definicion",
                (r"informaci[oó]n confidencial", r"(significa|incluye|se entiende)"),
            ),
        ),
    ),
}

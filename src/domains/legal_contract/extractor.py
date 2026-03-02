from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime

from domains.legal_contract.templates import build_output

ROLE_NAMES = (
    "licensor",
    "licensee",
    "buyer",
    "seller",
    "client",
    "contractor",
    "provider",
    "customer",
    "vendor",
    "company",
    "discloser",
    "recipient",
)

MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

PARTY_LINE_PATTERN = re.compile(
    r"(?P<name>[A-Z][A-Za-z0-9&.,'\- ]+?),\s+a[n]?\s+[^,\n]+?\((?P<labels>[^)]+)\)",
    re.IGNORECASE,
)
ROLE_PAIR_PATTERN = re.compile(
    r"\b(?P<left>[A-Z][A-Za-z0-9&.,'\- ]+?)\s+as\s+(?P<left_role>"
    + "|".join(ROLE_NAMES)
    + r")\s+and\s+(?P<right>[A-Z][A-Za-z0-9&.,'\- ]+?)\s+as\s+(?P<right_role>"
    + "|".join(ROLE_NAMES)
    + r")\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(?P<day>\d{1,2}),\s+(?P<year>\d{4})\b"
)
EFFECTIVE_DATE_PATTERN = re.compile(
    r"(?:effective\s+date|entered\s+into\s+as\s+of)\W{0,20}(?P<date>"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
TERM_PATTERN = re.compile(
    r"begin\s+on\s+(?P<start>(?:the\s+)?Effective Date|"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})"
    r".{0,120}?continue\s+until\s+(?P<end>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})"
    r".{0,80}?for\s+(?P<duration>[^.,]+)",
    re.IGNORECASE | re.DOTALL,
)
DEFINED_TERM_PATTERNS = (
    re.compile(
        (
            r'"(?P<term>[A-Z][A-Za-z0-9 ]+)"\s+'
            r"(?:means|shall mean)\s+(?P<definition>[^.]+)\."
        ),
        re.IGNORECASE,
    ),
    re.compile(
        (
            r"(?P<definition>[A-Za-z0-9 ,\-]+?)\s+"
            r'\(the\s+"(?P<term>[A-Z][A-Za-z0-9 ]+)"\)'
        ),
        re.IGNORECASE,
    ),
)
OBLIGATION_PATTERN = re.compile(
    r"\b(shall|must|agrees to|is required to|will)\b",
    re.IGNORECASE,
)
GOVERNING_LAW_PATTERN = re.compile(
    (
        r"(?P<clause>This Agreement shall be governed by the laws of "
        r"(?P<jurisdiction>[^.]+)\.)"
    ),
    re.IGNORECASE,
)
TERMINATION_PATTERN = re.compile(
    r"(?P<clause>[^.]*\bterminate(?:d|s)?\b[^.]*\.)",
    re.IGNORECASE,
)
SENTENCE_PATTERN = re.compile(r"[^.!?]+[.!?]", re.DOTALL)
WHITESPACE_PATTERN = re.compile(r"[ \t]+")


def _normalize_text(text: str) -> str:
    if text is None:
        return ""
    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2019", "'")
        .replace("\u2018", "'")
    )
    paragraphs = [
        WHITESPACE_PATTERN.sub(" ", block.strip()) for block in normalized.split("\n\n")
    ]
    return "\n\n".join([block for block in paragraphs if block])


def _date_to_iso(raw_date: str | None) -> str | None:
    if not raw_date:
        return None
    match = DATE_PATTERN.search(raw_date)
    if not match:
        return None
    month = MONTH_NAMES[match.group("month").lower()]
    day = int(match.group("day"))
    year = int(match.group("year"))
    return datetime(year, month, day).strftime("%Y-%m-%d")


def _clean_clause(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text.strip())


def _clean_party_name(text: str) -> str:
    cleaned = _clean_clause(text).rstrip(",")
    cleaned = re.sub(r"^(by and between|and)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _ordered_term_map(terms: dict[str, str]) -> OrderedDict[str, str]:
    ordered = OrderedDict()
    for key in sorted(terms):
        ordered[key] = terms[key]
    return ordered


class LegalContractExtractors:
    domain = "legal_contract"

    def normalize_input(self, text: str) -> str:
        return _normalize_text(text)

    def extract(self, normalized_text: str, context: dict):
        try:
            parties, party_aliases = self._extract_parties(normalized_text)
            effective_date = self._extract_effective_date(normalized_text)
            term = self._extract_term(normalized_text, effective_date)
            obligations = self._extract_obligations(
                normalized_text, parties, party_aliases
            )
            defined_terms = self._extract_defined_terms(normalized_text)
            governing_law = self._extract_governing_law(normalized_text)
            termination_conditions = self._extract_termination_conditions(
                normalized_text
            )
            warnings = self._warnings_for(
                parties=parties,
                effective_date=effective_date,
                term=term,
                obligations=obligations,
                defined_terms=defined_terms,
                governing_law=governing_law,
                termination_conditions=termination_conditions,
            )
        except Exception as exc:
            return {
                "parties": [],
                "effective_date": None,
                "term": {"start": None, "end": None, "duration_string": None},
                "obligations": [],
                "defined_terms": OrderedDict(),
                "governing_law": {"jurisdiction": None, "full_clause": None},
                "termination_conditions": [],
                "extraction_warnings": [f"structured_error: {exc}"],
            }

        return {
            "parties": parties,
            "effective_date": effective_date,
            "term": term,
            "obligations": obligations,
            "defined_terms": defined_terms,
            "governing_law": governing_law,
            "termination_conditions": termination_conditions,
            "extraction_warnings": warnings,
        }

    def build_evidence_map(self, extracted: dict, normalized_text: str):
        return {
            "parties": extracted["parties"],
            "obligations": extracted["obligations"],
            "defined_terms": [
                {"term": term, "definition": definition}
                for term, definition in extracted["defined_terms"].items()
            ],
            "governing_law": extracted["governing_law"],
            "termination_conditions": [
                {"id": f"termination_{idx}", "text": clause}
                for idx, clause in enumerate(extracted["termination_conditions"])
            ],
        }

    def template_fallback(self, input_ref: str, context: dict, normalized_text: str):
        return None

    def build_context(
        self, input_ref, input_data, normalized_text, extracted, evidence_map, context
    ):
        return {
            "contract_ref": input_ref,
            "party_names": [party["name"] for party in extracted["parties"]],
            "effective_date": extracted["effective_date"],
            "governing_jurisdiction": extracted["governing_law"]["jurisdiction"],
        }

    def render_output(
        self,
        input_ref,
        input_data,
        normalized_text,
        extracted,
        evidence_map,
        rendered,
        context,
    ):
        return build_output(
            parties=extracted["parties"],
            effective_date=extracted["effective_date"],
            term=extracted["term"],
            obligations=extracted["obligations"],
            defined_terms=extracted["defined_terms"],
            governing_law=extracted["governing_law"],
            termination_conditions=extracted["termination_conditions"],
            extraction_warnings=extracted["extraction_warnings"],
        )

    def _extract_parties(self, text: str) -> tuple[list[dict], dict[str, str]]:
        role_map: dict[str, str] = {}
        for match in ROLE_PAIR_PATTERN.finditer(text):
            role_map[_clean_clause(match.group("left"))] = match.group(
                "left_role"
            ).lower()
            role_map[_clean_clause(match.group("right"))] = match.group(
                "right_role"
            ).lower()

        parties: list[dict] = []
        aliases: dict[str, str] = {}
        seen_names: set[str] = set()
        for match in PARTY_LINE_PATTERN.finditer(text):
            name = _clean_party_name(match.group("name"))
            if name in seen_names:
                continue
            labels = re.findall(r'"([^"]+)"', match.group("labels"))
            role = None
            for label in labels:
                aliases[label] = name
                if label.lower() in ROLE_NAMES:
                    role = label.lower()
            role = role or role_map.get(name)
            if role:
                parties.append({"name": name, "role": role})
                seen_names.add(name)

        parties.sort(key=lambda item: item["name"])
        return parties, aliases

    def _extract_effective_date(self, text: str) -> str | None:
        match = EFFECTIVE_DATE_PATTERN.search(text)
        if match:
            return _date_to_iso(match.group("date"))
        return None

    def _extract_term(self, text: str, effective_date: str | None) -> dict:
        match = TERM_PATTERN.search(text)
        if not match:
            return {"start": effective_date, "end": None, "duration_string": None}
        start = match.group("start")
        start_iso = (
            effective_date if "effective date" in start.lower() else _date_to_iso(start)
        )
        return {
            "start": start_iso,
            "end": _date_to_iso(match.group("end")),
            "duration_string": _clean_clause(match.group("duration")),
        }

    def _extract_obligations(
        self, text: str, parties: list[dict], aliases: dict[str, str]
    ) -> list[dict]:
        known_subjects = [(party["name"], party["name"]) for party in parties]
        for alias, canonical in aliases.items():
            known_subjects.append((alias, canonical))
        for party in parties:
            known_subjects.append((party["role"].title(), party["name"]))

        obligations: list[dict] = []
        for match in SENTENCE_PATTERN.finditer(text):
            sentence = _clean_clause(match.group(0))
            if not OBLIGATION_PATTERN.search(sentence):
                continue
            subject_hits = []
            for subject, canonical in known_subjects:
                subject_match = re.search(rf"\b{re.escape(subject)}\b", sentence)
                if subject_match:
                    subject_hits.append((subject_match.start(), canonical))
            party_name = None
            if subject_hits:
                party_name = sorted(subject_hits, key=lambda item: item[0])[0][1]
            if not party_name:
                continue
            obligations.append(
                {
                    "party": party_name,
                    "text": sentence,
                    "offset": match.start(),
                }
            )
        obligations.sort(key=lambda item: item["offset"])
        return obligations

    def _extract_defined_terms(self, text: str) -> OrderedDict[str, str]:
        terms: dict[str, str] = {}
        for pattern in DEFINED_TERM_PATTERNS:
            for match in pattern.finditer(text):
                term = _clean_clause(match.group("term"))
                definition = _clean_clause(match.group("definition")).rstrip(",")
                if term not in terms:
                    terms[term] = definition
        return _ordered_term_map(terms)

    def _extract_governing_law(self, text: str) -> dict:
        match = GOVERNING_LAW_PATTERN.search(text)
        if not match:
            return {"jurisdiction": None, "full_clause": None}
        return {
            "jurisdiction": _clean_clause(match.group("jurisdiction")),
            "full_clause": _clean_clause(match.group("clause")),
        }

    def _extract_termination_conditions(self, text: str) -> list[str]:
        clauses = []
        for match in TERMINATION_PATTERN.finditer(text):
            clause = _clean_clause(match.group("clause"))
            if clause.lower().startswith("the term of this agreement"):
                continue
            if clause not in clauses:
                clauses.append(clause)
        return clauses

    def _warnings_for(self, **fields) -> list[str]:
        warnings = []
        if not fields["parties"]:
            warnings.append("parties_not_found")
        if not fields["effective_date"]:
            warnings.append("effective_date_not_found")
        if not fields["term"].get("end"):
            warnings.append("term_not_found")
        if not fields["obligations"]:
            warnings.append("obligations_not_found")
        if not fields["defined_terms"]:
            warnings.append("defined_terms_not_found")
        if not fields["governing_law"].get("full_clause"):
            warnings.append("governing_law_not_found")
        if not fields["termination_conditions"]:
            warnings.append("termination_conditions_not_found")
        return warnings

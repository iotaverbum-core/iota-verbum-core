from __future__ import annotations

import re

from iota_verbum_api.constants import LANGUAGES_SUPPORTED


def detect_language(text: str) -> tuple[str, float, dict]:
    try:
        from langdetect import DetectorFactory, detect_langs
        import langid
    except ImportError:
        return _detect_language_fallback(text)

    DetectorFactory.seed = 0
    langdetect_result = detect_langs(text[:10000] or "en")[0]
    langid_result, langid_confidence = langid.classify(text)

    raw_a = langdetect_result.lang
    raw_b = langid_result
    detected_a = raw_a if raw_a in LANGUAGES_SUPPORTED else "en"
    detected_b = raw_b if raw_b in LANGUAGES_SUPPORTED else "en"
    agreement = detected_a == detected_b

    if agreement:
        language = detected_a
        confidence = float(langdetect_result.prob)
    elif float(langdetect_result.prob) >= float(langid_confidence):
        language = detected_a
        confidence = float(langdetect_result.prob)
    else:
        language = detected_b
        confidence = float(langid_confidence)

    metadata = {
        "langdetect_result": detected_a,
        "langid_result": detected_b,
        "agreement": agreement,
        "confidence": round(confidence, 4),
        "language_fallback": raw_a not in LANGUAGES_SUPPORTED
        and raw_b not in LANGUAGES_SUPPORTED,
    }
    if raw_a not in LANGUAGES_SUPPORTED and raw_b not in LANGUAGES_SUPPORTED:
        language = "en"

    return language, confidence, metadata


def _detect_language_fallback(text: str) -> tuple[str, float, dict]:
    lowered = text.lower()
    scores = {
        "fr": len(re.findall(r"\b(accord|confidentielle|juridiction|loi|partie)\b", lowered)),
        "de": len(re.findall(r"\b(vereinbarung|vertraulich|gerichtsstand|recht|partei)\b", lowered)),
        "es": len(re.findall(r"\b(acuerdo|confidencial|jurisdiccion|ley|parte)\b", lowered)),
        "en": len(re.findall(r"\b(agreement|confidential|jurisdiction|law|party)\b", lowered)),
    }
    language = max(scores, key=scores.get)
    if scores[language] == 0:
        language = "en"
    metadata = {
        "langdetect_result": language,
        "langid_result": language,
        "agreement": True,
        "confidence": 0.8,
        "language_fallback": language not in LANGUAGES_SUPPORTED,
    }
    return language, 0.8, metadata

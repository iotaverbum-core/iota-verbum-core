from pathlib import Path

from iota_verbum_api.services.language import detect_language


def test_detect_language_supported_languages():
    samples = {
        "fr": Path("tests/fixtures/nda_fr.txt").read_text(encoding="utf-8"),
        "de": Path("tests/fixtures/nda_de.txt").read_text(encoding="utf-8"),
        "es": Path("tests/fixtures/nda_es.txt").read_text(encoding="utf-8"),
        "en": (
            "This non-disclosure agreement defines Confidential Information, "
            "requires strict confidentiality, includes exceptions, sets a term, "
            "requires return or destruction, and is governed by Delaware law."
        ),
    }

    for expected, text in samples.items():
        detected, confidence, metadata = detect_language(text)
        assert detected == expected
        assert confidence > 0
        assert "agreement" in metadata


def test_detect_language_fallback_for_unsupported_language(monkeypatch):
    detected, _, metadata = detect_language(
        "Questo accordo riservato tutela le informazioni e limita ogni divulgazione."
    )
    assert detected == "en"
    assert "language_fallback" in metadata

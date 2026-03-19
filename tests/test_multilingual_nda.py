from pathlib import Path

from iota_verbum_api.services.extraction import extract_symbolic


def test_french_nda_clause_coverage():
    text = Path("tests/fixtures/nda_fr.txt").read_text(encoding="utf-8")
    result = extract_symbolic("nda", "fr", text).result
    assert result["schema_version"] == "1.1"
    assert len(result["review_findings"]) == 7
    assert result["review_findings"][0]["finding_class"] == "clause_detected"
    assert result["review_summary"]["status"] == "ready_for_review"
    assert result["review_summary"]["priority"] == "low"
    assert result["review_summary"]["finding_count"] == 7
    clause_types = {item["clause_type"] for item in result["extraction"]["clauses"]}
    assert clause_types == {
        "confidentialite",
        "duree",
        "exceptions",
        "restitution",
        "loi_applicable",
        "juridiction",
        "definition_information_confidentielle",
    }


def test_german_nda_clause_coverage():
    text = Path("tests/fixtures/nda_de.txt").read_text(encoding="utf-8")
    result = extract_symbolic("nda", "de", text).result
    assert result["schema_version"] == "1.1"
    assert len(result["review_findings"]) == 7
    assert result["review_summary"]["status"] == "ready_for_review"
    assert result["review_summary"]["finding_count"] == 7
    clause_types = {item["clause_type"] for item in result["extraction"]["clauses"]}
    assert clause_types == {
        "vertraulichkeitspflichten",
        "laufzeit",
        "ausnahmen",
        "rueckgabe",
        "anwendbares_recht",
        "gerichtsstand",
        "definition_vertrauliche_informationen",
    }


def test_spanish_nda_clause_coverage():
    text = Path("tests/fixtures/nda_es.txt").read_text(encoding="utf-8")
    result = extract_symbolic("nda", "es", text).result
    assert result["schema_version"] == "1.1"
    assert len(result["review_findings"]) == 7
    assert result["review_summary"]["status"] == "ready_for_review"
    assert result["review_summary"]["finding_count"] == 7
    clause_types = {item["clause_type"] for item in result["extraction"]["clauses"]}
    assert clause_types == {
        "obligaciones_confidencialidad",
        "vigencia",
        "excepciones",
        "devolucion",
        "ley_aplicable",
        "jurisdiccion",
        "definicion_informacion_confidencial",
    }

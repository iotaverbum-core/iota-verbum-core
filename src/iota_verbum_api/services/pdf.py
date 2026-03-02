from __future__ import annotations

import io
from collections import Counter

from iota_verbum_api.utils import normalize_text


class ExtractionFailure(Exception):
    pass


def extract_text_pdfplumber(pdf_bytes: bytes) -> tuple[str, dict]:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [(page.extract_text() or "") for page in pdf.pages]
        raw_text = "\n\n".join(pages).strip()
        metadata = {
            "page_count": len(pdf.pages),
            "has_tables": any(bool(page.extract_tables()) for page in pdf.pages),
            "producer": (pdf.metadata or {}).get("Producer"),
            "creation_date": (pdf.metadata or {}).get("CreationDate"),
            "extraction_method": "pdfplumber",
        }
    if len(normalize_text(raw_text)) < 50:
        raise ExtractionFailure("pdf_text_too_sparse")
    return raw_text, metadata


def extract_text_ocr(pdf_bytes: bytes, language: str = "eng") -> tuple[str, dict]:
    import pytesseract
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(pdf_bytes, dpi=300)
    texts: list[str] = []
    confidences: list[int] = []
    for image in images:
        data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT,
        )
        texts.append(pytesseract.image_to_string(image, lang=language))
        for value in data.get("conf", []):
            if value and value != "-1":
                confidences.append(int(float(value)))

    raw_text = "\n\n".join(texts).strip()
    if len(normalize_text(raw_text)) < 50:
        raise ExtractionFailure("ocr_text_too_sparse")

    metadata = {
        "dpi": 300,
        "language": language,
        "page_count": len(images),
        "confidence_scores": dict(sorted(Counter(confidences).items())),
        "extraction_method": "ocr",
    }
    return raw_text, metadata


def clean_extracted_text(raw_text: str) -> str:
    return normalize_text(raw_text)


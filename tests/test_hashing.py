import hashlib

from core.determinism.hashing import sha256_text


def test_sha256_text_normalizes_crlf_to_lf():
    assert sha256_text("line 1\r\nline 2") == sha256_text("line 1\nline 2")


def test_sha256_text_normalizes_unicode_to_nfc():
    expected = hashlib.sha256("Caf\u00e9".encode("utf-8")).hexdigest()

    assert sha256_text("Cafe\u0301") == expected

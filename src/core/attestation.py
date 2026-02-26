import hashlib
import json
from pathlib import Path


def canonicalize_json(data) -> bytes:
    text = json.dumps(data, sort_keys=True, ensure_ascii=True, indent=2)
    return (text + "\n").encode("utf-8")


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, data) -> str:
    payload = canonicalize_json(data)
    path.write_bytes(payload)
    return compute_sha256(payload)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def build_provenance_chain(
    input_sha256: str,
    extraction_sha256: str,
    template_sha256: str,
    output_sha256: str,
    generator_sha256: str,
    extra: dict | None = None,
) -> dict:
    provenance = {
        "input_sha256": input_sha256,
        "extraction_sha256": extraction_sha256,
        "template_sha256": template_sha256,
        "output_sha256": output_sha256,
        "generator_sha256": generator_sha256,
    }
    if extra:
        provenance.update(extra)
    return provenance


def verify_attestation(output_json_path: Path, attestation_path: Path) -> dict:
    output_bytes = output_json_path.read_bytes()
    computed = compute_sha256(output_bytes)
    recorded = attestation_path.read_text(encoding="utf-8").strip()
    return {
        "computed": computed,
        "recorded": recorded,
        "match": computed == recorded,
    }

import argparse
import json
from pathlib import Path

from core.attestation import sha256_bytes, sha256_text, verify_attestation
from core.manifest import resolve_input
from core.pipeline import DeterministicPipeline
from domains.biblical_text.extractors import BiblicalTextExtractors
from domains.clinical_records.extractors import ClinicalRecordsExtractors
from domains.credit_scoring.extractors import CreditScoringExtractors


def _find_repo_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "pyproject.toml").exists():
            return p
    return start.parent


def _relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


CODE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = _find_repo_root(CODE_ROOT)
DATA_ROOT = REPO_ROOT / "data"

DOMAIN_REGISTRY = {
    "biblical_text": {
        "extractor": BiblicalTextExtractors(),
        "templates": CODE_ROOT / "domains/biblical_text/templates",
        "manifest": CODE_ROOT / "domains/biblical_text/manifest.json",
    },
    "credit_scoring": {
        "extractor": CreditScoringExtractors(),
        "templates": CODE_ROOT / "domains/credit_scoring/templates",
        "manifest": DATA_ROOT / "credit/manifest.json",
    },
    "clinical_records": {
        "extractor": ClinicalRecordsExtractors(),
        "templates": CODE_ROOT / "domains/clinical_records/templates",
        "manifest": DATA_ROOT / "clinical/manifest.json",
    },
}


def _parse_context(entries):
    context = {}
    for entry in entries or []:
        if "=" not in entry:
            raise ValueError("context must be key=value")
        key, value = entry.split("=", 1)
        context[key.strip()] = value.strip()
    return context


def _load_input(domain, input_ref, input_file, dataset, manifest):
    if input_file:
        path = Path(input_file)
        data_bytes = path.read_bytes()
        if domain == "biblical_text":
            data = data_bytes.decode("utf-8")
        else:
            data = json.loads(data_bytes.decode("utf-8-sig"))
        return {
            "ref": input_ref,
            "data": data,
            "bytes": data_bytes,
            "input_meta": {"input_file": _relpath(path, REPO_ROOT)},
        }

    if dataset and domain == "biblical_text":
        manifest_path = DATA_ROOT / "scripture" / dataset / "manifest.json"
    else:
        manifest_path = Path(manifest) if manifest else DOMAIN_REGISTRY[domain]["manifest"]
    resolved = resolve_input(input_ref, manifest_path)
    data_bytes = resolved["data_bytes"]
    if domain == "biblical_text":
        data = data_bytes.decode("utf-8")
    else:
        data = json.loads(data_bytes.decode("utf-8-sig"))

    return {
        "ref": resolved["ref"],
        "data": data,
        "bytes": data_bytes,
        "input_meta": {
            "input_file": _relpath(resolved["file_path"], REPO_ROOT),
            "manifest_sha256": resolved["manifest_sha256"],
        },
    }


def run_pipeline(args):
    domain_config = DOMAIN_REGISTRY.get(args.domain)
    if not domain_config:
        raise ValueError(f"unknown domain: {args.domain}")

    pipeline = DeterministicPipeline(
        args.domain,
        domain_config["extractor"],
        domain_config["templates"],
        manifest_path=domain_config["manifest"],
    )

    context = _parse_context(args.context)
    resolved = _load_input(
        args.domain, args.input_ref, args.input_file, args.dataset, args.manifest
    )

    output_dir = Path(args.out)
    return pipeline.process(
        resolved["ref"],
        resolved["data"],
        resolved["bytes"],
        context,
        output_dir,
        input_meta=resolved["input_meta"],
    )


def validate_provenance(paths):
    results = []
    for p in paths:
        path = Path(p)
        data = json.loads(path.read_text(encoding="utf-8"))
        output_path = path.parent / "output.json"
        attestation_path = path.parent / "attestation.sha256"
        attestation = verify_attestation(output_path, attestation_path)
        template_path = data.get("template_path")
        template_sha = data.get("template_sha256")
        template_match = None
        if template_path and Path(template_path).exists():
            raw = Path(template_path).read_text(encoding="utf-8")
            normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
            template_match = sha256_text(normalized) == template_sha
        input_match = None
        input_meta = data.get("input_meta") or {}
        input_file = input_meta.get("input_file")
        if input_file and Path(input_file).exists():
            input_match = sha256_bytes(Path(input_file).read_bytes()) == data.get("input_sha256")
        results.append(
            {
                "path": str(path),
                "attestation_match": attestation["match"],
                "template_match": template_match,
                "input_match": input_match,
            }
        )
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic AI Platform")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run deterministic pipeline")
    run_parser.add_argument("--domain", required=True)
    run_parser.add_argument("--input-ref", required=True)
    run_parser.add_argument("--input-file")
    run_parser.add_argument("--dataset")
    run_parser.add_argument("--manifest")
    run_parser.add_argument("--context", action="append")
    run_parser.add_argument("--out", required=True)

    validate_parser = subparsers.add_parser("validate-provenance")
    validate_parser.add_argument("paths", nargs="+")

    if argv is None:
        argv = list(__import__("sys").argv[1:])
    else:
        argv = list(argv)
    if argv and argv[0] not in ("run", "validate-provenance"):
        argv = ["run"] + argv
    args = parser.parse_args(argv)

    if args.command == "validate-provenance":
        results = validate_provenance(args.paths)
        print(json.dumps(results, indent=2))
        return

    if args.command in (None, "run"):
        run_pipeline(args)
        return


if __name__ == "__main__":
    main()

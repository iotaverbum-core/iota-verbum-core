import hashlib
from pathlib import Path

from core import attestation, templates


class DeterministicPipeline:
    def __init__(self, domain_name, extractor, template_dir, manifest_path=None):
        self.domain = domain_name
        self.extractor = extractor
        self.template_dir = Path(template_dir)
        self.manifest_path = Path(manifest_path) if manifest_path else None

    def process(
        self,
        input_ref,
        input_data,
        input_bytes,
        context,
        output_dir: Path,
        input_meta: dict | None = None,
        provenance_meta: dict | None = None,
    ):
        normalized = self.extractor.normalize_input(input_data)
        extracted = self.extractor.extract(normalized, context)
        evidence_map = self.extractor.build_evidence_map(extracted, normalized)
        fallback = self.extractor.template_fallback(input_ref, context, normalized)
        template = templates.load_template(input_ref, self.template_dir, chain=fallback)
        render_context = self.extractor.build_context(
            input_ref, input_data, normalized, extracted, evidence_map, context
        )
        rendered = templates.resolve_placeholders(template, render_context)

        output_data = self.extractor.render_output(
            input_ref,
            input_data,
            normalized,
            extracted,
            evidence_map,
            rendered,
            context,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        output_json_path = output_dir / "output.json"
        output_sha256 = attestation.write_json(output_json_path, output_data)

        extraction_sha256 = attestation.compute_sha256(
            attestation.canonicalize_json(
                {"extracted": extracted, "evidence_map": evidence_map}
            )
        )
        input_sha256 = attestation.sha256_bytes(input_bytes)
        template_sha256 = template.get("_template_sha256", "")
        generator_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

        extra = {
            "domain": self.domain,
            "input_ref": input_ref,
            "template_path": template.get("_template_path"),
            "context": context,
            "input_meta": input_meta or {},
        }
        if provenance_meta:
            extra["provenance_meta"] = provenance_meta

        provenance = attestation.build_provenance_chain(
            input_sha256=input_sha256,
            extraction_sha256=extraction_sha256,
            template_sha256=template_sha256,
            output_sha256=output_sha256,
            generator_sha256=generator_sha256,
            extra=extra,
        )

        attestation.write_json(output_dir / "provenance.json", provenance)
        attestation.write_text(output_dir / "attestation.sha256", output_sha256 + "\n")
        attestation.write_text(
            output_dir / "log.txt",
            (
                f"deterministic_ai domain={self.domain}\n"
                "files_written=output.json, provenance.json, "
                "attestation.sha256, log.txt\n"
            ),
        )

        return {
            "output_data": output_data,
            "provenance": provenance,
            "attestation_sha256": output_sha256,
        }

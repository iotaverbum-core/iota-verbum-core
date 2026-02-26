from __future__ import annotations

from core import attestation


class AttestationEngine:
    def attest(self, ground_truth: dict, llm_output: str | None, validation: dict) -> dict:
        ground_truth_sha = ground_truth.get("attestation_sha256")
        if not ground_truth_sha:
            ground_truth_sha = attestation.compute_sha256(
                attestation.canonicalize_json(ground_truth)
            )

        passed = bool(validation.get("passes"))
        combined_source = f"{ground_truth_sha}{'true' if passed else 'false'}"
        combined_sha = attestation.sha256_text(combined_source)

        llm_sha = None
        if llm_output is not None:
            llm_sha = attestation.sha256_text(llm_output)

        return {
            "ground_truth_sha256": ground_truth_sha,
            "combined_guarantee_sha256": combined_sha,
            "llm_output_sha256": llm_sha,
            "validation_passed": passed,
        }

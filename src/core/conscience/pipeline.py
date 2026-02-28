from __future__ import annotations

from core.conscience.attester import AttestationEngine
from core.conscience.constrainer import LLMConstrainer
from core.conscience.extractor import GroundTruthExtractor
from core.conscience.validator import LLMValidator


class ConSciencePipeline:
    def __init__(self, domain: str):
        self.domain = domain
        self.extractor = GroundTruthExtractor(domain)
        self.constrainer = LLMConstrainer()
        self.validator = LLMValidator()
        self.attester = AttestationEngine()

    def process(
        self,
        domain: str,
        input_data,
        task: str,
        llm_provider,
        max_retries: int = 3,
        fallback: bool = True,
        persona: str | None = None,
    ) -> dict:
        if domain != self.domain:
            self.__init__(domain)

        ground_truth = self.extractor.extract(input_data)
        deterministic_output = ground_truth.get("deterministic_output")

        if llm_provider in (None, "offline"):
            validation = {"passes": True, "checks": {}, "severity": "info"}
            attestation = self.attester.attest(ground_truth, None, validation)
            return {
                "ground_truth": ground_truth,
                "llm_output": None,
                "validation": validation,
                "attestation": attestation,
                "final_output": deterministic_output,
                "deterministic_output": deterministic_output,
                "used_fallback": True,
                "attempts": 0,
                "offline": True,
            }

        prompt = self.constrainer.build_prompt(ground_truth, task, persona)
        attempts = 0
        last_validation = None
        last_output = None
        violations = {}

        while attempts < max_retries:
            attempts += 1
            llm_output = llm_provider(prompt)
            last_output = llm_output
            validation = self.validator.validate(
                llm_output, ground_truth, strict_mode=True
            )
            last_validation = validation
            if validation["passes"]:
                attestation = self.attester.attest(ground_truth, llm_output, validation)
                return {
                    "ground_truth": ground_truth,
                    "llm_output": llm_output,
                    "validation": validation,
                    "attestation": attestation,
                    "final_output": llm_output,
                    "deterministic_output": deterministic_output,
                    "used_fallback": False,
                    "attempts": attempts,
                    "offline": False,
                }
            violations = {
                k: v for k, v in validation["checks"].items() if not v["pass"]
            }
            prompt = self.constrainer.add_rejection_context(prompt, violations)

        if not fallback:
            attestation = self.attester.attest(
                ground_truth, last_output, last_validation or {}
            )
            return {
                "ground_truth": ground_truth,
                "llm_output": last_output,
                "validation": last_validation,
                "attestation": attestation,
                "final_output": last_output,
                "deterministic_output": deterministic_output,
                "used_fallback": False,
                "attempts": attempts,
                "offline": False,
            }

        validation = last_validation or {
            "passes": False,
            "checks": violations,
            "severity": "high",
        }
        attestation = self.attester.attest(ground_truth, last_output, validation)
        return {
            "ground_truth": ground_truth,
            "llm_output": last_output,
            "validation": validation,
            "attestation": attestation,
            "final_output": deterministic_output,
            "deterministic_output": deterministic_output,
            "used_fallback": True,
            "attempts": attempts,
            "offline": False,
        }

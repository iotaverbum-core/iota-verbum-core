import json
from pathlib import Path

from core.conscience.attester import AttestationEngine
from core.conscience.constrainer import LLMConstrainer
from core.conscience.extractor import GroundTruthExtractor
from core.conscience.pipeline import ConSciencePipeline
from core.conscience.validator import LLMValidator


def _load_credit_sample():
    path = Path("data/credit/sample_applicant.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_extractor_determinism():
    extractor = GroundTruthExtractor("credit_scoring")
    data = _load_credit_sample()
    gt_a = extractor.extract(data)
    gt_b = extractor.extract(data)
    assert gt_a["attestation_sha256"] == gt_b["attestation_sha256"]


def test_constrainer_includes_all_facts():
    extractor = GroundTruthExtractor("credit_scoring")
    data = _load_credit_sample()
    gt = extractor.extract(data)
    prompt = LLMConstrainer().build_prompt(
        gt, task="Summarize decision", persona="Tester"
    )
    for fact in gt["facts"]:
        assert fact in prompt


def test_constrainer_forbids_all_cannot_invent():
    extractor = GroundTruthExtractor("credit_scoring")
    data = _load_credit_sample()
    gt = extractor.extract(data)
    prompt = LLMConstrainer().build_prompt(
        gt, task="Summarize decision", persona="Tester"
    )
    for item in gt["constraints"]["CANNOT_invent"]:
        assert item in prompt


def test_validator_catches_invented_facts():
    extractor = GroundTruthExtractor("credit_scoring")
    data = _load_credit_sample()
    gt = extractor.extract(data)
    llm_output = "co_signer=yes\nunicorn=present"
    result = LLMValidator().validate(llm_output, gt, strict_mode=True)
    assert not result["checks"]["invented_facts"]["pass"]


def test_validator_catches_numerical_mismatches():
    extractor = GroundTruthExtractor("credit_scoring")
    data = _load_credit_sample()
    gt = extractor.extract(data)
    true_score = gt["facts_map"]["credit_score"]
    llm_output = f"credit_score={true_score + 100}"
    result = LLMValidator().validate(llm_output, gt, strict_mode=True)
    assert not result["checks"]["numbers"]["pass"]


def test_attester_dual_sha256():
    extractor = GroundTruthExtractor("credit_scoring")
    data = _load_credit_sample()
    gt = extractor.extract(data)
    validation = {"passes": True}
    attester = AttestationEngine()
    att_a = attester.attest(gt, "output_a", validation)
    att_b = attester.attest(gt, "output_b", validation)
    assert att_a["ground_truth_sha256"] == att_b["ground_truth_sha256"]
    assert att_a["combined_guarantee_sha256"] == att_b["combined_guarantee_sha256"]
    assert att_a["llm_output_sha256"] != att_b["llm_output_sha256"]


def test_pipeline_fallback():
    data = _load_credit_sample()

    def bad_llm(_prompt: str) -> str:
        return "unicorn=present"

    pipeline = ConSciencePipeline("credit_scoring")
    result = pipeline.process(
        "credit_scoring",
        data,
        task="Summarize decision",
        llm_provider=bad_llm,
        max_retries=2,
        fallback=True,
    )
    assert result["used_fallback"] is True
    assert result["final_output"] == result["deterministic_output"]

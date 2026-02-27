import json
from pathlib import Path

from deterministic_ai import main


def _normalize_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _run(args):
    main(args)


def test_determinism_cross_domain(tmp_path: Path):
    cases = [
        (
            "biblical_text",
            [
                "--domain",
                "biblical_text",
                "--input-ref",
                "John 4:7-10",
                "--dataset",
                "esv_sample",
                "--context",
                "moment=smoke test",
            ],
        ),
        (
            "credit_scoring",
            [
                "--domain",
                "credit_scoring",
                "--input-ref",
                "applicant_12345",
                "--input-file",
                "data/credit/sample_applicant.json",
            ],
        ),
        (
            "clinical_records",
            [
                "--domain",
                "clinical_records",
                "--input-ref",
                "patient_67890",
                "--input-file",
                "data/clinical/sample_patient_record.json",
            ],
        ),
    ]

    for name, base_args in cases:
        out_a = tmp_path / f"{name}_a"
        out_b = tmp_path / f"{name}_b"
        _run(base_args + ["--out", str(out_a)])
        _run(base_args + ["--out", str(out_b)])
        att_a = (out_a / "attestation.sha256").read_text(encoding="utf-8")
        att_b = (out_b / "attestation.sha256").read_text(encoding="utf-8")
        assert att_a == att_b


def test_no_invention_cross_domain(tmp_path: Path):
    out_dir = tmp_path / "credit_missing"
    _run(
        [
            "--domain",
            "credit_scoring",
            "--input-ref",
            "applicant_12345",
            "--input-file",
            "data/credit/sample_applicant.json",
            "--out",
            str(out_dir),
        ]
    )
    output = (out_dir / "output.json").read_text(encoding="utf-8")
    assert "{missing:" in output


GOLDENS = [
    (
        "biblical_text",
        [
            "--domain",
            "biblical_text",
            "--input-ref",
            "John 4:7-10",
            "--dataset",
            "esv_sample",
            "--context",
            "moment=smoke test",
        ],
        "tests/golden/biblical_text/john_4_7_10",
    ),
    (
        "credit_scoring",
        [
            "--domain",
            "credit_scoring",
            "--input-ref",
            "applicant_12345",
            "--input-file",
            "data/credit/sample_applicant.json",
        ],
        "tests/golden/credit_scoring/applicant_12345",
    ),
    (
        "clinical_records",
        [
            "--domain",
            "clinical_records",
            "--input-ref",
            "patient_67890",
            "--input-file",
            "data/clinical/sample_patient_record.json",
        ],
        "tests/golden/clinical_records/patient_67890",
    ),
]


def test_golden_snapshots(tmp_path: Path):
    for _, base_args, golden_dir in GOLDENS:
        out_dir = tmp_path / Path(golden_dir).name
        _run(base_args + ["--out", str(out_dir)])

        expected = json.loads(
            (Path(golden_dir) / "expected_output.json").read_text(encoding="utf-8")
        )
        actual = json.loads((out_dir / "output.json").read_text(encoding="utf-8"))
        assert actual == expected

        expected_prov = json.loads(
            (Path(golden_dir) / "expected_provenance.json").read_text(encoding="utf-8")
        )
        actual_prov = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
        assert actual_prov == expected_prov

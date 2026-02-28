import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from deterministic_ai import main  # noqa: E402

CASES = [
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
    (
        "legal_contract",
        [
            "--domain",
            "legal_contract",
            "--input-ref",
            "sample_contract",
            "--input-file",
            "data/legal_contract_sample/sample_contract.txt",
            "--timestamp",
            "2026-02-28T14:32:00Z",
            "--commit-ref",
            "e20fbd8",
            "--repo-tag",
            "v0.2.0-legal-domain",
        ],
    ),
]


def _run(args, out_dir: Path):
    if out_dir.exists():
        _safe_rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    main(args + ["--out", str(out_dir)])


def _compare_dirs(dir_a: Path, dir_b: Path):
    files_a = sorted([p.name for p in dir_a.iterdir() if p.is_file()])
    files_b = sorted([p.name for p in dir_b.iterdir() if p.is_file()])
    if files_a != files_b:
        raise SystemExit(f"File lists differ: {files_a} != {files_b}")
    for name in files_a:
        a_bytes = (dir_a / name).read_bytes()
        b_bytes = (dir_b / name).read_bytes()
        if a_bytes != b_bytes:
            raise SystemExit(f"File contents differ for {name}")


def _on_rm_error(func, path, exc_info):
    Path(path).chmod(stat.S_IWRITE)
    func(path)


def _safe_rmtree(path: Path):
    try:
        shutil.rmtree(path, onerror=_on_rm_error)
    except PermissionError:
        pass


def main_check():
    base = Path("tmp_repro_check")
    if base.exists():
        _safe_rmtree(base)
    base.mkdir(parents=True, exist_ok=True)

    for name, args in CASES:
        out_a = base / f"{name}_a"
        out_b = base / f"{name}_b"
        _run(args, out_a)
        _run(args, out_b)
        _compare_dirs(out_a, out_b)

    _safe_rmtree(base)


if __name__ == "__main__":
    main_check()

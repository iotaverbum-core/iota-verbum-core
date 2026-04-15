from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.cuc_metacognition_shared import build_shared_runtime_source

TASK_JSON_PATH = REPO_ROOT / "benchmark" / "cuc_metacognition_v5a_candidate.task.json"
NOTEBOOK_PATH = (
    REPO_ROOT / "scripts" / "cuc_metacognition_v5a_candidate_runner_export_stub.ipynb"
)

TASK_NAME = "cuc_metacognition_v5a_candidate"

V5A_TASK_RUNTIME_SOURCE = r'''
TASK_NAME = "cuc_metacognition_v5a_candidate"

RUN1_TEMPLATE = """You are evaluating the CLEAN CUC v5a evidence pack below.

Return a concise analyst snapshot. It does not have to be valid JSON, but keep it structured and compact.

Include:
- ACTIVE_CLAIMS: claims that currently look most decision-relevant
- REVISION_TARGETS: claims most likely to need revision if a key artifact changes
- PRESERVE_WATCH: stable sibling claims that should not be rewritten without new contrary evidence
- OPEN_UNKNOWNS: unresolved issues that would materially change the downstream assessment

=== CLEAN PACK ===
{clean_pack_text}
=== END CLEAN PACK ===
"""

RUN2A_HEADER = """Here is your prior analyst snapshot from Run 1.
Use it only as prior state, not as new evidence.

{run1_response}

The evidence pack has been perturbed after your first analysis.

Use your prior analysis plus the perturbed pack to output STRICT JSON only.
"""

RUN2B_HEADER = """You are evaluating the evidence pack below as a first-pass structured analysis.

No prior snapshot exists. Produce a complete, fully grounded structured delta as if you are seeing this perturbed evidence pack for the first time. Account for every structurally relevant claim in the citation map. Do not economise on citation coverage - every node whose status is determined by evidence in this pack should appear in the citations object with its supporting evidence id.
"""

RUN2_PACK_TEMPLATE = """=== PERTURBED PACK ===
{perturbed_pack_text}
=== END PERTURBED PACK ===

{canonical_reference}
"""


@kbench.task(name=TASK_NAME)
def cuc_metacognition_v5a_candidate(
    llm,
    case_id,
    family_id,
    sector_skin,
    render_profile,
    hop_depth,
    named_evidence_artifact,
    clean_pack_text,
    perturbed_pack_text,
    clean_pack_json,
    perturbed_pack_json,
    expected_delta_json,
    causal_chain_json,
    scoring_manifest_json,
    source_case_id=None,
    source_param_id=None,
    v5a_pilot_bucket=None,
    v5a_pack_version=None,
    v5a_prompt_stages=None,
    **_,
):
    scoring_manifest = normalize_jsonish(scoring_manifest_json)
    citation_obligation_map = scoring_manifest.get("citation_obligation_map", {})
    canonical_reference = build_canonical_reference(
        expected_delta_json=expected_delta_json,
        scoring_manifest_json=scoring_manifest_json,
        perturbed_pack_json=perturbed_pack_json,
    )

    run1_prompt = "\n\n".join(
        [
            SYSTEM_PROMPT,
            RUN1_TEMPLATE.replace("{clean_pack_text}", clean_pack_text),
        ]
    )
    run1_response = llm.prompt(run1_prompt)

    run2a_prompt = "\n\n".join(
        [
            SYSTEM_PROMPT,
            RUN2A_HEADER.format(run1_response=run1_response.strip()),
            RUN2_SCHEMA_INSTRUCTIONS.strip(),
            RUN2_PACK_TEMPLATE.format(
                perturbed_pack_text=perturbed_pack_text,
                canonical_reference=canonical_reference,
            ),
        ]
    )
    run2a_response = llm.prompt(run2a_prompt)

    run2b_prompt = "\n\n".join(
        [
            SYSTEM_PROMPT,
            RUN2B_HEADER.strip(),
            RUN2_SCHEMA_INSTRUCTIONS.strip(),
            RUN2_PACK_TEMPLATE.format(
                perturbed_pack_text=perturbed_pack_text,
                canonical_reference=canonical_reference,
            ),
        ]
    )
    run2b_response = llm.prompt(run2b_prompt)

    run2a_score = score_structured_response(
        run2a_response,
        expected_delta_json=expected_delta_json,
        scoring_manifest_json=scoring_manifest_json,
        clean_pack_json=clean_pack_json,
        perturbed_pack_json=perturbed_pack_json,
    )
    run2b_score = score_structured_response(
        run2b_response,
        expected_delta_json=expected_delta_json,
        scoring_manifest_json=scoring_manifest_json,
        clean_pack_json=clean_pack_json,
        perturbed_pack_json=perturbed_pack_json,
    )

    try:
        run2a_parsed = extract_json_object(run2a_response) if run2a_score["parse_ok"] else {}
    except Exception:
        run2a_parsed = {}
    try:
        run2b_parsed = extract_json_object(run2b_response) if run2b_score["parse_ok"] else {}
    except Exception:
        run2b_parsed = {}

    diagnostics = diagnostics_to_dict(
        compute_prior_anchor_diagnostics(
            run2a_parsed,
            run2b_parsed,
            citation_obligation_map,
        )
    )
    diagnostic_payload = {
        "case_id": case_id,
        "source_case_id": source_case_id,
        "v5a_pilot_bucket": v5a_pilot_bucket,
        "run2a_overall_score": run2a_score["overall_score"],
        "run2a_overall_pass": run2a_score["overall_pass"],
        "run2b_overall_score": run2b_score["overall_score"],
        "run2b_overall_pass": run2b_score["overall_pass"],
        "diagnostics": diagnostics,
    }
    kbench.assertions.assert_true(
        True,
        expectation="V5A_PRIOR_ANCHOR_DIAGNOSTICS="
        + json.dumps(diagnostic_payload, sort_keys=True),
    )

    for label, score in (("Run 2A", run2a_score), ("Run 2B", run2b_score)):
        kbench.assertions.assert_true(
            not score["hard_fail_reasons"],
            expectation=(
                f"{case_id} {label} should avoid hard fails around changed artifact "
                f"{named_evidence_artifact}: {score['hard_fail_reasons']} "
                f"source_case_id={source_case_id} bucket={v5a_pilot_bucket}"
            ),
        )
        kbench.assertions.assert_true(
            score["overall_pass"],
            expectation=(
                f"{case_id} {label} should satisfy the v5a structured pass rule. "
                f"family_id={family_id} render_profile={render_profile} hop_depth={hop_depth} "
                f"named_evidence_artifact={named_evidence_artifact} "
                f"source_case_id={source_case_id} bucket={v5a_pilot_bucket} score={score}"
            ),
        )

    return None
'''


NOTEBOOK_CELL_SOURCE = r'''import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import kaggle_benchmarks as kbench

TASK_JSON_RELATIVE_PATH = "benchmark/cuc_metacognition_v5a_candidate.task.json"
PARAMS_JSON_RELATIVE_PATHS = [
    "benchmark/cuc_v5_64_params.json",
    "benchmark/cuc_v5a_candidate_params.json",
]
INPUT_ROOTS = [Path("/kaggle/input"), Path.cwd()]
EXPORT_BASE = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path(tempfile.gettempdir())
EXPORT_ROOT = EXPORT_BASE / "cuc_v5a_candidate_export"
CASE_LIMIT = None


def resolve_artifact_path(relative_path: str) -> Path:
    local_candidate = Path(relative_path)
    if local_candidate.is_file():
        return local_candidate

    for input_root in INPUT_ROOTS:
        if not input_root.exists():
            continue
        exact_candidate = input_root / relative_path
        if exact_candidate.is_file():
            return exact_candidate
        matches = sorted(
            input_root.rglob(Path(relative_path).name),
            key=lambda p: (len(str(p)), str(p)),
        )
        if matches:
            return matches[0]

    raise FileNotFoundError(f"Could not resolve artifact path for {relative_path}")


def resolve_first_artifact_path(relative_paths: list[str]) -> tuple[str, Path]:
    for relative_path in relative_paths:
        try:
            return relative_path, resolve_artifact_path(relative_path)
        except FileNotFoundError:
            continue

    raise FileNotFoundError(
        "Could not resolve any artifact path from "
        + ", ".join(relative_paths)
    )


TASK_JSON_PATH = resolve_artifact_path(TASK_JSON_RELATIVE_PATH)
PARAMS_JSON_RELATIVE_PATH, PARAMS_JSON_PATH = resolve_first_artifact_path(PARAMS_JSON_RELATIVE_PATHS)

print("Resolved TASK_JSON_PATH:", TASK_JSON_PATH)
print("Resolved PARAMS_JSON_PATH:", PARAMS_JSON_PATH)

task_spec = json.loads(TASK_JSON_PATH.read_text(encoding="utf-8"))
TASK_NAME = task_spec["name"]
assert TASK_NAME == "cuc_metacognition_v5a_candidate"

task_runtime_dir = Path(tempfile.gettempdir()) / "cuc_v5a_candidate_runtime"
task_runtime_dir.mkdir(parents=True, exist_ok=True)
TASK_RUNTIME_MODULE_PATH = task_runtime_dir / "cuc_metacognition_v5a_candidate_runtime.py"
TASK_RUNTIME_MODULE_PATH.write_text(task_spec["definition"] + "\n", encoding="utf-8")
compiled_task_definition = compile(task_spec["definition"], str(TASK_RUNTIME_MODULE_PATH), "exec")
exec(compiled_task_definition, globals())
assert "cuc_metacognition_v5a_candidate" in globals()

print("Loaded task:", TASK_NAME)
print("Task definition path:", TASK_JSON_PATH)
print("Runtime task module path:", TASK_RUNTIME_MODULE_PATH)

records = json.loads(PARAMS_JSON_PATH.read_text(encoding="utf-8"))
assert isinstance(records, list) and records, "Params JSON must contain at least one record"

if CASE_LIMIT is not None:
    records = records[:CASE_LIMIT]

df = pd.DataFrame(records)
assert not df.empty, "No v5a candidate rows loaded"
required_columns = {
    "case_id",
    "family_id",
    "render_profile",
    "hop_depth",
    "clean_pack_text",
    "perturbed_pack_text",
    "clean_pack_json",
    "perturbed_pack_json",
    "expected_delta_json",
    "causal_chain_json",
    "scoring_manifest_json",
    "source_case_id",
    "v5a_pilot_bucket",
}
missing = sorted(required_columns.difference(df.columns))
assert not missing, f"Missing required columns: {missing}"

print("Loaded rows:", len(df))
print(
    df[
        [
            "case_id",
            "source_case_id",
            "family_id",
            "v5a_pilot_bucket",
            "sector_skin",
            "render_profile",
            "hop_depth",
        ]
    ].to_string(index=False)
)

assert not df.empty, "df must not be empty"
sample_row = df.iloc[0]
sample_score = score_structured_response(
    json.dumps(
        {
            "q1_delta_detection": {
                "summary": "smoke",
                "changed_state_ids": [],
                "changed_event_ids": [],
                "changed_edge_ids": [],
                "changed_scenario_ids": [],
            },
            "q2_revision": {
                "preserve_ids": [],
                "weaken_ids": [],
                "strengthen_ids": [],
                "retract_ids": [],
                "newly_relevant_unknown_ids": [],
                "forbidden_revision_ack": [],
            },
            "q3_unknown_ledger": {
                "resolved_unknown_ids": [],
                "still_open_unknown_ids": [],
                "new_unknown_ids": [],
                "category_map": {},
                "summary": "smoke",
            },
            "citations": {},
            "self_check": {
                "no_global_rewrite_claimed": True,
                "max_hop_claimed": 0,
                "low_confidence_ids": [],
            },
        }
    ),
    expected_delta_json=sample_row["expected_delta_json"],
    scoring_manifest_json=sample_row["scoring_manifest_json"],
    clean_pack_json=sample_row["clean_pack_json"],
    perturbed_pack_json=sample_row["perturbed_pack_json"],
)
assert "overall_score" in sample_score and "axis_scores" in sample_score
print("Smoke test passed for sample case:", sample_row["case_id"])

results = cuc_metacognition_v5a_candidate.evaluate(
    llm=[kbench.llm],
    evaluation_data=df,
)

print(results)
for run in results.runs:
    print(run)


def iso_or_none(value):
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def safe_status(value):
    if value is None:
        return None
    return getattr(value, "value", str(value))


def summarize_assertion(assertion):
    return {
        "id": getattr(assertion, "id", None),
        "passed": bool(getattr(assertion, "passed", False)),
        "expectation": getattr(assertion, "expectation", None),
    }


def summarize_run(run):
    params = getattr(run, "params", {}) or {}
    llm_obj = params.get("llm")
    raw_passed = getattr(run, "passed", None)
    raw_result = getattr(run, "result", None)
    status = safe_status(getattr(run, "status", None))
    if raw_passed is not None:
        result = bool(raw_passed)
    elif isinstance(raw_result, bool):
        result = raw_result
    else:
        result = status == "PASS"
    return {
        "id": getattr(run, "id", None),
        "param_id": getattr(run, "param_id", None),
        "case_id": params.get("case_id", getattr(run, "case_id", None)),
        "source_case_id": params.get("source_case_id"),
        "family_id": params.get("family_id"),
        "v5a_pilot_bucket": params.get("v5a_pilot_bucket"),
        "sector_skin": params.get("sector_skin"),
        "render_profile": params.get("render_profile"),
        "hop_depth": params.get("hop_depth"),
        "named_evidence_artifact": params.get("named_evidence_artifact"),
        "llm": getattr(llm_obj, "name", str(llm_obj)) if llm_obj is not None else getattr(run, "llm_name", None),
        "result": result,
        "passed": result,
        "status": status,
        "error_message": getattr(run, "error_message", None),
        "start_time": iso_or_none(getattr(run, "start_time", None)),
        "end_time": iso_or_none(getattr(run, "end_time", None)),
        "assertion_results": [
            summarize_assertion(a) for a in getattr(run, "assertion_results", [])
        ],
    }


EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
shutil.copy2(TASK_JSON_PATH, EXPORT_ROOT / TASK_JSON_PATH.name)
shutil.copy2(PARAMS_JSON_PATH, EXPORT_ROOT / PARAMS_JSON_PATH.name)

preview_columns = [
    "param_id",
    "case_id",
    "source_case_id",
    "family_id",
    "v5a_pilot_bucket",
    "sector_skin",
    "render_profile",
    "hop_depth",
    "named_evidence_artifact",
]
preview_df = df[preview_columns].copy()
preview_df.to_csv(EXPORT_ROOT / "evaluation_input_preview.csv", index=False)

runs_summary = [summarize_run(run) for run in getattr(results, "runs", [])]

export_payload = {
    "task_name": TASK_NAME,
    "task_json_relative_path": TASK_JSON_RELATIVE_PATH,
    "params_json_relative_path": PARAMS_JSON_RELATIVE_PATH,
    "params_json_relative_path_candidates": PARAMS_JSON_RELATIVE_PATHS,
    "resolved_task_json_path": str(TASK_JSON_PATH),
    "resolved_params_json_path": str(PARAMS_JSON_PATH),
    "exported_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "case_count": len(df),
    "run_count": len(runs_summary),
    "pass_count": sum(1 for run in runs_summary if run["result"]),
    "fail_count": sum(1 for run in runs_summary if not run["result"]),
    "results_repr": repr(results),
    "runs": runs_summary,
}

(EXPORT_ROOT / "results_export.json").write_text(
    json.dumps(export_payload, indent=2, sort_keys=True),
    encoding="utf-8",
)
(EXPORT_ROOT / "results_repr.txt").write_text(f"{results}\n", encoding="utf-8")

print("Exported notebook stub artifacts to:", EXPORT_ROOT)
for path in sorted(EXPORT_ROOT.iterdir()):
    print(" -", path)
'''


def build_task_definition() -> str:
    return build_shared_runtime_source() + "\n" + V5A_TASK_RUNTIME_SOURCE.strip() + "\n"


def build_task_spec() -> dict[str, object]:
    return {
        "versionNumber": 1,
        "name": TASK_NAME,
        "definition": build_task_definition(),
    }


def build_notebook_document() -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [line + "\n" for line in NOTEBOOK_CELL_SOURCE.rstrip().splitlines()],
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    task_spec = build_task_spec()
    notebook = build_notebook_document()

    TASK_JSON_PATH.write_text(json.dumps(task_spec, indent=2) + "\n", encoding="utf-8")
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {TASK_JSON_PATH}")
    print(f"Wrote {NOTEBOOK_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

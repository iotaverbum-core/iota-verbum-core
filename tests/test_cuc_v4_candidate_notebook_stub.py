from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path


def test_v4_candidate_notebook_stub_references_task_and_params() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = (
        repo_root / "scripts" / "cuc_metacognition_v4_candidate_runner_export_stub.ipynb"
    )

    notebook = json.loads(notebook_path.read_text(encoding="utf-8-sig"))
    cell_sources: list[str] = []
    for cell in notebook["cells"]:
        source = cell.get("source", "")
        if isinstance(source, list):
            cell_sources.append("".join(source))
        else:
            cell_sources.append(str(source))

    notebook_source = "\n\n".join(cell_sources)

    assert "benchmark/cuc_metacognition_v4_candidate.task.json" in notebook_source
    assert "benchmark/cuc_v4_candidate_params.json" in notebook_source
    assert "kbench.llm" in notebook_source
    assert "llm=[kbench.llm]" in notebook_source


def test_v4_candidate_notebook_stub_executes_with_fake_kbench(
    tmp_path, monkeypatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = (
        repo_root / "scripts" / "cuc_metacognition_v4_candidate_runner_export_stub.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8-sig"))

    @dataclass
    class FakeRun:
        case_id: str
        llm_name: str
        passed: bool

    @dataclass
    class FakeResults:
        runs: list[FakeRun]

    class FakeAssertions:
        def assert_true(self, condition, expectation="") -> None:
            if not condition:
                raise AssertionError(expectation)

    class FakeLLM:
        name = "fake-kbench-llm"

        def __init__(self) -> None:
            self._row = None
            self._prompt_count = 0
            self.prompts: list[str] = []

        def set_row(self, row: dict[str, object]) -> None:
            self._row = row
            self._prompt_count = 0

        def prompt(self, prompt: str) -> str:
            self.prompts.append(prompt)
            self._prompt_count += 1
            if self._prompt_count == 1:
                return "ACTIVE_CLAIMS: smoke"
            assert self._row is not None
            expected_delta = self._row["expected_delta_json"]
            changed_states = [item["id"] for item in expected_delta["changed_states"]]
            changed_events = [item["id"] for item in expected_delta["changed_events"]]
            changed_edges = [item["id"] for item in expected_delta["changed_edges"]]
            changed_scenarios = [
                item["scenario_id"] for item in expected_delta["scenario_rank_changes"]
            ]
            new_unknowns = [item["id"] for item in expected_delta["new_unknowns"]]
            resolved_unknowns = [
                item["id"] for item in expected_delta["resolved_unknowns"]
            ]
            return json.dumps(
                {
                    "q1_delta_detection": {
                        "summary": "detected revised branch",
                        "changed_state_ids": changed_states,
                        "changed_event_ids": changed_events,
                        "changed_edge_ids": changed_edges,
                        "changed_scenario_ids": changed_scenarios,
                    },
                    "q2_revision": {
                        "preserve_ids": expected_delta["preserved_items"],
                        "weaken_ids": [],
                        "strengthen_ids": [],
                        "retract_ids": [],
                        "newly_relevant_unknown_ids": new_unknowns,
                        "forbidden_revision_ack": expected_delta["forbidden_revisions"],
                    },
                    "q3_unknown_ledger": {
                        "resolved_unknown_ids": resolved_unknowns,
                        "still_open_unknown_ids": new_unknowns,
                        "new_unknown_ids": new_unknowns,
                        "category_map": {unknown_id: "new" for unknown_id in new_unknowns},
                        "summary": "tracked unknowns",
                    },
                    "citations": expected_delta["supporting_evidence_map"],
                    "self_check": {
                        "no_global_rewrite_claimed": True,
                        "max_hop_claimed": int(self._row["hop_depth"]),
                        "low_confidence_ids": new_unknowns,
                    },
                }
            )

    class FakeTask:
        def __init__(self, fn):
            self._fn = fn

        def evaluate(self, llm, evaluation_data):
            models = llm if isinstance(llm, list) else [llm]
            rows = evaluation_data.to_dict(orient="records")
            runs = []
            for model in models:
                for row in rows:
                    if hasattr(model, "set_row"):
                        model.set_row(row)
                    passed = self._fn(llm=model, **row)
                    runs.append(
                        FakeRun(
                            case_id=row["case_id"],
                            llm_name=getattr(model, "name", str(model)),
                            passed=bool(passed),
                        )
                    )
            return FakeResults(runs=runs)

    class FakeKBench(types.ModuleType):
        def __init__(self) -> None:
            super().__init__("kaggle_benchmarks")
            self.assertions = FakeAssertions()
            self.llm = FakeLLM()

        def task(self, name):
            def decorator(fn):
                return FakeTask(fn)

            return decorator

    fake_kbench = FakeKBench()
    monkeypatch.setitem(sys.modules, "kaggle_benchmarks", fake_kbench)

    namespace = {"__name__": "__main__"}
    for cell_index, cell in enumerate(notebook["cells"], start=1):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        else:
            source = str(source)
        if cell_index == 6:
            namespace["EXPORT_ROOT"] = tmp_path / "cuc_v4_candidate_export"
        exec(source, namespace)

    df = namespace["df"]
    first_row = df.iloc[0]
    assert "sections" in first_row["clean_pack_json"]
    assert "sections" in first_row["perturbed_pack_json"]
    assert "changed_states" in first_row["expected_delta_json"]
    assert "weights" in first_row["scoring_manifest_json"]
    assert "operational_pass_rule" in first_row["scoring_manifest_json"]

    export_root = namespace["EXPORT_ROOT"]
    assert export_root.exists()
    assert (export_root / "cuc_metacognition_v4_candidate.task.json").is_file()
    assert (export_root / "cuc_v4_candidate_params.json").is_file()
    assert (export_root / "evaluation_input_preview.csv").is_file()
    assert (export_root / "results_export.json").is_file()
    assert (export_root / "results_repr.txt").is_file()

    export_payload = json.loads(
        (export_root / "results_export.json").read_text(encoding="utf-8")
    )
    assert export_payload["task_name"] == "cuc_metacognition_v4_candidate"
    assert export_payload["case_count"] == 24
    assert export_payload["run_count"] == 24
    assert export_payload["pass_count"] == 24
    assert export_payload["fail_count"] == 0
    assert len(export_payload["runs"]) == 24
    assert all(run["result"] for run in export_payload["runs"])
    assert all(run["passed"] for run in export_payload["runs"])

    prompt_log = "\n\n".join(fake_kbench.llm.prompts)
    assert "=== CANONICAL ID REFERENCE ===" in prompt_log
    assert "SUPPORTING_EVIDENCE_MAP:" in prompt_log
    assert "ALLOWED_EVIDENCE_IDS:" in prompt_log
    assert (
        "never surface artifact labels like CL-0055-R, POD-882, NL-204, or AC-778"
        in prompt_log
    )
    assert "state:penalty_triggered" in prompt_log
    assert "evidence:retraction" in prompt_log
    assert "state:attack_origin_attribution" in prompt_log
    assert "evidence:vendor_credential_alert" in prompt_log


def test_v4_candidate_notebook_stub_readme_links_main_handoff_files() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    readme_path = (
        repo_root
        / "scripts"
        / "cuc_metacognition_v4_candidate_runner_export_stub.README.md"
    )

    readme_text = readme_path.read_text(encoding="utf-8")

    assert "cuc_metacognition_v4_candidate_runner_export_stub.ipynb" in readme_text
    assert "copy_cuc_v4_candidate_kaggle_cell.ps1" in readme_text
    assert "export_cuc_v4_candidate_kaggle_cells.ps1" in readme_text
    assert "build_cuc_v4_candidate_params.py" in readme_text
    assert "prepare_cuc_v4_candidate_five_model_sweep.ps1" in readme_text
    assert "import_cuc_v4_candidate_five_model_sweep.py" in readme_text
    assert "import_cuc_v4_candidate_five_model_sweep.ps1" in readme_text
    assert "benchmark/cuc_metacognition_v4_candidate.task.json" in readme_text
    assert "benchmark/cuc_v4_candidate_params.json" in readme_text
    assert "/kaggle/working/cuc_v4_candidate_export/" in readme_text
    assert "CUC_V4_CANDIDATE_FIVE_MODEL_SWEEP_2026_04_08.md" in readme_text


def test_v4_candidate_task_uses_axis_assertions_as_diagnostics_after_operational_pass() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    task_path = repo_root / "benchmark" / "cuc_metacognition_v4_candidate.task.json"
    task_doc = json.loads(task_path.read_text(encoding="utf-8"))
    definition = task_doc["definition"]

    class FakeAssertions:
        def assert_true(self, condition, expectation="") -> None:
            if not condition:
                raise AssertionError(expectation)

    class FakeKBench:
        def __init__(self) -> None:
            self.assertions = FakeAssertions()

        def task(self, name):
            def decorator(fn):
                return fn

            return decorator

    class FakeLLM:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def prompt(self, prompt: str) -> str:
            self.prompts.append(prompt)
            return "snapshot" if len(self.prompts) == 1 else "{}"

    def fake_score_structured_response(*args, **kwargs):
        return {
            "hard_fail_reasons": [],
            "axis_scores": {
                "delta_detection": 0.5,
                "causal_temporal_propagation": 0.4,
                "selective_revision": 1.0,
                "unknown_ledger_discipline": 1.0,
                "evidence_grounding": 1.0,
            },
            "overall_score": 0.78,
            "overall_pass": True,
        }

    namespace = {
        "TASK_NAME": "cuc_metacognition_v4_candidate",
        "kbench": FakeKBench(),
        "SYSTEM_PROMPT": "system",
        "RUN1_TEMPLATE": "clean {clean_pack_text}",
        "RUN2_TEMPLATE": "perturbed {perturbed_pack_text}",
        "score_structured_response": fake_score_structured_response,
    }
    exec(definition, namespace)
    task_fn = namespace["cuc_metacognition_v4_candidate"]

    fake_llm = FakeLLM()
    pack = {
        "sections": {
            "states": [
                {
                    "state_id": "state:delivery_complete",
                    "predicate": "delivery_complete",
                    "object": "true",
                    "status": "supported",
                    "evidence_ids": ["evidence:delivery"],
                },
                {
                    "state_id": "state:notice_timely",
                    "predicate": "notice_timely",
                    "object": "true",
                    "status": "supported",
                    "evidence_ids": ["evidence:notice"],
                },
                {
                    "state_id": "state:penalty_triggered",
                    "predicate": "penalty_triggered",
                    "object": "uncertain",
                    "status": "contested",
                    "evidence_ids": ["evidence:admission", "evidence:retraction"],
                },
                {
                    "state_id": "state:recovery_recommended",
                    "predicate": "formal_recovery_recommended",
                    "object": "qualified",
                    "status": "under_review",
                    "evidence_ids": ["evidence:retraction"],
                },
            ],
            "events": [
                {
                    "event_id": "event:admission",
                    "type": "admission_event",
                    "action": "delay admission recorded",
                    "evidence_ids": ["evidence:admission"],
                },
                {
                    "event_id": "event:retraction",
                    "type": "retraction_event",
                    "action": "admission retracted",
                    "evidence_ids": ["evidence:retraction"],
                },
            ],
            "causal_edges": [
                {
                    "edge_id": "edge:admission_support",
                    "relation": "supports",
                    "to_id": "state:penalty_triggered",
                    "evidence_ids": ["evidence:admission"],
                },
                {
                    "edge_id": "edge:recovery_dependency",
                    "relation": "supports_downstream_recovery",
                    "to_id": "state:recovery_recommended",
                    "evidence_ids": ["evidence:admission"],
                },
                {
                    "edge_id": "edge:retraction_support",
                    "relation": "supports_retraction",
                    "to_id": "state:penalty_triggered",
                    "evidence_ids": ["evidence:retraction"],
                },
            ],
            "scenarios": [
                {
                    "scenario_id": "scenario:performance_record",
                    "rank": 1,
                    "status": "live",
                    "basis_ids": ["state:delivery_complete", "state:notice_timely"],
                },
                {
                    "scenario_id": "scenario:recovery_path",
                    "rank": 2,
                    "status": "live",
                    "basis_ids": ["state:penalty_triggered", "state:recovery_recommended"],
                },
            ],
            "unknowns": [
                {
                    "unknown_id": "unknown:secondary_followup",
                    "category": "follow_up",
                    "status": "open",
                    "target_id": "event:notice",
                    "evidence_ids": ["evidence:notice"],
                },
                {
                    "unknown_id": "unknown:penalty_enforceability",
                    "category": "legal",
                    "status": "open",
                    "target_id": "state:penalty_triggered",
                    "evidence_ids": ["evidence:retraction"],
                },
            ],
            "evidence": [
                {
                    "evidence_id": "evidence:admission",
                    "source_type": "counterparty_letter",
                    "source_id": "src:admission",
                    "content": "Letter CL-0051 states Northwind accepted the delay penalty.",
                },
                {
                    "evidence_id": "evidence:delivery",
                    "source_type": "proof_of_delivery",
                    "source_id": "src:delivery",
                    "content": "Proof of delivery POD-882 shows complete delivery.",
                },
                {
                    "evidence_id": "evidence:notice",
                    "source_type": "notice_log",
                    "source_id": "src:notice",
                    "content": "Notice log NL-204 shows timely notice.",
                },
                {
                    "evidence_id": "evidence:retraction",
                    "source_type": "counterparty_retraction",
                    "source_id": "src:retraction",
                    "content": "Retraction CL-0055-R withdraws the admission pending interpretation.",
                },
            ],
        }
    }
    expected_delta_json = {
        "changed_states": [
            {"id": "state:penalty_triggered"},
            {"id": "state:recovery_recommended"},
        ],
        "changed_events": [{"id": "event:retraction"}],
        "changed_edges": [
            {"id": "edge:admission_support"},
            {"id": "edge:retraction_support"},
        ],
        "scenario_rank_changes": [
            {"scenario_id": "scenario:performance_record"},
            {"scenario_id": "scenario:recovery_path"},
        ],
        "new_unknowns": [{"id": "unknown:penalty_enforceability"}],
        "resolved_unknowns": [],
        "must_revise_claims": [
            "state:penalty_triggered",
            "state:recovery_recommended",
        ],
        "must_preserve_claims": [
            "state:delivery_complete",
            "state:notice_timely",
        ],
        "preserved_items": [
            "edge:delivery_support",
            "edge:notice_support",
            "state:delivery_complete",
            "state:notice_timely",
            "unknown:secondary_followup",
        ],
        "forbidden_revisions": [
            "edge:delivery_support",
            "edge:notice_support",
            "state:delivery_complete",
            "state:notice_timely",
            "unknown:secondary_followup",
        ],
        "supporting_evidence_map": {
            "edge:admission_support": ["evidence:admission", "evidence:retraction"],
            "edge:retraction_support": ["evidence:retraction"],
            "event:retraction": ["evidence:retraction"],
            "state:penalty_triggered": ["evidence:admission", "evidence:retraction"],
            "state:recovery_recommended": ["evidence:retraction"],
            "unknown:penalty_enforceability": ["evidence:retraction"],
        },
    }
    causal_chain_json = {
        "chain": ["C1", "C2"],
        "preserve_branch": ["C3", "C4"],
        "root": "C1",
        "structural_invariant": "Diagnostic chain invariant.",
    }
    scoring_manifest_json = {
        "operational_pass_rule": {
            "citation_coverage_min": 0.67,
            "delta_detection_min": 0.5,
            "overall_min": 0.78,
        },
        "evidence_grounding_requirement": "Use evidence:retraction for the revised branch.",
        "preservation_requirement": "Preserve delivery and notice branches.",
        "structural_propagation_requirement": "Qualify recovery if the penalty admission is retracted.",
    }

    result = task_fn(
        llm=fake_llm,
        case_id="CASE-1",
        family_id="selective_preservation_sibling_stability",
        sector_skin="legal_contract",
        render_profile="legal_formal_v1",
        hop_depth=2,
        named_evidence_artifact="Retraction CL-0055-R",
        clean_pack_text="clean pack",
        perturbed_pack_text="perturbed pack",
        clean_pack_json=pack,
        perturbed_pack_json=pack,
        expected_delta_json=expected_delta_json,
        causal_chain_json=causal_chain_json,
        scoring_manifest_json=scoring_manifest_json,
    )

    assert result is True
    assert len(fake_llm.prompts) == 2
    assert "=== CANONICAL ID REFERENCE ===" in fake_llm.prompts[1]
    assert "ALLOWED_EVIDENCE_IDS:" in fake_llm.prompts[1]

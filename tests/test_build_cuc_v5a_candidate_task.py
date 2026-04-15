from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from dataclasses import dataclass
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "build_cuc_v5a_candidate_task.py"
    spec = importlib.util.spec_from_file_location(
        "build_cuc_v5a_candidate_task",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_generated_v5a_task_and_notebook_match_builder() -> None:
    module = _load_module()
    repo_root = Path(__file__).resolve().parents[1]

    generated_task = json.loads(
        (repo_root / "benchmark" / "cuc_metacognition_v5a_candidate.task.json").read_text(
            encoding="utf-8"
        )
    )
    generated_notebook = json.loads(
        (
            repo_root
            / "scripts"
            / "cuc_metacognition_v5a_candidate_runner_export_stub.ipynb"
        ).read_text(encoding="utf-8")
    )

    assert generated_task == module.build_task_spec()
    assert generated_notebook == module.build_notebook_document()


def test_v5a_task_spec_is_self_contained_and_dual_run() -> None:
    module = _load_module()
    task_spec = module.build_task_spec()

    assert task_spec["name"] == "cuc_metacognition_v5a_candidate"
    definition = task_spec["definition"]

    assert "score_structured_response" in definition
    assert "build_canonical_reference" in definition
    assert "compute_prior_anchor_diagnostics" in definition
    assert "RUN2A_HEADER" in definition
    assert "RUN2B_HEADER" in definition
    assert "citation_obligation_map" in definition
    assert "V5A_PRIOR_ANCHOR_DIAGNOSTICS=" in definition
    assert "return None" in definition


def test_v5a_notebook_prefers_full_pack_with_pilot_fallback() -> None:
    module = _load_module()
    notebook = module.build_notebook_document()
    cell_source = "".join(notebook["cells"][0]["source"])

    assert '"benchmark/cuc_v5_64_params.json"' in cell_source
    assert '"benchmark/cuc_v5a_candidate_params.json"' in cell_source
    assert "resolve_first_artifact_path" in cell_source


def test_v5a_notebook_stub_executes_with_fake_kbench(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    notebook_path = (
        repo_root / "scripts" / "cuc_metacognition_v5a_candidate_runner_export_stub.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

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

        def set_row(self, row: dict[str, object]) -> None:
            self._row = row
            self._prompt_count = 0

        def prompt(self, prompt: str) -> str:
            self._prompt_count += 1
            if self._prompt_count == 1:
                return "ACTIVE_CLAIMS: smoke"

            assert self._row is not None
            expected_delta = self._row["expected_delta_json"]
            scoring_manifest = self._row["scoring_manifest_json"]
            changed_states = [item["id"] for item in expected_delta["changed_states"]]
            changed_events = [item["id"] for item in expected_delta["changed_events"]]
            changed_edges = [item["id"] for item in expected_delta["changed_edges"]]
            changed_scenarios = [
                item["scenario_id"] for item in expected_delta["scenario_rank_changes"]
            ]
            new_unknowns = [item["id"] for item in expected_delta["new_unknowns"]]
            resolved_unknowns = [item["id"] for item in expected_delta["resolved_unknowns"]]
            support_map = expected_delta["supporting_evidence_map"]
            citations = {
                node_id: list(evidence_ids)
                for node_id, evidence_ids in support_map.items()
            }
            target_ids = (
                changed_states
                + changed_events
                + changed_edges
                + new_unknowns
                + resolved_unknowns
            )
            if target_ids:
                fallback_evidence_id = next(
                    (
                        evidence_id
                        for evidence_ids in citations.values()
                        for evidence_id in evidence_ids
                    ),
                    None,
                )
                if fallback_evidence_id is None:
                    fallback_evidence_id = next(
                        iter(scoring_manifest["citation_obligation_map"].values()),
                        None,
                    )
                assert fallback_evidence_id is not None
                for item_id in target_ids:
                    citations.setdefault(item_id, [fallback_evidence_id])
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
                        "category_map": {
                            unknown_id: ("resolved" if unknown_id in resolved_unknowns else "new")
                            for unknown_id in (resolved_unknowns + new_unknowns)
                        },
                        "summary": "tracked unknowns",
                    },
                    "citations": citations,
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
                    self._fn(llm=model, **row)
                    runs.append(
                        FakeRun(
                            case_id=row["case_id"],
                            llm_name=getattr(model, "name", str(model)),
                            passed=True,
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

    monkeypatch.setitem(sys.modules, "kaggle_benchmarks", FakeKBench())

    namespace = {"__name__": "__main__"}
    for cell in notebook["cells"]:
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        else:
            source = str(source)
        exec(source, namespace)

    export_root = Path(tempfile.gettempdir()) / "cuc_v5a_candidate_export"
    assert (export_root / "results_export.json").is_file()
    payload = json.loads((export_root / "results_export.json").read_text(encoding="utf-8"))
    expected_case_count = len(
        json.loads(
            (
                repo_root / "benchmark" / "cuc_v5_64_params.json"
            ).read_text(encoding="utf-8")
        )
    )
    assert payload["task_name"] == "cuc_metacognition_v5a_candidate"
    assert payload["params_json_relative_path"] == "benchmark/cuc_v5_64_params.json"
    assert payload["case_count"] == expected_case_count
    assert payload["run_count"] == expected_case_count

from core.reasoning.casefile import build_casefile, casefile_artifact_sha256
from core.reasoning.causal import compute_causal_graph
from core.reasoning.causal_narrative_v2 import render_causal_narrative_v2
from core.reasoning.claim_graph import (
    build_claim_graph,
    claim_fingerprint,
    find_duplicates_and_contradictions,
    normalize_text,
)
from core.reasoning.closure import build_adjacency, compute_closure
from core.reasoning.constraint_diff import compute_constraint_diff
from core.reasoning.constraint_diff_narrative_v2 import (
    render_constraint_diff_narrative_v2,
)
from core.reasoning.constraint_narrative_v2 import render_constraint_narrative_v2
from core.reasoning.constraints import compute_constraints
from core.reasoning.counterfactual import (
    apply_counterfactual,
    canonicalize_counterfactual_task,
    canonicalize_counterfactual_task_file,
    compute_counterfactual_task_id,
    compute_task_id,
    load_base_output,
    load_counterfactual_task,
    run_counterfactual_task,
)
from core.reasoning.counterfactual_narrative_v2 import (
    render_counterfactual_narrative_v2,
)
from core.reasoning.critical_path import compute_critical_path
from core.reasoning.critical_path_narrative_v2 import (
    render_critical_path_narrative_v2,
)
from core.reasoning.narrative import render_narrative
from core.reasoning.narrative_v2 import render_narrative_v2
from core.reasoning.repair_hints import compute_repair_hints
from core.reasoning.repair_hints_narrative_v2 import (
    render_repair_hints_narrative_v2,
)
from core.reasoning.repair_loop import run_repair_loop
from core.reasoning.repair_narrative_v2 import render_repair_narrative_v2
from core.reasoning.repair_plan import compute_repair_plan
from core.reasoning.run_graph import run_graph_reasoning
from core.reasoning.support_tree import build_support_tree
from core.reasoning.verifier import load_ruleset, verify_claim
from core.reasoning.world_narrative import render_world_narrative
from core.reasoning.world_narrative_v2 import render_world_narrative_v2
from core.reasoning.world_patch import (
    apply_world_patch,
    build_patched_output,
    load_world_patch,
    run_world_patch,
)
from core.reasoning.world_patch_narrative_v2 import render_world_patch_narrative_v2

__all__ = [
    "build_claim_graph",
    "build_casefile",
    "compute_causal_graph",
    "compute_critical_path",
    "compute_constraint_diff",
    "compute_constraints",
    "compute_repair_hints",
    "compute_repair_plan",
    "compute_task_id",
    "build_adjacency",
    "build_support_tree",
    "claim_fingerprint",
    "compute_closure",
    "find_duplicates_and_contradictions",
    "normalize_text",
    "apply_counterfactual",
    "canonicalize_counterfactual_task_file",
    "canonicalize_counterfactual_task",
    "compute_counterfactual_task_id",
    "load_base_output",
    "load_counterfactual_task",
    "render_causal_narrative_v2",
    "render_critical_path_narrative_v2",
    "render_constraint_diff_narrative_v2",
    "render_constraint_narrative_v2",
    "render_counterfactual_narrative_v2",
    "render_repair_hints_narrative_v2",
    "render_repair_narrative_v2",
    "render_narrative",
    "render_narrative_v2",
    "run_counterfactual_task",
    "run_repair_loop",
    "render_world_narrative",
    "render_world_narrative_v2",
    "casefile_artifact_sha256",
    "load_world_patch",
    "apply_world_patch",
    "build_patched_output",
    "run_world_patch",
    "render_world_patch_narrative_v2",
    "run_graph_reasoning",
    "load_ruleset",
    "verify_claim",
]

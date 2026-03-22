"""Score CUC benchmark Run 2 responses against fixture diffs."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    from benchmark.run_evaluation import CASE_METADATA
except ModuleNotFoundError:
    from run_evaluation import CASE_METADATA

LOGGER = logging.getLogger(__name__)

Q1_HEADER = "Q1"
Q2_HEADER = "Q2"
Q3_HEADER = "Q3"
SECTION_LABELS = {
    Q1_HEADER: "DETECTION",
    Q2_HEADER: "SELF-CORRECTION",
    Q3_HEADER: "UNKNOWN TRACKING",
}
SECTION_HEADER_PATTERN = re.compile(
    r"(?im)^[ \t]*(?:##\s*)?(?P<axis>Q[123])(?:\s*[:\-—–]\s*|\s+)"
    r"(?P<label>DETECTION|SELF-CORRECTION|UNKNOWN TRACKING):?\s*$"
)
ID_PATTERN = re.compile(
    r"\b(?:scen_[A-Za-z0-9]+|inv_\d+|state_\d+|edge_\d+|unk_\d+)\b"
)
Q2_REVISION_MARKERS = (
    "invalidated",
    "weakened",
    "wrong",
    "revise",
    "revised",
    "no longer",
    "must be revised",
    "must revise",
    "invalid",
)
SCORE_COLUMNS = (
    "case_id",
    "domain",
    "perturbation_type",
    "model_slug",
    "q1_score",
    "q2_score",
    "q3_score",
    "total_score",
    "hallucination_count",
    "over_revision_count",
    "run2_response_file",
    "scored_at_utc",
)
SUMMARY_COLUMNS = (
    "model_slug",
    "mean_q1",
    "mean_q2",
    "mean_q3",
    "mean_total",
    "total_hallucinations",
    "total_over_revisions",
    "note",
)
DEFAULT_RUNS_DIR = Path("benchmark") / "runs"
DEFAULT_FIXTURES_DIR = Path("benchmark") / "fixtures"
DEFAULT_OUTPUT_PATH = Path("benchmark") / "SCORES.csv"
PLACEHOLDER_MARKER = "# PLACEHOLDER"


def configure_logging(verbose: bool) -> None:
    """Configure module logging."""

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp with microsecond precision."""

    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR), type=Path)
    parser.add_argument("--fixtures-dir", default=str(DEFAULT_FIXTURES_DIR), type=Path)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), type=Path)
    parser.add_argument("--cases", nargs="*", default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def discover_case_ids(fixtures_dir: Path) -> list[str]:
    """Return fixture case identifiers in deterministic order."""

    if not fixtures_dir.exists():
        return []
    return [
        entry.name
        for entry in sorted(fixtures_dir.iterdir(), key=lambda item: item.name)
        if entry.is_dir()
    ]


def normalize_text(value: str) -> str:
    """Normalize text for deterministic fuzzy matching."""

    return " ".join(value.lower().split())


def similarity(left: str, right: str) -> float:
    """Return a fuzzy similarity ratio."""

    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def best_match_index(
    candidate: str,
    truth_items: list[str],
    used: set[int],
    *,
    threshold: float = 0.75,
) -> int | None:
    """Return the best unused truth item index above threshold."""

    best_index: int | None = None
    best_ratio = threshold
    for index, truth_item in enumerate(truth_items):
        if index in used:
            continue
        ratio = similarity(candidate, truth_item)
        if ratio >= best_ratio:
            best_ratio = ratio
            best_index = index
    return best_index


def flatten_truth_item(item: Any) -> str:
    """Convert a ground-truth object into a comparable description string."""

    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        preferred_keys = (
            "description",
            "change",
            "state",
            "edge",
            "condition",
            "scenario",
            "original_conclusion",
            "revision",
            "revised_conclusion",
            "unknown",
            "name",
        )
        parts = [str(item[key]) for key in preferred_keys if key in item]
        if parts:
            return " | ".join(parts)
        ordered_keys = sorted(item)
        return " | ".join(f"{key}={item[key]}" for key in ordered_keys)
    return str(item)


def parse_sections(
    response_text: str,
    *,
    case_id: str | None = None,
    model_slug: str | None = None,
) -> dict[str, str]:
    """Extract Q1/Q2/Q3 sections from a run2 response."""

    sections = {Q1_HEADER: "", Q2_HEADER: "", Q3_HEADER: ""}
    matches = []
    for match in SECTION_HEADER_PATTERN.finditer(response_text):
        axis = match.group("axis").upper()
        label = match.group("label").upper()
        if SECTION_LABELS.get(axis) == label:
            matches.append((axis, match))
    if not matches:
        LOGGER.warning(
            "No Q1/Q2/Q3 section headers found for case=%s model=%s",
            case_id or "<unknown>",
            model_slug or "<unknown>",
        )
        return sections
    for index, (axis, match) in enumerate(matches):
        body_end = matches[index + 1][1].start() if index + 1 < len(matches) else None
        sections[axis] = response_text[match.end() : body_end].strip()
    return sections


def split_claims(section_text: str) -> list[str]:
    """Split a response section into deterministic claim units."""

    lines = [line.strip(" -*\t") for line in section_text.splitlines()]
    claims = [line for line in lines if line]
    if claims:
        return claims
    compact = section_text.strip()
    if not compact:
        return []
    return [item.strip() for item in compact.split(".") if item.strip()]


def score_detected_changes(
    claims: list[str],
    truth_items: list[str],
    penalty: int,
) -> tuple[int, int]:
    """Score Q1 or Q3 style change detection."""

    used_truth_indices: set[int] = set()
    score = 0
    hallucinations = 0
    for claim in claims:
        match_index = _best_match_index_by_id_or_similarity(
            claim,
            truth_items,
            used_truth_indices,
        )
        if match_index is None:
            hallucinations += 1
            score -= penalty
            continue
        used_truth_indices.add(match_index)
        score += 3
    return score, hallucinations


def _extract_ids(text: str) -> set[str]:
    """Extract stable scenario or invalidation identifiers from a claim."""

    return {match.group(0).lower() for match in ID_PATTERN.finditer(text)}


def _best_match_index_by_id_or_similarity(
    claim: str,
    truth_items: list[str],
    used: set[int],
) -> int | None:
    """Prefer exact ID overlap before falling back to fuzzy matching."""

    claim_ids = _extract_ids(claim)
    if claim_ids:
        for index, truth_item in enumerate(truth_items):
            if index in used:
                continue
            if claim_ids & _extract_ids(truth_item):
                return index
    return best_match_index(claim, truth_items, used)


def _is_connected_to_fired_invalidations(
    claim: str,
    fired_invalidations: list[str],
) -> bool:
    """Return True when a claim overlaps materially with a fired invalidation."""

    claim_ids = _extract_ids(claim)
    if claim_ids:
        fired_ids = {
            item
            for invalidation in fired_invalidations
            for item in _extract_ids(invalidation)
        }
        if claim_ids & fired_ids:
            return True
    return any(
        similarity(claim, invalidation) >= 0.65
        for invalidation in fired_invalidations
    )


def _is_over_revision_claim(
    claim: str,
    required_revisions: list[str],
    fired_invalidations: list[str],
) -> bool:
    """Return True when a claim asserts an unsupported specific revision."""

    normalized_claim = normalize_text(claim)
    if not any(marker in normalized_claim for marker in Q2_REVISION_MARKERS):
        return False
    if any(similarity(claim, revision) >= 0.65 for revision in required_revisions):
        return False
    if _is_connected_to_fired_invalidations(claim, fired_invalidations):
        return False
    return bool(_extract_ids(claim))


def score_revisions(
    claims: list[str],
    truth_items: list[str],
    fired_invalidations: list[str],
) -> tuple[int, int]:
    """Score Q2 self-correction against free-form required revision strings."""

    used_truth_indices: set[int] = set()
    score = 0
    over_revisions = 0
    for claim in claims:
        match_index = best_match_index(
            claim,
            truth_items,
            used_truth_indices,
            threshold=0.65,
        )
        if match_index is not None:
            used_truth_indices.add(match_index)
            score += 3
            continue
        if _is_over_revision_claim(claim, truth_items, fired_invalidations):
            over_revisions += 1
            score -= 3
    return score, over_revisions


def clamp_score(value: int, maximum: int) -> int:
    """Clamp a score into the specified benchmark range."""

    return max(0, min(maximum, value))


def load_json(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON document."""

    return json.loads(path.read_text(encoding="utf-8"))


def list_model_run2_files(case_runs_dir: Path) -> list[Path]:
    """Return model Run 2 response files in deterministic order."""

    if not case_runs_dir.exists():
        return []
    return sorted(
        [
            path
            for path in case_runs_dir.iterdir()
            if path.is_file() and path.name.endswith("_run2.txt")
        ],
        key=lambda item: item.name,
    )


def score_case_response(
    case_id: str,
    diff_payload: dict[str, Any],
    model_slug: str,
    response_text: str,
    response_file: Path,
) -> dict[str, Any]:
    """Score a single Run 2 response and return the CSV row payload."""

    sections = parse_sections(
        response_text,
        case_id=case_id,
        model_slug=model_slug,
    )
    q1_claims = split_claims(sections[Q1_HEADER])
    q2_claims = split_claims(sections[Q2_HEADER])
    q3_claims = split_claims(sections[Q3_HEADER])

    q1_truth = [
        flatten_truth_item(item)
        for item in (
            list(diff_payload.get("changed_states", []))
            + list(diff_payload.get("changed_edges", []))
            + list(diff_payload.get("fired_invalidations", []))
        )
    ]
    q2_truth = [
        flatten_truth_item(item)
        for item in diff_payload.get("invalidated_scenarios", [])
    ]
    q3_truth = [
        flatten_truth_item(item)
        for item in (
            list(diff_payload.get("resolved_unknowns", []))
            + list(diff_payload.get("unchanged_unknowns", []))
            + list(diff_payload.get("new_unknowns", []))
        )
    ]
    fired_invalidations = [
        flatten_truth_item(item) for item in diff_payload.get("fired_invalidations", [])
    ]

    q1_raw, q1_hallucinations = score_detected_changes(q1_claims, q1_truth, penalty=5)
    # Keep Kaggle-scoring criteria aligned: Q2 ground truth is free-form revision text,
    # not original/revised claim pairs, and over-revision penalties only apply to
    # unsupported specific revision claims not connected to fired invalidations.
    q2_raw, over_revisions = score_revisions(
        q2_claims,
        q2_truth,
        fired_invalidations,
    )
    q3_raw, q3_hallucinations = score_detected_changes(q3_claims, q3_truth, penalty=5)

    q1_score = clamp_score(q1_raw, 33)
    q2_score = clamp_score(q2_raw, 33)
    q3_score = clamp_score(q3_raw, 34)
    total_score = clamp_score(q1_score + q2_score + q3_score, 100)

    return {
        "case_id": case_id,
        "domain": str(
            CASE_METADATA.get(case_id, {}).get(
                "domain",
                diff_payload.get("domain", case_id),
            )
        ),
        "perturbation_type": str(
            CASE_METADATA.get(case_id, {}).get(
                "perturbation_type",
                diff_payload.get("perturbation_type", ""),
            )
        ),
        "model_slug": model_slug,
        "q1_score": q1_score,
        "q2_score": q2_score,
        "q3_score": q3_score,
        "total_score": total_score,
        "hallucination_count": q1_hallucinations + q3_hallucinations,
        "over_revision_count": over_revisions,
        "run2_response_file": response_file.as_posix(),
        "scored_at_utc": utc_timestamp(),
    }


def build_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate summary rows by model."""

    models = sorted({str(row["model_slug"]) for row in rows})
    summary_rows: list[dict[str, Any]] = []
    for model_slug in models:
        model_rows = [row for row in rows if row["model_slug"] == model_slug]
        count = len(model_rows)
        summary_rows.append(
            {
                "model_slug": model_slug,
                "mean_q1": mean_score(model_rows, "q1_score", count),
                "mean_q2": mean_score(model_rows, "q2_score", count),
                "mean_q3": mean_score(model_rows, "q3_score", count),
                "mean_total": mean_score(model_rows, "total_score", count),
                "total_hallucinations": sum(
                    int(row["hallucination_count"]) for row in model_rows
                ),
                "total_over_revisions": sum(
                    int(row["over_revision_count"]) for row in model_rows
                ),
                "note": "",
            }
        )
    summary_rows.append(human_baseline_row())
    return summary_rows


def mean_score(rows: list[dict[str, Any]], key: str, count: int) -> str:
    """Return a fixed-precision mean score string for a column."""

    return f"{sum(int(row[key]) for row in rows) / count:.2f}"


def human_baseline_row() -> dict[str, Any]:
    """Return the fixed human baseline summary row."""

    return {
        "model_slug": "Human Baseline",
        "mean_q1": "20.95",
        "mean_q2": "20.95",
        "mean_q3": "21.58",
        "mean_total": "63.475",
        "total_hallucinations": 0,
        "total_over_revisions": 0,
        "note": "estimated from per-perturbation-type overall scores",
    }


def write_scores(rows: list[dict[str, Any]], output_path: Path) -> None:
    """Write detailed and summary score CSV files."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SCORE_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary_path = output_path.with_name("SCORES_SUMMARY.csv")
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SUMMARY_COLUMNS))
        writer.writeheader()
        for row in build_summary_rows(rows):
            writer.writerow(row)


def resolve_cases(fixtures_dir: Path, requested_cases: list[str] | None) -> list[str]:
    """Resolve requested case identifiers."""

    available = discover_case_ids(fixtures_dir)
    if requested_cases:
        selected = sorted(requested_cases)
        missing = [case_id for case_id in selected if case_id not in available]
        if missing:
            raise SystemExit(f"Unknown case ids: {', '.join(missing)}")
        return selected
    return available


def is_placeholder_diff(diff_path: Path) -> bool:
    """Return True if the diff file is still a placeholder."""

    return PLACEHOLDER_MARKER in diff_path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the scoring CLI."""

    args = parse_args(argv)
    configure_logging(args.verbose)
    rows: list[dict[str, Any]] = []
    for case_id in resolve_cases(args.fixtures_dir, args.cases):
        diff_path = args.fixtures_dir / case_id / "diff.json"
        if is_placeholder_diff(diff_path):
            LOGGER.info("Skipping placeholder fixture %s", case_id)
            continue
        diff_payload = load_json(diff_path)
        for response_file in list_model_run2_files(args.runs_dir / case_id):
            model_slug = response_file.name[: -len("_run2.txt")]
            response_text = response_file.read_text(encoding="utf-8")
            rows.append(
                score_case_response(
                    case_id=case_id,
                    diff_payload=diff_payload,
                    model_slug=model_slug,
                    response_text=response_text,
                    response_file=response_file,
                )
            )
    rows = sorted(rows, key=lambda row: (str(row["case_id"]), str(row["model_slug"])))
    write_scores(rows, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

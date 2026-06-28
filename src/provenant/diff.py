"""Silent-regression diff between two Provenant decision records.

Compares the prior and current sealed record for the *same subject* and
reports whether the decision silently changed across a model/prompt change —
the question an examiner (or a careful risk lead) asks after every deploy:
"did our AI quietly change its mind, and on which cases?"
"""

from __future__ import annotations


def _reason_code_set(record: dict) -> set[str]:
    reasons = record.get("reason_codes") or []
    return {str(r.get("code")) for r in reasons if r.get("code")}


def diff_records(prior: dict, current: dict) -> dict:
    """Return a structured diff classifying decision change between two records."""
    prior_decision = prior.get("decision") or {}
    current_decision = current.get("decision") or {}

    prior_outcome = str(prior_decision.get("outcome", "")).upper()
    current_outcome = str(current_decision.get("outcome", "")).upper()
    outcome_changed = prior_outcome != current_outcome

    prior_score = prior_decision.get("score")
    current_score = current_decision.get("score")
    score_delta = None
    if isinstance(prior_score, (int, float)) and isinstance(
        current_score, (int, float)
    ):
        score_delta = round(float(current_score) - float(prior_score), 6)

    prior_reasons = _reason_code_set(prior)
    current_reasons = _reason_code_set(current)
    added_reasons = sorted(current_reasons - prior_reasons)
    removed_reasons = sorted(prior_reasons - current_reasons)

    prior_model = prior.get("model") or {}
    current_model = current.get("model") or {}
    model_changed = prior_model != current_model

    # A regression is an outcome flip between records for the same subject.
    regression = outcome_changed and prior.get("subject_ref") == current.get(
        "subject_ref"
    )
    if regression:
        severity = "high"
    elif added_reasons or removed_reasons:
        severity = "medium"
    elif score_delta:
        severity = "low"
    else:
        severity = "none"

    return {
        "subject_ref": current.get("subject_ref"),
        "prior_record_id": prior.get("record_id"),
        "current_record_id": current.get("record_id"),
        "model_changed": model_changed,
        "prior_model": prior_model,
        "current_model": current_model,
        "outcome_changed": outcome_changed,
        "prior_outcome": prior_outcome,
        "current_outcome": current_outcome,
        "score_delta": score_delta,
        "reason_codes_added": added_reasons,
        "reason_codes_removed": removed_reasons,
        "regression": regression,
        "severity": severity,
    }

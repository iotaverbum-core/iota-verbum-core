"""Provenant — verifiable, tamper-evident records for AI-assisted decisions.

A thin product layer over the iota-verbum deterministic engine that seals each
decision into a reproducible, independently verifiable record, detects silent
regressions across model changes, and exports examiner-ready evidence packs.
"""

from provenant.diff import diff_records
from provenant.export import build_examiner_pack, write_examiner_pack
from provenant.record import (
    evaluate_compliance,
    seal_decision,
    verify_record,
    write_record,
)

__all__ = [
    "seal_decision",
    "write_record",
    "verify_record",
    "evaluate_compliance",
    "diff_records",
    "build_examiner_pack",
    "write_examiner_pack",
]

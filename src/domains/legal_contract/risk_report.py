from __future__ import annotations

from collections import OrderedDict


def build_risk_report(extracted: dict, analysis: dict) -> OrderedDict:
    report = OrderedDict()
    report["executive_summary"] = analysis["executive_summary"]
    report["top_risks"] = analysis["risk_registry"][:5]
    report["conditional_trigger_count"] = len(extracted.get("conditional_triggers", []))
    report["rights_count"] = len(extracted.get("rights", []))
    report["prohibition_count"] = len(extracted.get("prohibitions", []))
    return report

"""Customer-facing audit report for a sealed decision portfolio.

Turns the machine artifacts (sealed records, verification results, diffs,
compliance warnings) into a plain-language report a risk/compliance lead — not
a developer — can read and hand to an examiner. Renders both Markdown and a
self-contained static HTML page (no external assets), plus a structured model.

All inputs are deterministic, so the rendered report bytes are stable for a
given portfolio.
"""

from __future__ import annotations

import html

REPORT_TITLE = "Provenant Audit-Ready Report"

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "none": 3}

_GAP_ACTION = {
    "ADVERSE_ACTION_NO_REASONS": (
        "Add ECOA / Reg B reason codes to this denial before issuing the "
        "adverse-action notice."
    ),
    "ADVERSE_FLAG_OUTCOME_MISMATCH": (
        "Reconcile the adverse-action flag with the recorded outcome."
    ),
    "REASON_EVIDENCE_MISSING": (
        "Attach the cited evidence to the record or correct the reason code."
    ),
}


def build_report_model(
    *,
    tenant_id: str,
    generated_utc: str,
    models_compared: list[str],
    records: list[dict],
    diffs: list[dict],
    verified_count: int,
) -> dict:
    """Assemble the structured report model from sealed-portfolio facts."""
    compliance_gaps = []
    for rec in records:
        for warning in rec.get("compliance_warnings", []):
            compliance_gaps.append(
                {
                    "record_id": rec["record_id"],
                    "subject_ref": rec["subject_ref"],
                    "outcome": rec["outcome"],
                    "code": warning["code"],
                    "severity": warning.get("severity", "medium"),
                    "regulation": warning.get("regulation", ""),
                    "message": warning.get("message", ""),
                    "recommended_action": _GAP_ACTION.get(
                        warning["code"], "Review this record before the audit."
                    ),
                }
            )
    compliance_gaps.sort(key=lambda g: (_SEVERITY_ORDER.get(g["severity"], 9), g["record_id"]))

    silent_regressions = []
    score_drift = []
    for d in diffs:
        if d.get("regression"):
            silent_regressions.append(
                {
                    "subject_ref": d["subject_ref"],
                    "prior_outcome": d["prior_outcome"],
                    "current_outcome": d["current_outcome"],
                    "severity": d["severity"],
                    "score_delta": d["score_delta"],
                    "recommended_action": (
                        "Review this flipped decision before promoting the new "
                        "model; confirm the change is intended and documented."
                    ),
                }
            )
        elif d.get("score_delta"):
            score_drift.append(
                {"subject_ref": d["subject_ref"], "score_delta": d["score_delta"]}
            )
    silent_regressions.sort(key=lambda r: r["subject_ref"])
    score_drift.sort(key=lambda r: r["subject_ref"])

    record_count = len(records)
    return {
        "title": REPORT_TITLE,
        "tenant_id": tenant_id,
        "generated_utc": generated_utc,
        "models_compared": models_compared,
        "headline": {
            "records_sealed": record_count,
            "records_verified": verified_count,
            "all_verified": verified_count == record_count,
            "compliance_gaps": len(compliance_gaps),
            "silent_regressions": len(silent_regressions),
        },
        "compliance_gaps": compliance_gaps,
        "silent_regressions": silent_regressions,
        "score_drift": score_drift,
        "evidence": [
            {
                "record_id": r["record_id"],
                "subject_ref": r["subject_ref"],
                "outcome": r["outcome"],
                "record_sha256": r["record_sha256"],
                "verified": r["verified"],
            }
            for r in records
        ],
        "what_this_proves": [
            "Every decision above is sealed and can be re-verified independently "
            "by an auditor — no need to trust the vendor or the lender.",
            "Any later change to a decision record breaks its hash and is "
            "detected by verification.",
            "Decisions that silently flipped between model versions are surfaced "
            "before the new model is promoted.",
        ],
    }


def render_markdown(model: dict) -> str:
    h = model["headline"]
    lines: list[str] = []
    lines.append(f"# {model['title']}")
    lines.append("")
    lines.append(f"- **Tenant:** {model['tenant_id']}")
    lines.append(f"- **Generated:** {model['generated_utc']}")
    lines.append(f"- **Models compared:** {' → '.join(model['models_compared'])}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    verified_phrase = (
        "all independently verifiable"
        if h["all_verified"]
        else "verification FAILED for some records"
    )
    lines.append(
        f"**{h['records_sealed']} decisions sealed** ({verified_phrase}). "
        f"**{h['compliance_gaps']} compliance gap(s)** and "
        f"**{h['silent_regressions']} silent regression(s)** detected."
    )
    lines.append("")

    lines.append("## 1. Chain of custody")
    lines.append("")
    lines.append(
        f"{h['records_verified']} of {h['records_sealed']} decision records "
        "passed independent tamper verification. Each record carries a SHA-256 "
        "seal an examiner can re-check with `provenant verify`."
    )
    lines.append("")

    lines.append("## 2. Compliance gaps")
    lines.append("")
    if model["compliance_gaps"]:
        lines.append("| Severity | Record | Outcome | Issue | Regulation | Recommended action |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for g in model["compliance_gaps"]:
            lines.append(
                f"| {g['severity']} | {g['record_id']} | {g['outcome']} | "
                f"{g['code']} | {g['regulation']} | {g['recommended_action']} |"
            )
    else:
        lines.append("No compliance gaps detected.")
    lines.append("")

    lines.append("## 3. Silent regressions (model change)")
    lines.append("")
    if model["silent_regressions"]:
        lines.append("| Severity | Subject | Prior | Current | Δ score | Recommended action |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for r in model["silent_regressions"]:
            lines.append(
                f"| {r['severity']} | {r['subject_ref']} | {r['prior_outcome']} | "
                f"{r['current_outcome']} | {r['score_delta']} | "
                f"{r['recommended_action']} |"
            )
    else:
        lines.append("No silently flipped decisions detected.")
    lines.append("")

    lines.append("## 4. Evidence (per-record verification)")
    lines.append("")
    lines.append("| Record | Subject | Outcome | Verified | record_sha256 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for e in model["evidence"]:
        verified = "yes" if e["verified"] else "NO"
        lines.append(
            f"| {e['record_id']} | {e['subject_ref']} | {e['outcome']} | "
            f"{verified} | `{e['record_sha256'][:16]}…` |"
        )
    lines.append("")

    lines.append("## What this proves")
    lines.append("")
    for item in model["what_this_proves"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_html(model: dict) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value))

    h = model["headline"]
    gap_rows = "".join(
        "<tr><td>{sev}</td><td>{rid}</td><td>{out}</td><td>{code}</td>"
        "<td>{reg}</td><td>{act}</td></tr>".format(
            sev=esc(g["severity"]),
            rid=esc(g["record_id"]),
            out=esc(g["outcome"]),
            code=esc(g["code"]),
            reg=esc(g["regulation"]),
            act=esc(g["recommended_action"]),
        )
        for g in model["compliance_gaps"]
    ) or "<tr><td colspan='6'>No compliance gaps detected.</td></tr>"

    reg_rows = "".join(
        "<tr><td>{sev}</td><td>{sub}</td><td>{p}</td><td>{c}</td>"
        "<td>{d}</td><td>{act}</td></tr>".format(
            sev=esc(r["severity"]),
            sub=esc(r["subject_ref"]),
            p=esc(r["prior_outcome"]),
            c=esc(r["current_outcome"]),
            d=esc(r["score_delta"]),
            act=esc(r["recommended_action"]),
        )
        for r in model["silent_regressions"]
    ) or "<tr><td colspan='6'>No silently flipped decisions detected.</td></tr>"

    ev_rows = "".join(
        "<tr><td>{rid}</td><td>{sub}</td><td>{out}</td><td>{v}</td>"
        "<td><code>{sha}…</code></td></tr>".format(
            rid=esc(e["record_id"]),
            sub=esc(e["subject_ref"]),
            out=esc(e["outcome"]),
            v="yes" if e["verified"] else "NO",
            sha=esc(e["record_sha256"][:16]),
        )
        for e in model["evidence"]
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{esc(model['title'])}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
   max-width:900px;margin:2rem auto;padding:0 1rem;color:#111;line-height:1.5}}
 h1{{margin-bottom:.2rem}} .meta{{color:#555;font-size:.9rem}}
 .cards{{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}}
 .card{{border:1px solid #e2e2e2;border-radius:8px;padding:.8rem 1rem;min-width:140px}}
 .card b{{display:block;font-size:1.6rem}}
 .bad{{color:#b00020}} .ok{{color:#0a7d32}}
 table{{border-collapse:collapse;width:100%;margin:.5rem 0 1.5rem}}
 th,td{{border:1px solid #e2e2e2;padding:.4rem .6rem;text-align:left;font-size:.92rem}}
 th{{background:#fafafa}} code{{font-size:.85rem}}
</style></head><body>
<h1>{esc(model['title'])}</h1>
<div class="meta">Tenant: {esc(model['tenant_id'])} &middot;
 Generated: {esc(model['generated_utc'])} &middot;
 Models: {esc(' → '.join(model['models_compared']))}</div>
<div class="cards">
 <div class="card"><b>{h['records_sealed']}</b>decisions sealed</div>
 <div class="card"><b class="{'ok' if h['all_verified'] else 'bad'}">{h['records_verified']}</b>verified</div>
 <div class="card"><b class="{'bad' if h['compliance_gaps'] else 'ok'}">{h['compliance_gaps']}</b>compliance gaps</div>
 <div class="card"><b class="{'bad' if h['silent_regressions'] else 'ok'}">{h['silent_regressions']}</b>silent regressions</div>
</div>
<h2>Compliance gaps</h2>
<table><tr><th>Severity</th><th>Record</th><th>Outcome</th><th>Issue</th>
 <th>Regulation</th><th>Recommended action</th></tr>{gap_rows}</table>
<h2>Silent regressions (model change)</h2>
<table><tr><th>Severity</th><th>Subject</th><th>Prior</th><th>Current</th>
 <th>&Delta; score</th><th>Recommended action</th></tr>{reg_rows}</table>
<h2>Evidence (per-record verification)</h2>
<table><tr><th>Record</th><th>Subject</th><th>Outcome</th><th>Verified</th>
 <th>record_sha256</th></tr>{ev_rows}</table>
<p class="meta">Every record above is independently re-verifiable with
 <code>provenant verify</code>; any change to a sealed record breaks its hash.</p>
</body></html>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from core.determinism.canonical_json import dumps_canonical
from core.determinism.finalize import finalize
from core.determinism.hashing import sha256_bytes, sha256_text
from core.determinism.ledger import write_run
from core.reasoning.casefile import build_casefile, casefile_artifact_sha256
from core.reasoning.causal import compute_causal_graph
from core.reasoning.causal_narrative_v2 import render_causal_narrative_v2
from core.reasoning.constraint_narrative_v2 import render_constraint_narrative_v2
from core.reasoning.constraints import compute_constraints
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
from core.reasoning.run_graph import build_graph_reasoning_output
from core.reasoning.verifier import verify_claim
from core.reasoning.world_diff import compute_world_diff, load_output_input
from core.reasoning.world_diff_narrative import render_world_diff_narrative
from core.reasoning.world_narrative import render_world_narrative
from core.reasoning.world_narrative_v2 import render_world_narrative_v2
from proposal.bundle_from_pack import build_evidence_bundle_from_pack
from proposal.claim_propose import dumps_claim_graph, propose_claim_graph
from proposal.evidence_pack import build_evidence_pack
from proposal.text_normalize import normalize_text
from proposal.world_enrich import apply_world_enrichment, load_world_enrichment
from proposal.world_propose import (
    dumps_world_model,
    propose_world_model_from_artifacts,
)


def _write_atomic(path: Path, data: bytes) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_bytes(data)
    os.replace(temp_path, path)


def _write_or_verify(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"existing demo file mismatch: {path}")
        return
    _write_atomic(path, data)


def _dir_matches_planned(run_dir: Path, planned_files: dict[str, bytes]) -> bool:
    for relpath, data in planned_files.items():
        path = run_dir / relpath
        if path.exists() and path.read_bytes() != data:
            return False
    return True


def _resolve_run_dir(base_run_dir: Path, planned_files: dict[str, bytes]) -> Path:
    if _dir_matches_planned(base_run_dir, planned_files):
        return base_run_dir

    conflict_index = 1
    while True:
        candidate = base_run_dir.parent / (
            f"{base_run_dir.name}__conflict_{conflict_index}"
        )
        if _dir_matches_planned(candidate, planned_files):
            return candidate
        conflict_index += 1


def _write_demo_outputs(run_dir: Path, planned_files: dict[str, bytes]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    for relpath, data in sorted(planned_files.items()):
        _write_or_verify(run_dir / relpath, data)


def _write_with_conflict_suffix(path: Path, data: bytes) -> Path:
    if not path.exists():
        _write_or_verify(path, data)
        return path
    if path.read_bytes() == data:
        return path
    conflict_index = 1
    while True:
        candidate = path.with_name(
            f"{path.stem}__conflict_{conflict_index}{path.suffix}"
        )
        if not candidate.exists():
            _write_or_verify(candidate, data)
            return candidate
        if candidate.read_bytes() == data:
            return candidate
        conflict_index += 1


def _compute_run_id(
    *,
    folder: str,
    query: str,
    prompt: str,
    max_chunks: int,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    world: bool,
    enrich: str,
) -> str:
    run_key = {
        "folder": Path(folder).resolve().as_posix(),
        "query": query,
        "prompt": prompt,
        "max_chunks": max_chunks,
        "created_utc": created_utc,
        "core_version": core_version,
        "ruleset_id": ruleset_id,
        "world": world,
        "enrich": Path(enrich).resolve().as_posix() if enrich else "",
    }
    return sha256_bytes(dumps_canonical(run_key))


def _select_target_claim_id(claim_graph: dict, query: str) -> str:
    claims = claim_graph["claims"]
    if not claims:
        raise ValueError("claim graph contains no claims")

    terms = [term for term in normalize_text(query).lower().split(" ") if term]
    if not terms:
        return claims[0]["claim_id"]

    scored_claims = []
    for claim in claims:
        subject_text = normalize_text(claim["subject"]).lower()
        object_text = normalize_text(claim["object"]).lower()
        relpath_text = normalize_text(
            str(claim.get("qualifiers", {}).get("relpath", ""))
        ).lower()
        score = 0
        for term in terms:
            if term in subject_text:
                score += 3
            if term in object_text:
                score += 2
            if term in relpath_text:
                score += 1
        scored_claims.append((score, claim["claim_id"]))

    scored_claims.sort(key=lambda item: (-item[0], item[1]))
    if scored_claims[0][0] == 0:
        return claims[0]["claim_id"]
    return scored_claims[0][1]


def _manifest_sha256() -> str:
    completed = subprocess.run(
        [sys.executable, "scripts/manifest_hash.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _format_report(narrative_text: str) -> str:
    return narrative_text.replace("\r\n", "\n").replace("\r", "\n")


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


def _world_target_claim_id(query: str) -> str:
    return "world:" + sha256_text(normalize_text(query))


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(Path.cwd().resolve()).as_posix()


def run_demo(
    *,
    folder: str,
    query: str,
    prompt: str,
    max_chunks: int,
    created_utc: str,
    core_version: str,
    ruleset_id: str,
    world: bool = False,
    verbosity: str = "brief",
    show_receipts: bool = False,
    max_lines: int = 200,
    diff_against: str = "",
    max_events: int = 30,
    enrich: str = "",
) -> dict:
    run_id = _compute_run_id(
        folder=folder,
        query=query,
        prompt=prompt,
        max_chunks=max_chunks,
        created_utc=created_utc,
        core_version=core_version,
        ruleset_id=ruleset_id,
        world=world,
        enrich=enrich,
    )
    base_run_dir = Path("outputs") / "demo" / run_id

    pack_obj, pack_bytes = build_evidence_pack(
        folder,
        root_hint=Path(folder).name,
    )

    bundle_obj, bundle_bytes, bundle_sha256 = build_evidence_bundle_from_pack(
        pack_obj,
        prompt=prompt,
        params={
            "mode": "topk",
            "query": query,
            "max_chunks": max_chunks,
        },
        created_utc=created_utc,
        core_version=core_version,
        ruleset_id=ruleset_id,
        mode="topk",
        query=query,
        max_chunks=max_chunks,
    )

    manifest_sha256 = _manifest_sha256()
    if world:
        target_claim_id = _world_target_claim_id(query)
        world_model = propose_world_model_from_artifacts(
            pack_obj,
            bundle_obj["artifacts"],
            query=query,
            max_chunks=max_chunks,
            max_events=max_events,
        )
        enrichment = None
        if enrich:
            enrichment = load_world_enrichment(enrich)
            world_model = apply_world_enrichment(world_model, enrichment)
        world_model_bytes = dumps_world_model(world_model)

        output_obj = {
            "world_model": world_model,
        }
        if enrichment is not None:
            output_obj["world_enrichment"] = enrichment
        causal_graph = compute_causal_graph(world_model)
        output_obj["causal_graph"] = causal_graph
        output_obj["causal_findings"] = causal_graph["findings"]
        critical_path = compute_critical_path(causal_graph)
        output_obj["critical_path"] = critical_path
        constraint_report = compute_constraints(world_model, causal_graph)
        output_obj["constraint_report"] = constraint_report
        repair_hints = compute_repair_hints(
            constraint_report,
            causal_graph,
            world_model,
        )
        output_obj["repair_hints"] = repair_hints
        verification_result = verify_claim(
            ruleset_id=ruleset_id,
            target_claim_id=target_claim_id,
            evidence_bundle_obj=bundle_obj,
            sealed_output_obj=output_obj,
        )
        world_narrative = render_world_narrative(
            world_model,
            verification_result=verification_result,
        )
        world_narrative_v2 = render_world_narrative_v2(
            world_model=world_model,
            verification_result=verification_result,
            mode=verbosity,
            show_receipts=show_receipts,
            max_lines=max_lines,
        )
        causal_narrative_v2 = render_causal_narrative_v2(
            causal_graph,
            verification_result=verification_result,
            max_lines=max_lines,
            verbosity=verbosity,
        )
        critical_path_narrative_v2 = render_critical_path_narrative_v2(
            critical_path,
            mode=verbosity,
            max_lines=max_lines,
        )
        constraint_narrative_v2 = render_constraint_narrative_v2(
            constraint_report,
            mode=verbosity,
            max_lines=max_lines,
        )
        repair_hints_narrative_v2 = render_repair_hints_narrative_v2(
            repair_hints,
            max_lines=max_lines,
            verbosity=verbosity,
        )
        output_obj["world_narrative"] = world_narrative
        output_obj["world_narrative_v2"] = world_narrative_v2
        output_obj["causal_narrative_v2"] = causal_narrative_v2
        output_obj["critical_path_narrative_v2"] = critical_path_narrative_v2
        output_obj["constraint_narrative_v2"] = constraint_narrative_v2
        output_obj["repair_hints_narrative_v2"] = repair_hints_narrative_v2
        output_obj["verification_result"] = verification_result
        run_dir = _resolve_run_dir(
            base_run_dir,
            {
                "evidence_bundle.json": bundle_bytes,
                "evidence_pack.json": pack_bytes,
                "world_model.json": world_model_bytes,
            },
        )
        ledger_dir_rel = (run_dir / "ledger" / bundle_sha256).as_posix()
        provisional_casefile = build_casefile(
            output_obj=output_obj,
            query=query,
            prompt=prompt,
            created_utc=created_utc,
            core_version=core_version,
            ruleset_id=ruleset_id,
            manifest_sha256=manifest_sha256,
            ledger_dir_rel=ledger_dir_rel,
            bundle_sha256=bundle_sha256,
            output_sha256="0" * 64,
            attestation_sha256="0" * 64,
        )
        output_obj["casefile"] = provisional_casefile
        sealed = finalize(
            bundle_obj,
            output_obj,
            manifest_sha256=manifest_sha256,
            core_version=core_version,
            ruleset_id=ruleset_id,
            created_utc=created_utc,
        )
        warning_line = ""
        if len(world_model["events"]) > 30:
            warning_line = (
                f"WARNING: world.events={len(world_model['events'])} exceeds 30; "
                "tighten --query or lower --max-chunks for a cleaner demo.\n"
            )

        planned_files = {
            "attestation.json": sealed["attestation_bytes"],
            "evidence_bundle.json": bundle_bytes,
            "evidence_pack.json": pack_bytes,
            "sealed_output.json": sealed["output_bytes"],
            "world_model.json": world_model_bytes,
        }
        final_casefile = build_casefile(
            output_obj=output_obj,
            query=query,
            prompt=prompt,
            created_utc=created_utc,
            core_version=core_version,
            ruleset_id=ruleset_id,
            manifest_sha256=manifest_sha256,
            ledger_dir_rel=ledger_dir_rel,
            bundle_sha256=bundle_sha256,
            output_sha256=sealed["output_sha256"],
            attestation_sha256=sealed["attestation_sha256"],
        )
        casefile_bytes = dumps_canonical(final_casefile)
        casefile_path = _write_with_conflict_suffix(
            run_dir / "casefile.json", casefile_bytes
        )
        _write_demo_outputs(run_dir, planned_files)
        ledger_dir = write_run(ledger_root=str(run_dir / "ledger"), **sealed)
        sealed = {**sealed, "ledger_dir": Path(ledger_dir).as_posix()}
        pack_path = run_dir / "evidence_pack.json"
        bundle_path = run_dir / "evidence_bundle.json"
        world_model_path = run_dir / "world_model.json"
        output_path = run_dir / "sealed_output.json"
        attestation_path = run_dir / "attestation.json"
        casefile_sha256 = casefile_artifact_sha256(final_casefile)

        replay_command = (
            "python -m core.determinism.replay "
            f"{Path(sealed['ledger_dir']).as_posix()} "
            "--strict-manifest"
        )
        narrative_text = world_narrative_v2["text"]
        causal_narrative_text = causal_narrative_v2["text"]
        has_temporal_cycle = any(
            finding["code"] == "CYCLE_TEMPORAL_CONSTRAINT"
            for finding in causal_graph["findings"]
        )
        causal_summary = (
            "Causal Summary\n"
            f"edges: {len(causal_graph['edges'])}\n"
            f"cycle: {'yes' if has_temporal_cycle else 'no'}\n"
            "causal_order: "
            + (
                ", ".join(causal_graph["causal_order"][:10])
                if causal_graph["causal_order"]
                else "none"
            )
            + "\n"
        )
        top_event = (
            critical_path["top_events"][0] if critical_path["top_events"] else None
        )
        critical_path_summary = (
            "Critical Path\n"
            "top: "
            + (
                f"{top_event['event_id']} score={top_event['score']}"
                if top_event is not None
                else "none"
            )
            + "\n"
            f"chain_length: {len(critical_path['critical_chain'])}\n"
        )
        constraint_summary = (
            "Constraint Summary\n"
            f"violations: {len(constraint_report['violations'])}\n"
            f"policy: {constraint_report['counts']['policy']}\n"
            f"temporal: {constraint_report['counts']['temporal']}\n"
            f"causal: {constraint_report['counts']['causal']}\n"
            f"state: {constraint_report['counts']['state']}\n"
        )
        repair_hint_preview = [
            f"{hint['action']} "
            + (
                ", ".join(hint["target"]["event_ids"] + hint["target"]["entity_ids"])
                or "none"
            )
            for hint in repair_hints["hints"][:3]
        ]
        repair_hints_summary = (
            "Repair Hints\n"
            f"count: {len(repair_hints['hints'])}\n"
            "first: "
            + ((" | ".join(repair_hint_preview)) if repair_hint_preview else "none")
            + "\n"
        )
        diff_narrative_text = ""
        diff_path = None
        diff_narrative_path = None
        if diff_against:
            diff = compute_world_diff(
                old_output=load_output_input(diff_against),
                new_output=load_output_input(sealed["ledger_dir"]),
            )
            diff_bytes = dumps_canonical(diff)
            diff_narrative = render_world_diff_narrative(diff, mode="brief")
            diff_narrative_bytes = dumps_canonical(diff_narrative)
            diff_path = _write_with_conflict_suffix(
                run_dir / "world_diff.json",
                diff_bytes,
            )
            diff_narrative_path = _write_with_conflict_suffix(
                run_dir / "world_diff_narrative.json",
                diff_narrative_bytes,
            )
            diff_narrative_text = "\nWorld Diff\n" + _format_report(
                diff_narrative["text"]
            )
        report = (
            (
                "Deterministic World Demo\n"
                f"pack_sha256:       {pack_obj['pack_sha256']}\n"
                f"bundle_sha256:     {bundle_sha256}\n"
                f"world_sha256:      {world_model['world_sha256']}\n"
                f"casefile_id:       {final_casefile['casefile_id']}\n"
                f"casefile_sha256:   {casefile_sha256}\n"
                f"output_sha256:     {sealed['output_sha256']}\n"
                f"attestation_sha256:{sealed['attestation_sha256']}\n"
                f"ledger_dir:        {sealed['ledger_dir']}\n\n"
                f"{warning_line}"
                "World Narrative\n"
                f"{_format_report(narrative_text)}\n"
                f"{causal_summary}"
                f"{critical_path_summary}"
                f"{constraint_summary}"
                f"{repair_hints_summary}"
                "Causal Narrative\n"
                f"{_format_report(causal_narrative_text)}\n"
                "Ledger Dir\n"
                f"{sealed['ledger_dir']}\n\n"
                "Replay Command\n"
                f"{replay_command}\n"
                f"{diff_narrative_text}"
            )
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        )
        result = {
            "run_dir": str(run_dir),
            "pack_path": str(pack_path),
            "bundle_path": str(bundle_path),
            "world_model_path": str(world_model_path),
            "output_path": str(output_path),
            "attestation_path": str(attestation_path),
            "pack_sha256": pack_obj["pack_sha256"],
            "bundle_sha256": bundle_sha256,
            "causal_graph": causal_graph,
            "world_sha256": world_model["world_sha256"],
            "output_sha256": sealed["output_sha256"],
            "attestation_sha256": sealed["attestation_sha256"],
            "target_claim_id": target_claim_id,
            "ledger_dir": sealed["ledger_dir"],
            "ledger_dir_rel": _repo_relative(Path(sealed["ledger_dir"])),
            "casefile": final_casefile,
            "casefile_path": str(casefile_path),
            "casefile_sha256": casefile_sha256,
            "report": report,
        }
        if diff_path is not None and diff_narrative_path is not None:
            result["world_diff_path"] = str(diff_path)
            result["world_diff_narrative_path"] = str(diff_narrative_path)
        return result

    claim_graph = propose_claim_graph(pack_obj)
    claim_graph_bytes = dumps_claim_graph(claim_graph)

    target_claim_id = _select_target_claim_id(claim_graph, query)
    output_obj = build_graph_reasoning_output(
        claim_graph,
        target_claim_id=target_claim_id,
    )
    verification_result = verify_claim(
        ruleset_id=ruleset_id,
        target_claim_id=target_claim_id,
        evidence_bundle_obj=bundle_obj,
        sealed_output_obj=output_obj,
    )
    output_obj["verification_result"] = verification_result
    output_obj["narrative"] = render_narrative(
        support_tree=output_obj["support_tree"],
        findings=output_obj["findings"],
        verification_result=verification_result,
    )
    output_obj["narrative_v2"] = render_narrative_v2(
        support_tree=output_obj["support_tree"],
        findings=output_obj["findings"],
        verification_result=verification_result,
        mode=verbosity,
        show_receipts=show_receipts,
        max_lines=max_lines,
    )
    sealed = finalize(
        bundle_obj,
        output_obj,
        manifest_sha256=manifest_sha256,
        core_version=core_version,
        ruleset_id=ruleset_id,
        created_utc=created_utc,
    )
    planned_files = {
        "attestation.json": sealed["attestation_bytes"],
        "claim_graph.json": claim_graph_bytes,
        "evidence_bundle.json": bundle_bytes,
        "evidence_pack.json": pack_bytes,
        "sealed_output.json": sealed["output_bytes"],
    }
    run_dir = _resolve_run_dir(base_run_dir, planned_files)
    _write_demo_outputs(run_dir, planned_files)
    ledger_dir = write_run(ledger_root=str(run_dir / "ledger"), **sealed)
    sealed = {**sealed, "ledger_dir": Path(ledger_dir).as_posix()}
    pack_path = run_dir / "evidence_pack.json"
    claim_graph_path = run_dir / "claim_graph.json"
    bundle_path = run_dir / "evidence_bundle.json"
    output_path = run_dir / "sealed_output.json"
    attestation_path = run_dir / "attestation.json"

    output_obj = json.loads(sealed["output_bytes"].decode("utf-8"))
    narrative_text = output_obj["narrative_v2"]["text"]
    target_claim = next(
        claim for claim in claim_graph["claims"] if claim["claim_id"] == target_claim_id
    )
    replay_command = (
        f"python -m core.determinism.replay {Path(sealed['ledger_dir']).as_posix()} "
        "--strict-manifest"
    )
    target_summary = f"{target_claim['subject']} | {target_claim['object'][:120]}"
    report = (
        (
            "Deterministic Demo\n"
            f"pack_sha256:       {pack_obj['pack_sha256']}\n"
            f"bundle_sha256:     {bundle_sha256}\n"
            f"output_sha256:     {sealed['output_sha256']}\n"
            f"attestation_sha256:{sealed['attestation_sha256']}\n"
            f"ledger_dir:        {sealed['ledger_dir']}\n"
            f"target_claim_id:   {target_claim_id}\n"
            f"target_claim:      {target_summary}\n\n"
            "Narrative\n"
            f"{_format_report(narrative_text)}\n"
            "Ledger Dir\n"
            f"{sealed['ledger_dir']}\n\n"
            "Replay Command\n"
            f"{replay_command}\n"
        )
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    return {
        "run_dir": str(run_dir),
        "pack_path": str(pack_path),
        "claim_graph_path": str(claim_graph_path),
        "bundle_path": str(bundle_path),
        "output_path": str(output_path),
        "attestation_path": str(attestation_path),
        "pack_sha256": pack_obj["pack_sha256"],
        "bundle_sha256": bundle_sha256,
        "output_sha256": sealed["output_sha256"],
        "attestation_sha256": sealed["attestation_sha256"],
        "target_claim_id": target_claim_id,
        "ledger_dir": sealed["ledger_dir"],
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-chunks", type=int, required=True)
    parser.add_argument("--created-utc", required=True)
    parser.add_argument("--core-version", required=True)
    parser.add_argument("--ruleset-id", required=True)
    parser.add_argument("--world", default="false")
    parser.add_argument("--verbosity", default="brief", choices=["brief", "full"])
    parser.add_argument("--show-receipts", default="false")
    parser.add_argument("--max-lines", type=int, default=200)
    parser.add_argument("--diff-against", default="")
    parser.add_argument("--max-events", type=int, default=30)
    parser.add_argument("--enrich", default="")
    args = parser.parse_args(argv)

    result = run_demo(
        folder=args.folder,
        query=args.query,
        prompt=args.prompt,
        max_chunks=args.max_chunks,
        created_utc=args.created_utc,
        core_version=args.core_version,
        ruleset_id=args.ruleset_id,
        world=_parse_bool(args.world),
        verbosity=args.verbosity,
        show_receipts=_parse_bool(args.show_receipts),
        max_lines=args.max_lines,
        diff_against=args.diff_against,
        max_events=args.max_events,
        enrich=args.enrich,
    )
    print(result["report"], end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

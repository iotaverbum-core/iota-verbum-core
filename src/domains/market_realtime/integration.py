from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.path_compiler import PathCompiler
from core.world.forward_projection import ForwardProjection
from domains.market_realtime.extractors import MarketRealtimeExtractors

_TEMPLATE_STUB_PATH = Path(__file__).with_name("template_stub.json")


def _public_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in context.items() if not str(key).startswith("__")
    }


def _seed_timestamp_from(output_data: dict, context: dict[str, Any]) -> str:
    if context.get("seed_timestamp"):
        return str(context["seed_timestamp"])
    market_input = output_data.get("market_input") or {}
    if market_input.get("timestamp"):
        return str(market_input["timestamp"])
    world_model = output_data.get("world_model") or {}
    if world_model.get("timestamp"):
        return str(world_model["timestamp"])
    return "2026-03-19T09:29:59Z"


def _parse_horizon_seconds(context: dict[str, Any]) -> int:
    value = context.get("horizon_seconds", context.get("horizon", 86400))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 86400


def _parse_utc_timestamp(raw_timestamp: str) -> datetime:
    normalized = raw_timestamp.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@contextmanager
def _fixed_projection_clock(seed_timestamp: str):
    import core.world.forward_projection as forward_projection_module

    fixed_dt = _parse_utc_timestamp(seed_timestamp)
    original_datetime = forward_projection_module.datetime
    original_time = forward_projection_module.time.time

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_dt.replace(tzinfo=None)
            return fixed_dt.astimezone(tz)

        @classmethod
        def fromtimestamp(cls, timestamp, tz=None):
            return original_datetime.fromtimestamp(timestamp, tz=tz)

    forward_projection_module.datetime = FixedDateTime
    forward_projection_module.time.time = lambda: fixed_dt.timestamp()
    try:
        yield
    finally:
        forward_projection_module.datetime = original_datetime
        forward_projection_module.time.time = original_time


class MarketRealtimePipelineAdapter:
    domain = "market_realtime"

    def __init__(self) -> None:
        self._extractor = MarketRealtimeExtractors()
        self._current_ref = "UNKNOWN"

    def set_input_ref(self, input_ref: str) -> None:
        self._current_ref = input_ref

    def normalize_input(self, data: dict) -> dict:
        return data or {}

    def extract(self, normalized_input: dict, context: dict):
        result = self._extractor.extract(
            data=normalized_input,
            ref=self._current_ref,
            context=_public_context(context),
        )
        return result.to_dict()

    def build_evidence_map(self, extracted: dict, normalized_input: dict):
        return {
            "entities": extracted.get("entities", []),
            "events": extracted.get("events", []),
            "edges": extracted.get("edges", []),
            "states": extracted.get("states", []),
            "unknowns": extracted.get("unknowns", []),
            "invalidations": extracted.get("invalidations", []),
            "scenarios": extracted.get("scenarios", []),
        }

    def template_fallback(
        self, input_ref: str, context: dict, normalized_input: dict
    ):
        return [_TEMPLATE_STUB_PATH]

    def build_context(
        self, input_ref, input_data, normalized_input, extracted, evidence_map, context
    ):
        world_model = extracted.get("world_model", {})
        return {
            "input_ref": input_ref,
            "symbol": normalized_input.get("symbol"),
            "timestamp": normalized_input.get("timestamp"),
            "mode": context.get("mode"),
            "horizon": context.get("horizon", context.get("horizon_seconds")),
            "scenario_labels": [
                scenario.get("label") for scenario in extracted.get("scenarios", [])
            ],
            "state_count": len(world_model.get("states", [])),
            "edge_count": len(world_model.get("edges", [])),
        }

    def render_output(
        self,
        input_ref,
        input_data,
        normalized_input,
        extracted,
        evidence_map,
        rendered,
        context,
    ):
        template_id = rendered.get("template_id") or rendered.get("id")
        return {
            "spec_version": "market_realtime_v1",
            "domain": "market_realtime",
            "input_ref": input_ref,
            "context": _public_context(context),
            "market_input": normalized_input,
            "world_model": extracted.get("world_model", {}),
            "entities": extracted.get("entities", []),
            "events": extracted.get("events", []),
            "edges": extracted.get("edges", []),
            "states": extracted.get("states", []),
            "unknowns": extracted.get("unknowns", []),
            "invalidations": extracted.get("invalidations", []),
            "scenarios": extracted.get("scenarios", []),
            "metadata": extracted.get("metadata", {}),
            "input_sha256": extracted.get("input_sha256", ""),
            "evidence_map": evidence_map,
            "template": {"id": template_id, "path": rendered.get("_template_path")},
        }


def compile_market_forward_artifacts(
    output_dir: Path, output_data: dict, context: dict[str, Any]
) -> dict:
    seed_timestamp = _seed_timestamp_from(output_data, context)
    horizon_seconds = _parse_horizon_seconds(context)
    world_model = output_data.get("world_model") or {}

    with _fixed_projection_clock(seed_timestamp):
        projector = ForwardProjection(
            world_model=world_model,
            horizon_seconds=horizon_seconds,
            domain=str(world_model.get("domain", "market_realtime")),
            seed_timestamp=seed_timestamp,
        )
        possibility_space = projector.project()
        sealed_path = projector.seal_optimal_path(possibility_space)

    compiler = PathCompiler(output_dir=Path(output_dir))
    return compiler.compile(sealed_path)

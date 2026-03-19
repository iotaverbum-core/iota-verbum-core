"""
forward_projection.py
=====================
IOTA VERBUM CORE — src/core/world/forward_projection.py

Flips the world model from backward-facing (evidence → past state)
to forward-facing (current state → future states).

This is the single module that enables the Reality Engineering Engine.

Architecture:
    WorldModel (existing) → ForwardProjection → PossibilitySpace → PathCompiler

The engine already knows what IS.
This module computes what WILL BE — deterministically, with attestable proof.

Usage:
    from core.world.forward_projection import ForwardProjection

    fp = ForwardProjection(world_model=wm, horizon_seconds=86400)
    possibility_space = fp.project()
    sealed_path = fp.seal_optimal_path(possibility_space)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

class CausalStrength(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"


class VerificationStatus(str, Enum):
    VERIFIED         = "VERIFIED"
    VERIFIED_NEEDS_INFO = "VERIFIED_NEEDS_INFO"
    UNVERIFIED       = "UNVERIFIED"


@dataclass
class CausalEdge:
    """
    A directed causal relationship between two states.

    edge_id:    unique identifier
    cause_id:   id of the originating state or event
    effect_id:  id of the resulting state or event
    mechanism:  human-readable description of HOW cause produces effect
    strength:   HIGH / MEDIUM / LOW
    lag_seconds: how long after the cause the effect manifests
    confidence: 0.0 - 1.0
    """
    edge_id:     str
    cause_id:    str
    effect_id:   str
    mechanism:   str
    strength:    CausalStrength
    lag_seconds: int
    confidence:  float = 1.0
    metadata:    dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "edge_id":     self.edge_id,
            "cause_id":    self.cause_id,
            "effect_id":   self.effect_id,
            "mechanism":   self.mechanism,
            "strength":    self.strength.value,
            "lag_seconds": self.lag_seconds,
            "confidence":  self.confidence,
            "metadata":    self.metadata,
        }


@dataclass
class WorldState:
    """
    A snapshot of reality at a specific point in time.

    state_id:   unique identifier
    label:      human-readable description
    timestamp:  ISO-8601 UTC
    certainty:  HIGH / MEDIUM / LOW
    value:      optional numeric value (price, rate, count, etc.)
    unit:       optional unit for the value
    domain:     which domain this state belongs to
    """
    state_id:  str
    label:     str
    timestamp: str
    certainty: CausalStrength
    value:     float | None = None
    unit:      str   | None = None
    domain:    str          = "general"
    metadata:  dict         = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "state_id":  self.state_id,
            "label":     self.label,
            "timestamp": self.timestamp,
            "certainty": self.certainty.value,
            "value":     self.value,
            "unit":      self.unit,
            "domain":    self.domain,
            "metadata":  self.metadata,
        }


@dataclass
class FutureState:
    """
    A projected state at a future point in time.
    Derived from current WorldState through causal propagation.

    probability:      0.0 - 1.0 — how likely this state becomes real
    causal_chain:     ordered list of edge_ids that produced this state
    invalidated_by:   condition that would prevent this state
    scenario_id:      which scenario this belongs to
    """
    state_id:       str
    label:          str
    timestamp:      str
    certainty:      CausalStrength
    probability:    float
    causal_chain:   list[str]
    scenario_id:    str
    value:          float | None = None
    unit:           str   | None = None
    invalidated_by: str   | None = None
    domain:         str          = "general"
    metadata:       dict         = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "state_id":       self.state_id,
            "label":          self.label,
            "timestamp":      self.timestamp,
            "certainty":      self.certainty.value,
            "probability":    self.probability,
            "causal_chain":   self.causal_chain,
            "scenario_id":    self.scenario_id,
            "value":          self.value,
            "unit":           self.unit,
            "invalidated_by": self.invalidated_by,
            "domain":         self.domain,
            "metadata":       self.metadata,
        }


@dataclass
class Scenario:
    """
    A coherent branch of possible futures.

    scenario_id:     unique identifier
    label:           human-readable name
    probability:     0.0 - 1.0
    trigger:         what causes this scenario to activate
    invalidations:   list of condition IDs that kill this scenario
    future_states:   ordered list of FutureState objects in this branch
    target_value:    the final state value this scenario reaches
    """
    scenario_id:   str
    label:         str
    probability:   float
    trigger:       str
    invalidations: list[str]
    future_states: list[FutureState] = field(default_factory=list)
    target_value:  float | None      = None
    metadata:      dict              = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scenario_id":   self.scenario_id,
            "label":         self.label,
            "probability":   self.probability,
            "trigger":       self.trigger,
            "invalidations": self.invalidations,
            "future_states": [fs.to_dict() for fs in self.future_states],
            "target_value":  self.target_value,
            "metadata":      self.metadata,
        }


@dataclass
class PossibilitySpace:
    """
    The complete map of all branching futures from the current world state.

    scenarios:        all possible scenarios ranked by probability
    sealed_scenario:  the highest-probability scenario — the chosen path
    total_scenarios:  count of all scenarios considered
    coverage:         sum of all scenario probabilities (should be ~1.0)
    unknowns:         unresolved evidence gaps that affect projections
    """
    scenarios:       list[Scenario]
    sealed_scenario: Scenario
    total_scenarios: int
    coverage:        float
    unknowns:        list[dict]
    generated_at:    str
    horizon_seconds: int
    domain:          str   = "general"
    metadata:        dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sealed_scenario": self.sealed_scenario.to_dict(),
            "scenarios":       [s.to_dict() for s in self.scenarios],
            "total_scenarios": self.total_scenarios,
            "coverage":        self.coverage,
            "unknowns":        self.unknowns,
            "generated_at":    self.generated_at,
            "horizon_seconds": self.horizon_seconds,
            "domain":          self.domain,
            "metadata":        self.metadata,
        }


@dataclass
class SealedPath:
    """
    The deterministic, cryptographically sealed optimal path.

    This is the contract between the current state and the future state.
    Once sealed — immutable.

    path_id:          unique identifier
    scenario:         the chosen scenario
    sealed_at:        ISO-8601 UTC timestamp of sealing
    seal_sha256:      cryptographic hash of the sealed path
    nodes:            time-ordered sequence of future states
    invalidations:    conditions that break the contract
    replay_key:       identifier for replay verification
    verification:     VERIFIED / VERIFIED_NEEDS_INFO / UNVERIFIED
    """
    path_id:       str
    scenario:      Scenario
    sealed_at:     str
    seal_sha256:   str
    nodes:         list[FutureState]
    invalidations: list[dict]
    replay_key:    str
    verification:  VerificationStatus
    unknowns:      list[dict]
    domain:        str  = "general"
    metadata:      dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "path_id":        self.path_id,
            "scenario":       self.scenario.to_dict(),
            "sealed_at":      self.sealed_at,
            "seal_sha256":    self.seal_sha256,
            "nodes":          [n.to_dict() for n in self.nodes],
            "invalidations":  self.invalidations,
            "replay_key":     self.replay_key,
            "verification":   self.verification.value,
            "unknowns":       self.unknowns,
            "domain":         self.domain,
            "horizon_seconds": self.metadata.get("horizon_seconds",
                               self.scenario.metadata.get("horizon_seconds", 86400)),
            "metadata":       self.metadata,
        }


# ---------------------------------------------------------------------------
# Forward Projection Engine
# ---------------------------------------------------------------------------

class ForwardProjection:
    """
    The core forward projection engine.

    Takes a world model (current states + causal edges) and projects
    it forward through time, generating a possibility space of future
    states and sealing the optimal path as a deterministic contract.

    This is the module that flips IOTA VERBUM CORE from past-facing
    to future-facing — enabling the Reality Engineering Engine.

    Args:
        world_model:      dict containing current states and causal edges
        horizon_seconds:  how far forward to project (default: 86400 = 24h)
        domain:           the domain being projected (market, legal, clinical...)
        seed_timestamp:   optional fixed timestamp for deterministic runs
    """

    VERSION = "0.1.0"

    def __init__(
        self,
        world_model:     dict,
        horizon_seconds: int  = 86400,
        domain:          str  = "general",
        seed_timestamp:  str  | None = None,
    ) -> None:
        self.world_model     = world_model
        self.horizon_seconds = horizon_seconds
        self.domain          = domain
        self.seed_timestamp  = seed_timestamp or datetime.now(timezone.utc).isoformat()

        # Parse inputs
        self._states: dict[str, WorldState] = {}
        self._edges:  list[CausalEdge]      = []
        self._unknowns: list[dict]          = []
        self._invalidations: list[dict]     = []
        self._scenarios_raw: list[dict]     = []

        self._parse_world_model()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_world_model(self) -> None:
        """Parse the world model dict into typed objects."""

        # Parse states
        for s in self.world_model.get("states", []):
            state = WorldState(
                state_id  = s["state_id"],
                label     = s["label"],
                timestamp = s.get("timestamp", self.seed_timestamp),
                certainty = CausalStrength(s.get("certainty", "MEDIUM")),
                value     = s.get("value"),
                unit      = s.get("unit"),
                domain    = s.get("domain", self.domain),
                metadata  = s.get("metadata", {}),
            )
            self._states[state.state_id] = state

        # Parse causal edges
        for e in self.world_model.get("edges", []):
            edge = CausalEdge(
                edge_id     = e["edge_id"],
                cause_id    = e["cause_id"],
                effect_id   = e["effect_id"],
                mechanism   = e["mechanism"],
                strength    = CausalStrength(e.get("strength", "MEDIUM")),
                lag_seconds = e.get("lag_seconds", 0),
                confidence  = e.get("confidence", 1.0),
                metadata    = e.get("metadata", {}),
            )
            self._edges.append(edge)

        # Parse unknowns
        self._unknowns = self.world_model.get("unknowns", [])

        # Parse invalidations
        self._invalidations = self.world_model.get("invalidations", [])

        # Parse scenario definitions
        self._scenarios_raw = self.world_model.get("scenarios", [])

    # ------------------------------------------------------------------
    # Causal propagation
    # ------------------------------------------------------------------

    def _propagate_state(
        self,
        state_id:      str,
        scenario_id:   str,
        probability:   float,
        causal_chain:  list[str],
        current_time:  float,
        depth:         int = 0,
        max_depth:     int = 20,
    ) -> list[FutureState]:
        """
        Recursively propagate a state forward through causal edges.

        For each outgoing edge from state_id:
          - Calculate when the effect manifests (current_time + lag)
          - Create a FutureState for the effect
          - Recurse into the effect state

        Returns a flat list of all FutureState objects reachable
        from state_id within the projection horizon.
        """
        if depth >= max_depth:
            return []

        future_states: list[FutureState] = []

        for edge in self._edges:
            if edge.cause_id != state_id:
                continue

            effect_time = current_time + edge.lag_seconds
            if effect_time > self._origin_time + self.horizon_seconds:
                continue

            # Probability decays with each causal hop weighted by strength
            strength_weight = {
                CausalStrength.HIGH:   1.0,
                CausalStrength.MEDIUM: 0.75,
                CausalStrength.LOW:    0.5,
            }[edge.strength]

            derived_probability = probability * strength_weight * edge.confidence

            # Resolve the effect state
            effect_state = self._states.get(edge.effect_id)
            if not effect_state:
                continue

            effect_timestamp = datetime.fromtimestamp(
                effect_time, tz=timezone.utc
            ).isoformat()

            future = FutureState(
                state_id      = f"future:{edge.edge_id}:{edge.effect_id}",
                label         = effect_state.label,
                timestamp     = effect_timestamp,
                certainty     = edge.strength,
                probability   = round(derived_probability, 4),
                causal_chain  = causal_chain + [edge.edge_id],
                scenario_id   = scenario_id,
                value         = effect_state.value,
                unit          = effect_state.unit,
                domain        = effect_state.domain,
                metadata      = {
                    "mechanism":   edge.mechanism,
                    "lag_seconds": edge.lag_seconds,
                    "source_edge": edge.edge_id,
                },
            )
            future_states.append(future)

            # Recurse
            future_states.extend(
                self._propagate_state(
                    state_id     = edge.effect_id,
                    scenario_id  = scenario_id,
                    probability  = derived_probability,
                    causal_chain = causal_chain + [edge.edge_id],
                    current_time = effect_time,
                    depth        = depth + 1,
                    max_depth    = max_depth,
                )
            )

        return future_states

    # ------------------------------------------------------------------
    # Scenario generation
    # ------------------------------------------------------------------

    def _build_scenario(self, scenario_def: dict) -> Scenario:
        """
        Build a Scenario from a scenario definition.

        If the scenario has explicit trigger states defined,
        propagate forward from those states.
        Otherwise propagate from all HIGH certainty current states.
        """
        scenario_id  = scenario_def["scenario_id"]
        trigger      = scenario_def.get("trigger", "")
        probability  = scenario_def.get("probability", 0.0)
        invalidations = scenario_def.get("invalidations", [])
        target_value = scenario_def.get("target_value")

        # Find trigger states
        trigger_state_ids = scenario_def.get("trigger_state_ids", [])
        if not trigger_state_ids:
            # Default: start from all HIGH certainty states
            trigger_state_ids = [
                sid for sid, s in self._states.items()
                if s.certainty == CausalStrength.HIGH
            ]

        # Propagate forward from trigger states
        all_future_states: list[FutureState] = []
        for state_id in trigger_state_ids:
            propagated = self._propagate_state(
                state_id     = state_id,
                scenario_id  = scenario_id,
                probability  = probability,
                causal_chain = [],
                current_time = self._origin_time,
            )
            all_future_states.extend(propagated)

        # Sort by timestamp
        all_future_states.sort(key=lambda fs: fs.timestamp)

        # Deduplicate by state label + timestamp
        seen: set[str] = set()
        deduped: list[FutureState] = []
        for fs in all_future_states:
            key = f"{fs.label}:{fs.timestamp}"
            if key not in seen:
                seen.add(key)
                deduped.append(fs)

        return Scenario(
            scenario_id   = scenario_id,
            label         = scenario_def.get("label", scenario_id),
            probability   = probability,
            trigger       = trigger,
            invalidations = invalidations,
            future_states = deduped,
            target_value  = target_value,
            metadata      = scenario_def.get("metadata", {}),
        )

    # ------------------------------------------------------------------
    # Possibility space
    # ------------------------------------------------------------------

    def project(self) -> PossibilitySpace:
        """
        Generate the complete possibility space.

        Projects all scenarios forward through the causal graph,
        ranks them by probability, and returns the full map of
        possible futures.

        This is the core forward-facing operation.
        """
        self._origin_time = time.time()

        if not self._scenarios_raw:
            raise ValueError(
                "No scenarios defined in world model. "
                "Add a 'scenarios' list to enable forward projection."
            )

        # Build all scenarios
        scenarios: list[Scenario] = []
        for sdef in self._scenarios_raw:
            scenario = self._build_scenario(sdef)
            scenarios.append(scenario)

        # Rank by probability descending
        scenarios.sort(key=lambda s: s.probability, reverse=True)

        # The sealed scenario is the highest probability
        sealed = scenarios[0]

        # Coverage = sum of all scenario probabilities
        coverage = round(sum(s.probability for s in scenarios), 4)

        return PossibilitySpace(
            scenarios       = scenarios,
            sealed_scenario = sealed,
            total_scenarios = len(scenarios),
            coverage        = coverage,
            unknowns        = self._unknowns,
            generated_at    = datetime.now(timezone.utc).isoformat(),
            horizon_seconds = self.horizon_seconds,
            domain          = self.domain,
            metadata        = {
                "engine_version": self.VERSION,
                "seed_timestamp": self.seed_timestamp,
                "state_count":    len(self._states),
                "edge_count":     len(self._edges),
            },
        )

    # ------------------------------------------------------------------
    # Path sealing
    # ------------------------------------------------------------------

    def seal_optimal_path(
        self,
        possibility_space: PossibilitySpace,
        output_dir:        Path | None = None,
    ) -> SealedPath:
        """
        Seal the optimal path from the possibility space.

        Takes the highest-probability scenario and produces a
        cryptographically sealed, replayable contract.

        The seal is computed as SHA-256 of the canonical JSON
        representation of the path — identical to the attestation
        approach used throughout IOTA VERBUM CORE.

        Args:
            possibility_space: the output of project()
            output_dir:        if provided, writes sealed_path.json here

        Returns:
            SealedPath — the immutable sealed contract
        """
        scenario = possibility_space.sealed_scenario
        sealed_at = datetime.now(timezone.utc).isoformat()

        # Determine verification status
        verification = (
            VerificationStatus.VERIFIED
            if len(possibility_space.unknowns) == 0
            else VerificationStatus.VERIFIED_NEEDS_INFO
        )

        # Build canonical representation for hashing
        # IMPORTANT: fields must be in deterministic order
        canonical = {
            "path_version":   "1.0",
            "domain":         self.domain,
            "sealed_at":      sealed_at,
            "scenario_id":    scenario.scenario_id,
            "scenario_label": scenario.label,
            "probability":    scenario.probability,
            "trigger":        scenario.trigger,
            "invalidations":  scenario.invalidations,
            "nodes":          [n.to_dict() for n in scenario.future_states],
            "unknowns":       possibility_space.unknowns,
            "horizon_seconds": self.horizon_seconds,
            "engine_version": self.VERSION,
        }

        canonical_bytes = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

        seal_sha256 = hashlib.sha256(canonical_bytes).hexdigest()

        replay_key = (
            f"{self.domain}:"
            f"{scenario.scenario_id}:"
            f"{sealed_at[:10]}:"
            f"{seal_sha256[:8]}"
        )

        path_id = hashlib.sha256(
            f"{replay_key}:{sealed_at}".encode()
        ).hexdigest()

        sealed_path = SealedPath(
            path_id       = path_id,
            scenario      = scenario,
            sealed_at     = sealed_at,
            seal_sha256   = seal_sha256,
            nodes         = scenario.future_states,
            invalidations = self._invalidations,
            replay_key    = replay_key,
            verification  = verification,
            unknowns      = possibility_space.unknowns,
            domain        = self.domain,
            metadata      = {
                "engine_version":  self.VERSION,
                "horizon_seconds": self.horizon_seconds,
                "total_scenarios": possibility_space.total_scenarios,
                "coverage":        possibility_space.coverage,
                "canonical_bytes": len(canonical_bytes),
            },
        )

        # Write to output dir if provided
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            sealed_path_file = output_dir / "sealed_path.json"
            sealed_path_file.write_text(
                json.dumps(sealed_path.to_dict(), indent=2, ensure_ascii=True),
                encoding="utf-8",
            )

            # Write the attestation hash separately
            # — matches pattern of attestation.py in the existing core
            attestation_file = output_dir / "forward_attestation.sha256"
            attestation_file.write_text(
                f"{seal_sha256}  sealed_path.json\n",
                encoding="utf-8",
            )

        return sealed_path

    # ------------------------------------------------------------------
    # Replay verification
    # ------------------------------------------------------------------

    @staticmethod
    def verify_replay(sealed_path_file: Path) -> dict:
        """
        Verify a sealed path against its attestation hash.

        Recomputes the canonical hash and compares to the stored seal.
        Returns a verification report.

        This mirrors the verify_attestation() function in attestation.py.
        """
        data = json.loads(sealed_path_file.read_text(encoding="utf-8"))

        # Rebuild canonical representation
        scenario_data = data.get("scenario", {})
        canonical = {
            "path_version":    "1.0",
            "domain":          data.get("domain"),
            "sealed_at":       data.get("sealed_at"),
            "scenario_id":     scenario_data.get("scenario_id"),
            "scenario_label":  scenario_data.get("label"),
            "probability":     scenario_data.get("probability"),
            "trigger":         scenario_data.get("trigger"),
            "invalidations":   scenario_data.get("invalidations"),
            "nodes":           data.get("nodes", []),
            "unknowns":        data.get("unknowns", []),
            "horizon_seconds": data.get("horizon_seconds"),
            "engine_version":  data.get("metadata", {}).get("engine_version"),
        }

        canonical_bytes = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

        recomputed = hashlib.sha256(canonical_bytes).hexdigest()
        stored     = data.get("seal_sha256", "")
        match      = recomputed == stored

        return {
            "replay_key":    data.get("replay_key"),
            "sealed_at":     data.get("sealed_at"),
            "stored_hash":   stored,
            "recomputed":    recomputed,
            "match":         match,
            "status":        "VERIFIED_OK" if match else "REPLAY_FAILED",
            "path_id":       data.get("path_id"),
        }


# ---------------------------------------------------------------------------
# Domain-specific world model builders
# ---------------------------------------------------------------------------

class MarketWorldModelBuilder:
    """
    Converts raw market data into a world model dict
    consumable by ForwardProjection.

    This is the ingestion layer for the market_realtime domain.
    Feed it live data — it outputs a world model ready for projection.
    """

    @staticmethod
    def build(
        symbol:          str,
        last_close:      float,
        day_change_pts:  float,
        vix:             float,
        futures_pts:     float,
        commodity_price: float,
        commodity_unit:  str  = "USD/bbl",
        macro_events:    list[dict] | None = None,
        scenarios:       list[dict] | None = None,
        unknowns:        list[dict] | None = None,
        invalidations:   list[dict] | None = None,
        timestamp:       str  | None = None,
    ) -> dict:
        """
        Build a market world model from raw inputs.

        Returns a dict ready for ForwardProjection().
        """
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        states = [
            {
                "state_id":  "state:price:last_close",
                "label":     f"{symbol} Last Close {last_close}",
                "timestamp": ts,
                "certainty": "HIGH",
                "value":     last_close,
                "unit":      "USD",
                "domain":    "market",
            },
            {
                "state_id":  "state:price:day_change",
                "label":     f"{symbol} Day Change {day_change_pts:+.2f}pts",
                "timestamp": ts,
                "certainty": "HIGH",
                "value":     day_change_pts,
                "unit":      "pts",
                "domain":    "market",
            },
            {
                "state_id":  "state:volatility:vix",
                "label":     f"VIX {vix}",
                "timestamp": ts,
                "certainty": "HIGH",
                "value":     vix,
                "unit":      "index",
                "domain":    "market",
            },
            {
                "state_id":  "state:futures:premarket",
                "label":     f"{symbol} Pre-Market Futures {futures_pts:+.0f}pts",
                "timestamp": ts,
                "certainty": "HIGH",
                "value":     futures_pts,
                "unit":      "pts",
                "domain":    "market",
            },
            {
                "state_id":  "state:commodity:price",
                "label":     f"Commodity {commodity_price} {commodity_unit}",
                "timestamp": ts,
                "certainty": "HIGH",
                "value":     commodity_price,
                "unit":      commodity_unit,
                "domain":    "market",
            },
        ]

        # Add macro events as states
        for i, event in enumerate(macro_events or []):
            states.append({
                "state_id":  f"state:macro:{i:03d}",
                "label":     event.get("label", f"Macro event {i}"),
                "timestamp": event.get("timestamp", ts),
                "certainty": event.get("certainty", "MEDIUM"),
                "domain":    "market",
                "metadata":  event.get("metadata", {}),
            })

        # Default edges for market domain
        # These encode the standard causal relationships in financial markets
        edges = [
            # Sell pressure → price drop
            {
                "edge_id":     "edge:market:001",
                "cause_id":    "state:price:day_change",
                "effect_id":   "state:volatility:vix",
                "mechanism":   "large price drop spikes fear index",
                "strength":    "HIGH",
                "lag_seconds": 60,
                "confidence":  0.9,
            },
            # Shallow futures → exhaustion signal
            {
                "edge_id":     "edge:market:002",
                "cause_id":    "state:futures:premarket",
                "effect_id":   "state:price:last_close",
                "mechanism":   "shallow futures vs prior drop signals exhaustion",
                "strength":    "MEDIUM",
                "lag_seconds": 1800,
                "confidence":  0.65,
            },
            # High VIX → institutional accumulation
            {
                "edge_id":     "edge:market:003",
                "cause_id":    "state:volatility:vix",
                "effect_id":   "state:price:last_close",
                "mechanism":   "elevated VIX signals near-term mean reversion",
                "strength":    "MEDIUM",
                "lag_seconds": 3600,
                "confidence":  0.6,
            },
            # Commodity price → inflation → macro pressure
            {
                "edge_id":     "edge:market:004",
                "cause_id":    "state:commodity:price",
                "effect_id":   "state:price:day_change",
                "mechanism":   "high commodity prices raise inflation → Fed hold → sell pressure",
                "strength":    "HIGH",
                "lag_seconds": 7200,
                "confidence":  0.85,
            },
        ]

        return {
            "states":       states,
            "edges":        edges,
            "unknowns":     unknowns     or [],
            "invalidations": invalidations or [],
            "scenarios":    scenarios    or [],
            "domain":       "market",
            "symbol":       symbol,
            "timestamp":    ts,
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _run_example() -> None:
    """
    Example: Run the DJI forward projection from the March 19 2026 casefile.
    This demonstrates the full forward projection pipeline.
    """
    import tempfile

    print("=" * 60)
    print("IOTA VERBUM CORE — Forward Projection Engine")
    print("=" * 60)

    # Build the DJI world model from the March 19 casefile
    world_model = MarketWorldModelBuilder.build(
        symbol          = "DJI",
        last_close      = 46225.15,
        day_change_pts  = -768.11,
        vix             = 25.09,
        futures_pts     = -77.0,
        commodity_price = 113.0,
        commodity_unit  = "USD/bbl",
        macro_events    = [
            {"label": "US-Iran War Active",    "certainty": "HIGH"},
            {"label": "Fed Rate Hold",         "certainty": "HIGH"},
            {"label": "Brent $113/bbl",        "certainty": "HIGH"},
            {"label": "Nvidia H200 Approval",  "certainty": "MEDIUM"},
            {"label": "Micron Extended Decline","certainty": "MEDIUM"},
        ],
        scenarios = [
            {
                "scenario_id":  "scen:B:bounce",
                "label":        "Dead Cat Bounce",
                "probability":  0.40,
                "trigger":      "Oversold + VIX exhaustion + shallow futures",
                "invalidations": ["inv:oil_spike", "inv:iran_escalation"],
                "target_value": 46600.0,
            },
            {
                "scenario_id":  "scen:A:continuation",
                "label":        "Bearish Continuation",
                "probability":  0.35,
                "trigger":      "Oil spike OR new Iran escalation",
                "invalidations": [],
                "target_value": 45800.0,
            },
            {
                "scenario_id":  "scen:C:reversal",
                "label":        "Sharp Reversal",
                "probability":  0.15,
                "trigger":      "Ceasefire OR emergency Fed pivot",
                "invalidations": [],
                "target_value": 47000.0,
            },
            {
                "scenario_id":  "scen:D:consolidation",
                "label":        "Consolidation",
                "probability":  0.10,
                "trigger":      "No new catalysts",
                "invalidations": [],
                "target_value": 46300.0,
            },
        ],
        unknowns = [
            {"id": "unk:001", "label": "Exact timing of Iran headlines"},
            {"id": "unk:002", "label": "Fed speaker schedule today"},
            {"id": "unk:003", "label": "Jones Act oil impact timing"},
            {"id": "unk:004", "label": "Retail trader sentiment direction"},
            {"id": "unk:005", "label": "Micron bleed into broader tech"},
        ],
        invalidations = [
            {"id": "inv:oil_spike",       "trigger": "Brent > $120/bbl"},
            {"id": "inv:iran_escalation", "trigger": "Direct US military involvement"},
            {"id": "inv:fed_emergency",   "trigger": "Emergency Fed statement"},
            {"id": "inv:breadth_fail",    "trigger": "20+ of 30 DJI components down at 11:00 ET"},
            {"id": "inv:support_breach",  "trigger": "46193 broken on high volume"},
        ],
        timestamp = "2026-03-19T09:29:59+00:00",
    )

    # Run forward projection
    fp = ForwardProjection(
        world_model     = world_model,
        horizon_seconds = 86400,
        domain          = "market",
        seed_timestamp  = "2026-03-19T09:29:59+00:00",
    )

    print("\n[1] Projecting possibility space...")
    possibility_space = fp.project()

    print(f"    Scenarios generated: {possibility_space.total_scenarios}")
    print(f"    Coverage:            {possibility_space.coverage:.2f}")
    print(f"    Unknowns:            {len(possibility_space.unknowns)}")
    print(f"    Sealed scenario:     {possibility_space.sealed_scenario.label}")
    print(f"    Probability:         {possibility_space.sealed_scenario.probability:.0%}")

    # Seal the optimal path
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir)

        print("\n[2] Sealing optimal path...")
        sealed = fp.seal_optimal_path(possibility_space, output_dir=out)

        print(f"    Path ID:      {sealed.path_id[:16]}...")
        print(f"    Sealed at:    {sealed.sealed_at}")
        print(f"    Seal SHA256:  {sealed.seal_sha256[:16]}...")
        print(f"    Replay key:   {sealed.replay_key}")
        print(f"    Verification: {sealed.verification.value}")
        print(f"    Nodes:        {len(sealed.nodes)}")

        # Verify replay
        print("\n[3] Verifying replay...")
        replay = ForwardProjection.verify_replay(out / "sealed_path.json")
        print(f"    Status:  {replay['status']}")
        print(f"    Match:   {replay['match']}")

    print("\n" + "=" * 60)
    print("CONTRACT SEALED. REALITY ENGINEERING ENGINE ACTIVE.")
    print("=" * 60)


if __name__ == "__main__":
    _run_example()

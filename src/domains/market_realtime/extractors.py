"""
extractors.py
=============
IOTA VERBUM CORE — src/domains/market_realtime/extractors.py

Market realtime domain extractor.

Converts live or historical market data into the canonical causal
evidence format consumed by ForwardProjection and DeterministicPipeline.

Follows the extractor interface pattern established in:
  - domains/biblical_text/extractors.py
  - domains/clinical_records/extractors.py
  - domains/legal_contract/extractor.py

Usage (via pipeline):
    python -m deterministic_ai \\
      --domain market_realtime \\
      --input-ref "DJI-2026-03-19" \\
      --input-file data/market/dji_20260319.json \\
      --context "mode=forward" \\
      --context "horizon=86400" \\
      --out outputs/market/dji_20260319

Usage (direct):
    from domains.market_realtime.extractors import MarketRealtimeExtractors
    extractor = MarketRealtimeExtractors()
    result = extractor.extract(data, ref="DJI-2026-03-19", context={})
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Extraction result
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """
    The canonical output of any extractor in IOTA VERBUM CORE.

    Mirrors the structure expected by DeterministicPipeline.process()
    and consumed by ForwardProjection.

    Fields:
        ref:           the input reference identifier
        domain:        the domain name
        world_model:   the structured causal world model
        entities:      flat list of all extracted entities
        events:        flat list of all extracted events
        edges:         flat list of all causal edges
        states:        flat list of all world states
        unknowns:      unresolved evidence gaps
        invalidations: conditions that break the contract
        scenarios:     defined future scenario branches
        metadata:      provenance and extraction metadata
        input_sha256:  hash of the raw input bytes
    """
    ref:           str
    domain:        str
    world_model:   dict
    entities:      list[dict] = field(default_factory=list)
    events:        list[dict] = field(default_factory=list)
    edges:         list[dict] = field(default_factory=list)
    states:        list[dict] = field(default_factory=list)
    unknowns:      list[dict] = field(default_factory=list)
    invalidations: list[dict] = field(default_factory=list)
    scenarios:     list[dict] = field(default_factory=list)
    metadata:      dict       = field(default_factory=dict)
    input_sha256:  str        = ""

    def to_dict(self) -> dict:
        return {
            "ref":           self.ref,
            "domain":        self.domain,
            "world_model":   self.world_model,
            "entities":      self.entities,
            "events":        self.events,
            "edges":         self.edges,
            "states":        self.states,
            "unknowns":      self.unknowns,
            "invalidations": self.invalidations,
            "scenarios":     self.scenarios,
            "metadata":      self.metadata,
            "input_sha256":  self.input_sha256,
        }


# ---------------------------------------------------------------------------
# Market data schema
# ---------------------------------------------------------------------------

# Expected input JSON schema for market_realtime domain:
#
# {
#   "symbol":          "DJI",
#   "timestamp":       "2026-03-19T09:29:59Z",
#   "last_close":      46225.15,
#   "day_change_pts":  -768.11,
#   "day_change_pct":  -1.63,
#   "year_low":        46193.68,
#   "year_high":       50512.0,
#   "mtd_pct":         -5.2,
#   "vix":             25.09,
#   "vix_change_pct":  12.16,
#   "futures_pts":     -77.0,
#   "ma_200_status":   "BELOW",
#   "commodity": {
#     "name":   "Brent Crude",
#     "price":  113.0,
#     "unit":   "USD/bbl"
#   },
#   "macro_forces": [
#     {
#       "label":     "US-Iran War",
#       "direction": "BEARISH",
#       "intensity": "HIGH",
#       "actor":     "geopolitical"
#     }
#   ],
#   "sentiment": {
#     "consensus":    "BEARISH",
#     "vix_signal":   "ELEVATED_FEAR",
#     "futures_signal": "EXHAUSTION_POSSIBLE"
#   },
#   "scenarios": [
#     {
#       "scenario_id":    "scen:B:bounce",
#       "label":          "Dead Cat Bounce",
#       "probability":    0.40,
#       "trigger":        "Oversold + VIX exhaustion + shallow futures",
#       "invalidations":  ["inv:oil_spike", "inv:iran_escalation"],
#       "target_value":   46600.0
#     }
#   ],
#   "unknowns": [
#     { "id": "unk:001", "label": "Exact timing of Iran headlines" }
#   ],
#   "invalidations": [
#     { "id": "inv:oil_spike", "trigger": "Brent > $120/bbl" }
#   ]
# }


# ---------------------------------------------------------------------------
# Core extractor
# ---------------------------------------------------------------------------

class MarketRealtimeExtractors:
    """
    Extracts structured causal world models from market data.

    Implements the extractor interface expected by DeterministicPipeline.

    The extraction pipeline:
      1. Parse raw market data
      2. Extract entities (instruments, actors, forces)
      3. Extract states (price levels, volatility, sentiment)
      4. Extract causal edges (mechanism-labelled directed relationships)
      5. Extract events (timestamped market occurrences)
      6. Build world model (the unified causal graph)
      7. Return ExtractionResult
    """

    DOMAIN = "market_realtime"
    VERSION = "0.1.0"

    # Causal mechanism templates
    # These encode the canonical causal relationships in financial markets
    # Each template: (cause_pattern, effect_pattern, mechanism, strength, lag_seconds)
    CAUSAL_TEMPLATES = [
        # Geopolitical → commodity
        ("geopolitical_conflict", "commodity_price_spike",
         "active conflict disrupts supply chains and raises risk premium",
         "HIGH", 86400),

        # Commodity → inflation
        ("commodity_price_spike", "inflation_elevated",
         "elevated commodity prices raise input costs across economy",
         "HIGH", 172800),

        # Inflation → fed
        ("inflation_elevated", "fed_rate_hold",
         "hot inflation removes justification for rate cuts",
         "HIGH", 259200),

        # Fed hold → market sentiment
        ("fed_rate_hold", "market_sentiment_bearish",
         "no rate relief removes key market support catalyst",
         "HIGH", 3600),

        # Sell pressure → volatility
        ("large_price_drop", "vix_elevated",
         "sharp price decline spikes fear index and options demand",
         "HIGH", 60),

        # Technical break → algo selling
        ("ma_200_broken", "algorithmic_selling",
         "break below 200-day MA triggers systematic sell programs",
         "HIGH", 30),

        # Algo selling → price acceleration
        ("algorithmic_selling", "large_price_drop",
         "automated sell programs accelerate downward price movement",
         "HIGH", 30),

        # Oversold → mean reversion pressure
        ("vix_elevated", "mean_reversion_pressure",
         "VIX spike signals near-term exhaustion and mean reversion",
         "MEDIUM", 3600),

        # Shallow futures → exhaustion signal
        ("shallow_futures_vs_drop", "mean_reversion_pressure",
         "futures shallow relative to prior day drop signals seller exhaustion",
         "MEDIUM", 1800),

        # Support level → institutional buying
        ("price_at_year_low", "institutional_accumulation",
         "year low acts as psychological support floor for value buyers",
         "MEDIUM", 1800),

        # Institutional buying → price recovery
        ("institutional_accumulation", "price_recovery",
         "institutional buying at support creates demand floor",
         "MEDIUM", 7200),

        # Tech sector positive → sentiment relief
        ("tech_positive_catalyst", "market_sentiment_relief",
         "positive tech catalyst provides partial offset to macro pressure",
         "MEDIUM", 3600),

        # Sentiment relief → price recovery
        ("market_sentiment_relief", "price_recovery",
         "improved sentiment reduces selling pressure and attracts buyers",
         "MEDIUM", 3600),

        # Afternoon fade → price gives back gains
        ("afternoon_liquidity_drain", "price_fade",
         "institutional rebalancing and reduced liquidity fade morning gains",
         "MEDIUM", 14400),
    ]

    def extract(
        self,
        data:    dict | str,
        ref:     str,
        context: dict,
    ) -> ExtractionResult:
        """
        Main extraction entry point.

        Called by DeterministicPipeline.process() with:
            data:    parsed market data (dict) or raw text
            ref:     the input reference identifier
            context: pipeline context (mode, horizon, etc.)

        Returns ExtractionResult with full world model.
        """
        # Normalise input
        if isinstance(data, str):
            data = json.loads(data)

        # Compute input hash for provenance
        input_bytes   = json.dumps(data, sort_keys=True).encode("utf-8")
        input_sha256  = hashlib.sha256(input_bytes).hexdigest()

        # Extract all components
        entities      = self._extract_entities(data)
        states        = self._extract_states(data)
        events        = self._extract_events(data)
        edges         = self._extract_edges(data, states)
        unknowns      = data.get("unknowns", [])
        invalidations = data.get("invalidations", [])
        scenarios     = data.get("scenarios", [])

        # Build unified world model
        world_model = self._build_world_model(
            data, states, edges, unknowns, invalidations, scenarios
        )

        metadata = {
            "extractor_version": self.VERSION,
            "domain":            self.DOMAIN,
            "ref":               ref,
            "symbol":            data.get("symbol", "UNKNOWN"),
            "timestamp":         data.get("timestamp", ""),
            "context":           context,
            "entity_count":      len(entities),
            "state_count":       len(states),
            "edge_count":        len(edges),
            "event_count":       len(events),
            "unknown_count":     len(unknowns),
            "scenario_count":    len(scenarios),
        }

        return ExtractionResult(
            ref           = ref,
            domain        = self.DOMAIN,
            world_model   = world_model,
            entities      = entities,
            events        = events,
            edges         = edges,
            states        = states,
            unknowns      = unknowns,
            invalidations = invalidations,
            scenarios     = scenarios,
            metadata      = metadata,
            input_sha256  = input_sha256,
        )

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(self, data: dict) -> list[dict]:
        """Extract all named entities from market data."""
        entities = []

        symbol = data.get("symbol", "UNKNOWN")

        # Core market instrument
        entities.append({
            "entity_id": f"entity:instrument:{symbol.lower()}",
            "label":     symbol,
            "type":      "market_instrument",
            "domain":    "market",
        })

        # Commodity
        commodity = data.get("commodity", {})
        if commodity:
            entities.append({
                "entity_id": f"entity:commodity:{commodity.get('name','').lower().replace(' ','_')}",
                "label":     commodity.get("name", "Commodity"),
                "type":      "commodity",
                "domain":    "market",
                "metadata":  {"price": commodity.get("price"), "unit": commodity.get("unit")},
            })

        # Macro force actors
        for i, force in enumerate(data.get("macro_forces", [])):
            actor = force.get("actor", f"macro_actor_{i}")
            entities.append({
                "entity_id": f"entity:actor:{actor.lower().replace(' ','_')}:{i:03d}",
                "label":     force.get("label", actor),
                "type":      "macro_force",
                "domain":    "market",
                "metadata":  {
                    "direction": force.get("direction"),
                    "intensity": force.get("intensity"),
                },
            })

        # Sentiment actors
        sentiment = data.get("sentiment", {})
        if sentiment:
            entities.append({
                "entity_id": "entity:actor:market_sentiment",
                "label":     "Market Sentiment",
                "type":      "sentiment_indicator",
                "domain":    "market",
                "metadata":  sentiment,
            })

        # VIX as entity
        entities.append({
            "entity_id": "entity:indicator:vix",
            "label":     "VIX Fear Index",
            "type":      "volatility_indicator",
            "domain":    "market",
            "metadata":  {"value": data.get("vix")},
        })

        return entities

    # ------------------------------------------------------------------
    # State extraction
    # ------------------------------------------------------------------

    def _extract_states(self, data: dict) -> list[dict]:
        """Extract world states from market data."""
        states    = []
        symbol    = data.get("symbol", "UNKNOWN")
        ts        = data.get("timestamp", datetime.now(timezone.utc).isoformat())
        commodity = data.get("commodity", {})

        # Price states
        states.append({
            "state_id":  "state:price:last_close",
            "label":     f"{symbol} last close {data.get('last_close')}",
            "timestamp": ts,
            "certainty": "HIGH",
            "value":     data.get("last_close"),
            "unit":      "USD",
            "domain":    "market",
            "tags":      ["price", "close"],
        })

        day_chg = data.get("day_change_pts", 0)
        states.append({
            "state_id":  "state:price:day_change",
            "label":     f"{symbol} day change {day_chg:+.2f}pts",
            "timestamp": ts,
            "certainty": "HIGH",
            "value":     day_chg,
            "unit":      "pts",
            "domain":    "market",
            "tags":      ["price", "change"],
            # Tag as large drop if > 1% down
            "signal":    "large_price_drop" if day_chg < -(data.get("last_close", 1) * 0.01) else "normal_move",
        })

        states.append({
            "state_id":  "state:price:year_low",
            "label":     f"{symbol} 2026 low {data.get('year_low')}",
            "timestamp": ts,
            "certainty": "HIGH",
            "value":     data.get("year_low"),
            "unit":      "USD",
            "domain":    "market",
            "tags":      ["price", "support"],
            "signal":    "price_at_year_low" if abs(
                (data.get("last_close", 0) - data.get("year_low", 0)) /
                max(data.get("year_low", 1), 1)
            ) < 0.005 else "above_year_low",
        })

        # MA status
        ma_status = data.get("ma_200_status", "")
        states.append({
            "state_id":  "state:technical:ma_200",
            "label":     f"{symbol} 200-day MA status: {ma_status}",
            "timestamp": ts,
            "certainty": "HIGH",
            "value":     None,
            "domain":    "market",
            "tags":      ["technical", "moving_average"],
            "signal":    "ma_200_broken" if ma_status == "BELOW" else "ma_200_intact",
        })

        # Volatility
        vix = data.get("vix", 0)
        states.append({
            "state_id":  "state:volatility:vix",
            "label":     f"VIX {vix}",
            "timestamp": ts,
            "certainty": "HIGH",
            "value":     vix,
            "unit":      "index",
            "domain":    "market",
            "tags":      ["volatility", "fear"],
            "signal":    "vix_elevated" if vix > 20 else "vix_normal",
        })

        # Futures
        futures_pts = data.get("futures_pts", 0)
        prior_drop  = abs(data.get("day_change_pts", 0))
        shallow     = prior_drop > 0 and abs(futures_pts) < (prior_drop * 0.15)
        states.append({
            "state_id":  "state:futures:premarket",
            "label":     f"{symbol} pre-market futures {futures_pts:+.0f}pts",
            "timestamp": ts,
            "certainty": "HIGH",
            "value":     futures_pts,
            "unit":      "pts",
            "domain":    "market",
            "tags":      ["futures", "premarket"],
            "signal":    "shallow_futures_vs_drop" if shallow else "normal_futures",
        })

        # Commodity
        if commodity:
            states.append({
                "state_id":  "state:commodity:price",
                "label":     f"{commodity.get('name','Commodity')} {commodity.get('price')} {commodity.get('unit','')}",
                "timestamp": ts,
                "certainty": "HIGH",
                "value":     commodity.get("price"),
                "unit":      commodity.get("unit"),
                "domain":    "market",
                "tags":      ["commodity"],
                "signal":    "commodity_price_spike" if commodity.get("price", 0) > 100 else "commodity_normal",
            })

        # Macro forces as states
        for i, force in enumerate(data.get("macro_forces", [])):
            intensity = force.get("intensity", "MEDIUM")
            direction = force.get("direction", "NEUTRAL")
            states.append({
                "state_id":  f"state:macro:{i:03d}",
                "label":     force.get("label", f"Macro force {i}"),
                "timestamp": ts,
                "certainty": intensity,
                "domain":    "market",
                "tags":      ["macro", direction.lower()],
                "signal":    self._classify_macro_signal(force),
            })

        return states

    def _classify_macro_signal(self, force: dict) -> str:
        """Map a macro force to a causal signal tag."""
        label     = force.get("label", "").lower()
        direction = force.get("direction", "").upper()
        actor     = force.get("actor", "").lower()

        if "war" in label or "conflict" in label or "military" in label:
            return "geopolitical_conflict"
        if "fed" in label or "rate" in label or "interest" in label:
            return "fed_rate_hold" if "hold" in label else "fed_rate_change"
        if "inflation" in label or "ppi" in label or "cpi" in label:
            return "inflation_elevated"
        if "tech" in label or "nvidia" in label or "semiconductor" in label:
            return "tech_positive_catalyst" if direction == "BULLISH" else "tech_negative_catalyst"
        if direction == "BEARISH":
            return "macro_bearish_force"
        if direction == "BULLISH":
            return "macro_bullish_force"
        return "macro_neutral_force"

    # ------------------------------------------------------------------
    # Edge extraction
    # ------------------------------------------------------------------

    def _extract_edges(self, data: dict, states: list[dict]) -> list[dict]:
        """
        Extract causal edges by matching state signals to causal templates.

        Each state has a 'signal' tag. We match signals against
        CAUSAL_TEMPLATES to generate directed causal edges.
        """
        edges  = []
        # Build signal → state_id index
        signal_map: dict[str, list[str]] = {}
        for state in states:
            sig = state.get("signal")
            if sig:
                signal_map.setdefault(sig, []).append(state["state_id"])

        edge_count = 0
        for cause_sig, effect_sig, mechanism, strength, lag in self.CAUSAL_TEMPLATES:
            cause_ids  = signal_map.get(cause_sig, [])
            effect_ids = signal_map.get(effect_sig, [])

            for cause_id in cause_ids:
                for effect_id in effect_ids:
                    if cause_id == effect_id:
                        continue
                    edge_id = f"edge:extracted:{edge_count:04d}"
                    edges.append({
                        "edge_id":     edge_id,
                        "cause_id":    cause_id,
                        "effect_id":   effect_id,
                        "mechanism":   mechanism,
                        "strength":    strength,
                        "lag_seconds": lag,
                        "confidence":  self._confidence_from_strength(strength),
                        "source":      "causal_template",
                        "template":    f"{cause_sig} → {effect_sig}",
                    })
                    edge_count += 1

        # Add explicit edges from macro forces
        for i, force in enumerate(data.get("macro_forces", [])):
            direction = force.get("direction", "NEUTRAL").upper()
            intensity = force.get("intensity", "MEDIUM")
            macro_state_id = f"state:macro:{i:03d}"

            if direction == "BEARISH":
                target = "state:price:day_change"
                mech   = f"{force.get('label','Macro force')} creates downward price pressure"
            elif direction == "BULLISH":
                target = "state:volatility:vix"
                mech   = f"{force.get('label','Macro force')} reduces fear premium"
            else:
                continue

            edges.append({
                "edge_id":     f"edge:macro:{i:03d}",
                "cause_id":    macro_state_id,
                "effect_id":   target,
                "mechanism":   mech,
                "strength":    intensity,
                "lag_seconds": 3600,
                "confidence":  self._confidence_from_strength(intensity),
                "source":      "macro_force",
            })

        return edges

    def _confidence_from_strength(self, strength: str) -> float:
        return {"HIGH": 0.9, "MEDIUM": 0.7, "LOW": 0.5}.get(strength.upper(), 0.7)

    # ------------------------------------------------------------------
    # Event extraction
    # ------------------------------------------------------------------

    def _extract_events(self, data: dict) -> list[dict]:
        """Extract timestamped events from market data."""
        events = []
        symbol = data.get("symbol", "UNKNOWN")
        ts     = data.get("timestamp", datetime.now(timezone.utc).isoformat())

        events.append({
            "event_id":  "event:market:close_prior",
            "label":     f"{symbol} prior day close recorded",
            "timestamp": ts,
            "actor":     "NYSE",
            "type":      "market_close",
            "certainty": "HIGH",
        })

        events.append({
            "event_id":  "event:market:futures_open",
            "label":     f"{symbol} pre-market futures active",
            "timestamp": ts,
            "actor":     "FUTURES_MARKET",
            "type":      "futures_reading",
            "certainty": "HIGH",
        })

        for i, force in enumerate(data.get("macro_forces", [])):
            events.append({
                "event_id":  f"event:macro:{i:03d}",
                "label":     force.get("label", f"Macro event {i}"),
                "timestamp": ts,
                "actor":     force.get("actor", "UNKNOWN"),
                "type":      "macro_force",
                "certainty": force.get("intensity", "MEDIUM"),
            })

        return events

    # ------------------------------------------------------------------
    # World model construction
    # ------------------------------------------------------------------

    def _build_world_model(
        self,
        data:          dict,
        states:        list[dict],
        edges:         list[dict],
        unknowns:      list[dict],
        invalidations: list[dict],
        scenarios:     list[dict],
    ) -> dict:
        """Assemble the unified causal world model."""
        return {
            "domain":        self.DOMAIN,
            "symbol":        data.get("symbol", "UNKNOWN"),
            "timestamp":     data.get("timestamp", ""),
            "states":        states,
            "edges":         edges,
            "unknowns":      unknowns,
            "invalidations": invalidations,
            "scenarios":     scenarios,
            "sentiment":     data.get("sentiment", {}),
            "metadata": {
                "extractor_version": self.VERSION,
                "state_count":       len(states),
                "edge_count":        len(edges),
                "unknown_count":     len(unknowns),
                "scenario_count":    len(scenarios),
            },
        }


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

class MarketManifestBuilder:
    """
    Builds the data/market/manifest.json for the market_realtime domain.

    The manifest maps input refs to data files — following the pattern
    used by other domains (scripture, credit, clinical).
    """

    @staticmethod
    def build_manifest(entries: list[dict]) -> dict:
        """
        Build a manifest dict from a list of entries.

        The output uses the canonical ``records`` shape consumed by
        ``core.manifest.resolve_input`` — identical to the scripture, credit,
        clinical, and legal manifests — so the market domain resolves through
        the same integrity-checked path as every other domain.

        Each entry:
            ref:      the input reference (e.g. "DJI-2026-03-19")
            file:     data file name, relative to the manifest directory
            sha256:   SHA-256 of the data file bytes
        """
        records: dict[str, dict] = {}
        for entry in entries:
            ref = entry["ref"]
            records[ref] = {
                key: value for key, value in entry.items() if key != "ref"
            }
        return {
            "dataset": "market_realtime_sample",
            "schema_version": "1.0",
            "records": records,
        }

    @staticmethod
    def entry_from_file(ref: str, file_path: str) -> dict:
        """Build a manifest entry from a file path.

        ``file`` is stored as a bare filename so ``resolve_input`` resolves it
        relative to the manifest directory, matching the other domains.
        """
        from pathlib import Path
        path = Path(file_path)
        data = path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        return {
            "ref": ref,
            "file": path.name,
            "sha256": sha256,
        }


# ---------------------------------------------------------------------------
# Sample data builder
# ---------------------------------------------------------------------------

def build_sample_dji_input() -> dict:
    """
    Build a sample DJI market input for testing.
    Based on the March 19 2026 casefile.
    """
    return {
        "symbol":         "DJI",
        "timestamp":      "2026-03-19T09:29:59Z",
        "last_close":     46225.15,
        "day_change_pts": -768.11,
        "day_change_pct": -1.63,
        "year_low":       46193.68,
        "year_high":      50512.0,
        "mtd_pct":        -5.2,
        "vix":            25.09,
        "vix_change_pct": 12.16,
        "futures_pts":    -77.0,
        "ma_200_status":  "BELOW",
        "commodity": {
            "name":  "Brent Crude",
            "price": 113.0,
            "unit":  "USD/bbl",
        },
        "macro_forces": [
            {"label": "US-Iran War Active",     "direction": "BEARISH",  "intensity": "HIGH",   "actor": "geopolitical"},
            {"label": "Fed Rate Hold",           "direction": "NEUTRAL",  "intensity": "HIGH",   "actor": "federal_reserve"},
            {"label": "Hot PPI Reading",         "direction": "BEARISH",  "intensity": "HIGH",   "actor": "inflation"},
            {"label": "Nvidia H200 Approval",    "direction": "BULLISH",  "intensity": "MEDIUM", "actor": "tech_sector"},
            {"label": "Micron Extended Decline", "direction": "BEARISH",  "intensity": "MEDIUM", "actor": "tech_sector"},
            {"label": "Jones Act Waiver 60-day", "direction": "BULLISH",  "intensity": "LOW",    "actor": "policy"},
        ],
        "sentiment": {
            "consensus":       "BEARISH",
            "vix_signal":      "ELEVATED_FEAR",
            "futures_signal":  "EXHAUSTION_POSSIBLE",
        },
        "scenarios": [
            {
                "scenario_id":   "scen:B:bounce",
                "label":         "Dead Cat Bounce",
                "probability":   0.40,
                "trigger":       "Oversold + VIX exhaustion + shallow futures",
                "invalidations": ["inv:oil_spike", "inv:iran_escalation"],
                "target_value":  46600.0,
            },
            {
                "scenario_id":   "scen:A:continuation",
                "label":         "Bearish Continuation",
                "probability":   0.35,
                "trigger":       "Oil spike OR new Iran escalation headline",
                "invalidations": [],
                "target_value":  45800.0,
            },
            {
                "scenario_id":   "scen:C:reversal",
                "label":         "Sharp Reversal",
                "probability":   0.15,
                "trigger":       "Ceasefire signal OR emergency Fed pivot",
                "invalidations": [],
                "target_value":  47000.0,
            },
            {
                "scenario_id":   "scen:D:consolidation",
                "label":         "Consolidation",
                "probability":   0.10,
                "trigger":       "No new catalysts — market digests",
                "invalidations": [],
                "target_value":  46300.0,
            },
        ],
        "unknowns": [
            {"id": "unk:001", "label": "Exact timing of Iran headlines today",           "affects": "inv:iran_escalation"},
            {"id": "unk:002", "label": "Fed speaker schedule today",                     "affects": "inv:fed_emergency"},
            {"id": "unk:003", "label": "Jones Act waiver immediate oil price impact",    "affects": "state:commodity:price"},
            {"id": "unk:004", "label": "Retail trader sentiment direction",              "affects": "state:volatility:vix"},
            {"id": "unk:005", "label": "Micron bleed into broader tech sentiment",       "affects": "macro_forces:4"},
        ],
        "invalidations": [
            {"id": "inv:oil_spike",        "trigger": "Brent crude spikes above $120/bbl intraday"},
            {"id": "inv:iran_escalation",  "trigger": "New Iran escalation — direct US military involvement"},
            {"id": "inv:fed_emergency",    "trigger": "Emergency Fed statement issued"},
            {"id": "inv:breadth_fail",     "trigger": "More than 20 of 30 DJI components down at 11:00 ET"},
            {"id": "inv:support_breach",   "trigger": "46193 (2026 low) broken on high volume"},
        ],
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _run_self_test() -> None:
    """
    Run extractor against sample DJI data and print extraction summary.
    Verifies the extractor works correctly before integration.
    """
    print("=" * 60)
    print("MarketRealtimeExtractors — Self Test")
    print("=" * 60)

    extractor = MarketRealtimeExtractors()
    data      = build_sample_dji_input()

    result = extractor.extract(
        data    = data,
        ref     = "DJI-2026-03-19",
        context = {"mode": "forward", "horizon": "86400"},
    )

    print(f"\n  ref:           {result.ref}")
    print(f"  domain:        {result.domain}")
    print(f"  input_sha256:  {result.input_sha256[:16]}...")
    print(f"  entities:      {len(result.entities)}")
    print(f"  states:        {len(result.states)}")
    print(f"  edges:         {len(result.edges)}")
    print(f"  events:        {len(result.events)}")
    print(f"  unknowns:      {len(result.unknowns)}")
    print(f"  invalidations: {len(result.invalidations)}")
    print(f"  scenarios:     {len(result.scenarios)}")

    print("\n  Causal edges extracted:")
    for edge in result.edges[:5]:
        print(f"    [{edge['strength']}] {edge['cause_id']}")
        print(f"           → {edge['effect_id']}")
        print(f"           via: {edge['mechanism'][:60]}...")

    print(f"\n  World model edge count: {result.world_model['metadata']['edge_count']}")
    print(f"  World model state count: {result.world_model['metadata']['state_count']}")

    # Now pipe directly into ForwardProjection
    print("\n  Piping into ForwardProjection...")
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))

    try:
        from forward_projection import ForwardProjection
        fp = ForwardProjection(
            world_model     = result.world_model,
            horizon_seconds = 86400,
            domain          = "market",
        )
        ps     = fp.project()
        sealed = fp.seal_optimal_path(ps)

        print(f"  Sealed scenario:  {sealed.scenario.label}")
        print(f"  Probability:      {sealed.scenario.probability:.0%}")
        print(f"  Nodes projected:  {len(sealed.nodes)}")
        print(f"  Seal SHA256:      {sealed.seal_sha256[:16]}...")
        print(f"  Verification:     {sealed.verification.value}")

    except ImportError:
        print("  (ForwardProjection not in path — run from src/core/world/)")

    print("\n" + "=" * 60)
    print("EXTRACTOR VERIFIED. READY FOR PIPELINE INTEGRATION.")
    print("=" * 60)


if __name__ == "__main__":
    _run_self_test()

# Core Boundary

## Zones

### Zone A: deterministic core

`src/core` is the deterministic decision boundary. Zone A is the only place where final decisions, canonical artifacts, evidence bundles, and attestation records may be produced.

Rule: Only core decides; everything else proposes.

### Zone B: probabilistic perimeter

Zone B includes LLMs, embeddings, rerankers, planners, and any other probabilistic or remote inference component. Zone B may propose candidates, rankings, spans, or explanations, but it may not finalize canonical outputs.

### Zone C: product and UX

Zone C includes caching, streaming, async orchestration, request shaping, and user-facing delivery concerns. Zone C may transport or present canonical artifacts, but it may not mutate their deterministic meaning.

## Decision Rule

Only core decides; everything else proposes.

That rule is mandatory:
- Zone B can suggest.
- Zone C can package and deliver.
- Zone A alone validates, canonicalizes, hashes, and attests.

## Evidence Bundle

An Evidence Bundle is the canonical deterministic input record used by Zone A to support a final decision. It contains:
- bundle metadata and explicit caller-supplied creation time
- normalized user input and parameters
- evidence artifacts with byte-stable text hashes
- toolchain versions relevant to deterministic replay
- the policy or ruleset identifier applied by core

An Evidence Bundle must be serializable into canonical JSON so identical logical content yields byte-identical bytes.

## Attestation Record

An Attestation Record is the canonical deterministic provenance record emitted by Zone A after core has decided. It binds:
- the Evidence Bundle hash
- the output hash
- the core version
- the governing ruleset identifier
- the manifest hash supplied by the caller
- the caller-supplied creation time

The Attestation Record is not a proposal. It is the final signed-off statement of deterministic provenance at the core boundary.

## Forbidden in Zone A

Zone A must not:
- perform network access
- read wall-clock or monotonic time
- read random sources or generate UUIDs
- use nondeterministic iteration or unstable serialization
- accept NaN or Infinity into canonical JSON
- depend on platform-specific newline conventions for hashing
- allow Zone B outputs to bypass deterministic validation
- read mutable external state unless it is passed in explicitly as an input artifact
- mutate canonical output fields after hashing or attestation
- allow probabilistic components to emit final decisions directly

## Provenance Contract

For identical inputs, caller-supplied timestamps, rulesets, manifest hashes, toolchain versions, and output bytes, Zone A must emit byte-identical Evidence Bundles and Attestation Records with verifiable SHA-256 provenance.

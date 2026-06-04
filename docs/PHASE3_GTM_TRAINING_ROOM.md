# IOTA VERBUM Phase 3 GTM Training Room

Iota Verbum is positioned as a verifier-governed training room for external
LLMs. A user brings a model, pays for a sealed benchmark run, then optionally
pays for an Iota discipline loop that retries the model under deterministic
verifier feedback.

The product boundary is fixed:

- the external model is the proposer, or inner narrator;
- Iota Verbum is the verifier, or outer conscience;
- the proposer never becomes the verifier;
- accepted improvements are sealed through doctrine context, trust chain, and
  ledger artifacts.

The Phase 3 addendum seals doctrine constants in `SEALED_DOCTRINE` and carries
that context through the verifier, diagnostic loop, session ledger, and trust
chain. The demo surface at `demo/iota_verbum_e2e.html` visualizes each proposed
claim-graph transition before and after verifier judgment.

## Paid Wrapper

The first production wrapper is `scripts/phase3_training_room_wrapper.py`.
It does not call a model unless `--allow-live-model` is explicitly present.

The wrapper has two service boundaries:

1. Benchmark test: run the customer's model once with the existing Claude or
   DeepSeek CUC runner and keep the failed or accepted `model_delta.json` plus
   `gap_report.json` as the sealed baseline.
2. Iota training: point the wrapper at that baseline, run bounded diagnostic
   retry passes, preserve the best verifier state with the no-regression guard,
   and emit a scorecard.

Example score-only or planning run:

```powershell
python scripts/phase3_training_room_wrapper.py `
  --provider deepseek `
  --case-id CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT `
  --params-json benchmark/cuc_v5a_candidate_params.json `
  --baseline-dir cuc-results/deepseek_v4_live_single_case `
  --output-dir cuc-results/phase3_training_room/deepseek_demo `
  --max-training-passes 1
```

Because `--allow-live-model` is omitted, the command writes a deterministic
training plan and scorecard without spending API budget.

Live training run:

```powershell
python scripts/phase3_training_room_wrapper.py `
  --provider deepseek `
  --case-id CUCV5A-GROUNDING-02-CONFLICT-RECONCILIATION-SECURITY-INCIDENT `
  --params-json benchmark/cuc_v5a_candidate_params.json `
  --baseline-dir cuc-results/deepseek_v4_live_single_case `
  --output-dir cuc-results/phase3_training_room/deepseek_demo `
  --max-training-passes 3 `
  --allow-live-model `
  --model deepseek-v4-pro `
  --fallback-model ""
```

The scorecard records:

- baseline acceptance, similarity, verifier reason families, and artifact paths;
- every training pass, including whether the retry was called and accepted;
- best candidate selected by `accepted > similarity > fewer verifier reasons`;
- no-regression handoff paths for the next baseline;
- ledger commit metadata when the accepted retry seals.

Accepted retry ledgers seal the current `MANIFEST.sha256` digest and must pass
strict-manifest replay. Reusing an output directory clears attempt-specific
retry artifacts first, so an accepted rerun cannot retain a stale failure file
from an earlier API or authentication error.

## Customer Evidence Package

Use `scripts/build_phase3_customer_evidence.py` after a controlled accepted
session. The builder validates the scorecard, diagnostic repair, no-regression
selection, ledger hashes, and strict replay against the exact sealed repository
manifest. It also proves that the sealed manifest is the `MANIFEST.sha256`
stored at the named repository commit and that the packaged retry delta exactly
matches the delta committed in the packaged ledger output under canonical JSON
byte comparison. The builder then writes a customer-facing Markdown report, a
machine-readable report, a canonical-JSON baseline and retry audit trail, and a
byte-exact replayable ledger.

The package deliberately preserves the proof boundary: it demonstrates one
verified in-context diagnostic-repair session. It does not claim fine-tuning,
persistent weight changes, or broad benchmark improvement.

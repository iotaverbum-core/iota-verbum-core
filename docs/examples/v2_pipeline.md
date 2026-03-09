# V2 Pipeline Example

```python
from core.engine import run_narrative_intelligence_v2
from proposal.evidence_pack import build_evidence_pack

pack, _ = build_evidence_pack("data/demo_cases/timeline_breach_chain")
result = run_narrative_intelligence_v2(pack, {"mode": "deterministic", "schema_version": "2.0"})
print(result["ledger"]["bundle_sha256"])
```

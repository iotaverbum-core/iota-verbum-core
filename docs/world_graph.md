# Canonical World Graph V2

`world_graph_v2` is the system of record for reasoning.

Fields:
- `entities`
- `events`
- `relations`
- `claims`
- `unknowns`
- `conflicts`
- `graph_version`
- `graph_sha256`

All downstream reasoning reads from this graph snapshot.

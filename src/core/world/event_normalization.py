from __future__ import annotations


def normalize_events(events: list[dict]) -> list[dict]:
    normalized = []
    for event in events:
        description = event["description"]
        lowered = description.lower()
        event_type = "other"
        for token, detected in (
            ("fraud", "fraud_signal"),
            ("approved", "approval"),
            ("transferred", "transfer"),
            ("escalated", "escalation"),
            ("restored", "restoration"),
            ("failed", "failure"),
        ):
            if token in lowered:
                event_type = detected
                break
        normalized.append({**event, "event_type": event_type})
    return sorted(normalized, key=lambda e: e["event_id"])

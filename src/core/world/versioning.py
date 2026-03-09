from __future__ import annotations


def next_version(previous: str | None) -> str:
    if not previous:
        return "2.0.0"
    major, minor, patch = (int(v) for v in previous.split("."))
    return f"{major}.{minor}.{patch + 1}"

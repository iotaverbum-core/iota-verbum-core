from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GapReport:
    matching_fields: int = 0
    missing_fields: list[str] = field(default_factory=list)
    extra_fields: list[str] = field(default_factory=list)
    type_mismatches: list[dict[str, str]] = field(default_factory=list)
    value_differences: list[dict[str, Any]] = field(default_factory=list)

    @property
    def compared_fields(self) -> int:
        return (
            self.matching_fields
            + len(self.missing_fields)
            + len(self.extra_fields)
            + len(self.type_mismatches)
            + len(self.value_differences)
        )

    @property
    def similarity_score(self) -> float:
        if self.compared_fields == 0:
            return 100.0
        return round((self.matching_fields / self.compared_fields) * 100.0, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "matching_fields": self.matching_fields,
                "compared_fields": self.compared_fields,
                "similarity_score_percent": self.similarity_score,
            },
            "missing_fields": sorted(self.missing_fields),
            "extra_fields": sorted(self.extra_fields),
            "type_mismatches": sorted(
                self.type_mismatches,
                key=lambda item: item["path"],
            ),
            "value_differences": sorted(
                self.value_differences,
                key=lambda item: item["path"],
            ),
        }


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def compare_deltas(model_delta: Any, gold_delta: Any) -> GapReport:
    report = GapReport()
    _compare_value(model_delta, gold_delta, "$", report)
    return report


def _compare_value(
    model_value: Any,
    gold_value: Any,
    path: str,
    report: GapReport,
) -> None:
    model_kind = _kind(model_value)
    gold_kind = _kind(gold_value)
    if model_kind != gold_kind:
        report.type_mismatches.append(
            {
                "path": path,
                "model_type": model_kind,
                "gold_type": gold_kind,
            }
        )
        return

    if isinstance(gold_value, dict):
        _compare_dict(model_value, gold_value, path, report)
        return
    if isinstance(gold_value, list):
        _compare_list(model_value, gold_value, path, report)
        return
    if model_value == gold_value:
        report.matching_fields += 1
        return
    report.value_differences.append(
        {
            "path": path,
            "model_value": model_value,
            "gold_value": gold_value,
        }
    )


def _compare_dict(
    model_value: dict[str, Any],
    gold_value: dict[str, Any],
    path: str,
    report: GapReport,
) -> None:
    model_keys = set(model_value)
    gold_keys = set(gold_value)
    for key in sorted(gold_keys - model_keys):
        report.missing_fields.extend(_leaf_paths(gold_value[key], _join(path, key)))
    for key in sorted(model_keys - gold_keys):
        report.extra_fields.extend(_leaf_paths(model_value[key], _join(path, key)))
    for key in sorted(model_keys & gold_keys):
        _compare_value(model_value[key], gold_value[key], _join(path, key), report)


def _compare_list(
    model_value: list[Any],
    gold_value: list[Any],
    path: str,
    report: GapReport,
) -> None:
    match_key = _list_match_key(model_value, gold_value)
    if match_key is not None:
        _compare_list_by_key(model_value, gold_value, match_key, path, report)
        return
    if _can_compare_as_string_set(model_value, gold_value):
        _compare_string_set(model_value, gold_value, path, report)
        return

    shared_length = min(len(model_value), len(gold_value))
    for index in range(shared_length):
        _compare_value(
            model_value[index],
            gold_value[index],
            f"{path}[{index}]",
            report,
        )
    for index in range(shared_length, len(gold_value)):
        report.missing_fields.extend(_leaf_paths(gold_value[index], f"{path}[{index}]"))
    for index in range(shared_length, len(model_value)):
        report.extra_fields.extend(_leaf_paths(model_value[index], f"{path}[{index}]"))


def _list_match_key(model_value: list[Any], gold_value: list[Any]) -> str | None:
    values = model_value + gold_value
    if not values:
        return None
    for key in ("id", "scenario_id"):
        if not all(
            isinstance(item, dict) and isinstance(item.get(key), str)
            for item in values
        ):
            continue
        model_keys = [item[key] for item in model_value]
        gold_keys = [item[key] for item in gold_value]
        if len(model_keys) == len(set(model_keys)) and len(gold_keys) == len(
            set(gold_keys)
        ):
            return key
    return None


def _can_compare_as_string_set(model_value: list[Any], gold_value: list[Any]) -> bool:
    values = model_value + gold_value
    return bool(values) and all(isinstance(item, str) for item in values)


def _compare_string_set(
    model_value: list[str],
    gold_value: list[str],
    path: str,
    report: GapReport,
) -> None:
    model_set = set(model_value)
    gold_set = set(gold_value)
    for item in sorted(gold_set - model_set):
        report.missing_fields.append(f"{path}[value={item!r}]")
    for item in sorted(model_set - gold_set):
        report.extra_fields.append(f"{path}[value={item!r}]")
    report.matching_fields += len(model_set & gold_set)


def _compare_list_by_key(
    model_value: list[dict[str, Any]],
    gold_value: list[dict[str, Any]],
    key_name: str,
    path: str,
    report: GapReport,
) -> None:
    model_by_id = {item[key_name]: item for item in model_value}
    gold_by_id = {item[key_name]: item for item in gold_value}
    model_ids = set(model_by_id)
    gold_ids = set(gold_by_id)
    for item_id in sorted(gold_ids - model_ids):
        report.missing_fields.extend(
            _leaf_paths(gold_by_id[item_id], f"{path}[{key_name}={item_id!r}]")
        )
    for item_id in sorted(model_ids - gold_ids):
        report.extra_fields.extend(
            _leaf_paths(model_by_id[item_id], f"{path}[{key_name}={item_id!r}]")
        )
    for item_id in sorted(model_ids & gold_ids):
        _compare_value(
            model_by_id[item_id],
            gold_by_id[item_id],
            f"{path}[{key_name}={item_id!r}]",
            report,
        )


def _leaf_paths(value: Any, path: str) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return [path]
        paths: list[str] = []
        for key in sorted(value):
            paths.extend(_leaf_paths(value[key], _join(path, key)))
        return paths
    if isinstance(value, list):
        if not value:
            return [path]
        paths = []
        for index, item in enumerate(value):
            paths.extend(_leaf_paths(item, f"{path}[{index}]"))
        return paths
    return [path]


def _join(path: str, key: str) -> str:
    if key.replace("_", "").replace("-", "").isalnum():
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key, ensure_ascii=False)}]"


def _kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a model RevisionDelta JSON file against a gold delta.",
    )
    parser.add_argument("--model-delta", required=True, type=Path)
    parser.add_argument("--gold-delta", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    model_delta = load_json(args.model_delta)
    gold_delta = load_json(args.gold_delta)
    report = compare_deltas(model_delta, gold_delta).to_dict()
    report["model_delta"] = str(args.model_delta)
    report["gold_delta"] = str(args.gold_delta)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


_TYPE_MAP = {
    "array": list,
    "boolean": bool,
    "integer": int,
    "null": type(None),
    "number": (int, float),
    "object": dict,
    "string": str,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_refs(schema: dict, root_schema: dict) -> dict:
    if isinstance(schema, dict):
        if "$ref" in schema:
            ref = schema["$ref"]
            if not ref.startswith("#/"):
                raise ValueError(f"unsupported schema ref: {ref}")
            target = root_schema
            for part in ref[2:].split("/"):
                target = target[part]
            return _resolve_refs(target, root_schema)
        return {
            key: _resolve_refs(value, root_schema)
            for key, value in schema.items()
            if key not in {"$schema", "$id"}
        }
    if isinstance(schema, list):
        return [_resolve_refs(item, root_schema) for item in schema]
    return schema


def _validate_type(instance, expected_type: str) -> bool:
    if expected_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected_type == "number":
        return (
            isinstance(instance, (int, float))
            and not isinstance(instance, bool)
        )
    return isinstance(instance, _TYPE_MAP[expected_type])


def _minimal_validate(
    instance, schema: dict, root_schema: dict, path: str = "$"
) -> None:
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"{path}: unsupported schema ref '{ref}'")
        target = root_schema
        for part in ref[2:].split("/"):
            target = target[part]
        _minimal_validate(instance, target, root_schema, path)
        return

    if "oneOf" in schema:
        errors = []
        for candidate in schema["oneOf"]:
            try:
                _minimal_validate(instance, candidate, root_schema, path)
                return
            except ValueError as exc:
                errors.append(str(exc))
        raise ValueError(f"{path}: did not match any allowed schema branch")

    schema_type = schema.get("type")
    if schema_type and not _validate_type(instance, schema_type):
        raise ValueError(f"{path}: expected {schema_type}")

    if "pattern" in schema and isinstance(instance, str):
        if re.match(schema["pattern"], instance) is None:
            raise ValueError(f"{path}: string does not match required pattern")

    if "enum" in schema and instance not in schema["enum"]:
        raise ValueError(f"{path}: value is not in enum")

    if "const" in schema and instance != schema["const"]:
        raise ValueError(f"{path}: value does not match const")

    if "minLength" in schema and isinstance(instance, str):
        if len(instance) < schema["minLength"]:
            raise ValueError(f"{path}: string shorter than minLength")

    if "minimum" in schema and isinstance(instance, (int, float)):
        if instance < schema["minimum"]:
            raise ValueError(f"{path}: number below minimum")

    if "minItems" in schema and isinstance(instance, list):
        if len(instance) < schema["minItems"]:
            raise ValueError(f"{path}: array shorter than minItems")

    if schema_type == "object":
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise ValueError(f"{path}: missing required property '{key}'")

        properties = schema.get("properties", {})
        pattern_properties = schema.get("patternProperties", {})
        allow_additional = schema.get("additionalProperties", True)

        for key, value in instance.items():
            matched = False
            if key in properties:
                _minimal_validate(value, properties[key], root_schema, f"{path}.{key}")
                matched = True
            for pattern, nested_schema in pattern_properties.items():
                if re.match(pattern, key):
                    _minimal_validate(
                        value,
                        nested_schema,
                        root_schema,
                        f"{path}.{key}",
                    )
                    matched = True
            if matched:
                continue
            if allow_additional is False:
                raise ValueError(f"{path}: unexpected property '{key}'")
            if isinstance(allow_additional, dict):
                _minimal_validate(value, allow_additional, root_schema, f"{path}.{key}")

    if schema_type == "array":
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, value in enumerate(instance):
                _minimal_validate(value, item_schema, root_schema, f"{path}[{index}]")


def validate(instance, schema_path: str | Path) -> None:
    schema_file = Path(schema_path)
    if not schema_file.is_absolute():
        schema_file = _repo_root() / schema_file

    raw_schema = json.loads(schema_file.read_text(encoding="utf-8"))
    if jsonschema is not None:
        validator = jsonschema.Draft202012Validator(raw_schema)
        errors = sorted(validator.iter_errors(instance), key=lambda err: err.path)
        if errors:
            first = errors[0]
            path = "$"
            if first.path:
                path = "$." + ".".join(str(part) for part in first.path)
            raise ValueError(f"{path}: {first.message}")
        return

    _minimal_validate(instance, raw_schema, raw_schema)

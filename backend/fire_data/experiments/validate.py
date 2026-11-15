"""Validator for the experiment configuration schema.

The validator implements the JSON Schema keywords used by
``research/experiment_config.schema.json``. It rejects a schema that uses a
keyword it does not implement, so a constraint cannot be declared and then
silently ignored.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fire_data.contract import BACKEND_ROOT

SCHEMA_PATH = BACKEND_ROOT / "research" / "experiment_config.schema.json"
EXAMPLES_DIR = BACKEND_ROOT / "research" / "examples"

ANNOTATIONS = {
    "$schema",
    "$id",
    "$comment",
    "$defs",
    "title",
    "description",
    "examples",
    "default",
}
APPLICATORS = {
    "$ref",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "properties",
    "items",
    "additionalProperties",
}
ASSERTIONS = {
    "type",
    "const",
    "enum",
    "required",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "pattern",
}
ALLOWED_KEYWORDS = ANNOTATIONS | APPLICATORS | ASSERTIONS


class SchemaError(ValueError):
    """The schema or an instance failed validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def load_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or SCHEMA_PATH
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise SchemaError(["schema root must be an object"])
    errors = unsupported_keywords(schema)
    if errors:
        raise SchemaError(errors)
    return schema


def unsupported_keywords(schema: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(schema, dict):
        unknown = sorted(set(schema) - ALLOWED_KEYWORDS)
        if unknown:
            errors.append(f"{path}: unsupported keywords {', '.join(unknown)}")
        for key, value in schema.items():
            if key in {"const", "enum", "examples", "default", "required"}:
                continue
            if key in {"properties", "$defs"} and isinstance(value, dict):
                for name, child in value.items():
                    errors.extend(unsupported_keywords(child, f"{path}.{key}.{name}"))
            elif key in {"items", "additionalProperties", "not", "if", "then", "else"}:
                if isinstance(value, dict):
                    errors.extend(unsupported_keywords(value, f"{path}.{key}"))
            elif key in {"allOf", "anyOf", "oneOf"} and isinstance(value, list):
                for index, child in enumerate(value):
                    errors.extend(unsupported_keywords(child, f"{path}.{key}[{index}]"))
    return errors


def validate_instance(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None, path: str = "$") -> list[str]:
    document = schema if root is None else root
    errors: list[str] = []
    if "$ref" in schema:
        errors.extend(_apply_ref(instance, schema["$ref"], document, path))
    for key in ("allOf", "anyOf", "oneOf", "not", "if"):
        if key in schema:
            errors.extend(_apply_applicator(instance, schema, document, path, key))
    errors.extend(_apply_assertions(instance, schema, document, path))
    return errors


def validate_config(instance: Any, schema: dict[str, Any] | None = None) -> list[str]:
    document = schema or load_schema()
    return validate_instance(instance, document, document)


def require_valid(instance: Any, schema: dict[str, Any] | None = None) -> None:
    errors = validate_config(instance, schema)
    if errors:
        raise SchemaError(errors)


def _apply_ref(instance: Any, ref: str, root: dict[str, Any], path: str) -> list[str]:
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return [f"{path}: only local $ref values are supported"]
    target: Any = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(target, dict) or part not in target:
            return [f"{path}: unresolved $ref {ref}"]
        target = target[part]
    if not isinstance(target, dict):
        return [f"{path}: $ref {ref} is not a schema object"]
    return validate_instance(instance, target, root, path)


def _apply_applicator(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str, key: str) -> list[str]:
    if key == "allOf":
        errors: list[str] = []
        for index, child in enumerate(schema["allOf"]):
            errors.extend(validate_instance(instance, child, root, f"{path}.allOf[{index}]"))
        return errors
    if key == "anyOf":
        branches = [validate_instance(instance, child, root, path) for child in schema["anyOf"]]
        if any(not branch for branch in branches):
            return []
        return [f"{path}: no anyOf alternative matched"]
    if key == "oneOf":
        branches = [validate_instance(instance, child, root, path) for child in schema["oneOf"]]
        matched = sum(not branch for branch in branches)
        if matched == 1:
            return []
        return [f"{path}: oneOf matched {matched} alternatives"]
    if key == "not":
        if not validate_instance(instance, schema["not"], root, path):
            return [f"{path}: instance must not match the not schema"]
        return []
    matched = not validate_instance(instance, schema["if"], root, path)
    if matched and "then" in schema:
        return validate_instance(instance, schema["then"], root, path)
    if not matched and "else" in schema:
        return validate_instance(instance, schema["else"], root, path)
    return []


def _apply_assertions(instance: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    if "type" in schema and not _type_matches(instance, schema["type"]):
        return [f"{path}: expected {schema['type']}"]
    if "const" in schema and not _same(instance, schema["const"]):
        errors.append(f"{path}: expected the required constant")
    if "enum" in schema and not any(_same(instance, item) for item in schema["enum"]):
        errors.append(f"{path}: value is outside the enum")
    if isinstance(instance, dict):
        if "required" in schema:
            missing = [key for key in schema["required"] if key not in instance]
            if missing:
                errors.append(f"{path}: missing {', '.join(missing)}")
        if "properties" in schema:
            for key, child in schema["properties"].items():
                if key in instance:
                    errors.extend(validate_instance(instance[key], child, root, f"{path}.{key}"))
        if "additionalProperties" in schema:
            allowed = set(schema.get("properties", {}))
            extra = [key for key in instance if key not in allowed]
            rule = schema["additionalProperties"]
            if rule is False and extra:
                errors.append(f"{path}: unexpected properties {', '.join(sorted(extra))}")
            elif isinstance(rule, dict):
                for key in extra:
                    errors.extend(validate_instance(instance[key], rule, root, f"{path}.{key}"))
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(validate_instance(item, schema["items"], root, f"{path}[{index}]"))
    if _is_number(instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: not above {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: not below {schema['exclusiveMaximum']}")
    return errors


def _type_matches(instance: Any, expected: str | list[str]) -> bool:
    names = [expected] if isinstance(expected, str) else list(expected)
    return any(_is_type(instance, name) for name in names)


def _is_type(instance: Any, name: str) -> bool:
    if name == "object":
        return isinstance(instance, dict)
    if name == "array":
        return isinstance(instance, list)
    if name == "string":
        return isinstance(instance, str)
    if name == "boolean":
        return isinstance(instance, bool)
    if name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if name == "number":
        return _is_number(instance)
    if name == "null":
        return instance is None
    raise SchemaError([f"unsupported type name {name}"])


def _is_number(instance: Any) -> bool:
    return isinstance(instance, (int, float)) and not isinstance(instance, bool)


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    return left == right

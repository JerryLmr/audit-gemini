from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple


def _preview(value: Any, *, limit: int = 800) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text[:limit]


def parse_llm_json_with_meta(raw_content: Any) -> Tuple[Dict[str, Any], bool]:
    if isinstance(raw_content, dict):
        return raw_content, True
    text = str(raw_content or "").strip()
    if not text:
        return {}, False
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, True
        return {}, False
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed, True
                return {}, False
            except json.JSONDecodeError:
                return {}, False
    return {}, False


def parse_llm_json(raw_content: Any) -> Dict[str, Any]:
    parsed, _ = parse_llm_json_with_meta(raw_content)
    return parsed


def _allows_null(type_name: str) -> bool:
    return "null" in str(type_name or "").lower()


def _base_type(type_name: str) -> str:
    value = str(type_name or "string").lower()
    if value.startswith("enum"):
        return "enum"
    return value.split("|", 1)[0].strip()


def _coerce_value(value: Any, definition: Dict[str, Any]) -> Tuple[Any, str | None]:
    if value is None:
        return None, None
    field_type = str(definition.get("type") or "string")
    enum_values = definition.get("enum")
    if isinstance(enum_values, list) and enum_values:
        if value in enum_values:
            return value, None
        return None, f"enum value {value!r} is not allowed"

    base = _base_type(field_type)
    if base in {"string", "enum"}:
        return str(value).strip(), None
    if base == "boolean":
        if isinstance(value, bool):
            return value, None
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value), None
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "y", "是", "有", "属于"}:
            return True, None
        if text in {"0", "false", "no", "n", "否", "无", "不属于"}:
            return False, None
        return None, f"boolean value {value!r} is invalid"
    if base == "integer":
        if isinstance(value, bool):
            return None, f"integer value {value!r} is invalid"
        try:
            return int(value), None
        except (TypeError, ValueError):
            return None, f"integer value {value!r} is invalid"
    if base == "number":
        if isinstance(value, bool):
            return None, f"number value {value!r} is invalid"
        try:
            return float(value), None
        except (TypeError, ValueError):
            return None, f"number value {value!r} is invalid"
    if base == "date":
        text = str(value).strip()
        return text, None
    return value, None


def sanitize_llm_output(raw_output: Any, field_definitions: Dict[str, Any]) -> Dict[str, Any]:
    parsed, json_parse_ok = parse_llm_json_with_meta(raw_output)
    incoming_fields = parsed.get("fields", parsed)
    if not isinstance(incoming_fields, dict):
        incoming_fields = {}
    incoming_evidence = parsed.get("evidence", {})
    if not isinstance(incoming_evidence, dict):
        incoming_evidence = {}

    allowed_fields = {
        key: definition
        for key, definition in (field_definitions or {}).items()
        if definition.get("llm_extractable") is True
    }
    fields: Dict[str, Any] = {}
    evidence: Dict[str, Any] = {}
    validation_errors: List[str] = []
    dropped_fields: List[str] = []

    for field_key, value in incoming_fields.items():
        if field_key not in allowed_fields:
            dropped_fields.append(str(field_key))
            continue
        definition = allowed_fields[field_key]
        coerced, error = _coerce_value(value, definition)
        if error:
            validation_errors.append(f"{field_key}: {error}")
            coerced = None
        if coerced is None and not _allows_null(str(definition.get("type") or "")):
            # Null is still accepted for LLM uncertainty; rule engine decides final impact.
            pass
        fields[field_key] = coerced

    for field_key, value in incoming_evidence.items():
        if field_key not in fields:
            continue
        if value is None:
            continue
        evidence[field_key] = str(value).strip()[:500]

    uncertainties = parsed.get("uncertainties", [])
    if not isinstance(uncertainties, list):
        uncertainties = [str(uncertainties)]

    return {
        "fields": fields,
        "evidence": evidence,
        "uncertainties": [str(item).strip() for item in uncertainties if str(item).strip()],
        "validation_errors": validation_errors,
        "dropped_fields": dropped_fields,
        "json_parse_ok": json_parse_ok,
        "parsed_json_preview": _preview(json.dumps(parsed, ensure_ascii=False)),
        "raw_content_preview": _preview(raw_output),
    }

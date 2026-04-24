from typing import Any, Dict, List

from modules.audit_engine.services.audit_service import audit_project
from modules.audit_engine.services.rule_loader import load_rule_json


def _field_definitions() -> Dict[str, Any]:
    return load_rule_json("standard_field_definitions.json").get("fields", {})


def _field_mapping_records(standard_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    definitions = _field_definitions()
    records: List[Dict[str, Any]] = []
    for field_key, runtime in (standard_fields or {}).items():
        if not isinstance(runtime, dict):
            continue
        candidates = runtime.get("candidates") or []
        selected_index = runtime.get("selected_index", -1)
        selected = candidates[selected_index] if isinstance(selected_index, int) and 0 <= selected_index < len(candidates) else {}
        definition = definitions.get(field_key, {})
        records.append(
            {
                "standard_field": field_key,
                "value": runtime.get("value"),
                "source": selected.get("source_sheet") or selected.get("source_type") or runtime.get("status", ""),
                "source_field": selected.get("source_column"),
                "mapping_rule": definition.get("description") or definition.get("comment") or "",
                "field_comment": definition.get("comment") or definition.get("description") or "",
            }
        )
    return records


def run_audit_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    standard_fields = payload.get("standard_fields")
    if not isinstance(standard_fields, dict):
        raise ValueError("审计请求必须提供 standard_fields 运行时对象。")

    field_mapping_layer = {
        "standard_fields": standard_fields,
        "field_mappings": _field_mapping_records(standard_fields),
        "unmapped_sources": [],
        "warnings": payload.get("warnings", []),
        "mapped_objects": payload.get("mapped_objects", []),
        "matched_object_ids": payload.get("matched_object_ids", []),
    }
    return audit_project(field_mapping_layer)

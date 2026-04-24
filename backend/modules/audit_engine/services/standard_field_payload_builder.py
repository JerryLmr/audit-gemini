from __future__ import annotations

from typing import Any, Dict

from modules.audit_engine.core.field_resolver import resolve_all_fields
from modules.audit_engine.services.excel_row_mapper import map_excel_row_to_field_candidates
from modules.audit_engine.services.mapping_service import map_project_name


def build_standard_field_payload_from_flat_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    flat_fields = payload.get("flat_fields")
    if not isinstance(flat_fields, dict):
        raise ValueError("审计请求必须提供 standard_fields 或 flat_fields。")

    mapped = map_excel_row_to_field_candidates(flat_fields, filename="manual_input", sheet_name="manual_input")
    resolved = resolve_all_fields(mapped.get("field_candidates") or {}, catalog_mapper=map_project_name)
    project_name = str(resolved["standard_fields"].get("project_name", {}).get("value") or payload.get("project_name") or "")
    return {
        "project_name": project_name,
        "standard_fields": resolved["standard_fields"],
        "missing_fields": resolved["missing_fields"],
        "conflicting_fields": resolved["conflicting_fields"],
        "warnings": resolved["warnings"],
        "mapped_objects": resolved["mapped_objects"],
        "matched_object_ids": resolved["matched_object_ids"],
        "debug": {
            "unmapped_columns": mapped.get("unmapped_columns") or [],
        },
    }


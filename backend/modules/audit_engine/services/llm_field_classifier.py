from __future__ import annotations

from typing import Any, Dict

from modules.audit_engine.services.llm_field_prompt_builder import build_field_classification_prompt
from modules.audit_engine.services.llm_field_sanitizer import sanitize_llm_output
from modules.audit_engine.services.local_llm_client import call_local_llm_json
from modules.audit_engine.services.rule_loader import load_rule_json


def classify_fields_with_local_llm(raw_fields: Dict[str, Any], raw_text: str) -> Dict[str, Any]:
    definitions = load_rule_json("standard_field_definitions.json").get("fields", {})
    prompt = build_field_classification_prompt(
        field_definitions=definitions,
        raw_fields=raw_fields,
        raw_text=raw_text,
    )
    llm_response = call_local_llm_json(prompt)
    if llm_response.get("available") is not True:
        warnings = list(llm_response.get("warnings") or [])
        return {
            "available": False,
            "model": llm_response.get("model"),
            "requested_model": llm_response.get("requested_model"),
            "selected_model": llm_response.get("selected_model"),
            "fields": {},
            "evidence": {},
            "uncertainties": [
                f"本地 LLM 调用失败（{llm_response.get('error_type') or 'unknown'}），已跳过 AI 字段归类。"
            ],
            "warnings": warnings,
            "validation_errors": [],
            "dropped_fields": [],
            "error": llm_response.get("error"),
            "error_type": llm_response.get("error_type"),
            "error_message": llm_response.get("error_message") or llm_response.get("error"),
            "models_response": llm_response.get("models_response") or {},
        }

    sanitized = sanitize_llm_output(llm_response.get("raw_content"), definitions)
    return {
        "available": True,
        "model": llm_response.get("model"),
        "requested_model": llm_response.get("requested_model"),
        "selected_model": llm_response.get("selected_model"),
        "warnings": list(llm_response.get("warnings") or []),
        **sanitized,
        "error": None,
        "error_type": None,
        "error_message": None,
        "models_response": llm_response.get("models_response") or {},
    }

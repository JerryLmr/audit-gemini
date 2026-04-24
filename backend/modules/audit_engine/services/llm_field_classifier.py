from __future__ import annotations

from typing import Any, Dict

from modules.audit_engine.services.llm_field_prompt_builder import build_field_classification_prompt
from modules.audit_engine.services.llm_field_sanitizer import sanitize_llm_output
from modules.audit_engine.services.local_llm_client import call_local_llm_json
from modules.audit_engine.services.rule_loader import load_rule_json


def _as_bool(value: Any) -> bool:
    return value is True


def _raw_preview(raw_content: Any) -> str:
    text = str(raw_content or "").strip()
    if not text:
        return ""
    return text[:800]


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
        diagnostics = {
            "models_ok": _as_bool(llm_response.get("models_ok")),
            "chat_ok": _as_bool(llm_response.get("chat_ok")),
            "raw_content_present": bool(str(llm_response.get("raw_content") or "").strip()),
            "json_parse_ok": False,
            "field_count": 0,
            "validation_error_count": 0,
            "dropped_field_count": 0,
            "selected_model": llm_response.get("selected_model") or llm_response.get("model"),
            "error_type": llm_response.get("error_type"),
            "error_message": llm_response.get("error_message") or llm_response.get("error"),
            "timeout_seconds": llm_response.get("timeout_seconds"),
        }
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
            "raw_content_preview": _raw_preview(llm_response.get("raw_content")),
            "parsed_json_preview": "",
            "llm_diagnostics": diagnostics,
        }

    sanitized = sanitize_llm_output(llm_response.get("raw_content"), definitions)
    field_count = len(sanitized.get("fields") or {})
    validation_error_count = len(sanitized.get("validation_errors") or [])
    dropped_field_count = len(sanitized.get("dropped_fields") or [])
    json_parse_ok = _as_bool(sanitized.get("json_parse_ok"))
    warnings = list(llm_response.get("warnings") or [])
    error_type = None
    error_message = None
    if not json_parse_ok:
        warnings.append("本地 LLM 已响应，但字段 JSON 解析失败。")
        error_type = "json_parse_failed"
        error_message = "LLM 已响应，但返回内容未能解析为字段 JSON。"
    elif field_count == 0:
        warnings.append("本地 LLM 已响应，但未抽取到有效字段。")
        error_type = "empty_fields"
        error_message = "LLM 已响应，但 fields 为空。"

    models_ok = _as_bool(llm_response.get("models_ok")) if "models_ok" in llm_response else True
    chat_ok = _as_bool(llm_response.get("chat_ok")) if "chat_ok" in llm_response else True
    diagnostics = {
        "models_ok": models_ok,
        "chat_ok": chat_ok,
        "raw_content_present": bool(str(llm_response.get("raw_content") or "").strip()),
        "json_parse_ok": json_parse_ok,
        "field_count": field_count,
        "validation_error_count": validation_error_count,
        "dropped_field_count": dropped_field_count,
        "selected_model": llm_response.get("selected_model") or llm_response.get("model"),
        "error_type": error_type,
        "error_message": error_message,
        "timeout_seconds": llm_response.get("timeout_seconds"),
    }

    return {
        "available": True,
        "model": llm_response.get("model"),
        "requested_model": llm_response.get("requested_model"),
        "selected_model": llm_response.get("selected_model"),
        "warnings": warnings,
        **sanitized,
        "error": None,
        "error_type": error_type,
        "error_message": error_message,
        "models_response": llm_response.get("models_response") or {},
        "raw_content_preview": sanitized.get("raw_content_preview") or _raw_preview(llm_response.get("raw_content")),
        "parsed_json_preview": sanitized.get("parsed_json_preview") or "",
        "llm_diagnostics": diagnostics,
    }

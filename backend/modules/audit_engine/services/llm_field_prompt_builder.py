from __future__ import annotations

import json
from typing import Any, Dict


def _llm_schema(field_definitions: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    for field_key, definition in (field_definitions or {}).items():
        if definition.get("llm_extractable") is not True:
            continue
        fields[field_key] = {
            "type": definition.get("type"),
            "allow_inference": definition.get("allow_inference", False),
            "enum": definition.get("enum"),
            "description": definition.get("description") or definition.get("comment") or "",
        }
    return fields


def build_field_classification_prompt(
    *,
    field_definitions: Dict[str, Any],
    raw_fields: Dict[str, Any],
    raw_text: str,
) -> str:
    schema = _llm_schema(field_definitions)
    contract = {
        "fields": {"示例字段key": "字段值或null"},
        "evidence": {"示例字段key": "原文证据短句"},
        "uncertainties": ["不确定项1", "不确定项2"],
    }
    return "\n".join(
        [
            "你是维修资金审计系统的字段归类模块，只负责把输入材料归类到标准字段。",
            "强约束：",
            "1. 只能输出 schema 中定义的字段，不允许新增字段。",
            "2. 不能输出合规/不合规、审计结论、reason_code 或法规解释。",
            "3. 必须输出严格 JSON，不要 Markdown，不要解释性文字。",
            '4. 输出必须是 JSON object，且必须包含且仅包含顶层键 "fields"、"evidence"、"uncertainties"。',
            "5. fields 和 evidence 必须是对象；uncertainties 必须是数组。",
            "6. 只要存在一个可确定字段，就必须写入 fields。",
            "7. 无法判断的字段填 null。",
            "8. 有 enum 的字段只能从 enum 中选择。",
            "9. allow_inference=false 的字段必须来自原文明确事实，不能推断。",
            "10. 不得把推断结果伪装成确定事实；不确定时写入 uncertainties。",
            "输出 JSON 示例（仅示意结构）：",
            json.dumps(contract, ensure_ascii=False, indent=2),
            "schema：",
            json.dumps(schema, ensure_ascii=False, indent=2),
            "parser 已抽取字段：",
            json.dumps(raw_fields, ensure_ascii=False, indent=2, default=str),
            "输入材料文本：",
            raw_text[:12000],
        ]
    )

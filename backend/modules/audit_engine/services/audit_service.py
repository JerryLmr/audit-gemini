from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Iterable, List, Sequence

from modules.audit_engine.core.field_resolver import runtime_values
from modules.audit_engine.services.basis_resolver import build_default_compliant_basis, build_from_reason_codes
from modules.audit_engine.services.rule_loader import load_rule_json


DISPLAY_MAPPING = {
    "compliant": "初步符合",
    "non_compliant": "疑似违规",
    "need_supplement": "需补充材料",
    "manual_review": "建议人工复核",
    "info_only": "仅展示",
}
ENTITY_FIELDS = [
    "project_name",
    "warranty_status",
    "is_public_part",
    "is_private_part",
    "is_property_service_scope",
    "repair_nature",
]
TRACE_FIELDS = [
    "repair_nature",
    "is_emergency_repair",
    "has_vote_trace",
    "need_construction_contract",
    "has_construction_contract",
    "has_appraisal_contract",
    "has_appraisal_report",
]
PROCESS_FIELDS = [
    "property_raw_value",
    "property_value_valid",
    "repair_nature",
    "is_emergency_repair",
    "has_vote_trace",
    "vote_pass_rate_by_household",
    "vote_pass_rate_by_area",
    "vote_legal",
    "vote_start_date",
    "vote_end_date",
    "resolution_date",
    "registration_date",
    "construction_start_date",
    "is_before_vote_construct",
]
AMOUNT_FIELDS = ["budget_amount", "contract_amount"]
ENTITY_CODES = {
    "ENTITY_PUBLIC_REPAIR_OBJECT",
    "ENTITY_PRIVATE_PART_NOT_ELIGIBLE",
    "ENTITY_PROPERTY_SERVICE_SCOPE",
    "ENTITY_IN_WARRANTY_NOT_ELIGIBLE",
    "ENTITY_WARRANTY_UNKNOWN_NEED_REVIEW",
    "ENTITY_OBJECT_UNKNOWN_MANUAL_REVIEW",
    "ENTITY_FIELD_CONFLICT_MANUAL_REVIEW",
}
TRACE_CODES = {
    "TRACE_MISSING_VOTE_TRACE",
    "TRACE_MISSING_CONSTRUCTION_CONTRACT",
    "TRACE_MISSING_APPRAISAL_CONTRACT",
    "TRACE_MISSING_APPRAISAL_REPORT",
    "TRACE_NEED_CONSTRUCTION_CONTRACT_NOT_SIGNED",
}
PROCESS_CODES = {
    "PROCESS_NORMAL_VOTE_MISSING",
    "PROCESS_NORMAL_VOTE_NOT_LEGAL",
    "PROCESS_VOTE_END_DATE_MISSING",
    "PROCESS_CONSTRUCTION_BEFORE_VOTE_CONFIRMED",
    "PROCESS_EMERGENCY_FLOW_EXEMPTED",
    "PROCESS_EMERGENCY_TRACE_REVIEW_REQUIRED",
    "PROCESS_PROPERTY_VALUE_UNSUPPORTED",
}
AMOUNT_CODES = {"AMOUNT_BUDGET_DISPLAY", "AMOUNT_CONTRACT_DISPLAY", "AMOUNT_INFO_MISSING"}


@lru_cache(maxsize=1)
def load_reason_code_definitions() -> Dict[str, Any]:
    return load_rule_json("audit_reason_codes.json")


def _append_unique(items: List[str], values: Iterable[str]) -> None:
    for value in values:
        if value not in items:
            items.append(value)


def _display(result: str | None) -> str | None:
    if result is None:
        return None
    return DISPLAY_MAPPING.get(result, result)


def _result(
    result: str,
    reason_codes: Sequence[str],
    reasons: Sequence[str],
    missing_items: Sequence[str],
    audit_path: Sequence[str],
    used_fields: Sequence[str],
    applicable: bool = True,
    basis_documents_override: Sequence[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    return {
        "applicable": applicable,
        "result": result,
        "display_result": _display(result),
        "reason_codes": list(reason_codes),
        "reasons": list(reasons),
        "missing_items": list(missing_items),
        "basis_documents": (
            list(basis_documents_override)
            if basis_documents_override is not None
            else build_from_reason_codes(reason_codes)
        ),
        "audit_path": list(audit_path),
        "used_standard_fields": list(used_fields),
    }


def _validate_code_categories(sub_audits: Dict[str, Dict[str, Any]]) -> None:
    expected = {
        "entity_audit": ENTITY_CODES,
        "trace_audit": TRACE_CODES,
        "process_audit": PROCESS_CODES,
        "amount_info": AMOUNT_CODES,
    }
    for key, allowed_codes in expected.items():
        for code in sub_audits.get(key, {}).get("reason_codes", []):
            if code not in allowed_codes:
                raise ValueError(f"{key} 使用了非本层 reason_code: {code}")


def _audit_entity(fields: Dict[str, Any], mapping_layer: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    codes: List[str] = []
    missing: List[str] = []
    public_part = fields.get("is_public_part")
    private_part = fields.get("is_private_part")
    property_scope = fields.get("is_property_service_scope")
    warranty_status = fields.get("warranty_status")

    if warranty_status == "in_warranty":
        return _result(
            "non_compliant",
            ["ENTITY_IN_WARRANTY_NOT_ELIGIBLE"],
            ["项目明确仍在保修期内，专项维修资金原则上用于保修期满后的共用部位、共用设施设备维修和更新改造。"],
            [],
            ["field_mapping_layer", "entity_audit", "in_warranty"],
            ENTITY_FIELDS,
        )
    if warranty_status in (None, "unknown"):
        return _result(
            "manual_review",
            ["ENTITY_WARRANTY_UNKNOWN_NEED_REVIEW"],
            ["缺少保修期满依据或保修状态无法判断，需补充保修期材料后人工复核。"],
            ["warranty_status"],
            ["field_mapping_layer", "entity_audit", "warranty_unknown"],
            ENTITY_FIELDS,
        )

    if public_part is True and (private_part is True or property_scope is True):
        return _result(
            "manual_review",
            ["ENTITY_FIELD_CONFLICT_MANUAL_REVIEW"],
            ["目录映射显示为共用维修对象，但来源字段或项目语义存在专有部分/物业维保冲突，需人工复核。"],
            [],
            ["field_mapping_layer", "entity_audit", "field_conflict"],
            ENTITY_FIELDS,
        )
    if private_part is True:
        return _result(
            "non_compliant",
            ["ENTITY_PRIVATE_PART_NOT_ELIGIBLE"],
            ["项目属于业主专有部分，不符合维修资金使用条件。"],
            [],
            ["field_mapping_layer", "entity_audit", "private_part"],
            ENTITY_FIELDS,
        )
    if property_scope is True:
        return _result(
            "non_compliant",
            ["ENTITY_PROPERTY_SERVICE_SCOPE"],
            ["项目属于物业日常服务或维保范围，不符合维修资金使用条件。"],
            [],
            ["field_mapping_layer", "entity_audit", "property_service_scope"],
            ENTITY_FIELDS,
        )
    if public_part is True:
        return _result(
            "compliant",
            ["ENTITY_PUBLIC_REPAIR_OBJECT"],
            ["项目属于共用部位或共用设施设备维修对象，本体合规初步通过。"],
            [],
            ["field_mapping_layer", "entity_audit", "public_repair_object"],
            ENTITY_FIELDS,
        )

    missing.extend(["is_public_part", "is_private_part", "is_property_service_scope"])
    return _result(
        "manual_review",
        ["ENTITY_OBJECT_UNKNOWN_MANUAL_REVIEW"],
        ["项目本体对象或维修范围无法通过标准字段确认，需人工复核。"],
        missing,
        ["field_mapping_layer", "entity_audit", "object_unknown"],
        ENTITY_FIELDS,
    )


def _audit_trace(fields: Dict[str, Any]) -> Dict[str, Any]:
    codes: List[str] = []
    reasons: List[str] = []
    missing: List[str] = []
    is_emergency = fields.get("repair_nature") == "emergency" or fields.get("is_emergency_repair") is True

    if not is_emergency and fields.get("has_vote_trace") is not True:
        codes.append("TRACE_MISSING_VOTE_TRACE")
        reasons.append("缺少业主表决痕迹，需补充表决汇总或相关材料。")
        missing.append("has_vote_trace")
    if fields.get("need_construction_contract") is True and fields.get("has_construction_contract") is not True:
        codes.append("TRACE_NEED_CONSTRUCTION_CONTRACT_NOT_SIGNED")
        reasons.append(
            "当前项目需要施工合同，但未见施工合同签署痕迹。"
            if not is_emergency
            else "紧急维修仍需补充施工合同或事后确认材料，当前未见施工合同签署痕迹。"
        )
        missing.append("has_construction_contract")
    elif fields.get("has_construction_contract") is not True:
        codes.append("TRACE_MISSING_CONSTRUCTION_CONTRACT")
        reasons.append(
            "缺少施工合同签署痕迹，需补充施工合同材料。"
            if not is_emergency
            else "紧急维修未见施工合同或事后施工资料痕迹，建议补充核验。"
        )
        missing.append("has_construction_contract")
    if fields.get("has_appraisal_contract") is not True:
        codes.append("TRACE_MISSING_APPRAISAL_CONTRACT")
        reasons.append(
            "缺少审价合同签署痕迹，需补充审价合同材料。"
            if not is_emergency
            else "紧急维修未见审价/结算委托痕迹，建议补充事后审价或结算材料。"
        )
        missing.append("has_appraisal_contract")
    if fields.get("has_appraisal_report") is not True:
        codes.append("TRACE_MISSING_APPRAISAL_REPORT")
        reasons.append(
            "缺少审价报告痕迹，需补充审价报告材料。"
            if not is_emergency
            else "紧急维修未见审价报告或结算审核痕迹，建议补充事后审价/结算资料。"
        )
        missing.append("has_appraisal_report")

    if codes:
        return _result(
            "need_supplement",
            codes,
            reasons,
            missing,
            ["field_mapping_layer", "trace_audit", "trace_missing"],
            TRACE_FIELDS,
        )
    return _result(
        "compliant",
        [],
        ["资料/手续痕迹字段齐备。"],
        [],
        ["field_mapping_layer", "trace_audit", "trace_complete"],
        TRACE_FIELDS,
        basis_documents_override=build_default_compliant_basis(
            "trace_audit",
            "emergency" if is_emergency else "normal",
        ),
    )


def _audit_process(fields: Dict[str, Any], trace_result: Dict[str, Any]) -> Dict[str, Any]:
    if fields.get("property_value_valid") is False:
        return _result(
            "manual_review",
            ["PROCESS_PROPERTY_VALUE_UNSUPPORTED"],
            ["工程性质 property 值不在当前支持范围内（仅支持 1=一般维修、2=急修），未按普通维修静默处理。"],
            ["property"],
            ["field_mapping_layer", "process_audit", "property_value_unsupported"],
            PROCESS_FIELDS,
        )

    if fields.get("repair_nature") == "emergency" or fields.get("is_emergency_repair") is True:
        codes = ["PROCESS_EMERGENCY_FLOW_EXEMPTED"]
        reasons = ["紧急维修仅豁免普通维修流程，不豁免项目本体合规。"]
        missing: List[str] = []
        if trace_result.get("result") in {"need_supplement", "manual_review"}:
            codes.append("PROCESS_EMERGENCY_TRACE_REVIEW_REQUIRED")
            reasons.append("紧急维修仍需补充资料/手续痕迹以支撑事后复核。")
            missing.extend(trace_result.get("missing_items", []))
        return _result(
            "manual_review" if len(codes) > 1 else "compliant",
            codes,
            reasons,
            missing,
            ["field_mapping_layer", "process_audit", "emergency_flow"],
            PROCESS_FIELDS,
        )

    codes: List[str] = []
    reasons: List[str] = []
    missing: List[str] = []
    if fields.get("has_vote_trace") is not True:
        codes.append("PROCESS_NORMAL_VOTE_MISSING")
        reasons.append("普通维修缺少业主表决流程信息。")
        missing.append("has_vote_trace")
    elif fields.get("vote_legal") is not True:
        codes.append("PROCESS_NORMAL_VOTE_NOT_LEGAL")
        reasons.append("普通维修表决通过率未达到当前口径或无法确认，建议人工复核。")
        if fields.get("vote_legal") is None:
            missing.extend(["vote_pass_rate_by_household", "vote_pass_rate_by_area"])
    if fields.get("construction_start_date") and not fields.get("vote_end_date"):
        codes.append("PROCESS_VOTE_END_DATE_MISSING")
        reasons.append("缺少征询结束日期，无法完成普通维修开工与表决先后顺序校验。")
        missing.append("vote_end_date")
    elif fields.get("is_before_vote_construct") is True:
        codes.append("PROCESS_CONSTRUCTION_BEFORE_VOTE_CONFIRMED")
        reasons.append("普通维修已确认存在先开工后表决的流程时序风险。")

    if codes:
        hard_codes = {
            "PROCESS_NORMAL_VOTE_NOT_LEGAL",
            "PROCESS_CONSTRUCTION_BEFORE_VOTE_CONFIRMED",
        }
        if any(code in hard_codes for code in codes):
            result = "manual_review"
        else:
            result = "need_supplement"
        return _result(
            result,
            codes,
            reasons,
            missing,
            ["field_mapping_layer", "process_audit", "normal_flow"],
            PROCESS_FIELDS,
        )
    return _result(
        "compliant",
        [],
        ["普通维修流程字段初步符合当前审计口径。"],
        [],
        ["field_mapping_layer", "process_audit", "normal_flow"],
        PROCESS_FIELDS,
        basis_documents_override=build_default_compliant_basis("process_audit", "normal"),
    )


def _audit_amount(fields: Dict[str, Any]) -> Dict[str, Any]:
    codes: List[str] = []
    reasons: List[str] = []
    missing: List[str] = []
    budget_amount = fields.get("budget_amount")
    contract_amount = fields.get("contract_amount")
    if budget_amount is not None:
        codes.append("AMOUNT_BUDGET_DISPLAY")
        reasons.append(f"预算金额：{budget_amount:g}。")
    else:
        missing.append("budget_amount")
    if contract_amount is not None:
        codes.append("AMOUNT_CONTRACT_DISPLAY")
        reasons.append(f"合同金额：{contract_amount:g}。")
    else:
        missing.append("contract_amount")
    if not codes:
        codes.append("AMOUNT_INFO_MISSING")
        reasons.append("缺少预算金额和合同金额，金额层仅提示展示信息缺失。")
    return _result(
        "info_only",
        codes,
        reasons,
        missing,
        ["field_mapping_layer", "amount_info", "display_only"],
        AMOUNT_FIELDS,
    )


def _collect_top_values(
    sub_audits: Dict[str, Dict[str, Any]],
    field_name: str,
    ordered_keys: Sequence[str],
) -> List[str]:
    values: List[str] = []
    for key in ordered_keys:
        sub_result = sub_audits.get(key, {})
        for value in sub_result.get(field_name, []) or []:
            if value not in values:
                values.append(value)
    return values


def _basis_dedupe_key(document: Dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(document.get("title") or ""),
        str(document.get("document_no") or ""),
        str(document.get("article") or ""),
    )


def _collect_basis_documents(sub_audits: Dict[str, Dict[str, Any]], ordered_keys: Sequence[str]) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for key in ordered_keys:
        for document in sub_audits.get(key, {}).get("basis_documents", []) or []:
            dedupe_key = _basis_dedupe_key(document)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            documents.append(document)
    return documents


def _primary_basis_key(entity: Dict[str, Any], trace: Dict[str, Any], process: Dict[str, Any]) -> str:
    if "PROCESS_PROPERTY_VALUE_UNSUPPORTED" in process.get("reason_codes", []):
        return "process_audit"
    if entity.get("result") in {"non_compliant", "manual_review"}:
        return "entity_audit"
    if process.get("result") in {"manual_review", "non_compliant"}:
        return "process_audit"
    if trace.get("result") == "need_supplement":
        return "trace_audit"
    if process.get("result") == "need_supplement":
        return "process_audit"
    return "entity_audit"


def _reason_order(primary_key: str) -> List[str]:
    if primary_key == "entity_audit":
        return ["entity_audit", "trace_audit", "process_audit"]
    if primary_key == "trace_audit":
        return ["trace_audit", "process_audit", "entity_audit"]
    if primary_key == "process_audit":
        return ["process_audit", "entity_audit", "trace_audit"]
    return ["entity_audit", "trace_audit", "process_audit"]


def _aggregate(sub_audits: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    entity = sub_audits["entity_audit"]
    trace = sub_audits["trace_audit"]
    process = sub_audits["process_audit"]
    if "PROCESS_PROPERTY_VALUE_UNSUPPORTED" in process.get("reason_codes", []):
        overall = "manual_review"
    elif entity["result"] == "non_compliant":
        overall = "non_compliant"
    elif entity["result"] == "manual_review":
        overall = "manual_review"
    elif process["result"] in {"manual_review", "non_compliant"}:
        overall = process["result"]
    elif trace["result"] == "need_supplement":
        overall = "need_supplement"
    elif process["result"] == "need_supplement":
        overall = process["result"]
    else:
        overall = "compliant"

    primary_key = _primary_basis_key(entity, trace, process)
    ordered_reason_keys = _reason_order(primary_key)
    reason_codes = _collect_top_values(sub_audits, "reason_codes", ordered_reason_keys)
    reasons = _collect_top_values(sub_audits, "reasons", ordered_reason_keys)
    missing_items = _collect_top_values(sub_audits, "missing_items", ordered_reason_keys)
    top_basis_documents = _collect_basis_documents(sub_audits, [primary_key])
    all_basis_documents = _collect_basis_documents(
        sub_audits,
        ["entity_audit", "trace_audit", "process_audit"],
    )
    manual_review_required = overall == "manual_review" or any(
        sub.get("result") == "manual_review" for sub in sub_audits.values()
    )
    summary_type = overall
    base_message = DISPLAY_MAPPING.get(overall, overall)
    if overall == "compliant":
        display_summary = "项目本体、资料痕迹和流程合规初步通过；金额层仅作展示。"
    else:
        display_summary = reasons[0] if reasons else base_message
    return {
        "overall_result": overall,
        "display_result": DISPLAY_MAPPING[overall],
        "reason_codes": reason_codes,
        "reasons": reasons,
        "top_reasons": reasons,
        "missing_items": missing_items,
        "top_missing_items": missing_items,
        "basis_documents": all_basis_documents,
        "top_basis_documents": top_basis_documents,
        "all_basis_documents": all_basis_documents,
        "manual_review_required": manual_review_required,
        "summary_conclusion": {
            "type": summary_type,
            "entity_pass": entity.get("result") == "compliant",
            "conflict_detected": "ENTITY_FIELD_CONFLICT_MANUAL_REVIEW" in entity.get("reason_codes", []),
            "primary_message": reasons[0] if reasons else base_message,
            "display_summary": display_summary,
        },
        "display_summary": display_summary,
    }


def audit_project(field_mapping_layer: Dict[str, Any]) -> Dict[str, Any]:
    runtime_standard_fields = dict(field_mapping_layer.get("standard_fields", {}))
    fields = runtime_values(runtime_standard_fields)
    entity = _audit_entity(fields, field_mapping_layer)
    trace = _audit_trace(fields)
    process = _audit_process(fields, trace)
    amount = _audit_amount(fields)
    sub_audits = {
        "entity_audit": entity,
        "trace_audit": trace,
        "process_audit": process,
        "amount_info": amount,
    }
    _validate_code_categories(sub_audits)
    aggregate = _aggregate(sub_audits)
    return {
        "project_name": fields.get("project_name") or "",
        "mapped_objects": field_mapping_layer.get("mapped_objects", []),
        "matched_object_ids": field_mapping_layer.get("matched_object_ids", []),
        "audit_path": ["field_mapping_layer", "entity_audit", "trace_audit", "process_audit", "amount_info"],
        "sub_audits": sub_audits,
        "field_mapping_layer": {
            "standard_fields": runtime_standard_fields,
            "field_mappings": field_mapping_layer.get("field_mappings", []),
            "unmapped_sources": field_mapping_layer.get("unmapped_sources", []),
            "warnings": field_mapping_layer.get("warnings", []),
        },
        **aggregate,
    }

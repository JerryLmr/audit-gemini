from __future__ import annotations

from typing import Any, Dict, List, Tuple

from modules.audit_engine.core.field_resolver import make_candidate
from modules.audit_engine.services.rule_loader import load_rule_json


COLUMN_ALIASES: Dict[str, Tuple[str, str]] = {
    "project_name": ("text", "project_name"),
    "工程名称": ("text", "project_name"),
    "项目名称": ("text", "project_name"),
    "wsname": ("text", "project_name"),
    "工程名": ("text", "project_name"),
    "property": ("t_workspace", "property"),
    "工程性质": ("t_workspace", "property"),
    "维修性质": ("t_workspace", "property"),
    "expirer_remark": ("blueprint_draft", "expirer_remark"),
    "保修备注": ("blueprint_draft", "expirer_remark"),
    "保修说明": ("blueprint_draft", "expirer_remark"),
    "is_signed_pc": ("ws_project", "is_signed_pc"),
    "是否已签订施工合同": ("ws_project", "is_signed_pc"),
    "施工合同": ("ws_project", "is_signed_pc"),
    "is_signed_esc": ("ws_project", "is_signed_esc"),
    "是否已签订审价合同": ("ws_project", "is_signed_esc"),
    "审价合同": ("ws_project", "is_signed_esc"),
    "is_signed_esr": ("ws_project", "is_signed_esr"),
    "是否已出具审价报告": ("ws_project", "is_signed_esr"),
    "审价报告": ("ws_project", "is_signed_esr"),
    "need_con": ("ws_project", "need_con"),
    "是否需要签订施工合同": ("ws_project", "need_con"),
    "需要施工合同": ("ws_project", "need_con"),
    "has_hou_notion_sum": ("hou_notion_sum", "__row_exists__"),
    "存在表决汇总": ("hou_notion_sum", "__row_exists__"),
    "是否存在表决汇总": ("hou_notion_sum", "__row_exists__"),
    "有无表决汇总": ("hou_notion_sum", "__row_exists__"),
    "count_hou": ("hou_notion_sum", "count_hou"),
    "总户数": ("hou_notion_sum", "count_hou"),
    "agree_hou": ("hou_notion_sum", "agree_hou"),
    "同意户数": ("hou_notion_sum", "agree_hou"),
    "sum_area": ("hou_notion_sum", "sum_area"),
    "总面积": ("hou_notion_sum", "sum_area"),
    "agree_area": ("hou_notion_sum", "agree_area"),
    "同意面积": ("hou_notion_sum", "agree_area"),
    "request_enddate": ("hou_notion_sum", "request_enddate"),
    "征询结束日期": ("hou_notion_sum", "request_enddate"),
    "表决结束日期": ("hou_notion_sum", "request_enddate"),
    "request_startdate": ("hou_notion_sum", "request_startdate"),
    "征询开始日期": ("hou_notion_sum", "request_startdate"),
    "表决开始日期": ("hou_notion_sum", "request_startdate"),
    "reg_date": ("hou_notion_sum", "reg_date"),
    "录入日期": ("hou_notion_sum", "reg_date"),
    "startup_date": ("project_contract", "startup_date"),
    "开工日期": ("project_contract", "startup_date"),
    "orgn_amt": ("project_contract", "orgn_amt"),
    "预算金额": ("project_contract", "orgn_amt"),
    "contract_amt": ("project_contract", "contract_amt"),
    "合同金额": ("project_contract", "contract_amt"),
}

FLAT_FIELD_ALIASES: Dict[str, Tuple[str, str, str]] = {
    "project_name": ("project_name", "text", "project_name"),
    "工程名称": ("project_name", "text", "project_name"),
    "项目名称": ("project_name", "text", "project_name"),
    "wsname": ("project_name", "text", "project_name"),
    "mo_name": ("project_name", "text", "mo_name"),
    "工程名": ("project_name", "text", "project_name"),
    "wscode": ("project_item_code", "excel", "wscode"),
    "wsid": ("project_item_code", "excel", "wsid"),
    "range": ("repair_scope", "excel", "range"),
    "reason": ("repair_reason", "excel", "reason"),
    "repairreason": ("repair_reason", "excel", "repairreason"),
    "hc_name": ("applicant", "excel", "hc_name"),
    "property": ("property_raw_value", "excel", "property"),
    "工程性质": ("property_raw_value", "excel", "property"),
    "维修性质": ("property_raw_value", "excel", "property"),
    "expirer_remark": ("warranty_status", "excel", "expirer_remark"),
    "保修备注": ("warranty_status", "excel", "expirer_remark"),
    "保修说明": ("warranty_status", "excel", "expirer_remark"),
    "is_signed_pc": ("has_construction_contract", "excel", "is_signed_pc"),
    "是否已签订施工合同": ("has_construction_contract", "excel", "is_signed_pc"),
    "施工合同": ("has_construction_contract", "excel", "is_signed_pc"),
    "is_signed_esc": ("has_appraisal_contract", "excel", "is_signed_esc"),
    "是否已签订审价合同": ("has_appraisal_contract", "excel", "is_signed_esc"),
    "审价合同": ("has_appraisal_contract", "excel", "is_signed_esc"),
    "is_signed_esr": ("has_appraisal_report", "excel", "is_signed_esr"),
    "是否已出具审价报告": ("has_appraisal_report", "excel", "is_signed_esr"),
    "审价报告": ("has_appraisal_report", "excel", "is_signed_esr"),
    "need_con": ("need_construction_contract", "excel", "need_con"),
    "need_pro_contract": ("need_construction_contract", "excel", "need_pro_contract"),
    "是否需要签订施工合同": ("need_construction_contract", "excel", "need_con"),
    "需要施工合同": ("need_construction_contract", "excel", "need_con"),
    "need_check_amt": ("need_cost_review", "excel", "need_check_amt"),
    "是否审价": ("need_cost_review", "excel", "need_check_amt"),
    "是否需要审价": ("need_cost_review", "excel", "need_check_amt"),
    "has_hou_notion_sum": ("has_vote_trace", "excel", "__row_exists__"),
    "is_voted": ("has_vote_trace", "excel", "is_voted"),
    "存在表决汇总": ("has_vote_trace", "excel", "__row_exists__"),
    "是否存在表决汇总": ("has_vote_trace", "excel", "__row_exists__"),
    "有无表决汇总": ("has_vote_trace", "excel", "__row_exists__"),
    "count_hou": ("vote_total_households", "excel", "count_hou"),
    "总户数": ("vote_total_households", "excel", "count_hou"),
    "agree_hou": ("vote_approved_households", "excel", "agree_hou"),
    "同意户数": ("vote_approved_households", "excel", "agree_hou"),
    "sum_area": ("vote_total_area", "excel", "sum_area"),
    "总面积": ("vote_total_area", "excel", "sum_area"),
    "agree_area": ("vote_approved_area", "excel", "agree_area"),
    "同意面积": ("vote_approved_area", "excel", "agree_area"),
    "request_enddate": ("vote_end_date", "excel", "request_enddate"),
    "征询结束日期": ("vote_end_date", "excel", "request_enddate"),
    "表决结束日期": ("vote_end_date", "excel", "request_enddate"),
    "request_startdate": ("vote_start_date", "excel", "request_startdate"),
    "征询开始日期": ("vote_start_date", "excel", "request_startdate"),
    "表决开始日期": ("vote_start_date", "excel", "request_startdate"),
    "reg_date": ("registration_date", "excel", "reg_date"),
    "录入日期": ("registration_date", "excel", "reg_date"),
    "startup_date": ("construction_start_date", "excel", "startup_date"),
    "开工日期": ("construction_start_date", "excel", "startup_date"),
    "finish_date": ("construction_finish_date", "excel", "finish_date"),
    "完工日期": ("construction_finish_date", "excel", "finish_date"),
    "orgn_amt": ("budget_amount", "excel", "orgn_amt"),
    "ws_amt": ("budget_amount", "excel", "ws_amt"),
    "预算金额": ("budget_amount", "excel", "orgn_amt"),
    "final_amt": ("final_amount", "excel", "final_amt"),
    "决案金额": ("final_amount", "excel", "final_amt"),
    "contract_amt": ("contract_amount", "excel", "contract_amt"),
    "合同金额": ("contract_amount", "excel", "contract_amt"),
}

STANDARD_FIELD_TYPES = {
    field_key: str(definition.get("type") or "")
    for field_key, definition in load_rule_json("standard_field_definitions.json").get("fields", {}).items()
}


def _normalize_column(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_present(value: Any) -> bool:
    return value is not None and value != ""


def _to_bool_marker(value: Any) -> Any:
    if value is None or value == "":
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "y", "yes", "是", "有", "存在", "已存在"}:
        return True
    if text in {"0", "false", "n", "no", "否", "无", "不存在"}:
        return False
    return value


def map_excel_row_to_audit_request(row: Dict[str, Any]) -> Dict[str, Any]:
    """Map one parsed Excel row dict into the unified audit request shape.

    This helper intentionally does not parse xlsx files. The future upload API can
    parse rows with any Excel library and call this function row by row.
    """
    sources: Dict[str, Dict[str, Any]] = {
        "t_workspace": {},
        "ws_project": {},
        "blueprint_draft": {},
        "hou_notion_sum": {},
        "project_contract": {},
        "text": {},
    }
    unmapped_columns = []

    for column_name, value in (row or {}).items():
        normalized = _normalize_column(column_name)
        target = COLUMN_ALIASES.get(normalized)
        if not target:
            if _is_present(value):
                unmapped_columns.append(normalized)
            continue
        source_name, source_field = target
        if source_name == "hou_notion_sum" and source_field == "__row_exists__":
            value = _to_bool_marker(value)
        sources.setdefault(source_name, {})[source_field] = value

    project_name = str(sources.get("text", {}).get("project_name") or "").strip()
    if project_name:
        sources["t_workspace"].setdefault("wsname", project_name)
        sources["blueprint_draft"].setdefault("wsname", project_name)
        sources["project_contract"].setdefault("name", project_name)

    return {
        "project_name": project_name,
        "sources": {source: values for source, values in sources.items() if values},
        "unmapped_columns": sorted(set(unmapped_columns)),
    }


def map_excel_row_to_field_candidates(row: Dict[str, Any], filename: str = "", sheet_name: str = "") -> Dict[str, Any]:
    candidates: Dict[str, List[Any]] = {}
    unmapped_columns: List[str] = []
    for column_name, value in (row or {}).items():
        normalized = _normalize_column(column_name)
        target = FLAT_FIELD_ALIASES.get(normalized)
        if not target:
            if _is_present(value):
                unmapped_columns.append(normalized)
            continue
        field_key, source_sheet, source_column = target
        if source_column == "__row_exists__":
            value = _to_bool_marker(value)
        candidates.setdefault(field_key, []).append(
            make_candidate(
                field_type=STANDARD_FIELD_TYPES.get(field_key, ""),
                source_type="excel",
                source_file=filename,
                source_sheet=source_sheet or sheet_name,
                source_column=source_column,
                raw_value=value,
            )
        )
    return {
        "field_candidates": candidates,
        "unmapped_columns": sorted(set(unmapped_columns)),
    }

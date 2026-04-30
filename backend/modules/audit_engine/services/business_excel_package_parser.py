from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from modules.audit_engine.core.field_resolver import make_candidate, resolve_all_fields
from modules.audit_engine.services.mapping_service import map_project_name
from modules.audit_engine.services.rule_loader import load_rule_json


BUSINESS_SHEET_TYPES = {
    "维修工程信息": "t_workspace",
    "T_WORKSPACE": "t_workspace",
    "T_Workspace": "t_workspace",
    "维修预案": "blueprint_draft",
    "Blueprint_draft": "blueprint_draft",
    "维修决案": "blueprint",
    "Blueprint": "blueprint",
    "三审工程维修项目表": "ws_project",
    "Ws_project": "ws_project",
    "WS_PROJECT": "ws_project",
    "施工合同表": "project_contract",
    "Project_contract": "project_contract",
    "项目完工报告表": "ws_project_report",
    "维修工单": "repair_order",
    "维修对象": "repair_object",
    "业主征询意见": "vote_detail",
    "业主表决汇总": "hou_notion_sum",
    "业主大会决议": "owner_resolution",
    "业主表决结果": "vote_result",
}

KEY_FIELDS = {"WSID", "WSCODE", "WSNAME", "BPPID", "BPID", "MO_ID"}
TECHNICAL_HEADER_HINTS = KEY_FIELDS | {
    "PROPERTY",
    "ORGN_AMT",
    "FINAL_AMT",
    "CONTRACT_AMT",
    "COUNT_HOU",
    "AGREE_HOU",
    "SUM_AREA",
    "AGREE_AREA",
}


STANDARD_FIELD_TYPES = {
    field_key: str(definition.get("type") or "")
    for field_key, definition in load_rule_json("standard_field_definitions.json").get("fields", {}).items()
}


def _cell_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return value


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized_key(value: Any) -> str:
    return _text(value).upper()


def _is_technical_header(values: Iterable[Any]) -> bool:
    normalized = {_normalized_key(value) for value in values if _present(value)}
    return len(normalized & TECHNICAL_HEADER_HINTS) >= 2


def _build_headers(values: Tuple[Any, ...]) -> Tuple[List[str], List[str]]:
    headers: List[str] = []
    warnings: List[str] = []
    seen: Dict[str, int] = {}
    for index, value in enumerate(values, start=1):
        header = _text(value)
        if not header:
            header = f"未命名列{index}"
            warnings.append(f"第 {index} 列表头为空，已按 {header} 处理。")
        count = seen.get(header, 0)
        seen[header] = count + 1
        if count:
            unique_header = f"{header}__{count + 1}"
            warnings.append(f"表头 {header} 重复，重复列已标记为 {unique_header}。")
            header = unique_header
        headers.append(header)
    return headers, warnings


def _row_get(row: Dict[str, Any], *fields: str) -> Any:
    for field in fields:
        if field in row and _present(row[field]):
            return row[field]
    return None


def _copy_fields(row: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for source_field, target_field in mapping.items():
        value = _row_get(row, source_field)
        if _present(value):
            output[target_field] = value
    return output


def _first_row(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return rows[0] if rows else {}


def _parse_sheet(sheet: Any) -> Dict[str, Any]:
    all_rows = list(sheet.iter_rows(values_only=True))
    warnings: List[str] = []
    if not all_rows:
        return {
            "sheet_name": sheet.title,
            "sheet_type": BUSINESS_SHEET_TYPES.get(sheet.title),
            "headers": [],
            "rows": [],
            "key_fields": [],
            "warnings": ["工作表为空。"],
        }

    header_index = 1 if len(all_rows) > 1 and _is_technical_header(all_rows[1]) else 0
    headers, header_warnings = _build_headers(all_rows[header_index])
    warnings.extend(header_warnings)
    rows: List[Dict[str, Any]] = []
    for values in all_rows[header_index + 1 :]:
        row = {
            headers[index]: _cell_value(values[index]) if index < len(values) else None
            for index in range(len(headers))
        }
        if any(_present(value) for value in row.values()):
            rows.append(row)
    key_fields = sorted({_normalized_key(header) for header in headers} & KEY_FIELDS)
    return {
        "sheet_name": sheet.title,
        "sheet_type": BUSINESS_SHEET_TYPES.get(sheet.title),
        "headers": headers,
        "rows": rows,
        "key_fields": key_fields,
        "warnings": warnings,
    }


def _is_business_package(tables: Dict[str, Dict[str, Any]]) -> bool:
    matched_types = {table.get("sheet_type") for table in tables.values() if table.get("sheet_type")}
    if len(matched_types) >= 2:
        return True
    for sheet_name in ("维修工程信息", "维修预案", "维修决案"):
        table = tables.get(sheet_name)
        if table and table.get("key_fields"):
            return True
    return False


def _build_indexes(tables: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    indexes: Dict[str, Dict[str, str]] = {
        "bppid_to_wsid": {},
        "bpid_to_wsid": {},
        "mo_id_to_wsid": {},
    }
    for sheet_name in ("维修预案", "维修决案", "业主征询意见", "业主表决结果"):
        for row in tables.get(sheet_name, {}).get("rows", []):
            wsid = _text(_row_get(row, "WSID"))
            if not wsid:
                continue
            bppid = _text(_row_get(row, "BPPID"))
            bpid = _text(_row_get(row, "BPID"))
            mo_id = _text(_row_get(row, "MO_ID"))
            if bppid:
                indexes["bppid_to_wsid"].setdefault(bppid, wsid)
            if bpid:
                indexes["bpid_to_wsid"].setdefault(bpid, wsid)
            if mo_id:
                indexes["mo_id_to_wsid"].setdefault(mo_id, wsid)
    return indexes


def _resolve_wsid(row: Dict[str, Any], indexes: Dict[str, Dict[str, str]]) -> Optional[str]:
    wsid = _text(_row_get(row, "WSID", "工程id", "工程ID"))
    if wsid:
        return wsid
    bppid = _text(_row_get(row, "BPPID"))
    if bppid and bppid in indexes["bppid_to_wsid"]:
        return indexes["bppid_to_wsid"][bppid]
    bpid = _text(_row_get(row, "BPID"))
    if bpid and bpid in indexes["bpid_to_wsid"]:
        return indexes["bpid_to_wsid"][bpid]
    mo_id = _text(_row_get(row, "MO_ID"))
    if mo_id and mo_id in indexes["mo_id_to_wsid"]:
        return indexes["mo_id_to_wsid"][mo_id]
    return None


def _group_rows_by_project(tables: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    indexes = _build_indexes(tables)
    projects: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for sheet_name, table in tables.items():
        if not table.get("sheet_type"):
            continue
        for row in table.get("rows", []):
            wsid = _resolve_wsid(row, indexes)
            if not wsid:
                continue
            projects.setdefault(wsid, {}).setdefault(sheet_name, []).append(row)
    return projects


def _first_available(project_rows: Dict[str, List[Dict[str, Any]]], *sheet_names: str) -> Dict[str, Any]:
    for sheet_name in sheet_names:
        row = _first_row(project_rows.get(sheet_name, []))
        if row:
            return row
    return {}


def _project_name_from_sources(*rows: Dict[str, Any]) -> str:
    for row in rows:
        value = _row_get(row, "WSNAME", "MO_NAME", "REPAIRREASON")
        if _present(value):
            return _text(value)
    return ""


FIELD_COLUMN_MAPPINGS: Tuple[Tuple[str, str, str], ...] = (
    ("project_name", "维修工程信息", "WSNAME"),
    ("project_name", "维修决案", "WSNAME"),
    ("project_name", "维修预案", "WSNAME"),
    ("project_name", "维修对象", "MO_NAME"),
    ("project_name", "施工合同表", "NAME"),
    ("project_item_code", "维修工程信息", "WSCODE"),
    ("project_item_code", "维修决案", "WSCODE"),
    ("project_item_code", "维修预案", "WSCODE"),
    ("project_item_code", "维修工程信息", "WSID"),
    ("property_raw_value", "维修工程信息", "PROPERTY"),
    ("property_raw_value", "维修决案", "PROPERTY"),
    ("property_raw_value", "维修预案", "PROPERTY"),
    ("need_construction_contract", "三审工程维修项目表", "NEED_CON"),
    ("need_construction_contract", "维修工程信息", "NEED_PRO_CONTRACT"),
    ("need_construction_contract", "维修决案", "NEED_PRO_CONTRACT"),
    ("need_construction_contract", "维修预案", "NEED_PRO_CONTRACT"),
    ("need_cost_review", "维修工程信息", "NEED_CHECK_AMT"),
    ("need_cost_review", "维修决案", "NEED_CHECK_AMT"),
    ("need_cost_review", "维修预案", "NEED_CHECK_AMT"),
    ("has_construction_contract", "三审工程维修项目表", "IS_SIGNED_PC"),
    ("has_appraisal_contract", "三审工程维修项目表", "IS_SIGNED_ESC"),
    ("has_appraisal_report", "三审工程维修项目表", "IS_SIGNED_ESR"),
    ("budget_amount", "三审工程维修项目表", "ORGN_AMT"),
    ("budget_amount", "维修决案", "ORGN_AMT"),
    ("budget_amount", "维修预案", "ORGN_AMT"),
    ("budget_amount", "维修工程信息", "WS_AMT"),
    ("final_amount", "三审工程维修项目表", "FINAL_AMT"),
    ("final_amount", "维修决案", "FINAL_AMT"),
    ("final_amount", "业主表决结果", "FINAL_AMT"),
    ("contract_amount", "施工合同表", "CONTRACT_AMT"),
    ("construction_start_date", "施工合同表", "STARTUP_DATE"),
    ("construction_start_date", "三审工程维修项目表", "STARTUP_DATE"),
    ("construction_finish_date", "施工合同表", "FINISH_DATE"),
    ("construction_finish_date", "三审工程维修项目表", "FINISH_DATE"),
    ("contract_sign_date", "施工合同表", "SIGN_DATE"),
    ("repair_scope", "维修决案", "RANGE"),
    ("repair_scope", "维修预案", "RANGE"),
    ("repair_scope", "三审工程维修项目表", "RANGE"),
    ("repair_reason", "维修决案", "REASON"),
    ("repair_reason", "维修预案", "REASON"),
    ("repair_reason", "维修工单", "REPAIRREASON"),
    ("vote_total_households", "业主表决汇总", "COUNT_HOU"),
    ("vote_approved_households", "业主表决汇总", "AGREE_HOU"),
    ("vote_total_area", "业主表决汇总", "SUM_AREA"),
    ("vote_approved_area", "业主表决汇总", "AGREE_AREA"),
    ("vote_end_date", "业主表决汇总", "REQUEST_ENDDATE"),
    ("vote_end_date", "业主大会决议", "发送征求意见表结束日期"),
    ("vote_start_date", "业主表决汇总", "REQUEST_STARTDATE"),
    ("vote_start_date", "业主大会决议", "发送征求意见表开始日期"),
    ("registration_date", "业主表决汇总", "REG_DATE"),
    ("resolution_date", "业主大会决议", "决议生成日期"),
    ("warranty_status", "维修决案", "EXPIRER_REMARK"),
    ("warranty_status", "维修预案", "EXPIRER_REMARK"),
)


def _field_type(field_key: str) -> str:
    return STANDARD_FIELD_TYPES.get(field_key, "")


def _add_candidate(
    candidates: Dict[str, List[Any]],
    field_key: str,
    *,
    filename: str,
    sheet_name: str,
    column_name: str,
    value: Any,
) -> None:
    if not _present(value):
        return
    candidates.setdefault(field_key, []).append(
        make_candidate(
            field_type=_field_type(field_key),
            source_type="excel",
            source_file=filename,
            source_sheet=sheet_name,
            source_column=column_name,
            raw_value=value,
        )
    )


def extract_field_candidates(
    project_rows: Dict[str, List[Dict[str, Any]]],
    filename: str = "",
) -> Dict[str, List[Any]]:
    candidates: Dict[str, List[Any]] = {}
    for field_key, sheet_name, column_name in FIELD_COLUMN_MAPPINGS:
        for row in project_rows.get(sheet_name, []):
            _add_candidate(
                candidates,
                field_key,
                filename=filename,
                sheet_name=sheet_name,
                column_name=column_name,
                value=_row_get(row, column_name),
            )

    if project_rows.get("业主表决汇总"):
        _add_candidate(
            candidates,
            "has_vote_trace",
            filename=filename,
            sheet_name="业主表决汇总",
            column_name="__row_exists__",
            value=True,
        )
    else:
        workspace = _first_available(project_rows, "维修工程信息")
        _add_candidate(
            candidates,
            "has_vote_trace",
            filename=filename,
            sheet_name="维修工程信息",
            column_name="IS_VOTED",
            value=_row_get(workspace, "IS_VOTED"),
        )
    return candidates


def _build_runtime_project(row_index: int, project_key: str, project_rows: Dict[str, List[Dict[str, Any]]], filename: str) -> Dict[str, Any]:
    candidates = extract_field_candidates(project_rows, filename=filename)
    resolved = resolve_all_fields(candidates, catalog_mapper=map_project_name)
    project_name = str(resolved["standard_fields"].get("project_name", {}).get("value") or "")
    source_sheets = [sheet_name for sheet_name, rows in project_rows.items() if rows]
    has_vote_summary = bool(project_rows.get("业主表决汇总"))
    business_summary = [
        f"已按 WSID 聚合项目 {project_key}。",
        f"已聚合 {len(source_sheets)} 张业务表。",
        "已识别业主表决汇总。" if has_vote_summary else "未识别业主表决汇总。",
    ]
    audit_request = {
        "project_name": project_name,
        "standard_fields": resolved["standard_fields"],
        "missing_fields": resolved["missing_fields"],
        "conflicting_fields": resolved["conflicting_fields"],
        "warnings": resolved["warnings"],
        "mapped_objects": resolved["mapped_objects"],
        "matched_object_ids": resolved["matched_object_ids"],
    }
    return {
        "row_index": row_index,
        "project_key": project_key,
        "project_name": project_name,
        "raw_row": {},
        "standard_fields": resolved["standard_fields"],
        "missing_fields": resolved["missing_fields"],
        "conflicting_fields": resolved["conflicting_fields"],
        "audit_ready": resolved["audit_ready"],
        "audit_request": audit_request,
        "source_sheets": source_sheets,
        "business_summary": business_summary,
        "warnings": resolved["warnings"],
        "mapped_objects": resolved["mapped_objects"],
        "matched_object_ids": resolved["matched_object_ids"],
        "debug": {
            "source_sheets": source_sheets,
            "unmapped_columns": [],
        },
    }


def _build_project_request(row_index: int, project_key: str, project_rows: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    workspace = _first_available(project_rows, "维修工程信息")
    draft = _first_available(project_rows, "维修预案")
    blueprint = _first_available(project_rows, "维修决案")
    vote_sum = _first_available(project_rows, "业主表决汇总")
    resolution = _first_available(project_rows, "业主大会决议")
    vote_result = _first_available(project_rows, "业主表决结果")
    repair_object = _first_available(project_rows, "维修对象")
    project_name = _project_name_from_sources(workspace, draft, blueprint, repair_object)

    sources: Dict[str, Dict[str, Any]] = {}
    t_workspace = _copy_fields(
        workspace,
        {
            "WSID": "wsid",
            "WSCODE": "wscode",
            "WSNAME": "wsname",
            "PROPERTY": "property",
            "NEED_VOTE": "need_vote",
            "IS_VOTED": "is_voted",
            "NEED_PRO_CONTRACT": "need_pro_contract",
            "NEED_CHECK_AMT": "need_check_amt",
        },
    )
    if t_workspace:
        sources["t_workspace"] = t_workspace

    blueprint_draft = _copy_fields(
        draft,
        {
            "BPPID": "bppid",
            "DESION_TYPE": "desion_type",
            "WSCODE": "wscode",
            "WSNAME": "wsname",
            "PROPERTY": "property",
            "ORGN_AMT": "orgn_amt",
            "RANGE": "range",
            "REASON": "reason",
            "EXPIRER_REMARK": "expirer_remark",
        },
    )
    if blueprint_draft:
        sources["blueprint_draft"] = blueprint_draft

    blueprint_source = _copy_fields(
        blueprint,
        {
            "BPID": "bpid",
            "WSCODE": "wscode",
            "WSNAME": "wsname",
            "PROPERTY": "property",
            "ORGN_AMT": "orgn_amt",
            "FINAL_AMT": "final_amt",
            "RANGE": "range",
            "REASON": "reason",
            "WSID": "wsid",
        },
    )
    if blueprint_source:
        sources["blueprint"] = blueprint_source

    hou_notion_sum = _copy_fields(
        vote_sum,
        {
            "COUNT_HOU": "count_hou",
            "SUM_AREA": "sum_area",
            "AGREE_HOU": "agree_hou",
            "AGREE_AREA": "agree_area",
        },
    )
    if vote_sum:
        hou_notion_sum["__row_exists__"] = True
    if resolution:
        end_date = _row_get(resolution, "发送征求意见表结束日期")
        start_date = _row_get(resolution, "发送征求意见表开始日期")
        reg_date = _row_get(resolution, "决议生成日期")
        if _present(end_date):
            hou_notion_sum["request_enddate"] = end_date
        if _present(start_date):
            hou_notion_sum["request_startdate"] = start_date
        if _present(reg_date):
            hou_notion_sum["reg_date"] = reg_date
    if hou_notion_sum:
        sources["hou_notion_sum"] = hou_notion_sum

    ws_project: Dict[str, Any] = {}
    need_con = _row_get(draft, "NEED_PRO_CONTRACT") or _row_get(blueprint, "NEED_PRO_CONTRACT")
    if _present(need_con):
        ws_project["need_con"] = need_con
    orgn_amt = _row_get(draft, "ORGN_AMT") or _row_get(blueprint, "ORGN_AMT")
    if _present(orgn_amt):
        ws_project["orgn_amt"] = orgn_amt
    repair_type = _row_get(vote_result, "REPAIR_TYPE")
    if _present(repair_type):
        ws_project["repair_type"] = repair_type
    if ws_project:
        sources["ws_project"] = ws_project

    project_contract: Dict[str, Any] = {}
    if project_name:
        project_contract["name"] = project_name
    if _present(orgn_amt):
        project_contract["orgn_amt"] = orgn_amt
    if project_contract:
        sources["project_contract"] = project_contract

    if project_name:
        sources["text"] = {"project_name": project_name}

    source_sheets = [sheet_name for sheet_name, rows in project_rows.items() if rows]
    has_vote_summary = bool(vote_sum)
    business_summary = [
        f"已按 WSID 聚合项目 {project_key}。",
        f"已聚合 {len(source_sheets)} 张业务表。",
        "已识别业主表决汇总。" if has_vote_summary else "未识别业主表决汇总。",
    ]
    return {
        "row_index": row_index,
        "project_key": project_key,
        "project_name": project_name,
        "raw_row": {},
        "audit_request": {"project_name": project_name, "sources": sources},
        "unmapped_columns": [],
        "source_sheets": source_sheets,
        "business_summary": business_summary,
        "warnings": [],
    }


def try_parse_business_package(workbook: Any, filename: str = "") -> Optional[Dict[str, Any]]:
    tables = {sheet.title: _parse_sheet(sheet) for sheet in workbook.worksheets}
    if not _is_business_package(tables):
        return None

    projects = _group_rows_by_project(tables)
    rows = [
        _build_runtime_project(index, project_key, project_rows, filename)
        for index, (project_key, project_rows) in enumerate(sorted(projects.items()), start=1)
    ]
    warnings: List[str] = []
    for table in tables.values():
        warnings.extend(table.get("warnings", []))
    return {
        "filename": filename,
        "file_type": "xlsx",
        "status": "parsed",
        "parse_mode": "business_package",
        "sheet_name": ",".join(tables.keys()),
        "rows": rows,
        "documents": [],
        "warnings": warnings,
        "business_summary": [
            "已识别为维修资金业务导出包。",
            f"已按业务主键聚合 {len(rows)} 个项目。",
        ],
        "sheets": [
            {
                "sheet_name": table["sheet_name"],
                "sheet_type": table.get("sheet_type") or "unknown",
                "row_count": len(table.get("rows", [])),
                "key_fields": table.get("key_fields", []),
            }
            for table in tables.values()
        ],
    }

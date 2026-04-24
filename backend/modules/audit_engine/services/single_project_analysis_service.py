from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import UploadFile

from modules.audit_engine.services.audit_pipeline_service import run_audit_pipeline
from modules.audit_engine.services.llm_field_classifier import classify_fields_with_local_llm
from modules.audit_engine.services.uploaded_file_parser import parse_uploaded_file


SEMANTIC_LLM_FIELDS = {
    "project_name",
    "project_type",
    "repair_object",
    "repair_scope",
    "repair_reason",
    "is_public_part",
    "is_private_part",
    "is_property_service_scope",
    "mixed_scope_detected",
}

FIELD_LABELS = {
    "project_name": "项目名称",
    "project_item_code": "工程编号",
    "warranty_status": "保修状态",
    "is_public_part": "共用部位/设施",
    "is_private_part": "专有部分",
    "is_property_service_scope": "物业服务范围",
    "has_vote_trace": "业主表决材料",
    "vote_date": "表决日期",
    "need_construction_contract": "是否需要施工合同",
    "has_construction_contract": "施工合同",
    "has_appraisal_contract": "审价合同 / 造价咨询合同",
    "has_appraisal_report": "审价报告 / 预算审核报告",
    "budget_amount": "预算金额",
    "contract_amount": "合同金额",
    "repair_scope": "维修范围",
    "repair_reason": "维修原因",
    "project_type": "项目类型",
    "repair_object": "维修对象",
    "mixed_scope_detected": "边界风险",
}


def _runtime_value(runtime: Any) -> Any:
    if isinstance(runtime, dict):
        return runtime.get("value")
    return runtime


def _display_value(value: Any) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    if value is None or value == "":
        return "未知"
    if value == "in_warranty":
        return "保修期内"
    if value == "out_of_warranty":
        return "已过保/保修期外"
    if value == "unknown":
        return "未知"
    return str(value)


def _raw_fields_from_standard_fields(standard_fields: Dict[str, Any]) -> Dict[str, Any]:
    return {
        field_key: _runtime_value(runtime)
        for field_key, runtime in (standard_fields or {}).items()
        if _runtime_value(runtime) is not None
    }


def _raw_text_from_row(row: Dict[str, Any]) -> str:
    parts: List[str] = []
    if row.get("project_name"):
        parts.append(f"项目名称：{row.get('project_name')}")
    if row.get("project_key"):
        parts.append(f"项目主键：{row.get('project_key')}")
    for item in row.get("business_summary") or []:
        parts.append(str(item))
    for field_key, runtime in (row.get("standard_fields") or {}).items():
        if not isinstance(runtime, dict):
            continue
        value = runtime.get("value")
        if value is not None:
            parts.append(f"{field_key}: {value}")
        for candidate in runtime.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            raw_value = candidate.get("raw_value")
            if raw_value is None or raw_value == "":
                continue
            source = ".".join(
                item
                for item in [
                    str(candidate.get("source_sheet") or ""),
                    str(candidate.get("source_column") or ""),
                ]
                if item
            )
            parts.append(f"{field_key} 来源 {source}: {raw_value}")
    return "\n".join(parts)


def _llm_candidate(field_key: str, value: Any, evidence: Optional[str]) -> Dict[str, Any]:
    return {
        "source_type": "llm",
        "source_file": "",
        "source_sheet": "llm",
        "source_column": field_key,
        "raw_value": evidence or value,
        "normalized_value": value,
        "confidence": 0.6,
    }


def _empty_runtime(field_key: str) -> Dict[str, Any]:
    return {
        "field_key": field_key,
        "value": None,
        "status": "missing",
        "candidates": [],
        "selected_index": -1,
    }


def merge_llm_fields(
    standard_fields: Dict[str, Any],
    llm_result: Dict[str, Any],
) -> Dict[str, Any]:
    final_fields = deepcopy(standard_fields or {})
    conflicts: List[Dict[str, Any]] = []
    if llm_result.get("available") is not True:
        return {"final_fields": final_fields, "field_conflicts": conflicts}

    evidence = llm_result.get("evidence") or {}
    for field_key, llm_value in (llm_result.get("fields") or {}).items():
        if field_key not in SEMANTIC_LLM_FIELDS:
            continue
        runtime = final_fields.setdefault(field_key, _empty_runtime(field_key))
        if not isinstance(runtime, dict):
            runtime = _empty_runtime(field_key)
            final_fields[field_key] = runtime

        candidate = _llm_candidate(field_key, llm_value, evidence.get(field_key))
        runtime.setdefault("candidates", []).append(candidate)
        llm_index = len(runtime["candidates"]) - 1
        current_value = runtime.get("value")

        if current_value is None and llm_value is not None:
            runtime["value"] = llm_value
            runtime["status"] = "llm_classified"
            runtime["selected_index"] = llm_index
            continue
        if current_value is not None and llm_value is not None and current_value != llm_value:
            conflicts.append(
                {
                    "field": field_key,
                    "parser_value": current_value,
                    "llm_value": llm_value,
                    "final_value": current_value,
                    "evidence": evidence.get(field_key),
                }
            )
            if runtime.get("status") != "conflicting":
                runtime["status"] = "conflicting"

    return {"final_fields": final_fields, "field_conflicts": conflicts}


def _structured_conflicts(raw_conflicts: List[Any], final_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for item in raw_conflicts or []:
        if isinstance(item, dict):
            field_key = str(item.get("field") or "")
            output.append(
                {
                    "field": field_key,
                    "field_label": FIELD_LABELS.get(field_key, field_key or "字段"),
                    "parser_value": _display_value(item.get("parser_value")),
                    "llm_value": _display_value(item.get("llm_value")),
                    "final_value": _display_value(item.get("final_value")),
                    "reason": "保守采用 parser / 规则字段作为最终值。",
                    "evidence": item.get("evidence") or "",
                }
            )
            continue
        field_key = str(item or "")
        runtime = final_fields.get(field_key, {}) if isinstance(final_fields, dict) else {}
        output.append(
            {
                "field": field_key,
                "field_label": FIELD_LABELS.get(field_key, field_key),
                "parser_value": "多来源不一致",
                "llm_value": "无",
                "final_value": _display_value(_runtime_value(runtime)),
                "reason": "parser 多来源字段存在冲突，按字段优先级保守采用最终值。",
                "evidence": "",
            }
        )
    return output


def _is_excel(filename: str) -> bool:
    return Path(filename or "").suffix.lower() in {".xlsx", ".xls"}


def _is_pdf(filename: str) -> bool:
    return Path(filename or "").suffix.lower() == ".pdf"


def _attachment_item(file: UploadFile, *, used_for_audit: bool, status: str, message: str = "") -> Dict[str, Any]:
    return {
        "filename": file.filename or "",
        "content_type": file.content_type or "application/octet-stream",
        "file_size": getattr(file, "size", None),
        "status": status,
        "used_for_audit": used_for_audit,
        "message": message,
    }


def _select_row(parsed_excel_files: List[Dict[str, Any]], warnings: List[str]) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    candidates: List[tuple[Dict[str, Any], Dict[str, Any]]] = []
    for file_result in parsed_excel_files:
        if file_result.get("status") != "parsed":
            continue
        rows = file_result.get("rows") or []
        for row in rows:
            candidates.append((file_result, row))

    if not candidates:
        return None, None

    if len(candidates) > 1:
        warnings.append(f"检测到 {len(candidates)} 个候选项目，已按第一个项目完成审计，其余请人工复核。")
    return candidates[0]


async def analyze_single_project_file(files: Iterable[UploadFile]) -> Dict[str, Any]:
    file_list = list(files)
    if not file_list:
        return {
            "status": "unsupported",
            "single_project_supported": False,
            "message": "未上传文件。",
            "attachments": [],
            "warnings": ["未上传文件。"],
        }

    warnings: List[str] = []
    attachments: List[Dict[str, Any]] = []
    parsed_excel_files: List[Dict[str, Any]] = []

    for upload in file_list:
        filename = upload.filename or ""
        if _is_excel(filename):
            parsed = await parse_uploaded_file(upload)
            parsed_excel_files.append(parsed)
            if parsed.get("status") == "parsed":
                attachments.append(_attachment_item(upload, used_for_audit=False, status="parsed"))
            else:
                attachments.append(
                    _attachment_item(
                        upload,
                        used_for_audit=False,
                        status=parsed.get("status") or "failed",
                        message=parsed.get("message") or "Excel 解析失败。",
                    )
                )
                warnings.extend(parsed.get("warnings") or [])
            continue

        if _is_pdf(filename):
            attachments.append(_attachment_item(upload, used_for_audit=False, status="attached", message="PDF 已接收，本期仅附件展示。"))
            continue

        attachments.append(_attachment_item(upload, used_for_audit=False, status="ignored", message="当前仅 Excel 参与审计。"))
        warnings.append(f"{filename} 非本期审计输入，已作为附件保留。")

    if not parsed_excel_files:
        warnings.append("未检测到可用于审计的 Excel 文件。")
        return {
            "status": "unsupported",
            "single_project_supported": False,
            "message": "未检测到可用于审计的 Excel 文件。",
            "attachments": attachments,
            "warnings": warnings,
            "field_conflicts": [],
            "raw_fields": {},
            "llm_result": {"available": False, "error_message": "无可审计 Excel"},
        }

    selected = _select_row(parsed_excel_files, warnings)
    if not selected or not selected[0] or not selected[1]:
        return {
            "status": "manual_review",
            "single_project_supported": False,
            "message": "Excel 文件未解析到可审计项目。",
            "attachments": attachments,
            "warnings": warnings + ["Excel 文件未解析到可审计项目。"],
            "field_conflicts": [],
            "raw_fields": {},
            "llm_result": {"available": False, "error_message": "无可审计项目"},
        }

    file_result, row = selected

    # Mark only the selected Excel as the active audit source.
    selected_name = file_result.get("filename") or ""
    for item in attachments:
        if item["filename"] == selected_name and item["status"] == "parsed":
            item["used_for_audit"] = True
            item["status"] = "used_for_audit"
            break

    raw_fields = _raw_fields_from_standard_fields(row.get("standard_fields") or {})
    raw_text = _raw_text_from_row(row)
    llm_result = classify_fields_with_local_llm(raw_fields, raw_text)
    merged = merge_llm_fields(row.get("standard_fields") or {}, llm_result)
    field_conflicts = list(row.get("conflicting_fields") or []) + merged["field_conflicts"]
    structured_conflicts = _structured_conflicts(field_conflicts, merged["final_fields"])

    final_request = dict(row.get("audit_request") or {})
    final_request["standard_fields"] = merged["final_fields"]
    final_request["warnings"] = list(final_request.get("warnings") or []) + [
        "本地 LLM 字段归类仅作辅助，最终审计结论由规则引擎输出。"
    ]

    llm_warnings = list(llm_result.get("warnings") or [])
    warnings.extend(llm_warnings)
    if llm_result.get("available") is not True:
        warnings.append("本地 LLM 不可用，已跳过 AI 字段归类。")
    if field_conflicts:
        warnings.append("存在 parser 与 LLM 或多来源字段冲突，建议人工复核。")

    audit_result = run_audit_pipeline(final_request)
    return {
        "status": "analyzed",
        "single_project_supported": True,
        "filename": file_result.get("filename"),
        "parse_mode": file_result.get("parse_mode"),
        "project_key": row.get("project_key"),
        "project_name": row.get("project_name"),
        "source_sheets": row.get("source_sheets") or [],
        "business_summary": row.get("business_summary") or [],
        "attachments": attachments,
        "raw_fields": raw_fields,
        "llm_result": llm_result,
        "final_fields": merged["final_fields"],
        "field_conflicts": structured_conflicts,
        "audit_result": audit_result,
        "warnings": warnings + list(row.get("warnings") or []),
    }

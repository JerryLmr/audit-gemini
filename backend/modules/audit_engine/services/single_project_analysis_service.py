from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import UploadFile

from modules.audit_engine.core.field_resolver import resolve_all_fields, runtime_values
from modules.audit_engine.core.field_runtime import FieldCandidate
from modules.audit_engine.services.audit_pipeline_service import run_audit_pipeline
from modules.audit_engine.services.audit_view_builder import build_audit_view
from modules.audit_engine.services.llm_field_classifier import classify_fields_with_local_llm
from modules.audit_engine.services.mapping_service import map_project_name
from modules.audit_engine.services.pdf_evidence_mapper import map_pdf_parse_results_to_field_candidates
from modules.audit_engine.services.pdf_material_parser import parse_pdf_material
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
    "budget_amount": "预算金额",
    "final_amount": "决算/最终金额",
    "repair_scope": "维修范围",
    "repair_reason": "维修原因",
    "vote_start_date": "征询开始日期",
    "vote_end_date": "征询结束日期",
    "resolution_date": "决议生成日期",
    "registration_date": "录入日期",
    "vote_pass_rate_by_household": "按户数通过率",
    "vote_pass_rate_by_area": "按面积通过率",
}


def _runtime_value(runtime: Any) -> Any:
    if isinstance(runtime, dict):
        return runtime.get("value")
    return runtime


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


def _attachment_item_from_pdf(parsed_pdf: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "filename": parsed_pdf.get("filename") or parsed_pdf.get("file_name") or "",
        "content_type": "application/pdf",
        "file_size": None,
        "status": parsed_pdf.get("status") or "failed",
        "used_for_audit": False,
        "message": parsed_pdf.get("message") or "",
        "material_type": parsed_pdf.get("material_type") or "unknown_pdf",
        "material_type_label": parsed_pdf.get("material_type_label") or "未识别PDF材料",
    }


def _select_row(parsed_excel_files: List[Dict[str, Any]], warnings: List[str]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    candidates: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for file_result in parsed_excel_files:
        if file_result.get("status") != "parsed":
            continue
        for row in file_result.get("rows") or []:
            candidates.append((file_result, row))
    if not candidates:
        return None, None
    if len(candidates) > 1:
        warnings.append(f"检测到 {len(candidates)} 个候选项目，已按第一个项目完成审计，其余请人工复核。")
    return candidates[0]


def _row_candidates(standard_fields_runtime: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for field_key, runtime in (standard_fields_runtime or {}).items():
        if not isinstance(runtime, dict):
            continue
        items = [c for c in (runtime.get("candidates") or []) if isinstance(c, dict)]
        if items:
            out[field_key] = items
    return out


def _normalize_candidates_for_resolver(candidates_by_field: Dict[str, List[Any]]) -> Dict[str, List[FieldCandidate]]:
    normalized: Dict[str, List[FieldCandidate]] = {}
    for field_key, items in (candidates_by_field or {}).items():
        bucket: List[FieldCandidate] = []
        for item in items or []:
            if isinstance(item, FieldCandidate):
                bucket.append(item)
                continue
            if isinstance(item, dict):
                bucket.append(FieldCandidate.from_dict(item))
        if bucket:
            normalized[field_key] = bucket
    return normalized


def _raw_fields_from_standard_fields(standard_fields: Dict[str, Any]) -> Dict[str, Any]:
    return {
        field_key: _runtime_value(runtime)
        for field_key, runtime in (standard_fields or {}).items()
        if _runtime_value(runtime) is not None
    }


def _external_flat_fields(standard_fields: Dict[str, Any]) -> Dict[str, Any]:
    values = runtime_values(standard_fields)
    values.pop("vote_date", None)
    return values


def _raw_text_from_row(row: Dict[str, Any], standard_fields: Dict[str, Any]) -> str:
    parts: List[str] = []
    if row.get("project_name"):
        parts.append(f"项目名称：{row.get('project_name')}")
    for field_key, runtime in (standard_fields or {}).items():
        if not isinstance(runtime, dict):
            continue
        value = runtime.get("value")
        if value is not None:
            parts.append(f"{field_key}: {value}")
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
        "metadata": {"evidence": evidence or ""},
    }


def merge_llm_fields(standard_fields: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
    final_fields = {k: dict(v) if isinstance(v, dict) else v for k, v in (standard_fields or {}).items()}
    conflicts: List[Dict[str, Any]] = []
    if llm_result.get("available") is not True:
        return {"final_fields": final_fields, "field_conflicts": conflicts}
    evidence = llm_result.get("evidence") or {}
    for field_key, llm_value in (llm_result.get("fields") or {}).items():
        if field_key not in SEMANTIC_LLM_FIELDS:
            continue
        runtime = final_fields.setdefault(field_key, {"field_key": field_key, "value": None, "status": "missing", "candidates": [], "selected_index": -1})
        if not isinstance(runtime, dict):
            continue
        runtime.setdefault("candidates", []).append(_llm_candidate(field_key, llm_value, evidence.get(field_key)))
        if runtime.get("value") is None and llm_value is not None:
            runtime["value"] = llm_value
            runtime["status"] = "llm_classified"
            runtime["selected_index"] = len(runtime["candidates"]) - 1
        elif runtime.get("value") is not None and llm_value is not None and runtime.get("value") != llm_value:
            conflicts.append(
                {
                    "field": field_key,
                    "field_label": FIELD_LABELS.get(field_key, field_key),
                    "parser_value": runtime.get("value"),
                    "llm_value": llm_value,
                    "final_value": runtime.get("value"),
                    "reason": "保守采用 parser/规则字段。",
                }
            )
            runtime["status"] = "conflicting"
    return {"final_fields": final_fields, "field_conflicts": conflicts}


def _build_field_sources(standard_fields: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    field_sources: Dict[str, List[Dict[str, Any]]] = {}
    for field_key, runtime in (standard_fields or {}).items():
        if not isinstance(runtime, dict):
            continue
        sources = []
        seen = set()
        for c in runtime.get("candidates") or []:
            if not isinstance(c, dict):
                continue
            dedupe_key = (
                field_key,
                str(c.get("source_file") or ""),
                str(c.get("source_column") or ""),
                repr(c.get("normalized_value")),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            sources.append(
                {
                    "source_type": c.get("source_type"),
                    "file_name": c.get("source_file"),
                    "source_field": c.get("source_column"),
                    "source_sheet": c.get("source_sheet"),
                    "value": c.get("normalized_value"),
                    "confidence": c.get("confidence"),
                    "metadata": c.get("metadata") if isinstance(c.get("metadata"), dict) else {},
                }
            )
        if sources:
            field_sources[field_key] = sources
    return field_sources


def _build_structured_conflicts(standard_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    for field_key, runtime in (standard_fields or {}).items():
        if not isinstance(runtime, dict) or runtime.get("status") != "conflicting":
            continue
        selected_index = runtime.get("selected_index", -1)
        candidates = [c for c in (runtime.get("candidates") or []) if isinstance(c, dict)]
        selected = candidates[selected_index] if isinstance(selected_index, int) and 0 <= selected_index < len(candidates) else None
        pdf_candidate = next((c for c in candidates if c.get("source_type") == "pdf"), None)
        excel_candidate = next((c for c in candidates if c.get("source_type") == "excel"), None)
        scored = []
        for c in candidates:
            score = float(c.get("confidence") or 0) + float(((c.get("metadata") or {}).get("quality_score") or 0))
            scored.append((c, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        score_gap = round(scored[0][1] - scored[1][1], 3) if len(scored) >= 2 else None
        conflicts.append(
            {
                "field": field_key,
                "field_label": FIELD_LABELS.get(field_key, field_key),
                "final_value": runtime.get("value"),
                "pdf_value": pdf_candidate.get("normalized_value") if pdf_candidate else None,
                "excel_value": excel_candidate.get("normalized_value") if excel_candidate else None,
                "chosen_source": selected.get("source_type") if selected else "",
                "score_gap": score_gap,
                "reason": "多来源不一致，系统按优先级选值，建议人工复核。",
            }
        )
    return conflicts


def _dedupe_material_evidence(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    seen = set()
    for item in items or []:
        key = (
            str(item.get("standard_field") or ""),
            str(item.get("file_name") or ""),
            str(item.get("raw_field") or ""),
            repr(item.get("value")),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


async def analyze_single_project_file(files: Iterable[UploadFile]) -> Dict[str, Any]:
    file_list = list(files)
    if not file_list:
        return {"audit_view": build_audit_view(status="unsupported", message="未上传文件。", attachments=[], warnings=["未上传文件。"])}

    warnings: List[str] = []
    attachments: List[Dict[str, Any]] = []
    parsed_excel_files: List[Dict[str, Any]] = []
    pdf_parse_results: List[Dict[str, Any]] = []

    for upload in file_list:
        filename = upload.filename or ""
        if _is_excel(filename):
            parsed = await parse_uploaded_file(upload)
            parsed_excel_files.append(parsed)
            attachments.append(_attachment_item(upload, used_for_audit=False, status=parsed.get("status") or "failed", message=parsed.get("message") or ""))
            warnings.extend(parsed.get("warnings") or [])
            continue
        if _is_pdf(filename):
            parsed_pdf = parse_pdf_material(filename, await upload.read())
            pdf_parse_results.append(parsed_pdf)
            attachments.append(_attachment_item_from_pdf(parsed_pdf))
            warnings.extend(parsed_pdf.get("warnings") or [])
            continue
        attachments.append(_attachment_item(upload, used_for_audit=False, status="ignored", message="当前仅 Excel/PDF 参与审计。"))

    if not parsed_excel_files:
        warnings.append("未检测到可用于主审计的 Excel 文件。")
        pdf_mapped = map_pdf_parse_results_to_field_candidates(pdf_parse_results)
        return {
            "audit_view": build_audit_view(
                status="unsupported",
                message="未检测到可用于主审计的 Excel 文件。",
                attachments=attachments,
                pdf_parse_results=pdf_parse_results,
                llm_result={"available": False, "error_message": "无可审计 Excel"},
                warnings=warnings,
                flat_standard_fields={},
                field_sources={},
                material_evidence=_dedupe_material_evidence(pdf_mapped["material_evidence"]),
                field_conflicts=[],
                user_overrides=[],
            )
        }

    selected = _select_row(parsed_excel_files, warnings)
    if not selected or not selected[0] or not selected[1]:
        return {"audit_view": build_audit_view(status="manual_review", message="Excel 文件未解析到可审计项目。", attachments=attachments, warnings=warnings)}

    file_result, row = selected
    selected_name = file_result.get("filename") or ""
    for item in attachments:
        if item.get("filename") == selected_name and item.get("status") == "parsed":
            item["used_for_audit"] = True
            item["status"] = "used_for_audit"

    excel_candidates = _row_candidates(row.get("standard_fields") or {})
    pdf_mapped = map_pdf_parse_results_to_field_candidates(pdf_parse_results)
    merged_candidates: Dict[str, List[Any]] = {k: list(v) for k, v in excel_candidates.items()}
    for field_key, candidates in (pdf_mapped.get("field_candidates") or {}).items():
        merged_candidates.setdefault(field_key, []).extend(candidates)
    normalized_candidates = _normalize_candidates_for_resolver(merged_candidates)
    resolved = resolve_all_fields(normalized_candidates, catalog_mapper=map_project_name)
    raw_fields = _raw_fields_from_standard_fields(resolved["standard_fields"])
    raw_text = _raw_text_from_row(row, resolved["standard_fields"])
    llm_result = classify_fields_with_local_llm(raw_fields, raw_text)
    merged = merge_llm_fields(resolved["standard_fields"], llm_result)

    final_request = dict(row.get("audit_request") or {})
    final_request["standard_fields"] = merged["final_fields"]
    final_request["warnings"] = list(final_request.get("warnings") or []) + ["本地 LLM 字段归类仅作辅助，最终审计结论由规则引擎输出。"]
    audit_result = run_audit_pipeline(final_request)

    field_conflicts = _build_structured_conflicts(merged["final_fields"])
    if field_conflicts:
        warnings.append("Excel 与 PDF 存在字段冲突，建议人工复核。")

    return {
        "audit_view": build_audit_view(
            status="analyzed",
            attachments=attachments,
            pdf_parse_results=pdf_parse_results,
            standard_fields=merged["final_fields"],
            source_sheets=row.get("source_sheets") or [],
            llm_result=llm_result,
            audit_result=audit_result,
            warnings=warnings + list(row.get("warnings") or []) + list(llm_result.get("warnings") or []),
            field_conflicts=field_conflicts,
            flat_standard_fields=_external_flat_fields(merged["final_fields"]),
            field_sources=_build_field_sources(merged["final_fields"]),
            material_evidence=_dedupe_material_evidence(pdf_mapped["material_evidence"]),
            user_overrides=[],
        )
    }

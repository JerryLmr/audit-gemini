from __future__ import annotations

import re
from typing import Any, Dict, List

from modules.audit_engine.core.field_runtime import FieldCandidate
from modules.audit_engine.core.field_resolver import make_candidate
from modules.audit_engine.services.excel_row_mapper import STANDARD_FIELD_TYPES


PDF_FIELD_TO_STANDARD_FIELD: Dict[str, str] = {
    "project_name": "project_name",
    "repair_scope": "repair_scope",
    "repair_reason": "repair_reason",
    "budget_amount": "budget_amount",
    "resolution_no": "resolution_no",
    "print_date": "print_date",
    "vote_start_date": "vote_start_date",
    "vote_end_date": "vote_end_date",
    "resolution_date": "resolution_date",
    "registration_date": "registration_date",
    "vote_passed": "vote_passed",
    "agree_hou": "vote_approved_households",
    "agree_area": "vote_approved_area",
    "count_hou": "vote_total_households",
    "sum_area": "vote_total_area",
}

POLLUTION_KEYWORDS = ["预算金额", "决策主体", "施工单位", "工程验收单位", "根据《"]


def _candidate_quality(raw_field: str, value: Any, raw_text: str, confidence: float) -> Dict[str, Any]:
    text = str(value or "")
    flags: List[str] = []
    penalty = 0.0

    if raw_field == "repair_scope" and (len(text) > 180 or len(text) < 4):
        penalty += 0.15
        flags.append("length_abnormal")
    if raw_field == "repair_reason" and (len(text) > 120 or len(text) < 4):
        penalty += 0.15
        flags.append("length_abnormal")
    if raw_field in {"budget_amount", "final_amount", "agree_hou", "agree_area", "count_hou", "sum_area"} and isinstance(value, (int, float)) and float(value) == 0.0:
        flags.append("zero_suspicious")

    pollution_hit = any(keyword in text or keyword in str(raw_text or "") for keyword in POLLUTION_KEYWORDS)
    if pollution_hit:
        penalty += 0.5
        flags.append("semantic_pollution")

    score = max(0.0, min(1.0, float(confidence or 0) - penalty))
    return {"quality_score": round(score, 3), "quality_flags": flags}


def map_pdf_parse_results_to_field_candidates(pdf_parse_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates_by_field: Dict[str, List[FieldCandidate]] = {}
    for pdf in pdf_parse_results or []:
        filename = str(pdf.get("filename") or pdf.get("file_name") or "")
        material_type = str(pdf.get("material_type") or "")
        for item in pdf.get("extracted_fields") or []:
            if not isinstance(item, dict):
                continue
            raw_field = str(item.get("raw_field") or "")
            standard_field = PDF_FIELD_TO_STANDARD_FIELD.get(raw_field)
            if not standard_field:
                continue
            if standard_field not in STANDARD_FIELD_TYPES:
                continue
            value = item.get("value")
            if value is None or value == "":
                continue
            confidence = float(item.get("confidence") or 0.85)
            candidate = make_candidate(
                field_type=STANDARD_FIELD_TYPES.get(standard_field, ""),
                source_type="pdf",
                source_file=filename,
                source_sheet=material_type or "pdf",
                source_column=raw_field,
                raw_value=value,
                confidence=confidence,
            )
            quality = _candidate_quality(raw_field, value, item.get("raw_text") or "", confidence)
            candidate.metadata = {
                "page": item.get("page"),
                "raw_text": item.get("raw_text") or "",
                "material_type": material_type,
                "label": item.get("label") or "",
                "source_field_label": item.get("label") or raw_field,
                "quality_score": quality["quality_score"],
                "quality_flags": quality["quality_flags"],
            }
            candidates_by_field.setdefault(standard_field, []).append(candidate)
    return {"field_candidates": candidates_by_field}

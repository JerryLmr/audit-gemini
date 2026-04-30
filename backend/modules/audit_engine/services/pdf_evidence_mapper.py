from __future__ import annotations

from typing import Any, Dict, List

from modules.audit_engine.core.field_runtime import FieldCandidate
from modules.audit_engine.core.field_resolver import make_candidate
from modules.audit_engine.services.excel_row_mapper import STANDARD_FIELD_TYPES


PDF_FIELD_TO_STANDARD_FIELD: Dict[str, str] = {
    "material_id": "project_item_code",
    "project_name": "project_name",
    "repair_scope": "repair_scope",
    "repair_reason": "repair_reason",
    "budget_amount": "budget_amount",
    "decision_subject": "decision_subject",
    "construction_unit_select_method": "contractor_selection_method",
    "acceptance_unit": "acceptance_unit",
    "management_unit": "construction_management_unit",
    "resolution_no": "resolution_no",
    "print_date": "print_date",
    "has_owner_meeting_seal": "has_owner_meeting_seal",
    "director_signed": "director_signed",
    "deputy_director_signed": "deputy_director_signed",
    "vote_date": "vote_date",
    "vote_passed": "vote_passed",
    "agree_count_rate": "vote_pass_rate_by_household",
    "agree_area_rate": "vote_pass_rate_by_area",
}


def map_pdf_parse_results_to_field_candidates(pdf_parse_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    candidates_by_field: Dict[str, List[FieldCandidate]] = {}
    material_evidence: List[Dict[str, Any]] = []

    for pdf in pdf_parse_results or []:
        filename = str(pdf.get("filename") or pdf.get("file_name") or "")
        material_type = str(pdf.get("material_type") or "")
        for item in pdf.get("raw_evidence") or []:
            if not isinstance(item, dict):
                continue
            raw_field = str(item.get("raw_field") or "")
            standard_field = PDF_FIELD_TO_STANDARD_FIELD.get(raw_field)
            if not standard_field:
                continue
            value = item.get("value")
            if value is None or value == "":
                continue
            candidate = make_candidate(
                field_type=STANDARD_FIELD_TYPES.get(standard_field, ""),
                source_type="pdf",
                source_file=filename,
                source_sheet=material_type or "pdf",
                source_column=raw_field,
                raw_value=value,
                confidence=float(item.get("confidence") or 0.85),
            )
            candidate.metadata = {
                "page": item.get("page"),
                "raw_text": item.get("raw_text") or "",
                "material_type": material_type,
                "label": item.get("label") or "",
            }
            candidates_by_field.setdefault(standard_field, []).append(candidate)
            material_evidence.append(
                {
                    "standard_field": standard_field,
                    "field_label": item.get("label") or standard_field,
                    "file_name": filename,
                    "material_type": material_type,
                    "page": item.get("page"),
                    "raw_field": raw_field,
                    "raw_text": item.get("raw_text") or "",
                    "value": candidate.normalized_value,
                    "confidence": candidate.confidence,
                }
            )
    return {"field_candidates": candidates_by_field, "material_evidence": material_evidence}

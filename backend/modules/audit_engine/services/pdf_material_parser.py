from __future__ import annotations

import io
import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber


MATERIAL_TYPE_LABELS = {
    "repair_plan_pdf": "维修预案",
    "implementation_plan_pdf": "维修工程实施方案",
    "vote_summary_pdf": "征求意见汇总表",
    "resolution_pdf": "业主大会决议",
    "unknown_pdf": "未识别PDF材料",
}

FIELD_LABELS = {
    "project_name": "工程名称",
    "repair_scope": "实施范围",
    "repair_reason": "维修原因",
    "budget_amount": "预算金额",
    "decision_subject": "决策主体",
    "construction_unit_select_method": "施工单位选择方式",
    "acceptance_unit": "工程验收单位",
    "management_unit": "施工管理单位",
    "print_date": "打印日期",
    "final_amount": "决案总金额",
    "decision_amount": "决案金额",
    "repair_object": "维修设施设备名称",
    "share_type": "分摊类型",
    "share_scope": "分摊范围",
    "share_area": "分摊面积",
    "construction_unit": "施工单位",
    "estimated_implementation_date": "预计实施时间",
    "material_id": "资料ID",
    "consultation_date": "征询时间",
    "vote_date": "表决时间",
    "vote_passed": "是否通过",
    "total_vote_count": "总投票权数",
    "total_vote_area": "总投票面积",
    "agree_count": "同意票数",
    "agree_area": "同意面积",
    "agree_count_rate": "同意票数比例",
    "agree_area_rate": "同意面积比例",
    "resolution_no": "编号",
    "vote_start_date": "征询开始日期",
    "vote_end_date": "征询结束日期",
    "has_owner_meeting_seal": "业主大会公章是否出现",
    "director_signed": "主任是否出现签章",
    "deputy_director_signed": "副主任是否出现签章",
}


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _normalize_amount(raw: str) -> Optional[float]:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", raw)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_percent(raw: str) -> Optional[float]:
    if not raw:
        return None
    cleaned = raw.replace("%", "").strip()
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_date(raw: str) -> Optional[str]:
    if not raw:
        return None
    text = raw.strip()
    m = re.search(r"(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?", text)
    if not m:
        return None
    try:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return d.isoformat()


def _scan_bool(text: str, keywords: List[str]) -> Optional[bool]:
    lower_text = text.lower()
    for kw in keywords:
        if kw.lower() in lower_text:
            return True
    return None


def _material_type(filename: str, first_page_text: str, full_text: str) -> str:
    text = f"{filename} {first_page_text} {full_text}"
    if "打印维修预案" in text or "物业大修和专项维修、更新、改造实施方案公示" in text:
        return "repair_plan_pdf"
    if "打印维修工程实施方案" in text or "维修工程实施方案" in text:
        return "implementation_plan_pdf"
    if "实施方案征求意见汇总表" in text or "征求意见汇总表" in text:
        return "vote_summary_pdf"
    if "打印决议" in text or "关于物业大修和专项维修、更新、改造使用维修资金的决议" in text:
        return "resolution_pdf"
    return "unknown_pdf"


def _build_evidence(
    *,
    filename: str,
    page: int,
    source_field: str,
    raw_value: str,
    normalized_value: Any,
    confidence: float,
) -> Dict[str, Any]:
    return {
        "source_type": "pdf",
        "source_file": filename,
        "source_page": page,
        "source_field": source_field,
        "raw_value": raw_value,
        "normalized_value": normalized_value,
        "confidence": confidence,
    }


def _match_field(
    *,
    filename: str,
    pages: List[str],
    pattern: str,
    source_field: str,
    value_type: str = "text",
    confidence: float = 0.85,
    flags: int = 0,
) -> Optional[Dict[str, Any]]:
    for idx, page_text in enumerate(pages, start=1):
        match = re.search(pattern, page_text, flags=flags)
        if not match:
            continue
        raw = _normalize_text(match.group(1))
        if not raw:
            continue
        normalized: Any = raw
        if value_type == "amount":
            normalized = _normalize_amount(raw)
        elif value_type == "date":
            normalized = _normalize_date(raw)
        elif value_type == "percent":
            normalized = _normalize_percent(raw)
        if value_type in {"amount", "date", "percent"} and normalized is None:
            return None
        return _build_evidence(
            filename=filename,
            page=idx,
            source_field=source_field,
            raw_value=raw,
            normalized_value=normalized,
            confidence=confidence,
        )
    return None


def _extract_fields(material_type: str, filename: str, pages: List[str], full_text: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    extracted: Dict[str, Any] = {}
    snippets: List[Dict[str, Any]] = []

    def put(field_key: str, evidence: Optional[Dict[str, Any]]) -> None:
        extracted[field_key] = evidence
        if evidence:
            snippets.append(evidence)

    # 通用字段
    put(
        "project_name",
        _match_field(
            filename=filename,
            pages=pages,
            pattern=r"(?:工程名称|项目名称)\s*[：:]\s*([^\n]{2,120})",
            source_field="工程名称",
            confidence=0.9,
        ),
    )
    put(
        "print_date",
        _match_field(
            filename=filename,
            pages=pages,
            pattern=r"打印日期\s*[：:]\s*([0-9]{4}[年/\-.][0-9]{1,2}[月/\-.][0-9]{1,2}日?)",
            source_field="打印日期",
            value_type="date",
            confidence=0.88,
        ),
    )
    put(
        "material_id",
        _match_field(
            filename=filename,
            pages=pages,
            pattern=r"(?:资料ID|资料编号|编号)\s*[：:]\s*([A-Za-z0-9\-_]{3,80})",
            source_field="资料ID",
            confidence=0.82,
        ),
    )

    if material_type == "repair_plan_pdf":
        put("repair_scope", _match_field(filename=filename, pages=pages, pattern=r"实施范围\s*[：:]\s*([^\n]{2,200})", source_field="实施范围"))
        put("repair_reason", _match_field(filename=filename, pages=pages, pattern=r"维修原因\s*[：:]\s*([^\n]{2,200})", source_field="维修原因"))
        put("budget_amount", _match_field(filename=filename, pages=pages, pattern=r"(?:维修资金预算金额|预算金额)\s*[：:]\s*([￥¥]?\s*[\d,]+(?:\.\d+)?\s*元?)", source_field="维修资金预算金额", value_type="amount", confidence=0.86))
        put("decision_subject", _match_field(filename=filename, pages=pages, pattern=r"决策主体\s*[：:]\s*([^\n]{2,120})", source_field="决策主体"))
        put("construction_unit_select_method", _match_field(filename=filename, pages=pages, pattern=r"施工单位选择方式\s*[：:]\s*([^\n]{2,120})", source_field="施工单位选择方式"))
        put("acceptance_unit", _match_field(filename=filename, pages=pages, pattern=r"工程验收单位\s*[：:]\s*([^\n]{2,120})", source_field="工程验收单位"))
        put("management_unit", _match_field(filename=filename, pages=pages, pattern=r"施工管理单位\s*[：:]\s*([^\n]{2,120})", source_field="施工管理单位"))

    if material_type == "implementation_plan_pdf":
        put("final_amount", _match_field(filename=filename, pages=pages, pattern=r"(?:决案总金额|决案金额)\s*[：:]\s*([￥¥]?\s*[\d,]+(?:\.\d+)?\s*元?)", source_field="决案总金额", value_type="amount", confidence=0.86))
        put("decision_amount", _match_field(filename=filename, pages=pages, pattern=r"决案金额\s*[：:]\s*([￥¥]?\s*[\d,]+(?:\.\d+)?\s*元?)", source_field="决案金额", value_type="amount", confidence=0.86))
        put("repair_object", _match_field(filename=filename, pages=pages, pattern=r"维修设施设备名称\s*[：:]\s*([^\n]{2,200})", source_field="维修设施设备名称"))
        put("share_type", _match_field(filename=filename, pages=pages, pattern=r"分摊类型\s*[：:]\s*([^\n]{2,120})", source_field="分摊类型"))
        put("share_scope", _match_field(filename=filename, pages=pages, pattern=r"分摊范围\s*[：:]\s*([^\n]{2,200})", source_field="分摊范围"))
        put("share_area", _match_field(filename=filename, pages=pages, pattern=r"分摊面积\s*[：:]\s*([\d,]+(?:\.\d+)?)", source_field="分摊面积", value_type="amount", confidence=0.82))
        put("construction_unit", _match_field(filename=filename, pages=pages, pattern=r"施工单位\s*[：:]\s*([^\n]{2,120})", source_field="施工单位"))
        put("management_unit", _match_field(filename=filename, pages=pages, pattern=r"施工管理单位\s*[：:]\s*([^\n]{2,120})", source_field="施工管理单位"))
        put("acceptance_unit", _match_field(filename=filename, pages=pages, pattern=r"工程验收单位\s*[：:]\s*([^\n]{2,120})", source_field="工程验收单位"))
        put("estimated_implementation_date", _match_field(filename=filename, pages=pages, pattern=r"预计实施时间\s*[：:]\s*([0-9]{4}[年/\-.][0-9]{1,2}[月/\-.][0-9]{1,2}日?)", source_field="预计实施时间", value_type="date", confidence=0.84))

    if material_type == "vote_summary_pdf":
        put("consultation_date", _match_field(filename=filename, pages=pages, pattern=r"(?:征询时间|表决时间)\s*[：:]\s*([0-9]{4}[年/\-.][0-9]{1,2}[月/\-.][0-9]{1,2}日?)", source_field="征询时间", value_type="date", confidence=0.86))
        put("vote_date", _match_field(filename=filename, pages=pages, pattern=r"表决时间\s*[：:]\s*([0-9]{4}[年/\-.][0-9]{1,2}[月/\-.][0-9]{1,2}日?)", source_field="表决时间", value_type="date", confidence=0.86))
        put("total_vote_count", _match_field(filename=filename, pages=pages, pattern=r"总投票权数\s*[：:]\s*([\d,]+(?:\.\d+)?)", source_field="总投票权数", value_type="amount", confidence=0.82))
        put("total_vote_area", _match_field(filename=filename, pages=pages, pattern=r"总投票面积\s*[：:]\s*([\d,]+(?:\.\d+)?)", source_field="总投票面积", value_type="amount", confidence=0.82))
        put("agree_count", _match_field(filename=filename, pages=pages, pattern=r"同意票数\s*[：:]\s*([\d,]+(?:\.\d+)?)", source_field="同意票数", value_type="amount", confidence=0.82))
        put("agree_area", _match_field(filename=filename, pages=pages, pattern=r"同意面积\s*[：:]\s*([\d,]+(?:\.\d+)?)", source_field="同意面积", value_type="amount", confidence=0.82))
        put("agree_count_rate", _match_field(filename=filename, pages=pages, pattern=r"同意票数比例\s*[：:]\s*([\d.]+%)", source_field="同意票数比例", value_type="percent", confidence=0.8))
        put("agree_area_rate", _match_field(filename=filename, pages=pages, pattern=r"同意面积比例\s*[：:]\s*([\d.]+%)", source_field="同意面积比例", value_type="percent", confidence=0.8))
        passed = _scan_bool(full_text, ["表决通过", "已通过", "通过"])
        put(
            "vote_passed",
            _build_evidence(
                filename=filename,
                page=1,
                source_field="是否通过",
                raw_value="表决通过" if passed is True else "",
                normalized_value=passed,
                confidence=0.78,
            ) if passed is not None else None,
        )

    if material_type == "resolution_pdf":
        put("resolution_no", _match_field(filename=filename, pages=pages, pattern=r"(?:编号|决议编号)\s*[：:]\s*([A-Za-z0-9\-_]{2,80})", source_field="编号", confidence=0.84))
        put("vote_start_date", _match_field(filename=filename, pages=pages, pattern=r"(?:征询开始日期|发送征求意见表开始日期)\s*[：:]\s*([0-9]{4}[年/\-.][0-9]{1,2}[月/\-.][0-9]{1,2}日?)", source_field="征询开始日期", value_type="date", confidence=0.86))
        put("vote_end_date", _match_field(filename=filename, pages=pages, pattern=r"(?:征询结束日期|发送征求意见表结束日期)\s*[：:]\s*([0-9]{4}[年/\-.][0-9]{1,2}[月/\-.][0-9]{1,2}日?)", source_field="征询结束日期", value_type="date", confidence=0.86))
        put("budget_amount", _match_field(filename=filename, pages=pages, pattern=r"(?:原维修资金预算金额|预算金额)\s*[：:]\s*([￥¥]?\s*[\d,]+(?:\.\d+)?\s*元?)", source_field="原维修资金预算金额", value_type="amount", confidence=0.86))
        put("final_amount", _match_field(filename=filename, pages=pages, pattern=r"(?:工程决案总金额|决案总金额)\s*[：:]\s*([￥¥]?\s*[\d,]+(?:\.\d+)?\s*元?)", source_field="工程决案总金额", value_type="amount", confidence=0.86))
        owner_seal = _scan_bool(full_text, ["业主大会公章", "业主大会（公章）", "业主大会盖章"])
        director_sign = _scan_bool(full_text, ["主任", "主任签字", "主任签章"])
        deputy_sign = _scan_bool(full_text, ["副主任", "副主任签字", "副主任签章"])
        put("has_owner_meeting_seal", _build_evidence(filename=filename, page=1, source_field="业主大会公章", raw_value="业主大会公章", normalized_value=owner_seal, confidence=0.8) if owner_seal is not None else None)
        put("director_signed", _build_evidence(filename=filename, page=1, source_field="主任签章", raw_value="主任签章", normalized_value=director_sign, confidence=0.78) if director_sign is not None else None)
        put("deputy_director_signed", _build_evidence(filename=filename, page=1, source_field="副主任签章", raw_value="副主任签章", normalized_value=deputy_sign, confidence=0.78) if deputy_sign is not None else None)

    return extracted, snippets


def parse_pdf_material(filename: str, content: bytes) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "filename": filename,
        "status": "failed",
        "material_type": "unknown_pdf",
        "material_type_label": MATERIAL_TYPE_LABELS["unknown_pdf"],
        "pages_count": 0,
        "extracted_fields": {},
        "evidence_snippets": [],
        "warnings": [],
    }
    try:
        pages: List[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            result["pages_count"] = len(pdf.pages)
            for page in pdf.pages:
                pages.append(_normalize_text(page.extract_text() or ""))
        full_text = "\n".join([item for item in pages if item])
        if not full_text.strip():
            result["status"] = "scan_or_unreadable"
            result["message"] = "当前 PDF 未提取到文本，疑似扫描件，暂未启用 OCR"
            result["warnings"] = ["当前 PDF 未提取到文本，疑似扫描件，暂未启用 OCR"]
            return result

        material_type = _material_type(filename, pages[0] if pages else "", full_text)
        result["material_type"] = material_type
        result["material_type_label"] = MATERIAL_TYPE_LABELS[material_type]
        extracted_fields, snippets = _extract_fields(material_type, filename, pages, full_text)
        result["extracted_fields"] = extracted_fields
        result["evidence_snippets"] = snippets
        if material_type == "unknown_pdf":
            result["status"] = "unrecognized_pdf"
            result["message"] = "未识别为预设的审计材料类型。"
        else:
            result["status"] = "parsed_pdf"
            result["message"] = "PDF 文本解析完成。"
        return result
    except Exception as exc:
        result["status"] = "failed"
        result["message"] = f"PDF 解析失败：{exc}"
        result["warnings"] = [str(exc)]
        return result

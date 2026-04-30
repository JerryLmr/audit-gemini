from __future__ import annotations

import io
import re
from datetime import date
from typing import Any, Dict, List, Optional

import pdfplumber


MATERIAL_TYPE_LABELS = {
    "repair_plan_pdf": "维修预案",
    "vote_summary_pdf": "征求意见汇总表",
    "resolution_pdf": "业主大会决议",
    "unknown_pdf": "未识别PDF材料",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _to_amount(raw: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.\-]", "", raw or "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_date(raw: str) -> Optional[str]:
    m = re.search(r"(\d{4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?", raw or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def _to_percent(raw: str) -> Optional[float]:
    cleaned = re.sub(r"[^\d.\-]", "", (raw or "").replace("%", ""))
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _material_type(filename: str, text: str) -> str:
    raw = f"{filename} {text}"
    if "打印维修预案" in raw or "物业大修和专项维修、更新、改造实施方案公示" in raw:
        return "repair_plan_pdf"
    if "实施方案征求意见汇总表" in raw or "征求意见汇总表" in raw:
        return "vote_summary_pdf"
    if "打印决议" in raw or "关于物业大修和专项维修、更新、改造使用维修资金的决议" in raw:
        return "resolution_pdf"
    return "unknown_pdf"


def _label_re(label: str) -> str:
    return rf"{re.escape(label)}\s*[：:]?\s*"


def _extract_between(text: str, start: str, end: str) -> Optional[str]:
    pattern = re.compile(rf"{_label_re(start)}(.*?)(?={_label_re(end)})", flags=re.S)
    match = pattern.search(text or "")
    if not match:
        return None
    value = normalize_whitespace(match.group(1))
    return value or None


def _evidence(raw_field: str, label: str, value: Any, page: int, raw_text: str, confidence: float) -> Dict[str, Any]:
    return {
        "raw_field": raw_field,
        "label": label,
        "value": value,
        "page": page,
        "raw_text": normalize_whitespace(raw_text),
        "confidence": confidence,
    }


def _find_line_value(page_text: str, keys: List[str], label: str, raw_field: str, parser, confidence: float) -> Optional[Dict[str, Any]]:
    for key in keys:
        m = re.search(rf"{_label_re(key)}([^\n]+)", page_text)
        if not m:
            continue
        raw = normalize_whitespace(m.group(1))
        val = parser(raw) if parser else raw
        if val is None:
            return None
        return _evidence(raw_field, label, val, 1, f"{key}: {raw}", confidence)
    return None


def parse_pdf_material(filename: str, content: bytes) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "file_name": filename,
        "filename": filename,
        "status": "failed",
        "material_type": "unknown_pdf",
        "material_type_label": MATERIAL_TYPE_LABELS["unknown_pdf"],
        "pages_count": 0,
        "extracted_fields": [],
        "warnings": [],
    }
    try:
        pages: List[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            result["pages_count"] = len(pdf.pages)
            for p in pdf.pages:
                pages.append(p.extract_text() or "")
        merged = "\n".join(pages)
        normalized = normalize_whitespace(merged)
        if not normalized:
            result["status"] = "scan_or_unreadable"
            result["message"] = "当前 PDF 未提取到文本，疑似扫描件，暂未启用 OCR"
            result["warnings"] = [result["message"]]
            return result

        material_type = _material_type(filename, normalized)
        result["material_type"] = material_type
        result["material_type_label"] = MATERIAL_TYPE_LABELS.get(material_type, MATERIAL_TYPE_LABELS["unknown_pdf"])

        evidence: List[Dict[str, Any]] = []
        raw_page1 = pages[0] if pages else ""
        normalized_page1 = normalize_whitespace(raw_page1)

        common_project = _find_line_value(raw_page1, ["工程名称", "项目名称"], "工程名称", "project_name", None, 0.9)
        if common_project:
            evidence.append(common_project)
        common_print = _find_line_value(raw_page1, ["打印日期"], "打印日期", "print_date", _to_date, 0.88)
        if common_print:
            evidence.append(common_print)

        if material_type == "repair_plan_pdf":
            spans = [
                ("repair_scope", "实施范围", "实施范围", "维修原因"),
                ("repair_reason", "维修原因", "维修原因", "维修资金预算金额"),
                ("budget_amount", "维修资金预算金额", "维修资金预算金额", "决策主体"),
                ("decision_subject", "决策主体", "决策主体", "施工单位选择方式"),
                ("construction_unit_select_method", "施工单位选择方式", "施工单位选择方式", "工程验收单位"),
                ("acceptance_unit", "工程验收单位", "工程验收单位", "施工管理单位"),
                ("management_unit", "施工管理单位", "施工管理单位", "根据《上海市住宅物业管理规定》"),
            ]
            for key, label, start, end in spans:
                raw = _extract_between(raw_page1, start, end)
                if raw is None:
                    continue
                value: Any = _to_amount(raw) if key == "budget_amount" else raw
                if value is None:
                    continue
                evidence.append(_evidence(key, label, value, 1, f"{label}: {raw}", 0.85))
        elif material_type == "vote_summary_pdf":
            for item in [
                _find_line_value(raw_page1, ["征询结束日期", "表决结束日期", "征询时间"], "征询结束日期", "vote_end_date", _to_date, 0.86),
                _find_line_value(raw_page1, ["征询开始日期", "表决开始日期"], "征询开始日期", "vote_start_date", _to_date, 0.84),
                _find_line_value(raw_page1, ["同意票数", "同意户数"], "同意票数", "agree_hou", _to_amount, 0.8),
                _find_line_value(raw_page1, ["同意面积"], "同意面积", "agree_area", _to_amount, 0.8),
                _find_line_value(raw_page1, ["总投票权数", "总户数"], "总投票权数", "count_hou", _to_amount, 0.8),
                _find_line_value(raw_page1, ["总投票面积", "总面积"], "总投票面积", "sum_area", _to_amount, 0.8),
            ]:
                if item:
                    evidence.append(item)
            if "通过" in normalized:
                evidence.append(_evidence("vote_passed", "是否通过", True, 1, "表决通过", 0.78))
        elif material_type == "resolution_pdf":
            for item in [
                _find_line_value(raw_page1, ["编号", "决议编号"], "编号", "resolution_no", None, 0.84),
                _find_line_value(raw_page1, ["征询开始日期", "发送征求意见表开始日期"], "征询开始日期", "vote_start_date", _to_date, 0.86),
                _find_line_value(raw_page1, ["征询结束日期", "发送征求意见表结束日期"], "征询结束日期", "vote_end_date", _to_date, 0.86),
                _find_line_value(raw_page1, ["录入日期"], "录入日期", "registration_date", _to_date, 0.82),
                _find_line_value(raw_page1, ["原维修资金预算金额", "预算金额"], "原维修资金预算金额", "budget_amount", _to_amount, 0.86),
                _find_line_value(raw_page1, ["工程决案总金额", "决案总金额"], "工程决案总金额", "final_amount", _to_amount, 0.86),
            ]:
                if item:
                    evidence.append(item)
            if "业主大会公章" in normalized_page1:
                evidence.append(_evidence("has_owner_meeting_seal", "业主大会公章", True, 1, "业主大会公章", 0.8))
            if "主任" in normalized_page1:
                evidence.append(_evidence("director_signed", "主任签章", True, 1, "主任签章", 0.78))
            if "副主任" in normalized_page1:
                evidence.append(_evidence("deputy_director_signed", "副主任签章", True, 1, "副主任签章", 0.78))

        result["extracted_fields"] = evidence
        result["status"] = "parsed_pdf" if material_type != "unknown_pdf" else "unrecognized_pdf"
        result["message"] = "PDF 文本解析完成。"
        return result
    except Exception as exc:
        result["status"] = "failed"
        result["message"] = f"PDF 解析失败：{exc}"
        result["warnings"] = [str(exc)]
        return result

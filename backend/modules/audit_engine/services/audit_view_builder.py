from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from modules.audit_engine.core.field_resolver import runtime_values


SOURCE_TYPE_LABELS = {
    "excel": "original",
    "llm": "extracted",
    "pdf": "extracted",
    "derived": "inferred",
}

FIELD_LABELS = {
    "project_name": "项目名称",
    "repair_scope": "维修范围",
    "repair_reason": "维修原因",
    "budget_amount": "预算金额",
    "final_amount": "决算/最终金额",
    "contract_amount": "合同金额",
    "applicant": "申报主体",
    "repair_nature": "维修性质",
    "need_cost_review": "是否需要审价",
    "has_construction_contract": "施工合同",
    "has_appraisal_contract": "审价合同",
    "has_appraisal_report": "审价报告",
    "has_vote_trace": "业主表决材料",
    "warranty_status": "保修状态",
    "is_public_part": "共用部位/设施",
    "is_private_part": "专有部分",
    "is_property_service_scope": "物业服务范围",
    "vote_start_date": "征询开始日期",
    "vote_end_date": "征询结束日期",
    "resolution_date": "决议生成日期",
    "registration_date": "录入日期",
}

OVERVIEW_FIELDS = [
    "project_name",
    "repair_scope",
    "repair_reason",
    "budget_amount",
    "final_amount",
    "need_cost_review",
    "repair_nature",
    "applicant",
]

STRUCTURED_FIELDS = [
    "project_name",
    "repair_scope",
    "repair_reason",
    "budget_amount",
    "final_amount",
    "contract_amount",
    "need_cost_review",
    "repair_nature",
    "has_vote_trace",
    "has_construction_contract",
    "has_appraisal_contract",
    "has_appraisal_report",
    "warranty_status",
]

RESULT_LABELS = {
    "compliant": "初步合规",
    "non_compliant": "疑似不合规",
    "need_supplement": "资料不完整",
    "manual_review": "建议人工复核",
    "info_only": "仅作展示",
    "not_applicable": "不适用",
}

AUDIT_POINT_LABELS = {
    "entity_audit": "使用范围审计",
    "trace_audit": "材料完整性审计",
    "process_audit": "流程合规审计",
    "amount_info": "金额/审价审计",
}


def _value(runtime: Any) -> Any:
    if isinstance(runtime, dict):
        return runtime.get("value")
    return runtime


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _display_value(value: Any) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    if value is None or value == "":
        return "未识别"
    if value == "normal":
        return "普通维修"
    if value == "emergency":
        return "紧急维修"
    if value == "unknown":
        return "未识别"
    if value == "out_of_warranty":
        return "已过保"
    if value == "in_warranty":
        return "保修期内"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _currency(value: Any) -> str:
    if not _present(value):
        return "未识别"
    try:
        amount = float(str(value).replace(",", ""))
    except ValueError:
        return _display_value(value)
    return f"¥{amount:,.2f}"


def _candidate_source(candidate: Dict[str, Any]) -> str:
    sheet = str(candidate.get("source_sheet") or "").strip()
    column = str(candidate.get("source_column") or "").strip()
    if not sheet and not column:
        return "未识别"
    if sheet == "derived":
        return "系统融合推断"
    if column == "__row_exists__":
        return f"{sheet}（工作表存在）"
    return ".".join(item for item in [sheet, column] if item)


def _selected_candidate(runtime: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(runtime, dict):
        return None
    candidates = runtime.get("candidates") or []
    index = runtime.get("selected_index", -1)
    if isinstance(index, int) and 0 <= index < len(candidates):
        candidate = candidates[index]
        return candidate if isinstance(candidate, dict) else None
    for candidate in candidates:
        if isinstance(candidate, dict) and _present(candidate.get("normalized_value")):
            return candidate
    return None


def _field_entry(standard_fields: Dict[str, Any], key: str, *, fallback_label: Optional[str] = None) -> Dict[str, Any]:
    runtime = standard_fields.get(key) or {}
    value = _value(runtime)
    label = fallback_label or FIELD_LABELS.get(key) or key
    if not _present(value):
        return {
            "field_key": key,
            "field_label": label,
            "value": None,
            "display_value": "未识别",
            "source_type": "missing",
            "source_label": "未识别",
            "confidence": 0,
            "evidence": [],
        }

    candidate = _selected_candidate(runtime)
    if candidate:
        source_type = SOURCE_TYPE_LABELS.get(str(candidate.get("source_type") or ""), "inferred")
        confidence = float(candidate.get("confidence") or 0.8)
        source_label = _candidate_source(candidate)
        evidence = [
            {
                "source_label": source_label,
                "raw_value": _display_value(candidate.get("raw_value")),
                "confidence": confidence,
            }
        ]
    else:
        source_type = "inferred"
        confidence = 0.7
        source_label = "系统融合推断"
        evidence = []

    if isinstance(runtime, dict) and runtime.get("status") in {"inferred", "llm_classified"}:
        source_type = "inferred" if source_type != "extracted" else "extracted"
    return {
        "field_key": key,
        "field_label": label,
        "value": value,
        "display_value": _currency(value) if "amount" in key else _display_value(value),
        "source_type": source_type,
        "source_label": source_label,
        "confidence": round(confidence, 2),
        "evidence": evidence,
    }


def _candidate_by_column(standard_fields: Dict[str, Any], field_key: str, columns: Sequence[str]) -> Optional[Dict[str, Any]]:
    runtime = standard_fields.get(field_key) or {}
    candidates = runtime.get("candidates") if isinstance(runtime, dict) else []
    wanted = {item.lower() for item in columns}
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        column = str(candidate.get("source_column") or "").lower()
        if column in wanted and _present(candidate.get("normalized_value")):
            return candidate
    return None


def _timeline_item(
    label: str,
    value: Any,
    source_type: str,
    source_label: str,
    business_meaning: str,
    confidence: float,
    warning: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "display_value": _display_value(value),
        "source_type": source_type,
        "source_label": source_label or "未识别",
        "business_meaning": business_meaning,
        "confidence": confidence,
        "warning": warning,
    }


def _timeline_from_candidates(standard_fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    request_start = _selected_candidate(standard_fields.get("vote_start_date") or {})
    request_end = _selected_candidate(standard_fields.get("vote_end_date") or {})
    reg_date = _selected_candidate(standard_fields.get("registration_date") or {})
    resolution_date = _selected_candidate(standard_fields.get("resolution_date") or {})
    start = _field_entry(standard_fields, "construction_start_date")
    finish = _field_entry(standard_fields, "construction_finish_date")

    timeline = []
    for label, candidate, meaning in [
        ("表决/征询开始", request_start, "业主征询意见表开始发送"),
        ("表决/征询结束", request_end, "业主征询意见表结束发送"),
    ]:
        timeline.append(
            _timeline_item(
                label,
                candidate.get("normalized_value") if candidate else None,
                "original" if candidate else "missing",
                _candidate_source(candidate) if candidate else "未识别",
                meaning if candidate else "当前材料未识别该时间节点",
                float(candidate.get("confidence") or 0.95) if candidate else 0,
            )
        )

    timeline.append(
        _timeline_item(
            "业主大会决议录入日期",
            reg_date.get("normalized_value") if reg_date else None,
            "original" if reg_date else "missing",
            _candidate_source(reg_date) if reg_date else "未识别",
            "系统中的决议记录/登记日期，不等同于维修预案或决案形成日期",
            float(reg_date.get("confidence") or 0.9) if reg_date else 0,
            "该日期不能直接作为维修预案/决案形成时间" if reg_date else "当前材料未识别决议录入日期",
        )
    )
    timeline.append(
        _timeline_item(
            "决议生成日期",
            resolution_date.get("normalized_value") if resolution_date else None,
            "original" if resolution_date else "missing",
            _candidate_source(resolution_date) if resolution_date else "未识别",
            "决议文本形成日期，需与征询时间共同判定流程时序",
            float(resolution_date.get("confidence") or 0.9) if resolution_date else 0,
            "当前材料未识别决议生成日期" if not resolution_date else None,
        )
    )

    for label, entry, meaning, warning in [
        ("施工开始", start, "需从施工合同、开工报告或施工记录中确认", "当前材料未提供施工合同/开工记录"),
        ("施工完成", finish, "需从完工验收报告或施工记录中确认", "当前材料未提供完工验收报告"),
    ]:
        timeline.append(
            _timeline_item(
                label,
                entry["value"],
                entry["source_type"],
                entry["source_label"],
                meaning if not entry["value"] else "已识别施工时序节点",
                entry["confidence"],
                None if entry["value"] else warning,
            )
        )
    return timeline


def _has_sheet(source_sheets: Iterable[str], names: Sequence[str]) -> bool:
    sheet_set = {str(item) for item in source_sheets or []}
    return any(name in sheet_set for name in names)


def _present_sheet(source_sheets: Iterable[str], names: Sequence[str]) -> Optional[str]:
    sheet_set = {str(item) for item in source_sheets or []}
    for name in names:
        if name in sheet_set:
            return name
    return None


def _bool_value(standard_fields: Dict[str, Any], key: str) -> Optional[bool]:
    value = _value(standard_fields.get(key))
    return value if isinstance(value, bool) else None


def _active_excel_filename(attachments: List[Dict[str, Any]]) -> str:
    for item in attachments:
        filename = str(item.get("filename") or "")
        if item.get("used_for_audit") is True and filename.lower().endswith((".xlsx", ".xls")):
            return filename
    for item in attachments:
        filename = str(item.get("filename") or "")
        if filename.lower().endswith((".xlsx", ".xls")):
            return filename
    return ""


def _material_source(active_excel_filename: str, sheet_name: Optional[str]) -> str:
    if not sheet_name:
        return "未识别"
    return f"{active_excel_filename} / {sheet_name}" if active_excel_filename else sheet_name


def _pdf_material_hit(pdf_parse_results: List[Dict[str, Any]], material_type: str) -> Optional[Dict[str, Any]]:
    for item in pdf_parse_results or []:
        if item.get("status") == "parsed_pdf" and item.get("material_type") == material_type:
            return item
    return None


def _pdf_source_label(item: Dict[str, Any]) -> str:
    return f"{item.get('filename') or ''} / 第1页 / {item.get('material_type_label') or 'PDF材料'}"


def _pdf_evidence_summary(item: Dict[str, Any]) -> str:
    labels = []
    for evidence in (item.get("raw_evidence") or []):
        if isinstance(evidence, dict) and evidence.get("value") is not None:
            labels.append(str(evidence.get("label") or evidence.get("raw_field") or ""))
    labels = labels[:3]
    if not labels:
        return "已识别PDF材料类型。"
    return f"从 PDF 中识别到{'、'.join(labels)}。"


def _material_scan(
    standard_fields: Dict[str, Any],
    source_sheets: List[str],
    attachments: List[Dict[str, Any]],
    pdf_parse_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    need_cost_review = _bool_value(standard_fields, "need_cost_review") is True
    final_amount_present = _present(_value(standard_fields.get("final_amount")))
    active_excel_filename = _active_excel_filename(attachments)

    rows = [
        ("维修工单", _present_sheet(source_sheets, ["维修工单"]), None, "建议补充维修工单或报修登记材料。", True),
        ("维修预案", _present_sheet(source_sheets, ["维修预案", "维修决案"]), _pdf_material_hit(pdf_parse_results, "repair_plan_pdf"), "建议补充维修预案、维修决案或实施方案材料。", True),
        ("业主征询意见/表决汇总", _present_sheet(source_sheets, ["业主征询意见", "业主表决汇总"]), _pdf_material_hit(pdf_parse_results, "vote_summary_pdf"), "建议补充业主征询意见或表决汇总材料。", True),
        ("业主大会决议", _present_sheet(source_sheets, ["业主大会决议"]), _pdf_material_hit(pdf_parse_results, "resolution_pdf"), "建议补充业主大会/业委会决议材料。", True),
        ("施工合同", _present_sheet(source_sheets, ["施工合同表"]) if _bool_value(standard_fields, "has_construction_contract") is True or _has_sheet(source_sheets, ["施工合同表"]) else None, None, "建议补充施工合同或中标/委托文件。", True),
        ("审价合同", _present_sheet(source_sheets, ["审价合同"]) if _bool_value(standard_fields, "has_appraisal_contract") is True else None, None, "建议补充审价合同或造价咨询委托材料。", need_cost_review),
        ("审价报告", _present_sheet(source_sheets, ["审价报告", "预算审核报告"]) if _bool_value(standard_fields, "has_appraisal_report") is True else None, None, "建议补充审价报告或预算审核报告。", need_cost_review),
        ("验收/完工报告", _present_sheet(source_sheets, ["项目完工报告表", "验收报告", "完工报告"]), None, "建议补充完工验收材料。", final_amount_present),
    ]
    output = []
    for name, sheet_name, pdf_item, remediation, affects_audit in rows:
        status = "extracted" if (sheet_name or pdf_item) else ("missing" if affects_audit else "not_applicable")
        if sheet_name:
            source_label = _material_source(active_excel_filename, sheet_name)
            evidence_summary = f"已识别{name}相关材料。"
        elif pdf_item:
            source_label = _pdf_source_label(pdf_item)
            evidence_summary = _pdf_evidence_summary(pdf_item)
        else:
            source_label = "未识别"
            evidence_summary = f"当前材料未识别{name}。"
        output.append(
            {
                "required_item": name,
                "status": status,
                "status_label": {"extracted": "已识别", "missing": "缺失", "partial": "部分识别", "not_applicable": "不适用"}[status],
                "source_label": source_label,
                "evidence_summary": evidence_summary,
                "affects_audit": bool(affects_audit),
                "remediation": "" if (sheet_name or pdf_item) or not affects_audit else remediation,
                "confidence": 0.9 if (sheet_name or pdf_item) else (0 if affects_audit else 0.4),
            }
        )
    return output


def _file_type(filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return suffix or "unknown"


def _material_role(filename: str, used_for_audit: bool) -> str:
    text = filename.lower()
    if used_for_audit:
        return "业务包/结构化审计材料"
    if "表决" in filename or "决议" in filename:
        return "业主表决材料"
    if "预算" in filename or "金额" in filename:
        return "维修预算材料"
    if "方案" in filename or "预案" in filename:
        return "实施方案材料"
    return "未知材料"


def _raw_materials(attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "file_name": item.get("filename") or "",
            "file_type": _file_type(item.get("filename") or ""),
            "recognized": item.get("status") in {"parsed", "used_for_audit", "parsed_pdf", "scan_or_unreadable", "unrecognized_pdf"},
            "role": item.get("material_type_label") or _material_role(item.get("filename") or "", item.get("used_for_audit") is True),
            "status": item.get("status") or "",
        }
        for item in attachments
    ]


def _pdf_extraction(pdf_parse_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for item in pdf_parse_results or []:
        extracted_fields = []
        for evidence in (item.get("raw_evidence") or []):
            if not isinstance(evidence, dict):
                continue
            if evidence.get("value") is None:
                continue
            page = evidence.get("page") or evidence.get("source_page") or 1
            extracted_fields.append(
                {
                    "field_key": evidence.get("raw_field") or "",
                    "field_label": evidence.get("label") or evidence.get("raw_field") or "",
                    "value": evidence.get("value"),
                    "source_label": f"{item.get('filename') or ''} / 第{page}页",
                    "raw_value": evidence.get("raw_text"),
                    "confidence": float(evidence.get("confidence") or 0.8),
                    "source_page": page,
                }
            )

        status = item.get("status") or "failed"
        status_label = "已解析"
        if status == "scan_or_unreadable":
            status_label = "扫描件/不可读"
        elif status in {"unrecognized_pdf", "failed"}:
            status_label = "未识别/失败"

        output.append(
            {
                "file_name": item.get("filename") or "",
                "material_type": item.get("material_type") or "unknown_pdf",
                "material_type_label": item.get("material_type_label") or "未识别PDF材料",
                "status": status,
                "status_label": status_label,
                "extracted_fields": extracted_fields,
                "warnings": item.get("warnings") or [],
            }
        )
    return output


def _structured_extraction(standard_fields: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    visible: List[Dict[str, Any]] = []
    low_confidence: List[Dict[str, Any]] = []
    for key in STRUCTURED_FIELDS:
        entry = _field_entry(standard_fields, key)
        if entry["source_type"] == "missing":
            continue
        if entry["confidence"] < 0.6:
            low_confidence.append(entry)
            continue
        visible.append(
            {
                "field_label": entry["field_label"],
                "value": entry["display_value"],
                "source_type": entry["source_type"],
                "source_label": entry["source_label"],
                "confidence": entry["confidence"],
            }
        )
    return visible, low_confidence


def _ai_interpretation(standard_fields: Dict[str, Any], llm_result: Dict[str, Any], material_scan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    values = runtime_values(standard_fields)
    project_name = str(values.get("project_name") or "")
    repair_reason = str(values.get("repair_reason") or "")
    amount = values.get("final_amount") or values.get("budget_amount")
    missing = [item["required_item"] for item in material_scan if item["status"] == "missing"]
    available = llm_result.get("available") is True
    base_confidence = 0.82 if available else 0.68
    source_note = "本地 LLM 辅助解释" if available else "内置规则保守解释"

    items = [
        {
            "title": "项目性质识别",
            "content": f"根据项目名称和维修原因，系统判断该项目与{project_name or '当前维修事项'}相关；{repair_reason or '维修原因仍需结合原始材料复核'}。",
            "confidence": base_confidence,
            "source_type": "extracted" if available else "inferred",
            "source_label": source_note,
            "basis_fields": ["project_name", "repair_reason", "repair_scope"],
        }
    ]
    if missing:
        items.append(
            {
                "title": "缺失材料解释",
                "content": f"当前材料未识别{ '、'.join(missing) }，无法形成完整审计闭环，建议补充后人工复核。",
                "confidence": 0.78,
                "source_type": "inferred",
                "source_label": "内置规则保守解释",
                "basis_fields": ["material_scan"],
            }
        )
    if amount is not None:
        items.append(
            {
                "title": "金额与审价提示",
                "content": f"当前识别金额为{_currency(amount)}，达到或接近审价触发条件时，应结合审价合同和审价报告复核。",
                "confidence": 0.76,
                "source_type": "inferred",
                "source_label": "金额字段与审价规则",
                "basis_fields": ["budget_amount", "final_amount", "need_cost_review"],
            }
        )
    return items


def _policy_tags(document: Dict[str, Any]) -> List[str]:
    title = str(document.get("title") or document.get("display_name") or "")
    doc_no = str(document.get("document_no") or "")
    source_type = str(document.get("source_type") or "")
    tags: List[str] = []
    if "上海" in title or "沪" in doc_no:
        tags.append("上海地方")
    if "民法典" in title or "住宅专项维修资金管理办法" in title:
        tags.append("国家法规")
    if source_type == "standard" or "DB31" in doc_no:
        tags.append("地方标准")
    if "合同" in title or "审价" in title:
        tags.append("流程材料")
    if not tags:
        tags.append("法规依据")
    return tags


def _policy_matches(audit_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str]] = set()
    for audit_key, sub in (audit_result.get("sub_audits") or {}).items():
        related_audit = AUDIT_POINT_LABELS.get(audit_key, "审计辅助复核")
        for doc in sub.get("basis_documents", []) or []:
            title = doc.get("title") or doc.get("display_name")
            article = doc.get("article") or ""
            key = (str(title), str(article), related_audit)
            if not title or key in seen:
                continue
            seen.add(key)
            matches.append(
                {
                    "policy_title": title,
                    "article": article,
                    "tags": _policy_tags(doc),
                    "matched_reason": doc.get("basis_explanation") or doc.get("section") or doc.get("display_text") or "当前审计点命中该法规依据。",
                    "related_audit": related_audit,
                    "match_type": "requirement",
                    "confidence": 0.82,
                }
            )
    return matches


def _audit_cards(audit_result: Dict[str, Any], material_scan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sub_audits = audit_result.get("sub_audits") or {}
    names = {
        "entity_audit": "使用范围审计",
        "trace_audit": "材料完整性审计",
        "process_audit": "流程合规审计",
        "amount_info": "金额/审价审计",
    }
    cards = []
    for key, title in names.items():
        sub = sub_audits.get(key) or {}
        result = sub.get("result") or "manual_review"
        cards.append(
            {
                "audit_type": title,
                "result": result,
                "result_label": RESULT_LABELS.get(result, "建议人工复核"),
                "summary": "；".join(sub.get("reasons") or []) or sub.get("display_result") or "建议结合材料人工复核。",
                "facts_used": [FIELD_LABELS.get(item, item) for item in sub.get("used_standard_fields", []) or []],
                "policy_matches": [
                    {
                        "policy_title": doc.get("title") or doc.get("display_name"),
                        "article": doc.get("article"),
                    }
                    for doc in sub.get("basis_documents", []) or []
                ],
                "missing_materials": [FIELD_LABELS.get(item, item) for item in sub.get("missing_items", []) or []],
                "recommendation": _recommendation_for_sub_audit(title, result, sub, material_scan),
            }
        )
    cards.append(
        {
            "audit_type": "时序审计",
            "result": "manual_review",
            "result_label": "建议人工复核",
            "summary": "施工开始/完成时间需结合施工合同、开工记录、完工验收材料核验。",
            "facts_used": ["表决/征询日期", "施工开始日期", "施工完成日期"],
            "policy_matches": [],
            "missing_materials": [item["required_item"] for item in material_scan if item["status"] == "missing"],
            "recommendation": "补充施工合同、开工记录、完工验收材料后复核时序。",
        }
    )
    return cards


def _recommendation_for_sub_audit(title: str, result: str, sub: Dict[str, Any], material_scan: List[Dict[str, Any]]) -> str:
    if result == "compliant":
        return "当前材料支持初步判断，仍建议保留人工复核记录。"
    missing = [item["required_item"] for item in material_scan if item["status"] == "missing"]
    if title == "材料完整性审计" and missing:
        return f"请补充{ '、'.join(missing) }后复核。"
    if title == "金额/审价审计":
        return "请结合审价合同、审价报告和最终结算金额复核。"
    return "请结合原始材料和法规命中结果进行人工复核。"


def _display_conclusion(audit_result: Dict[str, Any], standard_fields: Dict[str, Any], material_scan: List[Dict[str, Any]]) -> Dict[str, Any]:
    values = runtime_values(standard_fields)
    missing = [item["required_item"] for item in material_scan if item["status"] == "missing"]
    scope_reasonable = values.get("is_public_part") is True
    if missing:
        main_result = "资料不完整，建议人工复核"
        risk_level = "medium"
    elif audit_result.get("overall_result") == "compliant":
        main_result = "范围初步合规，建议留痕复核"
        risk_level = "low"
    elif audit_result.get("overall_result") == "non_compliant":
        main_result = "流程或范围存在高风险"
        risk_level = "high"
    else:
        main_result = "建议人工复核"
        risk_level = "medium"

    scope_text = "通常属于共用部位维修，使用维修资金的范围初步具备合理性" if scope_reasonable else "维修范围仍需结合材料确认"
    missing_text = f"但当前材料中未识别{ '、'.join(missing) }，无法形成完整审计闭环" if missing else "当前关键材料已形成初步证据链"
    next_actions = [item["remediation"] for item in material_scan if item.get("remediation")]
    if not next_actions:
        next_actions = ["保留人工复核记录。"]
    return {
        "main_result": main_result,
        "summary": f"该项目从项目名称、维修范围、维修原因看，{scope_text}；{missing_text}。",
        "risk_level": risk_level,
        "next_actions": next_actions,
    }


def build_audit_view(
    *,
    status: str,
    message: str = "",
    attachments: Optional[List[Dict[str, Any]]] = None,
    standard_fields: Optional[Dict[str, Any]] = None,
    source_sheets: Optional[List[str]] = None,
    llm_result: Optional[Dict[str, Any]] = None,
    audit_result: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    field_conflicts: Optional[List[Dict[str, Any]]] = None,
    pdf_parse_results: Optional[List[Dict[str, Any]]] = None,
    flat_standard_fields: Optional[Dict[str, Any]] = None,
    field_sources: Optional[Dict[str, Any]] = None,
    material_evidence: Optional[List[Dict[str, Any]]] = None,
    user_overrides: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    standard_fields = standard_fields or {}
    attachments = attachments or []
    source_sheets = source_sheets or []
    llm_result = llm_result or {}
    audit_result = audit_result or {}
    pdf_parse_results = pdf_parse_results or []
    flat_standard_fields = flat_standard_fields or {}
    field_sources = field_sources or {}
    material_evidence = material_evidence or []
    user_overrides = user_overrides or []
    material_scan = _material_scan(standard_fields, source_sheets, attachments, pdf_parse_results)
    structured, low_confidence = _structured_extraction(standard_fields)
    policy_matches = _policy_matches(audit_result)
    pdf_extraction = _pdf_extraction(pdf_parse_results)
    return {
        "display_conclusion": _display_conclusion(audit_result, standard_fields, material_scan)
        if standard_fields
        else {
            "main_result": "无法形成审计结论",
            "summary": message or "未识别可用于审计的结构化 Excel 材料。",
            "risk_level": "medium",
            "next_actions": ["请补充可解析的 Excel 业务包后重新审计。"],
        },
        "project_overview": {key: _field_entry(standard_fields, key) for key in OVERVIEW_FIELDS},
        "flat_standard_fields": flat_standard_fields,
        "field_sources": field_sources,
        "material_evidence": material_evidence,
        "field_conflicts": field_conflicts or [],
        "user_overrides": user_overrides,
        "timeline": _timeline_from_candidates(standard_fields) if standard_fields else [],
        "material_scan": material_scan,
        "evidence_sections": {
            "raw_materials": _raw_materials(attachments),
            "structured_extraction": structured,
            "ai_interpretation": _ai_interpretation(standard_fields, llm_result, material_scan) if standard_fields else [],
            "low_confidence_candidates": low_confidence,
            "pdf_extraction": pdf_extraction,
        },
        "policy_matches": policy_matches,
        "audit_cards": _audit_cards(audit_result, material_scan) if audit_result else [],
        "auditor_notes": {
            "status": status,
            "warnings": warnings or [],
            "conflict_count": len(field_conflicts or []),
            "llm_status": {
                "available": llm_result.get("available") is True,
                "selected_model": (llm_result.get("llm_diagnostics") or {}).get("selected_model")
                or llm_result.get("selected_model")
                or llm_result.get("model"),
                "diagnostics": llm_result.get("llm_diagnostics") or {},
            },
        },
    }

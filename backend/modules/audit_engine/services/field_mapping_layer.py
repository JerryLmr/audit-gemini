from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

from modules.audit_engine.services.mapping_service import map_project_name
from modules.audit_engine.services.rule_loader import load_rule_json


SOURCE_KEYS = (
    "t_workspace",
    "ws_project",
    "blueprint",
    "blueprint_draft",
    "hou_notion_sum",
    "project_contract",
    "excel",
    "ocr",
    "text",
)
PRIVATE_KEYWORDS = (
    "室内",
    "户内",
    "门锁",
    "室内门锁",
    "洁具",
    "入户门",
    "户门",
    "防盗门",
    "马桶",
    "水龙头",
    "墙面粉刷",
    "专有",
)
PROPERTY_SERVICE_KEYWORDS = ("树木修剪", "绿化养护", "保洁", "清洁", "卫生", "检测", "检查", "试验")
PUBLIC_PART_KEYWORDS = ("电梯", "消防", "水泵", "供水", "排水", "排污", "外墙", "外立面", "屋面", "屋顶")
OUT_OF_WARRANTY_KEYWORDS = ("过保", "已过保", "超过保修", "保修期外", "出保")


@lru_cache(maxsize=1)
def load_standard_field_definitions() -> Dict[str, Any]:
    return load_rule_json("standard_field_definitions.json")


@lru_cache(maxsize=1)
def load_field_mapping_rules() -> Dict[str, Any]:
    return load_rule_json("field_mapping_rules.json")


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _source_alias_map() -> Dict[str, str]:
    config = load_field_mapping_rules()
    aliases: Dict[str, str] = {}
    for canonical, values in config.get("source_aliases", {}).items():
        aliases[_normalize_key(canonical)] = canonical
        for value in values:
            aliases[_normalize_key(value)] = canonical
    return aliases


def _as_row(value: Any) -> Dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
        return {}
    if isinstance(value, dict):
        return value
    return {}


def _normalize_row_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    return {_normalize_key(key): value for key, value in row.items()}


def _normalize_sources(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    alias_map = _source_alias_map()
    raw_sources = payload.get("sources") if isinstance(payload.get("sources"), dict) else {}
    normalized: Dict[str, Dict[str, Any]] = {key: {} for key in SOURCE_KEYS}

    for source_name, source_value in raw_sources.items():
        canonical = alias_map.get(_normalize_key(source_name), _normalize_key(source_name))
        if canonical not in normalized:
            normalized[canonical] = {}
        normalized[canonical] = _normalize_row_keys(_as_row(source_value))

    if payload.get("project_name"):
        normalized["text"].setdefault("project_name", payload.get("project_name"))

    return normalized


def _get_value(sources: Dict[str, Dict[str, Any]], source: str, field: str) -> Any:
    return sources.get(source, {}).get(_normalize_key(field))


def _is_present(value: Any) -> bool:
    return value is not None and value != ""


def _to_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "y", "yes", "是", "有", "已签", "已"}:
        return True
    if text in {"0", "false", "n", "no", "否", "无", "未签", "未"}:
        return False
    return None


def _to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except ValueError:
        return None


def _to_date(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _date_lt(left: Optional[str], right: Optional[str]) -> Optional[bool]:
    if not left or not right:
        return None
    try:
        return datetime.strptime(left, "%Y-%m-%d").date() < datetime.strptime(right, "%Y-%m-%d").date()
    except ValueError:
        return None


def _field_comment(field_name: str) -> str:
    fields = load_standard_field_definitions().get("fields", {})
    return str(fields.get(field_name, {}).get("comment", ""))


def _rule_text(field_name: str) -> str:
    for rule in load_field_mapping_rules().get("rules", []):
        if rule.get("standard_field") == field_name:
            return str(rule.get("mapping_rule", ""))
    return ""


def _record(field_name: str, value: Any, source: str, source_field: Optional[str]) -> Dict[str, Any]:
    return {
        "standard_field": field_name,
        "value": value,
        "source": source,
        "source_field": source_field,
        "mapping_rule": _rule_text(field_name),
        "field_comment": _field_comment(field_name),
    }


def _first_non_empty(
    sources: Dict[str, Dict[str, Any]],
    candidates: Iterable[Tuple[str, str]],
) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    for source, field in candidates:
        value = _get_value(sources, source, field)
        if _is_present(value):
            return value, source, field
    return None, None, None


def _first_existing(
    sources: Dict[str, Dict[str, Any]],
    candidates: Iterable[Tuple[str, str]],
) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
    for source, field in candidates:
        normalized_field = _normalize_key(field)
        if normalized_field in sources.get(source, {}):
            return sources[source][normalized_field], source, field
    return None, None, None


def _map_project_name(sources: Dict[str, Dict[str, Any]], payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    value, source, field = _first_non_empty(
        sources,
        (
            ("t_workspace", "wsname"),
            ("blueprint", "wsname"),
            ("blueprint_draft", "wsname"),
            ("project_contract", "name"),
            ("text", "project_name"),
            ("ocr", "project_name"),
            ("excel", "project_name"),
        ),
    )
    if not _is_present(value):
        value = payload.get("project_name") or ""
        source = "request"
        field = "project_name"
    return str(value or ""), _record("project_name", str(value or ""), source or "request", field)


def _map_project_item_code(sources: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    value, source, field = _first_non_empty(
        sources,
        (
            ("t_workspace", "wscode"),
            ("blueprint", "wscode"),
            ("blueprint_draft", "wscode"),
            ("project_contract", "code"),
            ("t_workspace", "wsid"),
        ),
    )
    if not _is_present(value):
        return None, None
    return str(value), _record("project_item_code", str(value), source or "", field)


def _map_applicant(sources: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    value, source, field = _first_non_empty(
        sources,
        (
            ("excel", "hc_name"),
            ("blueprint", "hc_name"),
            ("blueprint_draft", "hc_name"),
        ),
    )
    if not _is_present(value):
        return None, None
    return str(value), _record("applicant", str(value), source or "", field)


def _map_property_fields(sources: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
    value, source, field = _first_existing(
        sources,
        (
            ("t_workspace", "property"),
            ("blueprint", "property"),
            ("blueprint_draft", "property"),
        ),
    )
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []
    raw_value = None if value is None else str(value).strip()
    fields: Dict[str, Any] = {
        "property_raw_value": raw_value,
        "property_value_valid": True,
    }

    if raw_value == "1" or raw_value in (None, ""):
        fields["is_emergency_repair"] = False
        fields["repair_nature"] = "normal"
    elif raw_value == "2":
        fields["is_emergency_repair"] = True
        fields["repair_nature"] = "emergency"
    else:
        fields["is_emergency_repair"] = None
        fields["repair_nature"] = "unknown"
        fields["property_value_valid"] = False
        warnings.append("property 值不在当前支持范围内（仅支持 1/2），需人工复核。")

    source_name = source or "default"
    source_field = field or "property"
    records.append(_record("property_raw_value", raw_value, source_name, source_field))
    records.append(_record("property_value_valid", fields["property_value_valid"], source_name, source_field))
    records.append(_record("is_emergency_repair", fields["is_emergency_repair"], source_name, source_field))
    records.append(_record("repair_nature", fields["repair_nature"], "derived", "is_emergency_repair"))
    return fields, records, warnings


def _map_warranty_status(sources: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], List[str]]:
    value, source, field = _first_existing(
        sources,
        (
            ("blueprint", "expirer_remark"),
            ("blueprint_draft", "expirer_remark"),
        ),
    )
    warnings: List[str] = []
    text = str(value or "").strip()
    if any(keyword in text for keyword in OUT_OF_WARRANTY_KEYWORDS):
        status = "out_of_warranty"
    elif any(keyword in text for keyword in ("保修期内", "未过保", "尚未过保", "仍在保修期", "在保")):
        status = "in_warranty"
    else:
        status = "unknown"
        warnings.append("保修状态缺失或无法判断，需补充保修期满依据。")
        source = source or "default"
        field = field or "expirer_remark"
    return status, _record("warranty_status", status, source or "", field), warnings


def _map_bool_field(
    sources: Dict[str, Dict[str, Any]],
    field_name: str,
    candidates: Iterable[Tuple[str, str]],
) -> Tuple[Optional[bool], Optional[Dict[str, Any]]]:
    value, source, field = _first_non_empty(sources, candidates)
    if value is None:
        return None, None
    result = _to_bool(value)
    return result, _record(field_name, result, source or "", field)


def _has_source_row(sources: Dict[str, Dict[str, Any]], source: str) -> bool:
    return any(_is_present(value) for value in sources.get(source, {}).values())


def _ratio(numerator: Any, denominator: Any) -> Optional[float]:
    num = _to_number(numerator)
    den = _to_number(denominator)
    if num is None or den in (None, 0):
        return None
    return round(num / den, 6)


def _first_number(row: Dict[str, Any], names: Iterable[str]) -> Optional[float]:
    for name in names:
        value = _to_number(row.get(_normalize_key(name)))
        if value is not None:
            return value
    return None


def _map_vote_fields(sources: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
    row = sources.get("hou_notion_sum", {})
    mapped: Dict[str, Any] = {}
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []
    row_exists = _has_source_row(sources, "hou_notion_sum")
    fallback_voted = _to_bool(_get_value(sources, "t_workspace", "is_voted"))

    has_vote_trace = True if row_exists else bool(fallback_voted)
    mapped["has_vote_trace"] = has_vote_trace
    records.append(
        _record(
            "has_vote_trace",
            has_vote_trace,
            "hou_notion_sum" if row_exists else "t_workspace",
            "__row_exists__" if row_exists else "is_voted",
        )
    )

    total_households = _first_number(row, ("count_hou", "total_households", "sum_hou", "all_hou"))
    approved_households = _first_number(row, ("agree_hou", "yes_hou", "pass_hou", "agree_households"))
    total_area = _first_number(row, ("sum_area", "total_area", "all_area"))
    approved_area = _first_number(row, ("agree_area", "yes_area", "pass_area", "agree_area_sum"))

    household_rate = _ratio(approved_households, total_households)
    area_rate = _ratio(approved_area, total_area)
    mapped["vote_pass_rate_by_household"] = household_rate
    mapped["vote_pass_rate_by_area"] = area_rate
    mapped["vote_legal"] = None if household_rate is None or area_rate is None else household_rate >= 2 / 3 and area_rate >= 2 / 3

    records.append(_record("vote_pass_rate_by_household", household_rate, "hou_notion_sum", "agree_hou/count_hou"))
    records.append(_record("vote_pass_rate_by_area", area_rate, "hou_notion_sum", "agree_area/sum_area"))
    records.append(_record("vote_legal", mapped["vote_legal"], "hou_notion_sum", "vote_rate_fields"))
    if row_exists and mapped["vote_legal"] is None:
        warnings.append("Hou_notion_sum 存在但缺少计算通过率所需字段，vote_legal 需人工复核。")

    vote_start_date = _to_date(row.get("request_startdate"))
    vote_end_date = _to_date(row.get("request_enddate"))
    registration_date = _to_date(row.get("reg_date"))
    mapped["vote_start_date"] = vote_start_date
    mapped["vote_end_date"] = vote_end_date
    mapped["registration_date"] = registration_date
    records.append(_record("vote_start_date", vote_start_date, "hou_notion_sum", "request_startdate"))
    records.append(_record("vote_end_date", vote_end_date, "hou_notion_sum", "request_enddate"))
    records.append(_record("registration_date", registration_date, "hou_notion_sum", "reg_date"))
    return mapped, records, warnings


def _map_amount_field(
    sources: Dict[str, Dict[str, Any]],
    field_name: str,
    candidates: Iterable[Tuple[str, str]],
) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
    value, source, field = _first_non_empty(sources, candidates)
    result = _to_number(value)
    if result is None:
        return None, None
    return result, _record(field_name, result, source or "", field)


def _derive_catalog_fields(project_name: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    mapping_result = map_project_name(project_name)
    normalized_paths = [str(item.get("full_path", "")) for item in mapping_result.get("mapped_objects", [])]
    public_hit = any(
        path.startswith(("电梯/", "消防系统/", "消防泵/", "排水、排污设施/", "供水系统/", "楼栋外立面/"))
        or "屋面" in path
        or "屋顶" in path
        for path in normalized_paths
    ) or any(keyword in project_name for keyword in PUBLIC_PART_KEYWORDS)
    private_hit = any(keyword in project_name for keyword in PRIVATE_KEYWORDS)
    property_service_hit = any(keyword in project_name for keyword in PROPERTY_SERVICE_KEYWORDS)
    fields = {
        "is_public_part": True if public_hit else None,
        "is_private_part": True if private_hit else None,
        "is_property_service_scope": True if property_service_hit else None,
    }
    records = [
        _record("is_public_part", fields["is_public_part"], "catalog_mapping", "project_name"),
        _record("is_private_part", fields["is_private_part"], "catalog_mapping", "project_name"),
        _record("is_property_service_scope", fields["is_property_service_scope"], "catalog_mapping", "project_name"),
    ]
    return fields, records, mapping_result


def _collect_unmapped_sources(sources: Dict[str, Dict[str, Any]], mapped_records: List[Dict[str, Any]]) -> List[str]:
    mapped_pairs = {
        (str(item.get("source", "")).lower(), str(item.get("source_field", "")).lower())
        for item in mapped_records
        if item.get("source_field")
    }
    unmapped: List[str] = []
    for source, row in sources.items():
        for field, value in row.items():
            if not _is_present(value):
                continue
            if (source.lower(), field.lower()) not in mapped_pairs:
                unmapped.append(f"{source}.{field}")
    return sorted(set(unmapped))


def build_field_mapping_layer(payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = _normalize_sources(payload)
    standard_fields: Dict[str, Any] = {}
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []

    project_name, project_name_record = _map_project_name(sources, payload)
    standard_fields["project_name"] = project_name
    records.append(project_name_record)

    project_item_code, project_item_code_record = _map_project_item_code(sources)
    if project_item_code_record:
        standard_fields["project_item_code"] = project_item_code
        records.append(project_item_code_record)
    applicant, applicant_record = _map_applicant(sources)
    if applicant_record:
        standard_fields["applicant"] = applicant
        records.append(applicant_record)

    property_fields, property_records, property_warnings = _map_property_fields(sources)
    standard_fields.update(property_fields)
    records.extend(property_records)
    warnings.extend(property_warnings)

    warranty_status, warranty_record, warranty_warnings = _map_warranty_status(sources)
    if warranty_record:
        standard_fields["warranty_status"] = warranty_status
        records.append(warranty_record)
    warnings.extend(warranty_warnings)

    for field_name, candidates in (
        ("has_construction_contract", (("ws_project", "is_signed_pc"),)),
        ("has_appraisal_contract", (("ws_project", "is_signed_esc"),)),
        ("has_appraisal_report", (("ws_project", "is_signed_esr"),)),
        ("need_construction_contract", (("ws_project", "need_con"), ("t_workspace", "need_pro_contract"))),
    ):
        value, record = _map_bool_field(sources, field_name, candidates)
        if record:
            standard_fields[field_name] = value
            records.append(record)

    vote_fields, vote_records, vote_warnings = _map_vote_fields(sources)
    standard_fields.update(vote_fields)
    records.extend(vote_records)
    warnings.extend(vote_warnings)

    start_date_value = _get_value(sources, "project_contract", "startup_date")
    start_date = _to_date(start_date_value)
    if start_date:
        standard_fields["construction_start_date"] = start_date
        records.append(_record("construction_start_date", start_date, "project_contract", "startup_date"))

    is_before_vote_construct = None
    if standard_fields.get("repair_nature") == "normal":
        is_before_vote_construct = _date_lt(
            standard_fields.get("construction_start_date"),
            standard_fields.get("vote_end_date"),
        )
    standard_fields["is_before_vote_construct"] = is_before_vote_construct
    records.append(_record("is_before_vote_construct", is_before_vote_construct, "derived", "construction_start_date/vote_end_date"))

    for field_name, candidates in (
        (
            "budget_amount",
            (
                ("project_contract", "orgn_amt"),
                ("ws_project", "orgn_amt"),
                ("blueprint", "orgn_amt"),
                ("blueprint_draft", "orgn_amt"),
            ),
        ),
        ("contract_amount", (("project_contract", "contract_amt"),)),
    ):
        value, record = _map_amount_field(sources, field_name, candidates)
        if record:
            standard_fields[field_name] = value
            records.append(record)

    catalog_fields, catalog_records, mapping_result = _derive_catalog_fields(project_name)
    for field_name, value in catalog_fields.items():
        standard_fields.setdefault(field_name, value)
    records.extend(catalog_records)

    unmapped_sources = _collect_unmapped_sources(sources, records)
    return {
        "standard_fields": standard_fields,
        "field_mappings": records,
        "unmapped_sources": unmapped_sources,
        "warnings": warnings,
        "mapped_objects": mapping_result.get("mapped_objects", []),
        "matched_object_ids": mapping_result.get("matched_object_ids", []),
    }

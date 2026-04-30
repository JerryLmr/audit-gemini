from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from modules.audit_engine.core.field_runtime import FieldCandidate, FieldRuntime
from modules.audit_engine.services.rule_loader import load_rule_json


TRUTHY = {"1", "true", "y", "yes", "是", "有", "已签", "已", "存在", "已存在", "通过"}
FALSY = {"0", "false", "n", "no", "否", "无", "未签", "未", "不存在", "未通过"}
OUT_OF_WARRANTY_KEYWORDS = ("过保", "已过保", "超过保修", "保修期外", "出保")
IN_WARRANTY_KEYWORDS = ("保修期内", "未过保", "尚未过保", "仍在保修期", "在保")

def _is_present(value: Any) -> bool:
    return value is not None and value != ""


def to_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in TRUTHY:
        return True
    if text in FALSY:
        return False
    return None


def to_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except ValueError:
        return None


def to_date(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_value(value: Any, field_type: str) -> Any:
    if not _is_present(value):
        return None
    if field_type.startswith("boolean"):
        return to_bool(value)
    if field_type.startswith("number"):
        return to_number(value)
    if field_type.startswith("date"):
        return to_date(value)
    return str(value).strip() if isinstance(value, str) else value


def make_candidate(
    *,
    field_type: str,
    source_type: str,
    source_file: str,
    source_sheet: str,
    source_column: str,
    raw_value: Any,
    confidence: float = 1.0,
) -> FieldCandidate:
    return FieldCandidate(
        source_type=source_type,
        source_file=source_file,
        source_sheet=source_sheet,
        source_column=source_column,
        raw_value=raw_value,
        normalized_value=normalize_value(raw_value, field_type),
        confidence=confidence,
    )


def load_standard_field_definitions() -> Dict[str, Any]:
    return load_rule_json("standard_field_definitions.json")


def _priority_index(candidate: FieldCandidate, source_priority: Iterable[str]) -> int:
    priority = list(source_priority or [])
    labels = {
        str(candidate.source_sheet or ""),
        str(candidate.source_type or ""),
        f"{candidate.source_sheet}.{candidate.source_column}",
        f"{candidate.source_type}.{candidate.source_column}",
    }
    for index, item in enumerate(priority):
        if str(item) in labels:
            return index
    return len(priority)


def resolve_field(
    field_key: str,
    candidates: Iterable[FieldCandidate],
    field_definition: Optional[Dict[str, Any]] = None,
) -> FieldRuntime:
    definition = field_definition or {}
    ordered = sorted(
        list(candidates or []),
        key=lambda candidate: (
            _priority_index(candidate, definition.get("source_priority", [])),
            -float((candidate.confidence or 0) + float((candidate.metadata or {}).get("quality_score") or 0)),
        ),
    )
    present_indexes = [
        index
        for index, candidate in enumerate(ordered)
        if _is_present(candidate.normalized_value)
    ]
    if not present_indexes:
        return FieldRuntime(field_key=field_key, value=None, status="missing", candidates=ordered, selected_index=-1)

    selected_index = present_indexes[0]
    selected_value = ordered[selected_index].normalized_value
    distinct_values = {
        repr(ordered[index].normalized_value)
        for index in present_indexes
    }
    status = "resolved"
    if len(distinct_values) > 1:
        status = "conflicting"
        if len(present_indexes) >= 2:
            top = ordered[present_indexes[0]]
            second = ordered[present_indexes[1]]
            top_score = float(top.confidence or 0) + float((top.metadata or {}).get("quality_score") or 0)
            second_score = float(second.confidence or 0) + float((second.metadata or {}).get("quality_score") or 0)
            if abs(top_score - second_score) >= 0.2:
                status = "resolved"
    return FieldRuntime(
        field_key=field_key,
        value=selected_value,
        status=status,
        candidates=ordered,
        selected_index=selected_index,
    )


def _value(runtimes: Dict[str, FieldRuntime], field_key: str) -> Any:
    runtime = runtimes.get(field_key)
    return runtime.value if runtime else None


def _runtime(
    field_key: str,
    value: Any,
    status: str = "inferred",
    source_column: str = "derived",
) -> FieldRuntime:
    candidate = FieldCandidate(
        source_type="derived",
        source_file="",
        source_sheet="derived",
        source_column=source_column,
        raw_value=value,
        normalized_value=value,
        confidence=1.0,
    )
    return FieldRuntime(field_key=field_key, value=value, status=status, candidates=[candidate], selected_index=0)


def _date_lt(left: Optional[str], right: Optional[str]) -> Optional[bool]:
    if not left or not right:
        return None
    try:
        return datetime.strptime(left, "%Y-%m-%d").date() < datetime.strptime(right, "%Y-%m-%d").date()
    except ValueError:
        return None


def _ratio(numerator: Any, denominator: Any) -> Optional[float]:
    num = to_number(numerator)
    den = to_number(denominator)
    if num is None or den in (None, 0):
        return None
    return round(num / den, 6)


def _derive_fields(
    runtimes: Dict[str, FieldRuntime],
    catalog_mapper: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    warnings: List[str] = []
    mapping_result: Dict[str, Any] = {"mapped_objects": [], "matched_object_ids": []}
    property_value = _value(runtimes, "property_raw_value")
    raw_property = None if property_value is None else str(property_value).strip()

    property_valid = True
    if raw_property == "1" or raw_property in (None, ""):
        emergency = False
        repair_nature = "normal"
    elif raw_property == "2":
        emergency = True
        repair_nature = "emergency"
    else:
        emergency = None
        repair_nature = "unknown"
        property_valid = False
        warnings.append("property 值不在当前支持范围内（仅支持 1/2），需人工复核。")
    runtimes["property_value_valid"] = _runtime("property_value_valid", property_valid, "inferred", "property_raw_value")
    runtimes["is_emergency_repair"] = _runtime("is_emergency_repair", emergency, "inferred", "property_raw_value")
    runtimes["repair_nature"] = _runtime("repair_nature", repair_nature, "inferred", "is_emergency_repair")

    warranty_runtime = runtimes.get("warranty_status")
    warranty = "unknown"
    source_column = "expirer_remark"
    if warranty_runtime and warranty_runtime.status != "missing":
        text = str(warranty_runtime.value or "").strip()
        source_column = "warranty_status"
        if any(keyword in text for keyword in OUT_OF_WARRANTY_KEYWORDS):
            warranty = "out_of_warranty"
        elif any(keyword in text for keyword in IN_WARRANTY_KEYWORDS):
            warranty = "in_warranty"
    runtimes["warranty_status"] = _runtime("warranty_status", warranty, "inferred", source_column)
    if warranty == "unknown":
        warnings.append("保修状态缺失或无法判断，需补充保修期满依据。")

    vote_household_rate = _ratio(_value(runtimes, "vote_approved_households"), _value(runtimes, "vote_total_households"))
    vote_area_rate = _ratio(_value(runtimes, "vote_approved_area"), _value(runtimes, "vote_total_area"))
    runtimes["vote_pass_rate_by_household"] = _runtime("vote_pass_rate_by_household", vote_household_rate, "inferred", "agree_hou/count_hou")
    runtimes["vote_pass_rate_by_area"] = _runtime("vote_pass_rate_by_area", vote_area_rate, "inferred", "agree_area/sum_area")
    vote_legal = None if vote_household_rate is None or vote_area_rate is None else vote_household_rate >= 2 / 3 and vote_area_rate >= 2 / 3
    runtimes["vote_legal"] = _runtime("vote_legal", vote_legal, "inferred", "vote_rate_fields")

    explicit_vote = _value(runtimes, "has_vote_trace")
    vote_start_date = _value(runtimes, "vote_start_date")
    vote_end_date = _value(runtimes, "vote_end_date")
    resolution_date = _value(runtimes, "resolution_date")
    registration_date = _value(runtimes, "registration_date")
    if vote_end_date:
        vote_date = vote_end_date
    elif vote_start_date:
        vote_date = vote_start_date
    elif registration_date:
        vote_date = registration_date
    else:
        vote_date = resolution_date
    runtimes["vote_date"] = _runtime("vote_date", vote_date, "inferred", "vote_start_date/vote_end_date/resolution_date/registration_date")

    has_vote_trace = True if any(_value(runtimes, key) is not None for key in ("vote_total_households", "vote_approved_households", "vote_start_date", "vote_end_date", "resolution_date", "registration_date")) else bool(explicit_vote)
    runtimes["has_vote_trace"] = _runtime("has_vote_trace", has_vote_trace, "inferred", "vote_presence")
    vote_date_is_proxy = None
    if vote_date:
        vote_date_is_proxy = bool(vote_start_date or registration_date)
        if vote_date_is_proxy:
            warnings.append("当前表决关键日期来自征询开始/录入日期代替，建议人工复核。")
    runtimes["vote_date_is_proxy"] = _runtime("vote_date_is_proxy", vote_date_is_proxy, "inferred", "vote_split_dates")

    is_before_vote = None
    if repair_nature == "normal":
        is_before_vote = _date_lt(_value(runtimes, "construction_start_date"), _value(runtimes, "vote_date"))
    runtimes["is_before_vote_construct"] = _runtime("is_before_vote_construct", is_before_vote, "inferred", "construction_start_date/vote_date")

    project_name = str(_value(runtimes, "project_name") or "")
    if catalog_mapper:
        mapping_result = catalog_mapper(project_name)
    mapped_paths = [str(item.get("full_path", "")) for item in mapping_result.get("mapped_objects", [])]
    public_hit = any(
        path.startswith(("电梯/", "消防系统/", "消防泵/", "排水、排污设施/", "供水系统/", "楼栋外立面/"))
        or "屋面" in path
        or "屋顶" in path
        for path in mapped_paths
    ) or any(keyword in project_name for keyword in ("电梯", "消防", "水泵", "供水", "排水", "排污", "外墙", "外立面", "屋面", "屋顶"))
    private_hit = any(keyword in project_name for keyword in ("室内", "户内", "门锁", "室内门锁", "洁具", "入户门", "户门", "防盗门", "马桶", "水龙头", "墙面粉刷", "专有"))
    property_service_hit = any(keyword in project_name for keyword in ("树木修剪", "绿化养护", "保洁", "清洁", "卫生", "检测", "检查", "试验"))
    runtimes["is_public_part"] = _runtime("is_public_part", True if public_hit else None, "inferred", "project_name")
    runtimes["is_private_part"] = _runtime("is_private_part", True if private_hit else None, "inferred", "project_name")
    runtimes["is_property_service_scope"] = _runtime("is_property_service_scope", True if property_service_hit else None, "inferred", "project_name")
    return warnings, mapping_result


def resolve_all_fields(
    candidates_by_field: Dict[str, List[FieldCandidate]],
    *,
    catalog_mapper: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    definitions = load_standard_field_definitions().get("fields", {})
    runtimes = {
        field_key: resolve_field(field_key, candidates_by_field.get(field_key, []), definition)
        for field_key, definition in definitions.items()
    }
    warnings, mapping_result = _derive_fields(runtimes, catalog_mapper=catalog_mapper)
    runtime_dict = {field_key: runtime.to_dict() for field_key, runtime in runtimes.items()}
    missing_fields = [
        field_key
        for field_key, runtime in runtimes.items()
        if runtime.status == "missing" and definitions.get(field_key, {}).get("required_for_audit") is True
    ]
    conflicting_fields = [
        field_key
        for field_key, runtime in runtimes.items()
        if runtime.status == "conflicting"
    ]
    return {
        "standard_fields": runtime_dict,
        "missing_fields": missing_fields,
        "conflicting_fields": conflicting_fields,
        "audit_ready": not missing_fields and not conflicting_fields,
        "warnings": warnings,
        "mapped_objects": mapping_result.get("mapped_objects", []),
        "matched_object_ids": mapping_result.get("matched_object_ids", []),
    }


def runtime_values(standard_fields: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for field_key, field_value in (standard_fields or {}).items():
        if isinstance(field_value, FieldRuntime):
            values[field_key] = field_value.value
        elif isinstance(field_value, dict) and "value" in field_value:
            values[field_key] = field_value.get("value")
        else:
            values[field_key] = field_value
    return values

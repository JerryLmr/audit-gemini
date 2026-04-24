from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditRequest(BaseModel):
    project_name: Optional[str] = Field(default=None, description="工程名称；优先使用 standard_fields.project_name.value")
    standard_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="标准字段运行时对象，按 field_key 分组，每个字段包含 value/status/candidates/selected_index",
    )
    flat_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="手工演示表单输入；API 层会转换为标准字段运行时对象，pipeline 不直接读取该结构。",
    )
    missing_fields: List[str] = Field(default_factory=list)
    conflicting_fields: List[str] = Field(default_factory=list)


class BasisDocument(BaseModel):
    display_name: Optional[str] = None
    display_text: Optional[str] = None
    source_type: Optional[str] = None
    title: Optional[str] = None
    issuer: Optional[str] = None
    document_no: Optional[str] = None
    article: Optional[str] = None
    section: Optional[str] = None
    basis_strength: Optional[str] = None
    basis_explanation: Optional[str] = None


class FieldMappingRecord(BaseModel):
    standard_field: str
    value: Any = None
    source: str
    source_field: Optional[str] = None
    mapping_rule: str
    field_comment: str


class FieldMappingLayerResult(BaseModel):
    standard_fields: Dict[str, Any] = Field(default_factory=dict)
    field_mappings: List[FieldMappingRecord] = Field(default_factory=list)
    unmapped_sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MappedObject(BaseModel):
    id: int
    full_path: str
    match_score: float
    match_method: str


class AuditSubResult(BaseModel):
    applicable: bool
    result: Optional[str] = None
    display_result: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    missing_items: List[str] = Field(default_factory=list)
    basis_documents: List[BasisDocument] = Field(default_factory=list)
    audit_path: List[str] = Field(default_factory=list)
    used_standard_fields: List[str] = Field(default_factory=list)


class AuditSubAudits(BaseModel):
    entity_audit: AuditSubResult
    trace_audit: AuditSubResult
    process_audit: AuditSubResult
    amount_info: AuditSubResult


class SummaryConclusion(BaseModel):
    type: str
    entity_pass: bool = False
    conflict_detected: bool = False
    primary_message: str = ""
    display_summary: str = ""


class AuditResponse(BaseModel):
    project_name: str
    mapped_objects: List[MappedObject] = Field(default_factory=list)
    matched_object_ids: List[int] = Field(default_factory=list)
    overall_result: str
    display_result: str
    reason_codes: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    top_reasons: List[str] = Field(default_factory=list)
    basis_documents: List[BasisDocument] = Field(default_factory=list)
    top_basis_documents: List[BasisDocument] = Field(default_factory=list)
    all_basis_documents: List[BasisDocument] = Field(default_factory=list)
    missing_items: List[str] = Field(default_factory=list)
    top_missing_items: List[str] = Field(default_factory=list)
    audit_path: List[str] = Field(default_factory=list)
    manual_review_required: bool
    sub_audits: AuditSubAudits
    field_mapping_layer: FieldMappingLayerResult
    summary_conclusion: SummaryConclusion
    display_summary: str

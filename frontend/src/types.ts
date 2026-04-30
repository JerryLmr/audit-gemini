export type AuditSourceType = "original" | "extracted" | "inferred" | "missing" | "manual_required";

export interface AuditViewField {
  field_key?: string;
  field_label: string;
  value: unknown;
  display_value: string;
  source_type: AuditSourceType;
  source_label: string;
  confidence: number;
  evidence: Array<Record<string, unknown>>;
}

export interface AuditTimelineItem {
  label: string;
  value: unknown;
  display_value: string;
  source_type: AuditSourceType;
  source_label: string;
  business_meaning: string;
  confidence: number;
  warning?: string | null;
}

export interface AuditMaterialItem {
  required_item: string;
  status: "extracted" | "missing" | "partial" | "not_applicable";
  status_label: string;
  source_label: string;
  evidence_summary: string;
  affects_audit: boolean;
  remediation: string;
  confidence: number;
}

export interface RawMaterialEvidence {
  file_name: string;
  file_type: string;
  recognized: boolean;
  role: string;
  status: string;
}

export interface StructuredEvidence {
  field_label: string;
  value: string;
  source_type: AuditSourceType;
  source_label: string;
  confidence: number;
}

export interface AiInterpretation {
  title: string;
  content: string;
  confidence: number;
  source_type: AuditSourceType;
  source_label: string;
  basis_fields: string[];
}

export interface PdfExtractionField {
  field_key: string;
  field_label: string;
  value: unknown;
  source_label: string;
  raw_value: string;
  confidence: number;
  source_page: number;
}

export interface PdfExtractionEvidence {
  file_name: string;
  material_type: string;
  material_type_label: string;
  status: string;
  status_label: string;
  extracted_fields: PdfExtractionField[];
  warnings: string[];
}

export interface PolicyMatch {
  policy_title: string;
  article: string;
  tags: string[];
  matched_reason: string;
  related_audit: string;
  match_type: "support" | "risk" | "requirement";
  confidence: number;
}

export interface AuditCard {
  audit_type: string;
  result: string;
  result_label: string;
  summary: string;
  facts_used: string[];
  policy_matches: Array<Record<string, unknown>>;
  missing_materials: string[];
  recommendation: string;
}

export interface AuditView {
  display_conclusion: {
    main_result: string;
    summary: string;
    risk_level: "low" | "medium" | "high";
    next_actions: string[];
  };
  project_overview: Record<string, AuditViewField>;
  flat_standard_fields?: Record<string, unknown>;
  field_sources?: Record<string, Array<Record<string, unknown>>>;
  material_evidence?: Array<Record<string, unknown>>;
  timeline: AuditTimelineItem[];
  material_scan: AuditMaterialItem[];
  evidence_sections: {
    raw_materials: RawMaterialEvidence[];
    structured_extraction: StructuredEvidence[];
    ai_interpretation: AiInterpretation[];
    low_confidence_candidates: AuditViewField[];
    pdf_extraction?: PdfExtractionEvidence[];
  };
  policy_matches: PolicyMatch[];
  audit_cards: AuditCard[];
  auditor_notes: {
    status: string;
    warnings: string[];
    conflict_count: number;
    llm_status: Record<string, unknown>;
  };
}

export interface BackendAnalyzeResponse {
  audit_view: AuditView;
}

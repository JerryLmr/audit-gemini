export interface BackendAttachment {
  filename: string;
  content_type?: string;
  file_size?: number | null;
  status: string;
  used_for_audit: boolean;
  message?: string;
}

export interface BackendFieldConflict {
  field: string;
  field_label: string;
  parser_value: string;
  llm_value: string;
  final_value: string;
  reason: string;
  evidence?: string;
}

export interface BackendAuditSubResult {
  result?: string;
  display_result?: string;
  reason_codes?: string[];
  reasons?: string[];
  missing_items?: string[];
  basis_documents?: Array<Record<string, unknown>>;
}

export interface BackendAnalyzeResponse {
  status: string;
  message?: string;
  project_name?: string;
  warnings?: string[];
  attachments?: BackendAttachment[];
  raw_fields?: Record<string, unknown>;
  final_fields?: Record<string, unknown>;
  llm_result?: Record<string, unknown>;
  field_conflicts?: BackendFieldConflict[];
  audit_result?: {
    overall_result?: string;
    display_result?: string;
    sub_audits?: Record<string, BackendAuditSubResult>;
  };
}

export interface ViewSection {
  title: string;
  result: string;
  riskLevel: string;
  summary: string;
}

export interface ViewIssue {
  title: string;
  description: string;
  suggestion: string;
  basis: string[];
}

export interface ViewEvidence {
  label: string;
  value: string;
  source: string;
}

export interface AuditViewModel {
  projectName: string;
  summary: string;
  overallResult: string;
  riskLevel: string;
  llmStatus: string;
  llmModel: string;
  sections: ViewSection[];
  issues: ViewIssue[];
  evidence: ViewEvidence[];
  matrix: {
    timeline: Array<{ label: string; value: string; risk?: "none" | "medium" | "high" }>;
    materials: Array<{ label: string; status: "已提取" | "缺项" | "未识别" | "需复核" }>;
    finance: Array<{ label: string; value: string; note?: string }>;
  };
  attachments: BackendAttachment[];
  warnings: string[];
  auditorView: {
    reasonCodes: string[];
    rawFields: Array<{ label: string; value: string }>;
    conflicts: BackendFieldConflict[];
  };
}

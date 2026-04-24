import {
  AuditViewModel,
  BackendAnalyzeResponse,
  BackendAuditSubResult,
  BackendFieldConflict,
  ViewIssue,
  ViewSection,
} from "../types";

const FIELD_LABELS: Record<string, string> = {
  project_name: "项目名称",
  project_item_code: "工程编号",
  warranty_status: "保修状态",
  is_public_part: "共用部位/设施",
  is_private_part: "专有部分",
  is_property_service_scope: "物业服务范围",
  has_vote_trace: "业主表决材料",
  vote_date: "表决日期",
  need_construction_contract: "是否需要施工合同",
  has_construction_contract: "施工合同",
  has_appraisal_contract: "审价合同",
  has_appraisal_report: "审价报告",
  budget_amount: "预算金额",
  contract_amount: "合同金额",
  repair_scope: "维修范围",
  repair_reason: "维修原因",
  project_type: "项目类型",
  repair_object: "维修对象",
};

const SECTION_META: Array<{ key: string; title: string }> = [
  { key: "entity_audit", title: "使用范围" },
  { key: "process_audit", title: "流程" },
  { key: "trace_audit", title: "材料" },
  { key: "amount_info", title: "金额" },
];

function getRiskLevel(result: string): string {
  if (result === "non_compliant") return "高";
  if (result === "need_supplement" || result === "manual_review") return "中";
  return "低";
}

function normalizeValue(value: unknown): string {
  if (value === true) return "是";
  if (value === false) return "否";
  if (value === null || value === undefined || value === "") return "未知";
  if (value === "in_warranty") return "保修期内";
  if (value === "out_of_warranty") return "已过保";
  if (value === "unknown") return "未知";
  return String(value);
}

function pickOverallResult(result: BackendAnalyzeResponse): string {
  return result.audit_result?.display_result || result.audit_result?.overall_result || "待复核";
}

function buildSummary(result: BackendAnalyzeResponse): string {
  if (result.message) return result.message;
  const overall = pickOverallResult(result);
  const warningText = (result.warnings || []).slice(0, 2).join("；");
  if (warningText) return `总体结论：${overall}。提示：${warningText}`;
  return `总体结论：${overall}。`;
}

function buildSections(result: BackendAnalyzeResponse): ViewSection[] {
  const subAudits = result.audit_result?.sub_audits || {};
  return SECTION_META.map(({ key, title }) => {
    const sub = (subAudits[key] || {}) as BackendAuditSubResult;
    const subResult = sub.result || "manual_review";
    return {
      title,
      result: sub.display_result || "需复核",
      riskLevel: getRiskLevel(subResult),
      summary: (sub.reasons || [])[0] || "暂无异常提示。",
    };
  });
}

function dedupeBasis(basisDocs: Array<Record<string, unknown>> = []): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const doc of basisDocs) {
    const label = String(doc.display_text || doc.display_name || doc.title || "").trim();
    if (!label || seen.has(label)) continue;
    seen.add(label);
    out.push(label);
  }
  return out;
}

function buildIssues(result: BackendAnalyzeResponse): ViewIssue[] {
  const subAudits = result.audit_result?.sub_audits || {};
  const issues: ViewIssue[] = [];
  for (const section of Object.values(subAudits)) {
    const sub = (section || {}) as BackendAuditSubResult;
    const subResult = sub.result || "manual_review";
    if (subResult === "compliant" || subResult === "info_only") continue;

    const reasons = sub.reasons || [];
    const basis = dedupeBasis(sub.basis_documents || []);
    if (!reasons.length) {
      issues.push({
        title: "审计问题提示",
        description: "规则引擎提示该项需要人工复核。",
        suggestion: "请补充材料并复核相关字段。",
        basis,
      });
      continue;
    }

    for (const reason of reasons) {
      issues.push({
        title: "审计问题提示",
        description: reason,
        suggestion: "请补充材料并复核相关字段。",
        basis,
      });
    }
  }
  return issues;
}

function buildEvidence(result: BackendAnalyzeResponse) {
  const evidence = [];
  for (const [key, value] of Object.entries(result.raw_fields || {})) {
    evidence.push({
      label: FIELD_LABELS[key] || "其他字段",
      value: normalizeValue(value),
      source: "解析器",
    });
  }

  const llmFields = (result.llm_result?.fields || {}) as Record<string, unknown>;
  for (const [key, value] of Object.entries(llmFields)) {
    evidence.push({
      label: FIELD_LABELS[key] || "其他字段",
      value: normalizeValue(value),
      source: "LLM",
    });
  }
  return evidence;
}

function collectReasonCodes(result: BackendAnalyzeResponse): string[] {
  const subAudits = result.audit_result?.sub_audits || {};
  const codes = new Set<string>();
  for (const sub of Object.values(subAudits)) {
    ((sub as BackendAuditSubResult).reason_codes || []).forEach((code) => codes.add(code));
  }
  return [...codes];
}

function mapRawFields(result: BackendAnalyzeResponse): Array<{ label: string; value: string }> {
  return Object.entries(result.raw_fields || {}).map(([key, value]) => ({
    label: FIELD_LABELS[key] || key,
    value: normalizeValue(value),
  }));
}

export function mapBackendAuditToViewModel(result: BackendAnalyzeResponse): AuditViewModel {
  const overall = result.audit_result?.overall_result || "manual_review";
  const conflicts: BackendFieldConflict[] = result.field_conflicts || [];
  const riskLevel = conflicts.length ? "中" : getRiskLevel(overall);

  return {
    projectName: result.project_name || "未识别项目",
    summary: buildSummary(result),
    overallResult: pickOverallResult(result),
    riskLevel,
    sections: buildSections(result),
    issues: buildIssues(result),
    evidence: buildEvidence(result),
    attachments: result.attachments || [],
    warnings: result.warnings || [],
    auditorView: {
      reasonCodes: collectReasonCodes(result),
      rawFields: mapRawFields(result),
      conflicts,
    },
  };
}

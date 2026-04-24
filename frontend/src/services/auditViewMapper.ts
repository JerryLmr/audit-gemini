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
  final_amount: "决算金额",
  repair_scope: "维修范围",
  repair_reason: "维修原因",
  project_type: "项目类型",
  repair_object: "维修对象",
  construction_start_date: "施工开始日期",
  construction_finish_date: "施工完成日期",
  contract_sign_date: "合同签订日期",
  vote_date_is_proxy: "表决日期代理值",
};

const SECTION_META: Array<{ key: string; title: string }> = [
  { key: "entity_audit", title: "使用范围" },
  { key: "process_audit", title: "流程" },
  { key: "trace_audit", title: "材料" },
  { key: "amount_info", title: "金额" },
];

const ISSUE_TITLE_MAP: Array<{ match: RegExp; title: string }> = [
  { match: /IN_WARRANTY|WARRANTY_UNKNOWN|保修期/i, title: "保修期依据缺失" },
  { match: /MISSING_CONSTRUCTION_CONTRACT|CONSTRUCTION_CONTRACT/i, title: "施工合同材料缺失" },
  { match: /MISSING_APPRAISAL_CONTRACT|APPRAISAL_CONTRACT/i, title: "审价合同材料缺失" },
  { match: /MISSING_APPRAISAL_REPORT|APPRAISAL_REPORT/i, title: "审价报告材料缺失" },
  { match: /FIELD_CONFLICT|冲突/i, title: "字段来源存在冲突" },
  { match: /mixed_scope|边界风险|OBJECT_UNKNOWN/i, title: "维修范围存在边界风险" },
  { match: /llm|AI 字段归类/i, title: "AI字段归类未启用" },
];

function getRiskLevel(result: string): string {
  if (result === "non_compliant") return "高";
  if (result === "need_supplement" || result === "manual_review") return "中";
  return "低";
}

function normalizeValue(value: unknown): string {
  if (value === true) return "是";
  if (value === false) return "否";
  if (value === null || value === undefined || value === "") return "未识别";
  if (value === "in_warranty") return "保修期内";
  if (value === "out_of_warranty") return "已过保";
  if (value === "unknown") return "未识别";
  return String(value);
}

function runtimeValue(runtime: unknown): unknown {
  if (runtime && typeof runtime === "object" && "value" in (runtime as Record<string, unknown>)) {
    return (runtime as Record<string, unknown>).value;
  }
  return runtime;
}

function getField(result: BackendAnalyzeResponse, keys: string[]): unknown {
  const finalFields = (result.final_fields || {}) as Record<string, unknown>;
  const rawFields = (result.raw_fields || {}) as Record<string, unknown>;
  for (const key of keys) {
    const finalValue = runtimeValue(finalFields[key]);
    if (finalValue !== undefined && finalValue !== null && finalValue !== "") return finalValue;
    const rawValue = rawFields[key];
    if (rawValue !== undefined && rawValue !== null && rawValue !== "") return rawValue;
  }
  return null;
}

function formatLawText(rawTitle: string, rawArticle: string): string {
  const title = rawTitle.startsWith("《") ? rawTitle : `《${rawTitle}》`;
  if (!rawArticle) return title;
  return `${title}${rawArticle}`;
}

function formatBasisDoc(doc: Record<string, unknown>): string {
  const title = String(doc.title || doc.display_name || "").trim();
  if (!title) return "";
  const article = String(doc.article || "").trim();
  return formatLawText(title, article);
}

function dedupeBasis(basisDocs: Array<Record<string, unknown>> = []): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const doc of basisDocs) {
    const formatted = formatBasisDoc(doc);
    if (!formatted || seen.has(formatted)) continue;
    seen.add(formatted);
    out.push(formatted);
  }
  return out;
}

function pickOverallResult(result: BackendAnalyzeResponse): string {
  return result.audit_result?.display_result || result.audit_result?.overall_result || "待复核";
}

function buildSummary(result: BackendAnalyzeResponse): string {
  if (result.message) return result.message;
  const overall = pickOverallResult(result);
  return `总体结论：${overall}。请结合问题卡片与证据矩阵进行复核。`;
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

function deriveIssueTitle(reasonCode: string, description: string): string {
  const source = `${reasonCode} ${description}`;
  for (const rule of ISSUE_TITLE_MAP) {
    if (rule.match.test(source)) return rule.title;
  }
  return "审计问题提示";
}

function deriveSuggestion(reasonCode: string, missingItems: string[], description: string): string {
  const source = `${reasonCode} ${description}`;
  if (/WARRANTY|保修期/i.test(source)) {
    return "请补充保修期届满证明、质保责任期说明、建设单位/施工单位保修责任排除说明等材料。";
  }
  if (/CONSTRUCTION_CONTRACT/i.test(source)) {
    return "请补充施工合同、合同签署页与施工单位信息，必要时补充事后确认材料。";
  }
  if (/APPRAISAL_CONTRACT/i.test(source)) {
    return "请补充审价合同或造价咨询委托材料，并补全合同主体与时间信息。";
  }
  if (/APPRAISAL_REPORT/i.test(source)) {
    return "请补充审价报告/预算审核报告及对应金额明细。";
  }
  if (/FIELD_CONFLICT|冲突/i.test(source)) {
    return "请人工核验字段来源，确认最终取值并补充佐证材料。";
  }
  if (/mixed_scope|边界风险/i.test(source)) {
    return "请拆分维修对象边界，补充立项范围说明与对应材料。";
  }
  if (/llm/i.test(source)) {
    return "请确认 LM Studio 已启动并加载模型，或继续使用规则审计结果。";
  }
  if (missingItems.length) {
    const mapped = missingItems.map((item) => FIELD_LABELS[item] || item);
    return `请补充以下材料并复核：${mapped.join("、")}。`;
  }
  return "请结合原始资料进行人工复核，并补充缺失佐证材料。";
}

function decorateDescription(reasonCode: string, description: string): string {
  if (/WARRANTY|保修期/i.test(reasonCode + description)) {
    return (
      description +
      " 专项维修资金原则上用于物业保修期满后的共用部位、共用设施设备维修和更新改造。当前建议补充保修期相关材料后人工复核。"
    );
  }
  return description;
}

function buildIssues(result: BackendAnalyzeResponse): ViewIssue[] {
  const subAudits = result.audit_result?.sub_audits || {};
  const issues: ViewIssue[] = [];
  for (const section of Object.values(subAudits)) {
    const sub = (section || {}) as BackendAuditSubResult;
    const subResult = sub.result || "manual_review";
    if (subResult === "compliant" || subResult === "info_only") continue;

    const reasons = sub.reasons || [];
    const reasonCodes = sub.reason_codes || [];
    const basis = dedupeBasis(sub.basis_documents || []);
    const missingItems = sub.missing_items || [];
    const issueLength = Math.max(reasons.length, reasonCodes.length, 1);

    for (let i = 0; i < issueLength; i += 1) {
      const code = reasonCodes[i] || reasonCodes[0] || "";
      const reason = reasons[i] || reasons[0] || "规则引擎提示该项需要人工复核。";
      issues.push({
        title: deriveIssueTitle(code, reason),
        description: decorateDescription(code, reason),
        suggestion: deriveSuggestion(code, missingItems, reason),
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

function asDateValue(value: unknown): number | null {
  if (!value) return null;
  const time = new Date(String(value)).getTime();
  return Number.isNaN(time) ? null : time;
}

function formatCurrency(value: unknown): string {
  if (value === null || value === undefined || value === "") return "未识别";
  const num = typeof value === "number" ? value : Number(String(value).replace(/,/g, ""));
  if (Number.isNaN(num)) return "未识别";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 }).format(num);
}

function buildMatrix(result: BackendAnalyzeResponse, conflicts: BackendFieldConflict[]) {
  const voteDate = getField(result, ["vote_date"]);
  const startDate = getField(result, ["construction_start_date"]);
  const voteTime = asDateValue(voteDate);
  const startTime = asDateValue(startDate);
  const conflictFields = new Set(conflicts.map((item) => item.field));

  const timeline = [
    { label: "表决/征询开始日期", value: normalizeValue(getField(result, ["request_start_date", "vote_start_date"])) },
    { label: "表决/征询结束日期", value: normalizeValue(getField(result, ["request_end_date", "vote_date"])) },
    { label: "维修预案/决案日期", value: normalizeValue(getField(result, ["repair_plan_date", "decision_date"])) },
    { label: "施工开始日期", value: normalizeValue(startDate) },
    { label: "施工完成日期", value: normalizeValue(getField(result, ["construction_finish_date"])) },
    { label: "合同签订日期", value: normalizeValue(getField(result, ["contract_sign_date"])) },
    { label: "报修/工单创建日期", value: normalizeValue(getField(result, ["work_order_create_date", "report_date"])) },
  ].map((item) => ({ ...item, risk: "none" as "none" | "medium" | "high" }));

  if (voteTime && startTime && startTime < voteTime) {
    timeline[3].risk = "high";
    timeline[1].risk = "high";
  } else if (getField(result, ["vote_date_is_proxy"]) === true) {
    timeline[1].risk = "medium";
  }

  const materialStatus = (fieldKeys: string[]): "已提取" | "缺项" | "未识别" | "需复核" => {
    const field = fieldKeys[0];
    if (field && conflictFields.has(field)) return "需复核";
    const val = getField(result, fieldKeys);
    if (val === true) return "已提取";
    if (val === false) return "缺项";
    if (val === null || val === undefined || val === "") return "未识别";
    return "需复核";
  };

  const materials = [
    { label: "维修工单", status: materialStatus(["has_work_order"]) },
    { label: "维修预案", status: materialStatus(["has_repair_plan"]) },
    { label: "业主征询意见/表决汇总", status: materialStatus(["has_vote_trace"]) },
    { label: "业主大会决议", status: materialStatus(["has_owner_resolution"]) },
    { label: "施工合同", status: materialStatus(["has_construction_contract"]) },
    { label: "审价合同", status: materialStatus(["has_appraisal_contract"]) },
    { label: "审价报告", status: materialStatus(["has_appraisal_report"]) },
    { label: "验收报告/完工报告", status: materialStatus(["has_acceptance_report"]) },
  ];

  const finance = [
    { label: "预算金额", value: formatCurrency(getField(result, ["budget_amount"])), note: "仅展示" },
    { label: "合同金额", value: formatCurrency(getField(result, ["contract_amount"])), note: "仅展示" },
    { label: "决算/最终金额", value: formatCurrency(getField(result, ["final_amount"])), note: "仅展示" },
    { label: "是否需要审价", value: normalizeValue(getField(result, ["need_appraisal", "has_appraisal_contract"])) },
    { label: "维修资金性质/项目属性", value: normalizeValue(getField(result, ["repair_nature", "property_raw_value"])) },
    { label: "申报主体/相关人员", value: normalizeValue(getField(result, ["applicant_name", "applicants", "owner_name"])) },
  ];

  return { timeline, materials, finance };
}

function llmDisplay(result: BackendAnalyzeResponse): { llmStatus: string; llmModel: string } {
  const llm = (result.llm_result || {}) as Record<string, unknown>;
  const selected = String(llm.selected_model || llm.model || "").trim();
  const available = llm.available === true;
  if (available) {
    return { llmStatus: "可用", llmModel: selected || "未识别模型" };
  }
  return { llmStatus: "未启用（规则审计继续）", llmModel: selected || "不可用" };
}

export function mapBackendAuditToViewModel(result: BackendAnalyzeResponse): AuditViewModel {
  const overall = result.audit_result?.overall_result || "manual_review";
  const conflicts: BackendFieldConflict[] = result.field_conflicts || [];
  const riskLevel = conflicts.length ? "中" : getRiskLevel(overall);
  const llmInfo = llmDisplay(result);

  return {
    projectName: result.project_name || "未识别项目",
    summary: buildSummary(result),
    overallResult: pickOverallResult(result),
    riskLevel,
    llmStatus: llmInfo.llmStatus,
    llmModel: llmInfo.llmModel,
    sections: buildSections(result),
    issues: buildIssues(result),
    evidence: buildEvidence(result),
    matrix: buildMatrix(result, conflicts),
    attachments: result.attachments || [],
    warnings: result.warnings || [],
    auditorView: {
      reasonCodes: collectReasonCodes(result),
      rawFields: mapRawFields(result),
      conflicts,
    },
  };
}

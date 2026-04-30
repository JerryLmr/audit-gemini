import {
  AlertCircle,
  AlertTriangle,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Download,
  FileSearch,
  FileText,
  ListChecks,
  Scale,
  ShieldCheck,
  TimerReset,
  WalletCards,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  AuditMaterialItem,
  AuditSourceType,
  AuditView,
  AuditViewField,
} from "../types";

type Tone = "emerald" | "amber" | "rose" | "indigo" | "cyan" | "blue" | "slate";

type ComplianceDimension = {
  label: string;
  value: string;
  tone: Tone;
};

type IssueCard = {
  code: "TIMING" | "PROCESS" | "COMPLETENESS" | "AMOUNT" | "SCOPE";
  title: string;
  level: string;
  summary: string;
  recommendation: string;
  tone: Tone;
};

function sourceBadgeClass(type: AuditSourceType) {
  if (type === "original")
    return "border-blue-400/30 bg-blue-500/10 text-blue-200";
  if (type === "extracted")
    return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
  if (type === "inferred")
    return "border-violet-400/30 bg-violet-500/10 text-violet-200";
  if (type === "missing")
    return "border-rose-400/30 bg-rose-500/10 text-rose-200";
  return "border-amber-400/30 bg-amber-500/10 text-amber-200";
}

function sourceLabel(type: AuditSourceType) {
  return {
    original: "原始",
    extracted: "抽取",
    inferred: "推断",
    missing: "缺失",
    manual_required: "人工复核",
  }[type];
}

function materialStatusClass(status: AuditMaterialItem["status"]) {
  if (status === "extracted")
    return "text-emerald-200 bg-emerald-500/10 border-emerald-400/30";
  if (status === "partial")
    return "text-amber-200 bg-amber-500/10 border-amber-400/30";
  if (status === "missing")
    return "text-rose-200 bg-rose-500/10 border-rose-400/30";
  return "text-slate-300 bg-slate-500/10 border-slate-400/20";
}

function timelineDotClass(type: AuditSourceType) {
  if (type === "original")
    return "border-blue-200 bg-blue-400 shadow-[0_0_18px_rgba(96,165,250,0.55)]";
  if (type === "extracted")
    return "border-emerald-200 bg-emerald-400 shadow-[0_0_18px_rgba(52,211,153,0.45)]";
  if (type === "inferred")
    return "border-violet-200 bg-violet-400 shadow-[0_0_18px_rgba(167,139,250,0.45)]";
  if (type === "manual_required")
    return "border-amber-200 bg-amber-400 shadow-[0_0_18px_rgba(251,191,36,0.45)]";
  return "border-rose-200 bg-rose-400 shadow-[0_0_18px_rgba(251,113,133,0.45)]";
}

function toneBorderClass(tone: Tone) {
  return {
    emerald: "border-emerald-400/30 bg-emerald-500/10 text-emerald-100",
    amber: "border-amber-400/30 bg-amber-500/10 text-amber-100",
    rose: "border-rose-400/30 bg-rose-500/10 text-rose-100",
    indigo: "border-indigo-400/30 bg-indigo-500/10 text-indigo-100",
    cyan: "border-cyan-400/30 bg-cyan-500/10 text-cyan-100",
    blue: "border-blue-400/30 bg-blue-500/10 text-blue-100",
    slate: "border-slate-400/20 bg-slate-500/10 text-slate-200",
  }[tone];
}

function complianceSummaryClass(tone: Tone) {
  return {
    emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    amber: "border-amber-500/20 bg-amber-500/10 text-amber-400",
    rose: "border-rose-500/20 bg-rose-500/10 text-rose-400",
    indigo: "border-indigo-500/20 bg-indigo-500/10 text-indigo-400",
    cyan: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    blue: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
    slate: "border-slate-500/20 bg-slate-500/10 text-slate-400",
  }[tone];
}

function complianceSummaryBadgeClass(
  risk: AuditView["display_conclusion"]["risk_level"],
) {
  if (risk === "high") return "border-rose-500/30 bg-rose-500/20 text-rose-400";
  if (risk === "medium")
    return "border-amber-500/30 bg-amber-500/20 text-amber-400";
  return "border-emerald-500/30 bg-emerald-500/20 text-emerald-400";
}

function issueAccentClass(tone: Tone) {
  return {
    emerald: "border-l-emerald-400",
    amber: "border-l-amber-400",
    rose: "border-l-rose-400",
    indigo: "border-l-indigo-400",
    cyan: "border-l-cyan-400",
    blue: "border-l-blue-400",
    slate: "border-l-slate-400",
  }[tone];
}

function findAuditCard(view: AuditView, label: string) {
  return view.audit_cards.find((card) => card.audit_type.includes(label));
}

function resultTone(result?: string): Tone {
  if (result === "compliant") return "emerald";
  if (result === "non_compliant") return "rose";
  if (result === "need_supplement") return "amber";
  if (result === "manual_review") return "amber";
  return "slate";
}

function resultText(card: ReturnType<typeof findAuditCard>) {
  return card?.result_label || "需复核";
}

function buildComplianceDimensions(view: AuditView): ComplianceDimension[] {
  const scope = findAuditCard(view, "使用范围");
  const process = findAuditCard(view, "流程");
  const amount = findAuditCard(view, "金额");
  const missingCount = view.material_scan.filter(
    (item) => item.status === "missing",
  ).length;
  const hasTimelineMissing = view.timeline.some(
    (item) => item.source_type === "missing",
  );
  return [
    {
      label: "资金使用范围",
      value: resultText(scope),
      tone: resultTone(scope?.result),
    },
    {
      label: "流程合规性",
      value: resultText(process),
      tone: resultTone(process?.result),
    },
    {
      label: "时序完整性",
      value: hasTimelineMissing ? "缺失" : "合规",
      tone: hasTimelineMissing ? "rose" : "emerald",
    },
    {
      label: "材料完整性",
      value: missingCount > 0 ? "资料不完整" : "合规",
      tone: missingCount > 0 ? "amber" : "emerald",
    },
    {
      label: "金额合理性",
      value: resultText(amount),
      tone: resultTone(amount?.result),
    },
  ];
}

function buildIssueCards(view: AuditView): IssueCard[] {
  const issues: IssueCard[] = [];
  const missingItems = view.material_scan.filter(
    (item) => item.status === "missing",
  );
  const timelineWarnings = view.timeline.filter(
    (item) => item.warning || item.source_type === "missing",
  );
  const scope = findAuditCard(view, "使用范围");
  const process = findAuditCard(view, "流程");
  const amount = findAuditCard(view, "金额");

  if (timelineWarnings.length > 0) {
    issues.push({
      code: "TIMING",
      title: "施工与决议时序需复核",
      level: timelineWarnings.some((item) => item.source_type === "missing")
        ? "高风险"
        : "需复核",
      summary: timelineWarnings
        .map(
          (item) => `${item.label}：${item.warning || item.business_meaning}`,
        )
        .join("；"),
      recommendation: "请结合施工合同、开工记录、完工验收报告复核关键时序。",
      tone: "rose",
    });
  }

  if (process && process.result !== "compliant") {
    issues.push({
      code: "PROCESS",
      title: "流程合规仍需人工复核",
      level: process.result_label,
      summary: process.summary,
      recommendation:
        process.recommendation ||
        "请结合表决、公告、公示和验收材料复核流程闭环。",
      tone: "amber",
    });
  }

  if (missingItems.length > 0) {
    issues.push({
      code: "COMPLETENESS",
      title: "关键证明材料缺失",
      level: "资料不完整",
      summary: `当前未识别：${missingItems.map((item) => item.required_item).join("、")}。`,
      recommendation: "请补充缺失材料后再形成完整审计结论。",
      tone: "cyan",
    });
  }

  if (amount && amount.result !== "compliant") {
    issues.push({
      code: "AMOUNT",
      title: "金额与审价材料需复核",
      level: amount.result_label,
      summary: amount.summary,
      recommendation:
        amount.recommendation || "请结合审价合同、审价报告和最终结算金额复核。",
      tone: "indigo",
    });
  }

  if (scope) {
    issues.push({
      code: "SCOPE",
      title: "使用范围审计判断",
      level: scope.result_label,
      summary: scope.summary,
      recommendation:
        scope.recommendation || "请结合原始材料和法规命中结果保留复核记录。",
      tone: scope.result === "compliant" ? "blue" : "amber",
    });
  }

  return issues.slice(0, 6);
}

function projectTitle(view: AuditView) {
  return view.project_overview.project_name?.display_value || "未识别项目名称";
}

function todayText() {
  return new Date().toISOString().slice(0, 10);
}

function displayActionText(item: string) {
  return item.trim().replace(/[。.;；\s]+$/g, "");
}

export function ComplianceSummaryBar({ view }: { view: AuditView }) {
  const conclusion = view.display_conclusion;
  return (
    <section className="glass-card p-6">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h3 className="text-sm font-medium uppercase tracking-wide text-slate-400">
          合规维度摘要
        </h3>
        <div
          className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-widest ${complianceSummaryBadgeClass(conclusion.risk_level)}`}
        >
          {conclusion.main_result}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {buildComplianceDimensions(view).map((item) => (
          <div
            key={item.label}
            className={`rounded-xl border p-3 text-center transition-all ${complianceSummaryClass(item.tone)}`}
          >
            <p className="text-[9px] font-bold uppercase tracking-tighter opacity-80">
              {item.label}
            </p>
            <p className="mt-1 text-xs font-bold">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function ReportActionCard({ view }: { view: AuditView }) {
  const conclusion = view.display_conclusion;
  const nextActions = conclusion.next_actions
    .map(displayActionText)
    .filter(Boolean)
    .slice(0, 4);
  return (
    <section className="glass-card border border-cyan-400/10 bg-[radial-gradient(circle_at_top_right,rgba(34,211,238,0.12),transparent_34%),rgba(15,23,42,0.72)] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">
            Report Actions
          </p>
          <h3 className="mt-2 break-words text-lg font-black text-white">
            {projectTitle(view)}
          </h3>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${toneBorderClass(conclusion.risk_level === "high" ? "rose" : conclusion.risk_level === "low" ? "emerald" : "amber")}`}
            >
              {conclusion.main_result}
            </span>
            <span className="rounded-full border border-white/10 bg-white/[0.035] px-3 py-1 text-[11px] text-slate-400">
              AUDIT DATE · {todayText()}
            </span>
          </div>
        </div>
        <button
          type="button"
          className="inline-flex w-fit shrink-0 items-center justify-center gap-2 rounded-xl border border-cyan-300/20 bg-cyan-500/10 px-4 py-3 text-xs font-semibold text-cyan-100 transition hover:border-cyan-300/40 hover:bg-cyan-500/15"
        >
          <Download className="h-4 w-4" />
          下载审计报告
        </button>
      </div>
      <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-5">
        <div className="mb-3 flex items-center gap-2">
          <BrainCircuit className="h-4 w-4 text-cyan-300" />
          <p className="text-sm font-bold text-white">AI 审计综合意见</p>
        </div>
        <p className="text-sm leading-relaxed text-slate-300">
          {conclusion.summary}
        </p>
        {nextActions.length > 0 && (
          <div className="mt-4">
            <p className="mb-3 border-t border-white/10 pt-4 text-[11px] font-bold uppercase tracking-[0.18em] text-cyan-200/80">
              建议补充材料
            </p>
            <div className="space-y-2">
              {nextActions.map((item) => (
                <p
                  key={item}
                  className="border-l-2 border-cyan-400/40 bg-white/[0.025] px-3 py-2 text-xs leading-relaxed text-slate-300"
                >
                  {item}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function OverviewTextCard({ field }: { field: AuditViewField }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4 xl:col-span-2">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold text-slate-400">
          {field.field_label}
        </p>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sourceBadgeClass(field.source_type)}`}
        >
          {sourceLabel(field.source_type)}
        </span>
      </div>
      <p className="mt-3 break-words text-base font-semibold leading-relaxed text-slate-100">
        {field.display_value}
      </p>
      <p className="mt-3 break-words text-[11px] text-slate-500">
        来源：{field.source_label || "未识别"}
      </p>
      <p className="mt-1 text-[10px] text-slate-500">
        置信度：{Math.round((field.confidence || 0) * 100)}%
      </p>
    </div>
  );
}

function OverviewMetricCard({ field }: { field: AuditViewField }) {
  return (
    <div className="rounded-2xl border border-indigo-300/15 bg-indigo-500/[0.06] p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold text-indigo-200/80">
          {field.field_label}
        </p>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sourceBadgeClass(field.source_type)}`}
        >
          {sourceLabel(field.source_type)}
        </span>
      </div>
      <p className="mt-3 break-words text-xl font-black text-white">
        {field.display_value}
      </p>
      <p className="mt-3 break-words text-[11px] text-slate-500">
        来源：{field.source_label || "未识别"}
      </p>
      <p className="mt-1 text-[10px] text-slate-500">
        置信度：{Math.round((field.confidence || 0) * 100)}%
      </p>
    </div>
  );
}

export function ProjectOverviewPanel({ view }: { view: AuditView }) {
  const textFields = [
    "project_name",
    "repair_scope",
    "repair_reason",
    "applicant",
  ]
    .map((key) => view.project_overview[key])
    .filter(Boolean);
  const metricFields = [
    "budget_amount",
    "final_amount",
    "need_cost_review",
    "repair_nature",
  ]
    .map((key) => view.project_overview[key])
    .filter(Boolean);
  return (
    <section className="glass-card p-6">
      <div className="mb-5 flex items-center gap-3">
        <FileSearch className="h-5 w-5 text-blue-300" />
        <div>
          <h3 className="text-base font-bold text-white">项目概览</h3>
          <p className="text-xs text-slate-500">
            仅展示有明确业务标签的高价值字段
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
        {metricFields.map((field) => (
          <OverviewMetricCard
            key={field.field_key || field.field_label}
            field={field}
          />
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
        {textFields.map((field) => (
          <OverviewTextCard
            key={field.field_key || field.field_label}
            field={field}
          />
        ))}
      </div>
    </section>
  );
}

function IssueIcon({ code }: { code: IssueCard["code"] }) {
  if (code === "TIMING") return <TimerReset className="h-5 w-5" />;
  if (code === "COMPLETENESS") return <ListChecks className="h-5 w-5" />;
  if (code === "AMOUNT") return <WalletCards className="h-5 w-5" />;
  if (code === "SCOPE") return <ShieldCheck className="h-5 w-5" />;
  return <AlertTriangle className="h-5 w-5" />;
}

export function IssueCardsPanel({ view }: { view: AuditView }) {
  const issues = buildIssueCards(view);
  if (issues.length === 0) return null;
  return (
    <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      {issues.map((issue) => (
        <article
          key={issue.code}
          className={`glass-card border-l-4 p-5 ${issueAccentClass(issue.tone)}`}
        >
          <div className="flex items-start justify-between gap-4">
            <span
              className={`rounded-full border px-2.5 py-1 text-[10px] font-black tracking-[0.18em] ${toneBorderClass(issue.tone)}`}
            >
              {issue.code}
            </span>
            <div
              className={`rounded-xl border p-2 ${toneBorderClass(issue.tone)}`}
            >
              <IssueIcon code={issue.code} />
            </div>
          </div>
          <div className="mt-4 flex items-start justify-between gap-3">
            <h3 className="text-base font-black text-white">{issue.title}</h3>
            <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.035] px-2 py-0.5 text-[10px] text-slate-300">
              {issue.level}
            </span>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-slate-400">
            {issue.summary}
          </p>
          <p className="mt-3 text-xs leading-relaxed text-indigo-200">
            建议：{issue.recommendation}
          </p>
        </article>
      ))}
    </section>
  );
}

export function TimelineTracePanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card h-full w-full p-6">
      <div className="mb-6 flex items-center gap-3">
        <Clock3 className="h-5 w-5 text-indigo-300" />
        <div>
          <h3 className="text-base font-bold text-white">逻辑时序追踪</h3>
          <p className="text-xs text-slate-500">
            区分原始节点、系统推断节点和缺失节点
          </p>
        </div>
      </div>
      <div className="relative ml-2 space-y-5 pl-8 before:absolute before:bottom-2 before:left-[7px] before:top-2 before:w-px before:bg-white/10">
        {view.timeline.map((item) => (
          <div
            key={`${item.label}-${item.source_label}`}
            className="relative rounded-xl border border-white/10 bg-white/[0.03] p-4"
          >
            <span
              className={`absolute -left-[34px] top-5 h-4 w-4 rounded-full border-2 ${timelineDotClass(item.source_type)}`}
            />
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-lg font-bold text-slate-100">
                  {item.display_value}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-200">
                  {item.label}
                </p>
              </div>
              <span
                className={`w-fit rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sourceBadgeClass(item.source_type)}`}
              >
                {sourceLabel(item.source_type)}
              </span>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-slate-400">
              {item.business_meaning}
            </p>
            <p className="mt-2 break-words text-[11px] text-slate-500">
              来源：{item.source_label}
            </p>
            {item.warning && (
              <p className="mt-2 text-xs text-amber-300">{item.warning}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export function MaterialScanPanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card h-full w-full p-6">
      <div className="mb-5 flex items-center gap-3">
        <ListChecks className="h-5 w-5 text-emerald-300" />
        <div>
          <h3 className="text-base font-bold text-white">材料扫描结果</h3>
          <p className="text-xs text-slate-500">
            缺失材料明确标注，不做事实伪造
          </p>
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border border-white/10">
        <table className="w-full table-fixed text-xs">
          <thead className="bg-white/[0.04] text-slate-300">
            <tr>
              <th className="w-[26%] p-3 text-left font-semibold">审计要素</th>
              <th className="w-[18%] p-3 text-left font-semibold">材料状态</th>
              <th className="w-[56%] p-3 text-left font-semibold">识别来源</th>
            </tr>
          </thead>
          <tbody>
            {view.material_scan.map((item) => (
              <tr
                key={item.required_item}
                className="border-t border-white/5 align-top"
              >
                <td className="p-3 font-semibold text-slate-100">
                  {item.required_item}
                </td>
                <td className="p-3">
                  <span
                    className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${materialStatusClass(item.status)}`}
                  >
                    {item.status_label}
                  </span>
                </td>
                <td className="p-3 break-words text-slate-400">
                  {item.source_label}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function EvidenceExplorer({ view }: { view: AuditView }) {
  const fieldSources = view.field_sources || {};
  const fieldLabelMap = Object.fromEntries(
    Object.entries(view.project_overview || {}).map(([key, value]) => [key, value.field_label || key]),
  );
  const evidenceByField = Object.entries(fieldSources)
    .map(([fieldKey, sources]) => {
      const sourceList = (sources || [])
        .filter((source) => source.source_type === "pdf" || source.source_type === "excel" || source.source_type === "derived" || source.source_type === "manual_input")
        .filter((source, index, arr) => {
          const key = `${fieldKey}|${String(source.file_name || "")}|${String(source.source_sheet || "")}|${String(source.source_field || "")}|${String(source.value ?? "")}`;
          return arr.findIndex((x) => `${fieldKey}|${String(x.file_name || "")}|${String(x.source_sheet || "")}|${String(x.source_field || "")}|${String(x.value ?? "")}` === key) === index;
        });
      return { fieldKey, sources: sourceList };
    })
    .filter((item) => item.sources.length > 0);
  const buildSourceLabel = (source: Record<string, unknown>) => {
    const metadata = (source.metadata || {}) as Record<string, unknown>;
    const fileName = String(source.file_name || "");
    const sheet = String(source.source_sheet || "");
    const field = String(source.source_field || "");
    const label = String(metadata.label || field || "");
    if (String(source.source_type || "") === "pdf") {
      const page = metadata.page ? ` / 第${String(metadata.page)}页` : "";
      return `${fileName}${page} / ${label || "PDF字段"}`;
    }
    if (String(source.source_type || "") === "excel") {
      return `${fileName}${sheet ? ` / ${sheet}` : ""}${field ? ` / ${field}` : ""}`;
    }
    if (String(source.source_type || "") === "manual_input") {
      return "人工输入";
    }
    return `${sheet || "系统推断"}${field ? ` / ${field}` : ""}`;
  };
  return (
    <details className="glass-card p-6">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <BrainCircuit className="h-5 w-5 text-violet-300" />
          <div>
            <h3 className="text-base font-bold text-white">字段来源与候选值</h3>
            <p className="text-xs text-slate-500">用于审计留痕和字段来源追溯</p>
          </div>
        </div>
        <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-400">展开</span>
      </summary>
      <div className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <FileText className="h-4 w-4 text-blue-300" />
            原始材料
          </h4>
          <div className="space-y-3">
            {view.evidence_sections.raw_materials.map((item) => (
              <div
                key={item.file_name}
                className="border-b border-white/5 pb-2 text-xs"
              >
                <p className="break-words font-semibold text-slate-200">
                  {item.file_name}
                </p>
                <p className="mt-1 text-slate-500">
                  {item.file_type} · {item.role}
                </p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <CheckCircle2 className="h-4 w-4 text-emerald-300" />
            结构化抽取
          </h4>
          <div className="space-y-3">
            {view.evidence_sections.structured_extraction.map((item) => (
              <div
                key={`${item.field_label}-${item.source_label}`}
                className="border-b border-white/5 pb-2 text-xs"
              >
                <p className="font-semibold text-slate-200">
                  {item.field_label}：{item.value}
                </p>
                <p className="mt-1 break-words text-slate-500">
                  来源：{item.source_label}
                </p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <BrainCircuit className="h-4 w-4 text-violet-300" />
            AI 理解
          </h4>
          <div className="space-y-3">
            {view.evidence_sections.ai_interpretation.map((item) => (
              <div
                key={item.title}
                className="border-b border-white/5 pb-2 text-xs"
              >
                <p className="font-semibold text-slate-200">{item.title}</p>
                <p className="mt-1 leading-relaxed text-slate-400">
                  {item.content}
                </p>
                <p className="mt-1 text-slate-500">
                  置信度：{Math.round(item.confidence * 100)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
      {evidenceByField.length > 0 && (
        <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <FileText className="h-4 w-4 text-cyan-300" />
            字段来源与候选值
          </h4>
          <div className="space-y-4">
            {evidenceByField.map((entry) => (
              <div key={entry.fieldKey} className="rounded-lg border border-white/10 bg-black/20 p-3 text-xs">
                <p className="font-semibold text-slate-100">{fieldLabelMap[entry.fieldKey] || entry.fieldKey}</p>
                <p className="mt-1 text-slate-400">
                  标准值：{String((view.flat_standard_fields || {})[entry.fieldKey] ?? "未识别")}
                </p>
                <div className="mt-2 space-y-2">
                  {(entry.sources.filter((source) => source.value === (view.flat_standard_fields || {})[entry.fieldKey]).slice(0, 1)).map((source, index) => {
                    const metadata = (source.metadata || {}) as Record<string, unknown>;
                    return (
                      <div key={`${entry.fieldKey}-selected-${index}`} className="border-t border-white/5 pt-2">
                        <p className="break-words text-slate-300">
                          主来源：{buildSourceLabel(source)}
                        </p>
                        <p className="break-words text-slate-500">
                          {metadata.raw_text ? `原文：${String(metadata.raw_text)}` : `原字段：${String(source.source_field || "")}`}
                        </p>
                        <p className="text-slate-500">
                          置信度：{Math.round(Number(source.confidence || 0) * 100)}%
                        </p>
                      </div>
                    );
                  })}
                  <details className="rounded border border-white/5 p-2">
                    <summary className="cursor-pointer text-slate-400">查看其他来源</summary>
                    <div className="mt-2 space-y-2">
                      {entry.fieldKey === "repair_reason" && (() => {
                        const reasonDetails = entry.sources.filter((s) => String(s.source_field || "").toUpperCase() === "REPAIRREASON");
                        if (reasonDetails.length > 1) {
                          return (
                            <details className="rounded border border-white/5 p-2 text-slate-400">
                              <summary className="cursor-pointer">来自 REPAIRREASON 的 {reasonDetails.length} 条候选原因</summary>
                              <div className="mt-2 space-y-2">
                                {reasonDetails.map((source, index) => {
                                  const metadata = (source.metadata || {}) as Record<string, unknown>;
                                  return (
                                    <div key={`${entry.fieldKey}-repairreason-${index}`} className="border-t border-white/5 pt-2">
                                      <p className="break-words text-slate-300">来源：{buildSourceLabel(source)}</p>
                                      <p className="break-words text-slate-500">{metadata.raw_text ? `原文：${String(metadata.raw_text)}` : "原始字段：REPAIRREASON，业务含义待确认"}</p>
                                    </div>
                                  );
                                })}
                              </div>
                            </details>
                          );
                        }
                        return null;
                      })()}
                      {entry.sources.filter((source) => source.value !== (view.flat_standard_fields || {})[entry.fieldKey]).map((source, index) => {
                        if (entry.fieldKey === "repair_reason" && String(source.source_field || "").toUpperCase() === "REPAIRREASON") {
                          return null;
                        }
                        const metadata = (source.metadata || {}) as Record<string, unknown>;
                        return (
                          <div key={`${entry.fieldKey}-${index}`} className="border-t border-white/5 pt-2">
                            <p className="break-words text-slate-300">
                              来源：{buildSourceLabel(source)}
                            </p>
                            <p className="break-words text-slate-500">
                              {metadata.raw_text ? `原文：${String(metadata.raw_text)}` : `原字段：${String(source.source_field || "")}`}
                            </p>
                            <p className="text-slate-500">
                              置信度：{Math.round(Number(source.confidence || 0) * 100)}%
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </details>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </details>
  );
}

export function ConflictConfirmPanel({
  view,
  onConfirm,
}: {
  view: AuditView;
  onConfirm?: (overrides: Record<string, unknown>) => void;
}) {
  const conflicts = view.field_conflicts || [];
  const fieldSources = view.field_sources || {};
  const [manualValues, setManualValues] = useState<Record<string, string>>({});
  const [selection, setSelection] = useState<Record<string, string>>({});
  const [overrides, setOverrides] = useState<Array<Record<string, unknown>>>(view.user_overrides || []);
  const [feedback, setFeedback] = useState<string>("");
  const sourceOptions = useMemo(
    () =>
      conflicts.map((conflict) => {
        const key = String(conflict.field || "");
        const sources = (fieldSources[key] || [])
          .filter((s) => s.source_type === "pdf" || s.source_type === "excel")
          .filter((s, i, arr) => arr.findIndex((x) => `${String(x.file_name || "")}|${String(x.source_sheet || "")}|${String(x.source_field || "")}|${String(x.value ?? "")}` === `${String(s.file_name || "")}|${String(s.source_sheet || "")}|${String(s.source_field || "")}|${String(s.value ?? "")}`) === i);
        const distinctValues = sources.filter((s, i, arr) => arr.findIndex((x) => String(x.value ?? "") === String(s.value ?? "")) === i);
        return { key, sources: distinctValues };
      }),
    [conflicts, fieldSources],
  );
  const [appliedCount, setAppliedCount] = useState(0);
  if (conflicts.length === 0) return null;
  return (
    <section className="glass-card p-6">
      <div className="mb-4 flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-300" />
        <div>
          <h3 className="text-base font-bold text-white">冲突确认区</h3>
          <p className="text-xs text-slate-500">仅展示冲突字段，支持 Excel/PDF/手动确认。</p>
        </div>
      </div>
      <div className="space-y-4">
        {conflicts.map((conflict, idx) => {
          const fieldKey = String(conflict.field || "");
          const options = sourceOptions[idx]?.sources || [];
          return (
            <div key={fieldKey} className="rounded-xl border border-amber-400/20 bg-amber-500/5 p-4 text-xs">
              <p className="font-semibold text-amber-200">字段：{String(conflict.field_label || fieldKey)}</p>
              <p className="mt-1 text-slate-400">系统推荐：{String(conflict.chosen_source || "unknown")}（分差 {String(conflict.score_gap ?? "-")}）</p>
              <div className="mt-3 space-y-2">
                {options.map((opt, i) => (
                  <label key={`${fieldKey}-${i}`} className="flex items-center gap-2 text-slate-300">
                    <input type="radio" name={`conflict-${fieldKey}`} checked={selection[fieldKey] === `source-${i}`} onChange={() => setSelection((prev) => ({ ...prev, [fieldKey]: `source-${i}` }))} />
                    <span>{String(opt.source_type || "")}：{String(opt.value ?? "")}</span>
                    {Array.isArray((opt.metadata as Record<string, unknown> | undefined)?.quality_flags) && ((opt.metadata as Record<string, unknown>).quality_flags as unknown[]).includes("zero_suspicious") && (
                      <span className="rounded border border-amber-300/30 px-1 py-0.5 text-[10px] text-amber-300">该值可能异常（为0）</span>
                    )}
                  </label>
                ))}
                <label className="flex items-center gap-2 text-slate-300">
                  <input type="radio" name={`conflict-${fieldKey}`} checked={selection[fieldKey] === "manual"} onChange={() => setSelection((prev) => ({ ...prev, [fieldKey]: "manual" }))} />
                  <span>手动输入：</span>
                  <input className="rounded border border-white/20 bg-black/30 px-2 py-1 text-xs text-white" value={manualValues[fieldKey] || ""} onChange={(e) => setManualValues((prev) => ({ ...prev, [fieldKey]: e.target.value }))} />
                </label>
              </div>
            </div>
          );
        })}
      </div>
      <button
        className="mt-4 rounded border border-amber-300/30 px-3 py-2 text-amber-200 hover:bg-amber-500/10"
        onClick={() => {
          const payload: Record<string, unknown> = {};
          const nextOverrides: Array<Record<string, unknown>> = [];
          conflicts.forEach((conflict, idx) => {
            const fieldKey = String(conflict.field || "");
            const options = sourceOptions[idx]?.sources || [];
            const selected = selection[fieldKey] || "source-0";
            const selectedValue = selected === "manual" ? manualValues[fieldKey] || "" : options[Number(selected.split("-")[1])]?.value;
            payload[fieldKey] = selectedValue;
            nextOverrides.push({ field_key: fieldKey, selected_value: selectedValue, selected_by: "user_override", selected_at: new Date().toISOString() });
          });
          setOverrides(nextOverrides);
          setAppliedCount(Object.keys(payload).length);
          onConfirm?.(payload);
          setFeedback("已批量应用所选字段。");
        }}
      >
        确认采用所选字段
      </button>
      {feedback && <p className="mt-3 text-xs text-emerald-300">{feedback}</p>}
      {overrides.length > 0 && <p className="mt-3 text-xs text-slate-400">已记录 {appliedCount || overrides.length} 条人工确认（当前为前端会话态）。</p>}
    </section>
  );
}

export function PolicyMatchPanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card p-6">
      <div className="mb-5 flex items-center gap-3">
        <Scale className="h-5 w-5 text-amber-300" />
        <div>
          <h3 className="text-base font-bold text-white">法规匹配</h3>
          <p className="text-xs text-slate-500">
            展示当前项目命中的法规依据和审计点
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {view.policy_matches.map((item) => (
          <article
            key={`${item.policy_title}-${item.article}-${item.related_audit}`}
            className="rounded-xl border border-white/10 bg-white/[0.03] p-4"
          >
            <div className="flex flex-wrap gap-2">
              {item.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-2 py-0.5 text-[10px] text-indigo-200"
                >
                  {tag}
                </span>
              ))}
            </div>
            <h4 className="mt-3 text-sm font-bold text-white">
              《{item.policy_title}》{item.article}
            </h4>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">
              {item.matched_reason}
            </p>
            <p className="mt-2 text-[11px] text-slate-500">
              命中审计点：{item.related_audit}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function AuditCardsPanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card p-6">
      <div className="mb-5 flex items-center gap-3">
        <CheckCircle2 className="h-5 w-5 text-indigo-300" />
        <div>
          <h3 className="text-base font-bold text-white">分项审计卡片</h3>
          <p className="text-xs text-slate-500">
            保留审计类型、判断摘要和建议动作
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {view.audit_cards.map((card) => (
          <article
            key={card.audit_type}
            className="rounded-xl border border-white/10 bg-white/[0.03] p-5"
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-sm font-bold text-white">
                {card.audit_type}
              </h3>
              <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-slate-300">
                {card.result_label}
              </span>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-slate-400">
              {card.summary}
            </p>
            {card.recommendation && (
              <p className="mt-3 text-xs text-indigo-200">
                建议：{card.recommendation}
              </p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

export function AuditorNotesPanel({ view }: { view: AuditView }) {
  return (
    <details className="glass-card group p-6">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-slate-400" />
          <div>
            <h3 className="text-base font-bold text-white">
              技术诊断 / 审计留痕
            </h3>
            <p className="text-xs text-slate-500">
              展开后查看系统状态、冲突数量和运行提醒
            </p>
          </div>
        </div>
        <span className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-slate-400 group-open:text-indigo-200">
          展开
        </span>
      </summary>
      <div className="mt-5 grid grid-cols-1 gap-4 text-xs md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-semibold text-slate-200">
            系统状态：{view.auditor_notes.status}
          </p>
          <p className="mt-2 text-slate-500">
            字段冲突数：{view.auditor_notes.conflict_count}
          </p>
          <p className="mt-2 break-words text-slate-500">
            LLM：
            {String(view.auditor_notes.llm_status?.selected_model || "未记录")}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-semibold text-slate-200">提醒</p>
          <ul className="mt-2 space-y-1 text-slate-500">
            {view.auditor_notes.warnings.length === 0 && (
              <li>暂无额外提醒。</li>
            )}
            {view.auditor_notes.warnings.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 md:col-span-2">
          <p className="font-semibold text-slate-200">分项审计留痕</p>
          <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
            {view.audit_cards.map((card) => (
              <div
                key={card.audit_type}
                className="rounded-lg border border-white/5 bg-black/10 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="font-semibold text-slate-200">
                    {card.audit_type}
                  </p>
                  <span className="shrink-0 rounded-full border border-white/10 px-2 py-0.5 text-[10px] text-slate-400">
                    {card.result_label}
                  </span>
                </div>
                <p className="mt-2 line-clamp-2 text-slate-500">
                  {card.summary}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </details>
  );
}

export function AuditWorkspace({ view }: { view: AuditView }) {
  const [localOverrides, setLocalOverrides] = useState<Record<string, unknown>>({});
  const effectiveView = useMemo(() => {
    if (!Object.keys(localOverrides).length) return view;
    const next = { ...view };
    next.flat_standard_fields = { ...(view.flat_standard_fields || {}), ...localOverrides };
    const nextOverview = { ...(view.project_overview || {}) };
    Object.entries(localOverrides).forEach(([key, value]) => {
      const entry = nextOverview[key];
      if (entry) {
        nextOverview[key] = {
          ...entry,
          value,
          display_value: String(value ?? "未识别"),
          source_type: "manual_required",
          source_label: "人工确认覆盖（会话态）",
        };
      }
    });
    next.project_overview = nextOverview;
    return next;
  }, [view, localOverrides]);

  return (
    <div className="w-full space-y-6">
      <IssueCardsPanel view={effectiveView} />
      <ProjectOverviewPanel view={effectiveView} />
      <div className="grid w-full grid-cols-1 gap-6 xl:grid-cols-2">
        <MaterialScanPanel view={effectiveView} />
        <TimelineTracePanel view={effectiveView} />
      </div>
      <ConflictConfirmPanel view={effectiveView} onConfirm={(overrides) => setLocalOverrides((prev) => ({ ...prev, ...overrides }))} />
      <PolicyMatchPanel view={effectiveView} />
      <EvidenceExplorer view={effectiveView} />
      <AuditorNotesPanel view={effectiveView} />
    </div>
  );
}

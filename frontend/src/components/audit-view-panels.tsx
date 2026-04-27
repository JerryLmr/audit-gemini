import {
  AlertCircle,
  BookOpen,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  FileSearch,
  FileText,
  ListChecks,
  Scale,
} from "lucide-react";
import { AuditMaterialItem, AuditSourceType, AuditView, AuditViewField } from "../types";

function sourceBadgeClass(type: AuditSourceType) {
  if (type === "original") return "border-blue-400/30 bg-blue-500/10 text-blue-200";
  if (type === "extracted") return "border-emerald-400/30 bg-emerald-500/10 text-emerald-200";
  if (type === "inferred") return "border-violet-400/30 bg-violet-500/10 text-violet-200";
  if (type === "missing") return "border-rose-400/30 bg-rose-500/10 text-rose-200";
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
  if (status === "extracted") return "text-emerald-200 bg-emerald-500/10 border-emerald-400/30";
  if (status === "partial") return "text-amber-200 bg-amber-500/10 border-amber-400/30";
  if (status === "missing") return "text-rose-200 bg-rose-500/10 border-rose-400/30";
  return "text-slate-300 bg-slate-500/10 border-slate-400/20";
}

function riskClass(risk: AuditView["display_conclusion"]["risk_level"]) {
  if (risk === "high") return "border-rose-400/30 bg-rose-500/10 text-rose-100";
  if (risk === "medium") return "border-amber-400/30 bg-amber-500/10 text-amber-100";
  return "border-emerald-400/30 bg-emerald-500/10 text-emerald-100";
}

function FieldCard({ field }: { field: AuditViewField }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs text-slate-400">{field.field_label}</p>
        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sourceBadgeClass(field.source_type)}`}>
          {sourceLabel(field.source_type)}
        </span>
      </div>
      <p className="mt-2 break-words text-sm font-semibold text-slate-100">{field.display_value}</p>
      <p className="mt-2 break-words text-[11px] text-slate-500">来源：{field.source_label || "未识别"}</p>
      <p className="mt-1 text-[10px] text-slate-500">置信度：{Math.round((field.confidence || 0) * 100)}%</p>
    </div>
  );
}

export function AuditConclusionPanel({ view }: { view: AuditView }) {
  const conclusion = view.display_conclusion;
  return (
    <section className={`glass-card border p-6 ${riskClass(conclusion.risk_level)}`}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-400">审计辅助结论</p>
          <h2 className="mt-2 text-2xl font-bold text-white">{conclusion.main_result}</h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-300">{conclusion.summary}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-4 text-xs text-slate-300">
          <p className="font-semibold text-white">下一步</p>
          <ul className="mt-2 space-y-1">
            {conclusion.next_actions.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export function ProjectOverviewPanel({ view }: { view: AuditView }) {
  const fields = [
    "project_name",
    "repair_scope",
    "repair_reason",
    "budget_amount",
    "final_amount",
    "need_cost_review",
    "repair_nature",
    "applicant",
  ]
    .map((key) => view.project_overview[key])
    .filter(Boolean);
  return (
    <section className="glass-card p-6">
      <div className="mb-5 flex items-center gap-3">
        <FileSearch className="h-5 w-5 text-blue-300" />
        <div>
          <h3 className="text-base font-bold text-white">项目概览</h3>
          <p className="text-xs text-slate-500">仅展示有明确业务标签的高价值字段</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {fields.map((field) => (
          <FieldCard key={field.field_key || field.field_label} field={field} />
        ))}
      </div>
    </section>
  );
}

export function TimelineTracePanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card p-6">
      <div className="mb-6 flex items-center gap-3">
        <Clock3 className="h-5 w-5 text-indigo-300" />
        <div>
          <h3 className="text-base font-bold text-white">逻辑时序追踪</h3>
          <p className="text-xs text-slate-500">区分原始节点、系统推断节点和缺失节点</p>
        </div>
      </div>
      <div className="space-y-4">
        {view.timeline.map((item) => (
          <div key={`${item.label}-${item.source_label}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="text-lg font-bold text-slate-100">{item.display_value}</p>
                <p className="mt-1 text-sm font-semibold text-slate-200">{item.label}</p>
              </div>
              <span className={`w-fit rounded-full border px-2 py-0.5 text-[10px] font-semibold ${sourceBadgeClass(item.source_type)}`}>
                {sourceLabel(item.source_type)}
              </span>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-slate-400">{item.business_meaning}</p>
            <p className="mt-2 break-words text-[11px] text-slate-500">来源：{item.source_label}</p>
            {item.warning && <p className="mt-2 text-xs text-amber-300">{item.warning}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

export function MaterialScanPanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card p-6">
      <div className="mb-5 flex items-center gap-3">
        <ListChecks className="h-5 w-5 text-emerald-300" />
        <div>
          <h3 className="text-base font-bold text-white">材料扫描结果</h3>
          <p className="text-xs text-slate-500">缺失材料明确标注，不做事实伪造</p>
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border border-white/10">
        <table className="w-full text-xs">
          <thead className="bg-white/[0.04] text-slate-300">
            <tr>
              <th className="p-3 text-left font-semibold">审计要素</th>
              <th className="p-3 text-left font-semibold">材料状态</th>
              <th className="p-3 text-left font-semibold">识别来源</th>
              <th className="p-3 text-left font-semibold">影响结论</th>
              <th className="p-3 text-left font-semibold">补正建议</th>
            </tr>
          </thead>
          <tbody>
            {view.material_scan.map((item) => (
              <tr key={item.required_item} className="border-t border-white/5 align-top">
                <td className="p-3 font-semibold text-slate-100">{item.required_item}</td>
                <td className="p-3">
                  <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold ${materialStatusClass(item.status)}`}>
                    {item.status_label}
                  </span>
                </td>
                <td className="p-3 break-words text-slate-400">{item.source_label}</td>
                <td className="p-3 text-slate-300">{item.affects_audit ? "是" : "否"}</td>
                <td className="p-3 break-words text-slate-400">{item.remediation || "无"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function EvidenceExplorer({ view }: { view: AuditView }) {
  return (
    <section className="glass-card p-6">
      <div className="mb-5 flex items-center gap-3">
        <BrainCircuit className="h-5 w-5 text-violet-300" />
        <div>
          <h3 className="text-base font-bold text-white">证据区</h3>
          <p className="text-xs text-slate-500">原始材料、结构化抽取与 AI 理解分开呈现</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">
            <FileText className="h-4 w-4 text-blue-300" />
            原始材料
          </h4>
          <div className="space-y-3">
            {view.evidence_sections.raw_materials.map((item) => (
              <div key={item.file_name} className="border-b border-white/5 pb-2 text-xs">
                <p className="break-words font-semibold text-slate-200">{item.file_name}</p>
                <p className="mt-1 text-slate-500">{item.file_type} · {item.role}</p>
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
              <div key={`${item.field_label}-${item.source_label}`} className="border-b border-white/5 pb-2 text-xs">
                <p className="font-semibold text-slate-200">{item.field_label}：{item.value}</p>
                <p className="mt-1 break-words text-slate-500">来源：{item.source_label}</p>
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
              <div key={item.title} className="border-b border-white/5 pb-2 text-xs">
                <p className="font-semibold text-slate-200">{item.title}</p>
                <p className="mt-1 leading-relaxed text-slate-400">{item.content}</p>
                <p className="mt-1 text-slate-500">置信度：{Math.round(item.confidence * 100)}%</p>
              </div>
            ))}
          </div>
        </div>
      </div>
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
          <p className="text-xs text-slate-500">展示当前项目命中的法规依据和审计点</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {view.policy_matches.map((item) => (
          <article key={`${item.policy_title}-${item.article}-${item.related_audit}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <div className="flex flex-wrap gap-2">
              {item.tags.map((tag) => (
                <span key={tag} className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-2 py-0.5 text-[10px] text-indigo-200">
                  {tag}
                </span>
              ))}
            </div>
            <h4 className="mt-3 text-sm font-bold text-white">《{item.policy_title}》{item.article}</h4>
            <p className="mt-2 text-xs leading-relaxed text-slate-400">{item.matched_reason}</p>
            <p className="mt-2 text-[11px] text-slate-500">命中审计点：{item.related_audit}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function AuditCardsPanel({ view }: { view: AuditView }) {
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {view.audit_cards.map((card) => (
        <article key={card.audit_type} className="glass-card p-5">
          <div className="flex items-start justify-between gap-4">
            <h3 className="text-sm font-bold text-white">{card.audit_type}</h3>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-slate-300">
              {card.result_label}
            </span>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-slate-400">{card.summary}</p>
          {card.recommendation && <p className="mt-3 text-xs text-indigo-200">建议：{card.recommendation}</p>}
        </article>
      ))}
    </section>
  );
}

export function AuditorNotesPanel({ view }: { view: AuditView }) {
  return (
    <section className="glass-card p-6">
      <div className="mb-4 flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-amber-300" />
        <h3 className="text-base font-bold text-white">审计人员备注</h3>
      </div>
      <div className="grid grid-cols-1 gap-4 text-xs md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-semibold text-slate-200">系统状态：{view.auditor_notes.status}</p>
          <p className="mt-2 text-slate-500">字段冲突数：{view.auditor_notes.conflict_count}</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <p className="font-semibold text-slate-200">提醒</p>
          <ul className="mt-2 space-y-1 text-slate-500">
            {view.auditor_notes.warnings.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export function AuditWorkspace({ view }: { view: AuditView }) {
  return (
    <div className="space-y-6">
      <AuditConclusionPanel view={view} />
      <ProjectOverviewPanel view={view} />
      <TimelineTracePanel view={view} />
      <MaterialScanPanel view={view} />
      <EvidenceExplorer view={view} />
      <PolicyMatchPanel view={view} />
      <AuditCardsPanel view={view} />
      <AuditorNotesPanel view={view} />
    </div>
  );
}

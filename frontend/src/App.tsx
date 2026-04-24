import { ChangeEvent, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  AlertCircle,
  BookOpen,
  CircleDot,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  FileText,
  History,
  Info,
  LayoutDashboard,
  Loader2,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { analyzeFiles } from "./services/auditBackendService";
import { mapBackendAuditToViewModel } from "./services/auditViewMapper";
import { AuditViewModel } from "./types";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type Tab = "audit" | "history" | "policy";
type PolicyFileMeta = {
  id: string;
  name: string;
  type: string;
  status: "已上传";
  uploadedAt: string;
};

function riskColor(level: string) {
  if (level === "高") return "rose";
  if (level === "中") return "amber";
  return "emerald";
}

function matrixRiskClass(risk?: "none" | "medium" | "high") {
  if (risk === "high") return "text-rose-300";
  if (risk === "medium") return "text-amber-300";
  return "text-slate-300";
}

function matrixMaterialStatusClass(status: "已提取" | "缺项" | "未识别" | "需复核") {
  if (status === "已提取") return "text-emerald-300";
  if (status === "缺项") return "text-rose-300";
  if (status === "需复核") return "text-amber-300";
  return "text-slate-400";
}

function matrixMaterialDotClass(status: "已提取" | "缺项" | "未识别" | "需复核") {
  if (status === "已提取") return "bg-emerald-400";
  if (status === "缺项") return "bg-rose-400";
  if (status === "需复核") return "bg-amber-400";
  return "bg-slate-500";
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("audit");
  const [files, setFiles] = useState<File[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const [report, setReport] = useState<AuditViewModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(true);
  const [showAuditorView, setShowAuditorView] = useState(false);
  const [history, setHistory] = useState<AuditViewModel[]>(() => {
    const saved = localStorage.getItem("audit_history_v2");
    return saved ? (JSON.parse(saved) as AuditViewModel[]) : [];
  });
  const [policyFiles, setPolicyFiles] = useState<PolicyFileMeta[]>(() => {
    const saved = localStorage.getItem("policy_files_demo_v1");
    return saved ? (JSON.parse(saved) as PolicyFileMeta[]) : [];
  });

  const canStart = useMemo(() => files.length > 0 && !isAuditing, [files.length, isAuditing]);

  function saveToHistory(item: AuditViewModel) {
    const updated = [item, ...history].slice(0, 20);
    setHistory(updated);
    localStorage.setItem("audit_history_v2", JSON.stringify(updated));
  }

  function updatePolicyFiles(next: PolicyFileMeta[]) {
    setPolicyFiles(next);
    localStorage.setItem("policy_files_demo_v1", JSON.stringify(next));
  }

  function handleFileUpload(e: ChangeEvent<HTMLInputElement>) {
    if (!e.target.files) return;
    const picked = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...picked]);
  }

  function handlePolicyUpload(e: ChangeEvent<HTMLInputElement>) {
    if (!e.target.files) return;
    const added = Array.from(e.target.files).map((file) => ({
      id: `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: file.name,
      type: file.type || "application/octet-stream",
      status: "已上传" as const,
      uploadedAt: new Date().toLocaleString(),
    }));
    updatePolicyFiles([...
      added,
      ...policyFiles,
    ]);
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, idx) => idx !== index));
  }

  function removePolicyFile(id: string) {
    updatePolicyFiles(policyFiles.filter((item) => item.id !== id));
  }

  async function startAudit() {
    if (!canStart) return;
    setIsAuditing(true);
    setReport(null);
    setError(null);
    try {
      const result = await analyzeFiles(files);
      const mapped = mapBackendAuditToViewModel(result);
      setReport(mapped);
      saveToHistory(mapped);
    } catch (err) {
      setError(err instanceof Error ? err.message : "审计请求失败，请重试。");
    } finally {
      setIsAuditing(false);
    }
  }

  const cardResultClass = (level: string) => {
    const color = riskColor(level);
    if (color === "rose") return "bg-rose-500/10 border-rose-500/20 text-rose-300";
    if (color === "amber") return "bg-amber-500/10 border-amber-500/20 text-amber-300";
    return "bg-emerald-500/10 border-emerald-500/20 text-emerald-300";
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 selection:text-indigo-100 relative overflow-x-hidden">
      <div className="fixed top-[-20%] left-[-10%] w-[600px] h-[600px] bg-indigo-900/30 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-emerald-900/20 rounded-full blur-[100px] pointer-events-none" />

      <nav className="glass-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2 group cursor-pointer">
              <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center group-hover:rotate-6 transition-transform">
                <ClipboardCheck className="text-white w-5 h-5" />
              </div>
              <span className="font-bold text-xl tracking-tight text-white">
                专项维修资金智能审计
                <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded ml-2 uppercase tracking-widest hidden sm:inline">
                  本地 LLM + 规则引擎
                </span>
              </span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <div className="flex gap-6 text-sm font-medium">
                <button
                  onClick={() => setActiveTab("audit")}
                  className={cn(
                    "pb-1 transition-all",
                    activeTab === "audit" ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                  )}
                >
                  实时审计
                </button>
                <button
                  onClick={() => setActiveTab("history")}
                  className={cn(
                    "pb-1 transition-all",
                    activeTab === "history" ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                  )}
                >
                  历史报告
                </button>
                <button
                  onClick={() => setActiveTab("policy")}
                  className={cn(
                    "pb-1 transition-all",
                    activeTab === "policy" ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                  )}
                >
                  政策库
                </button>
              </div>
              <div className="w-10 h-10 rounded-full bg-white/10 border border-white/10" />
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-24 relative z-10">
        <AnimatePresence mode="wait">
          {activeTab === "audit" && (
            <motion.div
              key="audit-view"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-8"
            >
              <div className="lg:col-span-4 space-y-6">
                <div className="glass-card p-6 flex flex-col gap-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Upload className="w-4 h-4 text-indigo-400" />
                    文件上传
                  </h3>
                  <div className="relative group">
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.xlsx,.xls"
                      onChange={handleFileUpload}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    />
                    <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center group-hover:border-indigo-500 group-hover:bg-white/5 transition-all">
                      <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
                      <p className="text-xs text-slate-300">选择 Excel / PDF 文件（可多选）</p>
                    </div>
                  </div>

                  <div className="mt-2 space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    <AnimatePresence initial={false}>
                      {files.map((file, index) => (
                        <motion.div
                          key={`${file.name}-${index}`}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 10 }}
                          className="flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-xl group"
                        >
                          <div className="flex items-center gap-3 overflow-hidden">
                            <div className="text-emerald-400 shrink-0">✓</div>
                            <div className="overflow-hidden">
                              <p className="text-xs text-slate-200 truncate">{file.name}</p>
                              <p className="text-[10px] text-slate-500">
                                {file.name.toLowerCase().endsWith(".pdf") ? "PDF 附件" : "Excel 审计输入"}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => removeFile(index)}
                            className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-rose-500/20 text-rose-400 rounded-lg transition-all"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                    {files.length === 0 && (
                      <div className="text-center py-8 border border-dashed border-white/5 rounded-xl">
                        <p className="text-xs text-slate-500 italic">暂未导入审计材料</p>
                      </div>
                    )}
                  </div>

                  <button
                    disabled={!canStart}
                    onClick={startAudit}
                    className={cn(
                      "w-full mt-2 py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]",
                      canStart
                        ? "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
                        : "bg-white/5 text-slate-500 cursor-not-allowed border border-white/5"
                    )}
                  >
                    {isAuditing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        正在执行审计...
                      </>
                    ) : (
                      <>
                        <Search className="w-5 h-5" />
                        开始审计
                      </>
                    )}
                  </button>
                </div>

                <div className="glass-card p-6 space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">核心审计准则</h3>
                  <div className="space-y-4">
                    {[
                      { label: "资金用途", value: "共用部位/设施更新" },
                      { label: "表决门槛", value: "需满 2/3 业主同意" },
                      { label: "时序核对", value: "表决-公示-施工-验收" },
                      { label: "穿透审核", value: "字段证据 + 规则交叉核验" },
                    ].map((item) => (
                      <div key={item.label} className="flex justify-between border-b border-white/5 pb-2">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wide">{item.label}</span>
                        <span className="text-[11px] font-medium text-slate-300">{item.value}</span>
                      </div>
                    ))}
                  </div>
                  {report && (
                    <div className="pt-2 border-t border-white/10 text-xs">
                      <p className="text-slate-400">LLM 状态：{report.llmStatus}</p>
                      <p className="text-slate-500 mt-1">模型：{report.llmModel}</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="lg:col-span-8">
                <AnimatePresence mode="wait">
                  {!report && !isAuditing && !error && (
                    <motion.div
                      key="empty"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="glass-card h-full min-h-[500px] flex flex-col items-center justify-center text-slate-500 p-12 text-center"
                    >
                      <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-6 border border-white/5">
                        <LayoutDashboard className="w-10 h-10 opacity-20" />
                      </div>
                      <h3 className="text-xl font-bold text-slate-300 tracking-tight">审计引擎就绪</h3>
                      <p className="mt-3 max-w-sm text-sm text-slate-500 leading-relaxed">
                        上传 Excel 后将自动走字段归一化、本地 LLM 辅助分类与规则引擎判定。
                      </p>
                    </motion.div>
                  )}

                  {isAuditing && (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="glass-card p-12 h-full min-h-[500px] flex flex-col items-center justify-center gap-8 shadow-2xl"
                    >
                      <div className="relative">
                        <div className="w-32 h-32 border-[6px] border-white/5 border-t-indigo-500 rounded-full animate-[spin_1s_linear_infinite]" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center animate-pulse">
                            <Search className="w-8 h-8 text-indigo-400" />
                          </div>
                        </div>
                      </div>
                      <div className="text-center space-y-2">
                        <h3 className="text-2xl font-bold text-white tracking-tight">正在构建审计逻辑链路</h3>
                        <p className="text-slate-400 text-xs">字段解析中，请稍候...</p>
                      </div>
                    </motion.div>
                  )}

                  {error && (
                    <motion.div
                      key="error"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="glass-card p-12 text-center shadow-lg border-rose-500/20 bg-rose-500/5"
                    >
                      <div className="w-20 h-20 bg-rose-500/10 rounded-full flex items-center justify-center mx-auto mb-6 border border-rose-500/20">
                        <AlertCircle className="w-10 h-10 text-rose-500" />
                      </div>
                      <h3 className="text-xl font-bold text-rose-200">请求失败</h3>
                      <p className="text-rose-400/80 mt-3 max-w-xl mx-auto leading-relaxed text-sm">{error}</p>
                    </motion.div>
                  )}

                  {report && (
                    <motion.div key="report" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                      <div className="glass-card p-6">
                        <div className="flex justify-between items-center mb-6">
                          <h3 className="text-sm font-medium text-slate-400 tracking-wide uppercase">合规维度摘要</h3>
                          <div className={cn("text-xs px-3 py-1 rounded-full font-bold uppercase tracking-widest border", cardResultClass(report.riskLevel))}>
                            总体风险：{report.riskLevel}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {report.sections.map((item) => (
                            <div key={item.title} className={cn("p-3 rounded-xl text-center border transition-all", cardResultClass(item.riskLevel))}>
                              <p className="text-[9px] uppercase font-bold tracking-tighter opacity-80">{item.title}</p>
                              <p className="text-xs font-bold mt-1">{item.result}</p>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="glass-card p-8 relative overflow-hidden">
                        <div className="absolute top-[-50px] right-[-50px] p-20 bg-indigo-500/5 rounded-full blur-[60px]" />
                        <h2 className="text-3xl font-extrabold text-white tracking-tight leading-tight">{report.projectName}</h2>
                        <p className="text-xs text-slate-500 mt-2 font-bold tracking-widest uppercase">审计结论：{report.overallResult}</p>
                        <div className="bg-slate-900/40 p-6 rounded-2xl border border-white/5 relative mt-6">
                          <div className="text-slate-300 leading-relaxed text-sm font-medium markdown-body">
                            <ReactMarkdown>{report.summary}</ReactMarkdown>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {report.issues.map((issue, idx) => (
                          <motion.div
                            key={`${issue.title}-${idx}`}
                            whileHover={{ y: -4, boxShadow: "0 10px 30px -5px rgba(0,0,0,0.3)" }}
                            className="glass-card p-6 border-l-4 border-l-rose-500 transition-all hover:bg-white/10"
                          >
                            <h4 className="font-bold text-white mb-2 leading-snug">{issue.title}</h4>
                            <p className="text-xs text-slate-400 leading-relaxed mb-4">{issue.description}</p>
                            <div className="text-xs text-indigo-300 leading-relaxed">建议：{issue.suggestion}</div>
                            <div className="mt-3 text-xs text-slate-400">法规依据：{issue.basis.length ? issue.basis.join("；") : "无"}</div>
                          </motion.div>
                        ))}
                        {report.issues.length === 0 && (
                          <div className="glass-card p-6 text-sm text-emerald-300 border border-emerald-500/30">当前未发现需要展示的问题卡片。</div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {report && (
                <div className="lg:col-span-12 space-y-6">
                  <div className="glass-card overflow-hidden shadow-2xl relative">
                    <div className="p-8 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center border border-white/5">
                          <LayoutDashboard className="w-6 h-6 text-indigo-400" />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-white tracking-tight">关键审计证据提取矩阵</h3>
                          <p className="text-[9px] text-slate-500 uppercase tracking-widest font-bold mt-1">Cross-Reference Data Extraction</p>
                        </div>
                      </div>
                    </div>

                    <div className="p-8 grid grid-cols-1 md:grid-cols-12 gap-8 bg-black/20">
                      <div className="space-y-5 md:col-span-5 lg:col-span-3">
                        <h4 className="text-[11px] font-bold text-indigo-400 tracking-wide flex items-center gap-2">
                          <Clock3 className="w-4 h-4" />
                          逻辑时序追踪
                        </h4>
                        <div className="matrix-timeline">
                          {report.matrix.timeline.map((item, index) => (
                            <div key={`${item.title}-${index}`} className="matrix-timeline-item">
                              <div className={cn("matrix-timeline-dot", item.risk === "high" ? "matrix-timeline-dot-high" : item.risk === "medium" ? "matrix-timeline-dot-medium" : "matrix-timeline-dot-none")} />
                              <div className="matrix-timeline-content">
                                <p className={cn("text-2xl font-bold tracking-tight leading-none", matrixRiskClass(item.risk))}>{item.dateText}</p>
                                <p className="text-[11px] text-slate-100 mt-3 font-semibold">{item.title}</p>
                                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{item.description}</p>
                                <p className="text-[10px] text-slate-500 mt-2">来源：{item.source || "未识别"}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-5 md:col-span-7 lg:col-span-6">
                        <h4 className="text-[11px] font-bold text-indigo-400 tracking-wide flex items-center gap-2">
                          <FileText className="w-4 h-4" />
                          材料扫描结果
                        </h4>
                        <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
                          <div className="hidden lg:block">
                            <table className="w-full text-xs table-fixed matrix-evidence-table">
                              <colgroup>
                                <col className="w-[26%]" />
                                <col className="w-[54%]" />
                                <col className="w-[20%]" />
                              </colgroup>
                              <thead>
                                <tr className="bg-white/[0.04] text-slate-300">
                                  <th className="text-left p-3 font-semibold">审计要素</th>
                                  <th className="text-left p-3 font-semibold">来源材料/字段</th>
                                  <th className="text-left p-3 font-semibold">状态</th>
                                </tr>
                              </thead>
                              <tbody>
                                {report.matrix.materials.map((item) => (
                                  <tr key={item.label} className="border-t border-white/5 align-top">
                                    <td className="p-3 text-slate-100 font-semibold break-words">{item.label}</td>
                                    <td className="p-3 text-slate-400">
                                      <p className="break-words whitespace-pre-wrap" title={`来源：${item.source || "未识别"}`}>
                                        来源：{item.source || "未识别"}
                                      </p>
                                    </td>
                                    <td className="p-3">
                                      <span className={cn("inline-flex items-center gap-2 text-xs font-bold whitespace-nowrap", matrixMaterialStatusClass(item.status))}>
                                        <span className={cn("w-2.5 h-2.5 rounded-full", matrixMaterialDotClass(item.status))} />
                                        {item.status}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>

                          <div className="lg:hidden p-4 space-y-3">
                            {report.matrix.materials.map((item) => (
                              <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                                <div className="flex items-center justify-between gap-2">
                                  <p className="text-sm font-semibold text-slate-100">{item.label}</p>
                                  <span className={cn("inline-flex items-center gap-2 text-xs font-bold whitespace-nowrap", matrixMaterialStatusClass(item.status))}>
                                    <span className={cn("w-2.5 h-2.5 rounded-full", matrixMaterialDotClass(item.status))} />
                                    {item.status}
                                  </span>
                                </div>
                                <p className="text-xs text-slate-500 mt-1 break-words">来源：{item.source || "未识别"}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="space-y-5 md:col-span-12 lg:col-span-3">
                        <h4 className="text-[11px] font-bold text-indigo-400 tracking-wide">财务要素萃取</h4>
                        <div className="bg-indigo-500/10 border border-indigo-400/30 rounded-3xl p-6 max-w-full overflow-hidden">
                          <p className="text-xs font-semibold tracking-wide text-indigo-200">{report.matrix.finance.heroLabel}</p>
                          <p className="text-[clamp(1.35rem,3vw,2.2rem)] font-extrabold text-slate-100 mt-4 leading-none whitespace-nowrap overflow-hidden text-ellipsis">
                            {report.matrix.finance.compactAmount}
                          </p>
                          <p className="text-xs text-slate-400 mt-2">完整金额：{report.matrix.finance.fullAmount}</p>
                          <p className="text-[10px] text-slate-500 mt-1">来源：{report.matrix.finance.heroSource || "未识别"}</p>
                          <div className="h-px bg-white/15 my-6" />
                          <p className="text-xs text-slate-400">申报主体单位</p>
                          <p title={report.matrix.finance.applicantFullText} className="text-base font-bold text-slate-100 mt-3 leading-snug break-words">
                            {report.matrix.finance.applicantSummary}
                          </p>
                          <p className="text-[11px] text-slate-400 mt-2 break-words">完整名单：{report.matrix.finance.applicantFullText}</p>
                          <p className="text-[10px] text-slate-500 mt-1">来源：{report.matrix.finance.applicantSource || "未识别"}</p>
                        </div>
                        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5 space-y-3">
                          {report.matrix.finance.items.map((item) => (
                            <div key={item.label} className="flex items-start justify-between gap-4">
                              <p className="text-xs text-slate-400">{item.label}</p>
                              <div className="text-right">
                                <p className="text-sm text-slate-200">{item.value}</p>
                                <p className="text-[10px] text-slate-500 mt-1">来源：{item.source || "未识别"}</p>
                                {item.note && <p className="text-[10px] text-slate-500 mt-1">{item.note}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5">
                          <p className="text-sm font-semibold text-indigo-300 flex items-center gap-2">
                            <CircleDot className="w-4 h-4" />
                            AI 溯源
                          </p>
                          <p className="text-sm text-slate-400 mt-2 leading-relaxed">{report.matrix.finance.traceNote}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="glass-card overflow-hidden shadow-2xl relative">
                    <button
                      className="w-full p-5 border-b border-white/5 bg-white/[0.02] flex items-center justify-between"
                      onClick={() => setShowEvidence((v) => !v)}
                    >
                      <div className="flex items-center gap-3">
                        <Info className="w-5 h-5 text-indigo-400" />
                        <span className="text-sm font-bold text-white">证据区（字段来源 / parser vs LLM）</span>
                      </div>
                      {showEvidence ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                    </button>
                    {showEvidence && (
                      <div className="p-6 bg-black/20 grid grid-cols-1 md:grid-cols-2 gap-3">
                        {report.evidence.map((ev, idx) => (
                          <div key={`${ev.label}-${idx}`} className="bg-white/[0.03] p-3 rounded-xl border border-white/5 text-xs">
                            <div className="text-slate-300">{ev.label}</div>
                            <div className="text-white font-medium mt-1">{ev.value}</div>
                            <div className="text-slate-500 mt-1">来源：{ev.source}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="glass-card overflow-hidden">
                    <button
                      className="w-full p-5 border-b border-white/5 bg-white/[0.02] flex items-center justify-between"
                      onClick={() => setShowAuditorView((v) => !v)}
                    >
                      <div className="flex items-center gap-3">
                        <LayoutDashboard className="w-5 h-5 text-indigo-400" />
                        <span className="text-sm font-bold text-white">审计人员视图（折叠）</span>
                      </div>
                      {showAuditorView ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                    </button>
                    {showAuditorView && (
                      <div className="p-6 space-y-4 text-xs bg-black/20">
                        <div>
                          <h4 className="text-slate-300 mb-2 font-semibold">reason_code</h4>
                          <p className="text-slate-400">{report.auditorView.reasonCodes.join("，") || "无"}</p>
                        </div>
                        <div>
                          <h4 className="text-slate-300 mb-2 font-semibold">raw_fields</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {report.auditorView.rawFields.map((item, index) => (
                              <p key={`${item.label}-${index}`} className="text-slate-400">
                                {item.label}：{item.value}
                              </p>
                            ))}
                          </div>
                        </div>
                        <div>
                          <h4 className="text-slate-300 mb-2 font-semibold">conflicts</h4>
                          {report.auditorView.conflicts.length === 0 && <p className="text-slate-500">无</p>}
                          {report.auditorView.conflicts.map((item, index) => (
                            <p key={`${item.field}-${index}`} className="text-slate-400">
                              {item.field_label}：parser={item.parser_value} / llm={item.llm_value} / final={item.final_value}
                            </p>
                          ))}
                        </div>
                        <div>
                          <h4 className="text-slate-300 mb-2 font-semibold">llm_diagnostics</h4>
                          <pre className="text-slate-400 whitespace-pre-wrap break-words bg-white/[0.03] border border-white/10 rounded-xl p-3">
                            {JSON.stringify(report.auditorView.llmDiagnostics || {}, null, 2)}
                          </pre>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === "history" && (
            <motion.div key="history-view" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">
              <div className="glass-card p-8">
                <div className="flex items-center gap-4 mb-8">
                  <div className="w-12 h-12 bg-indigo-500/10 rounded-2xl flex items-center justify-center border border-indigo-500/20">
                    <History className="w-6 h-6 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white tracking-tight">审计历史报告</h2>
                    <p className="text-xs text-slate-500 font-bold tracking-widest uppercase mt-1">Audit Report History</p>
                  </div>
                </div>

                {history.length === 0 ? (
                  <div className="text-center py-20 border border-dashed border-white/10 rounded-3xl">
                    <p className="text-slate-500 italic">暂无历史审计记录</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {history.map((h, i) => (
                      <div
                        key={`${h.projectName}-${i}`}
                        className="glass-card p-6 hover:bg-white/10 transition-all cursor-pointer group border-white/5"
                        onClick={() => {
                          setReport(h);
                          setActiveTab("audit");
                        }}
                      >
                        <div className="flex justify-between items-start mb-4">
                          <div className={cn("px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-widest border", cardResultClass(h.riskLevel))}>风险{h.riskLevel}</div>
                        </div>
                        <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors">{h.projectName}</h3>
                        <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">{h.summary}</p>
                        <div className="mt-4 flex items-center gap-2 text-indigo-400 text-xs font-bold opacity-0 group-hover:opacity-100 transition-all">
                          查看详情 <ChevronRight className="w-4 h-4" />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === "policy" && (
            <motion.div key="policy-view" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">
              <div className="glass-card p-8">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-12 h-12 bg-indigo-500/10 rounded-2xl flex items-center justify-center border border-indigo-500/20">
                    <BookOpen className="w-6 h-6 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white tracking-tight">维修资金政策库</h2>
                    <p className="text-xs text-slate-500 font-bold tracking-widest uppercase mt-1">Policy Library (Demo)</p>
                  </div>
                </div>

                <div className="text-sm text-slate-400 leading-relaxed space-y-1 mb-6">
                  <p>当前政策库为演示版：支持本地开发上传并保存文件列表（localStorage）。</p>
                  <p>现阶段审计依据主要来自规则引擎 reason_code 与内置法规绑定。</p>
                  <p>后续可扩展为 RAG 检索、新法规上传与法规条款匹配。</p>
                </div>

                <label className="block border-2 border-dashed border-white/15 rounded-xl p-6 text-center cursor-pointer hover:border-indigo-500 transition-all">
                  <input type="file" multiple accept=".pdf,.docx,.txt,.md" className="hidden" onChange={handlePolicyUpload} />
                  <Upload className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
                  <p className="text-sm text-slate-300">上传政策文件（.pdf/.docx/.txt/.md）</p>
                </label>

                <div className="mt-6 space-y-2">
                  {policyFiles.length === 0 && <p className="text-sm text-slate-500">暂无上传文件。</p>}
                  {policyFiles.map((item) => (
                    <div key={item.id} className="bg-white/[0.03] border border-white/10 rounded-xl p-3 flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-sm text-slate-200 truncate">{item.name}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          类型：{item.type} | 状态：{item.status} | 时间：{item.uploadedAt}
                        </p>
                      </div>
                      <button onClick={() => removePolicyFile(item.id)} className="p-2 text-rose-300 hover:bg-rose-500/10 rounded">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 h-10 px-8 bg-slate-950/85 flex items-center justify-between text-[10px] text-slate-400 border-t border-white/10 backdrop-blur-sm z-50">
        <div className="flex gap-6 font-bold uppercase tracking-widest">
          <span className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
            节点状态: 正常
          </span>
          <span>LLM Engine: Local Studio</span>
        </div>
        <div className="flex gap-6 font-bold uppercase tracking-widest">
          <span>规则审计已启用</span>
          <span>最后同步: {new Date().toLocaleTimeString()}</span>
        </div>
      </footer>
    </div>
  );
}

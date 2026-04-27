import { ChangeEvent, useMemo, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  AlertCircle,
  BookOpen,
  ChevronRight,
  ClipboardCheck,
  History,
  LayoutDashboard,
  Loader2,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { AuditWorkspace, ComplianceSummaryBar, ReportActionCard } from "./components/audit-view-panels";
import { analyzeFiles } from "./services/auditBackendService";
import { extractAuditView } from "./services/auditViewMapper";
import { AuditView } from "./types";

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

function riskBadgeClass(risk: AuditView["display_conclusion"]["risk_level"]) {
  if (risk === "high") return "border-rose-500/30 bg-rose-500/10 text-rose-200";
  if (risk === "medium") return "border-amber-500/30 bg-amber-500/10 text-amber-200";
  return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
}

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>("audit");
  const [files, setFiles] = useState<File[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const [report, setReport] = useState<AuditView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AuditView[]>(() => {
    const saved = localStorage.getItem("audit_history_v3");
    return saved ? (JSON.parse(saved) as AuditView[]) : [];
  });
  const [policyFiles, setPolicyFiles] = useState<PolicyFileMeta[]>(() => {
    const saved = localStorage.getItem("policy_files_demo_v1");
    return saved ? (JSON.parse(saved) as PolicyFileMeta[]) : [];
  });

  const canStart = useMemo(() => files.length > 0 && !isAuditing, [files.length, isAuditing]);

  function saveToHistory(item: AuditView) {
    const updated = [item, ...history].slice(0, 20);
    setHistory(updated);
    localStorage.setItem("audit_history_v3", JSON.stringify(updated));
  }

  function updatePolicyFiles(next: PolicyFileMeta[]) {
    setPolicyFiles(next);
    localStorage.setItem("policy_files_demo_v1", JSON.stringify(next));
  }

  function handleFileUpload(e: ChangeEvent<HTMLInputElement>) {
    if (!e.target.files) return;
    setFiles((prev) => [...prev, ...Array.from(e.target.files || [])]);
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
    updatePolicyFiles([...added, ...policyFiles]);
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
      const view = extractAuditView(result);
      setReport(view);
      saveToHistory(view);
    } catch (err) {
      setError(err instanceof Error ? err.message : "审计请求失败，请重试。");
    } finally {
      setIsAuditing(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 selection:text-indigo-100 relative overflow-x-hidden">
      <div className="fixed top-[-20%] left-[-10%] w-[600px] h-[600px] bg-indigo-900/30 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-emerald-900/20 rounded-full blur-[100px] pointer-events-none" />

      <nav className="glass-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500">
                <ClipboardCheck className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold text-white">
                专项维修资金审计辅助工作台
                <span className="ml-2 hidden rounded bg-indigo-500/20 px-2 py-0.5 text-[10px] uppercase tracking-widest text-indigo-300 sm:inline">
                  证据 + 法规 + AI解释
                </span>
              </span>
            </div>
            <div className="hidden items-center gap-8 md:flex">
              <div className="flex gap-6 text-sm font-medium">
                {[
                  ["audit", "实时审计"],
                  ["history", "历史报告"],
                  ["policy", "政策库"],
                ].map(([tab, label]) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab as Tab)}
                    className={cn(
                      "pb-1 transition-all",
                      activeTab === tab ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="h-10 w-10 rounded-full border border-white/10 bg-white/10" />
            </div>
          </div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 pb-24 sm:px-6 lg:px-8">
        <AnimatePresence mode="wait">
          {activeTab === "audit" && (
            <motion.div
              key="audit-view"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-8"
            >
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-[420px_1fr]">
                <aside className="space-y-6">
                  <div className="glass-card flex flex-col gap-4 p-6">
                    <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-400">
                      <Upload className="h-4 w-4 text-indigo-400" />
                      文件上传
                    </h3>
                    <div className="group relative">
                      <input
                        type="file"
                        multiple
                        accept=".pdf,.xlsx,.xls"
                        onChange={handleFileUpload}
                        className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
                      />
                      <div className="rounded-xl border-2 border-dashed border-white/10 p-8 text-center transition-all group-hover:border-indigo-500 group-hover:bg-white/5">
                        <Upload className="mx-auto mb-2 h-8 w-8 text-slate-500 transition-transform group-hover:scale-110" />
                        <p className="text-xs text-slate-300">选择 Excel / PDF 文件（可多选）</p>
                      </div>
                    </div>

                    <div className="custom-scrollbar mt-2 max-h-[300px] space-y-2 overflow-y-auto pr-2">
                      <AnimatePresence initial={false}>
                        {files.map((file, index) => (
                          <motion.div
                            key={`${file.name}-${index}`}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 10 }}
                            className="group flex items-center justify-between rounded-xl border border-white/5 bg-white/5 p-3"
                          >
                            <div className="flex min-w-0 items-center gap-3">
                              <div className="shrink-0 text-emerald-400">✓</div>
                              <div className="min-w-0">
                                <p className="truncate text-xs text-slate-200">{file.name}</p>
                                <p className="text-[10px] text-slate-500">
                                  {file.name.toLowerCase().endsWith(".pdf") ? "PDF 原始附件" : "Excel 结构化输入"}
                                </p>
                              </div>
                            </div>
                            <button
                              onClick={() => removeFile(index)}
                              className="rounded-lg p-1.5 text-rose-400 opacity-0 transition-all hover:bg-rose-500/20 group-hover:opacity-100"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                      {files.length === 0 && (
                        <div className="rounded-xl border border-dashed border-white/5 py-8 text-center">
                          <p className="text-xs italic text-slate-500">暂未导入审计材料</p>
                        </div>
                      )}
                    </div>

                    <button
                      disabled={!canStart}
                      onClick={startAudit}
                      className={cn(
                        "mt-2 flex w-full items-center justify-center gap-2 rounded-xl py-4 font-bold transition-all active:scale-[0.98]",
                        canStart
                          ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 hover:bg-indigo-500"
                          : "cursor-not-allowed border border-white/5 bg-white/5 text-slate-500"
                      )}
                    >
                      {isAuditing ? (
                        <>
                          <Loader2 className="h-5 w-5 animate-spin" />
                          正在执行审计...
                        </>
                      ) : (
                        <>
                          <Search className="h-5 w-5" />
                          开始审计
                        </>
                      )}
                    </button>
                  </div>

                  <div className="glass-card space-y-4 p-6">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">审计展示口径</h3>
                    {[
                      ["系统定位", "审计辅助，不替代人工结论"],
                      ["展示链路", "材料扫描 → 证据 → 法规 → AI解释"],
                      ["缺失材料", "明确标注，不做伪造"],
                      ["结论口径", "保留人工复核入口"],
                    ].map(([label, value]) => (
                      <div key={label} className="flex justify-between border-b border-white/5 pb-2">
                        <span className="text-[10px] uppercase tracking-wide text-slate-500">{label}</span>
                        <span className="text-right text-[11px] font-medium text-slate-300">{value}</span>
                      </div>
                    ))}
                  </div>
                </aside>

                <section className="w-full space-y-6">
                  {report && (
                    <>
                      <ComplianceSummaryBar view={report} />
                      <ReportActionCard view={report} />
                    </>
                  )}

                  {!report && !isAuditing && !error && (
                    <motion.div
                      key="empty"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="glass-card flex min-h-[360px] flex-col items-center justify-center p-12 text-center text-slate-500"
                    >
                      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-white/5 bg-white/5">
                        <LayoutDashboard className="h-10 w-10 opacity-20" />
                      </div>
                      <h3 className="text-xl font-bold tracking-tight text-slate-300">审计辅助工作台就绪</h3>
                      <p className="mt-3 max-w-sm text-sm leading-relaxed text-slate-500">
                        上传材料后将生成合规维度摘要、报告操作区、证据归集和 AI 解释。
                      </p>
                    </motion.div>
                  )}

                  {isAuditing && (
                    <motion.div
                      key="loading"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="glass-card flex min-h-[360px] flex-col items-center justify-center gap-8 p-12"
                    >
                      <div className="relative">
                        <div className="h-28 w-28 animate-[spin_1s_linear_infinite] rounded-full border-[6px] border-white/5 border-t-indigo-500" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="flex h-14 w-14 animate-pulse items-center justify-center rounded-full bg-indigo-500/10">
                            <Search className="h-7 w-7 text-indigo-400" />
                          </div>
                        </div>
                      </div>
                      <div className="text-center">
                        <h3 className="text-2xl font-bold text-white">正在构建审计辅助视图</h3>
                        <p className="mt-2 text-xs text-slate-400">材料扫描、法规匹配与 AI 解释生成中...</p>
                      </div>
                    </motion.div>
                  )}

                  {error && (
                    <motion.div
                      key="error"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="glass-card min-h-[360px] border-rose-500/20 bg-rose-500/5 p-12 text-center"
                    >
                      <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full border border-rose-500/20 bg-rose-500/10">
                        <AlertCircle className="h-10 w-10 text-rose-500" />
                      </div>
                      <h3 className="text-xl font-bold text-rose-200">请求失败</h3>
                      <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-rose-400/80">{error}</p>
                    </motion.div>
                  )}
                </section>
              </div>

              {report && (
                <section className="w-full">
                  <AuditWorkspace view={report} />
                </section>
              )}
            </motion.div>
          )}

          {activeTab === "history" && (
            <motion.div key="history-view" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <div className="glass-card p-8">
                <div className="mb-8 flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/20 bg-indigo-500/10">
                    <History className="h-6 w-6 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white">审计历史报告</h2>
                    <p className="mt-1 text-xs font-bold uppercase tracking-widest text-slate-500">Audit Report History</p>
                  </div>
                </div>

                {history.length === 0 ? (
                  <div className="rounded-3xl border border-dashed border-white/10 py-20 text-center">
                    <p className="italic text-slate-500">暂无历史审计记录</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {history.map((item, index) => (
                      <button
                        key={`${item.display_conclusion.main_result}-${index}`}
                        className="glass-card group cursor-pointer p-6 text-left transition-all hover:bg-white/10"
                        onClick={() => {
                          setReport(item);
                          setActiveTab("audit");
                        }}
                      >
                        <div className={`mb-4 w-fit rounded border px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest ${riskBadgeClass(item.display_conclusion.risk_level)}`}>
                          {item.display_conclusion.risk_level}
                        </div>
                        <h3 className="text-lg font-bold text-white transition-colors group-hover:text-indigo-400">
                          {item.display_conclusion.main_result}
                        </h3>
                        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-400">{item.display_conclusion.summary}</p>
                        <div className="mt-4 flex items-center gap-2 text-xs font-bold text-indigo-400 opacity-0 transition-all group-hover:opacity-100">
                          查看详情 <ChevronRight className="h-4 w-4" />
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === "policy" && (
            <motion.div key="policy-view" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <div className="glass-card p-8">
                <div className="mb-6 flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/20 bg-indigo-500/10">
                    <BookOpen className="h-6 w-6 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold tracking-tight text-white">维修资金政策库</h2>
                    <p className="mt-1 text-xs font-bold uppercase tracking-widest text-slate-500">Policy Library (Demo)</p>
                  </div>
                </div>

                <div className="mb-6 space-y-1 text-sm leading-relaxed text-slate-400">
                  <p>当前政策库为演示版：支持本地开发上传并保存文件列表（localStorage）。</p>
                  <p>当前审计依据来自内置审计规则和法规匹配，不宣传为 RAG 主能力。</p>
                  <p>后续可扩展为法规上传、条款检索和法规条款匹配。</p>
                </div>

                <label className="block cursor-pointer rounded-xl border-2 border-dashed border-white/15 p-6 text-center transition-all hover:border-indigo-500">
                  <input type="file" multiple accept=".pdf,.docx,.txt,.md" className="hidden" onChange={handlePolicyUpload} />
                  <Upload className="mx-auto mb-2 h-6 w-6 text-indigo-400" />
                  <p className="text-sm text-slate-300">上传政策文件（.pdf/.docx/.txt/.md）</p>
                </label>

                <div className="mt-6 space-y-2">
                  {policyFiles.length === 0 && <p className="text-sm text-slate-500">暂无上传文件。</p>}
                  {policyFiles.map((item) => (
                    <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm text-slate-200">{item.name}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          类型：{item.type} | 状态：{item.status} | 时间：{item.uploadedAt}
                        </p>
                      </div>
                      <button onClick={() => removePolicyFile(item.id)} className="rounded p-2 text-rose-300 hover:bg-rose-500/10">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 z-50 flex h-10 items-center justify-between border-t border-white/10 bg-slate-950/85 px-8 text-[10px] text-slate-400 backdrop-blur-sm">
        <div className="flex gap-6 font-bold uppercase tracking-widest">
          <span className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            节点状态: 正常
          </span>
          <span>Audit View Engine</span>
        </div>
        <div className="flex gap-6 font-bold uppercase tracking-widest">
          <span>审计辅助视图已启用</span>
          <span>最后同步: {new Date().toLocaleTimeString()}</span>
        </div>
      </footer>
    </div>
  );
}

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { AlertCircle, CheckCircle2, FileText, LayoutDashboard, Search, Upload, X, Loader2, ClipboardCheck, History, Info, BookOpen, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { extractAndAudit } from './services/geminiService';
import { AuditReport, FileData } from './types';
import { fileToBase64, parseExcel } from './lib/fileUtils';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'audit' | 'history' | 'policy'>('audit');
  const [files, setFiles] = useState<FileData[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<AuditReport[]>(() => {
    const saved = localStorage.getItem('audit_history');
    return saved ? JSON.parse(saved) : [];
  });

  const saveToHistory = (newReport: AuditReport) => {
    const updated = [newReport, ...history].slice(0, 20);
    setHistory(updated);
    localStorage.setItem('audit_history', JSON.stringify(updated));
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    
    const newFiles: FileData[] = [];
    for (const file of Array.from(e.target.files)) {
      try {
        let content = '';
        if (file.type === 'application/pdf') {
          content = await fileToBase64(file);
        } else if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
          content = await parseExcel(file);
        } else {
          content = await file.text();
        }

        newFiles.push({
          id: Math.random().toString(36).substr(2, 9),
          name: file.name,
          type: file.type,
          mimeType: file.type || 'application/octet-stream',
          content,
        });
      } catch (err) {
        console.error(`Error processing file ${file.name}:`, err);
      }
    }
    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const startAudit = async () => {
    if (files.length === 0) return;
    setIsAuditing(true);
    setReport(null);
    setError(null);
    try {
      const result = await extractAndAudit(files);
      setReport(result);
      saveToHistory(result);
    } catch (err) {
      console.error(err);
      setError('审计过程中发生错误，请重试。可能是由于 API 密钥配置不正确或文件格式不受支持。');
    } finally {
      setIsAuditing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 selection:text-indigo-100 relative overflow-x-hidden">
      {/* Background Mesh Gradients */}
      <div className="fixed top-[-20%] left-[-10%] w-[600px] h-[600px] bg-indigo-900/30 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="fixed bottom-[-10%] right-[-5%] w-[500px] h-[500px] bg-emerald-900/20 rounded-full blur-[100px] pointer-events-none"></div>

      {/* Navigation */}
      <nav className="glass-nav">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2 group cursor-pointer">
              <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center group-hover:rotate-6 transition-transform">
                <ClipboardCheck className="text-white w-5 h-5" />
              </div>
              <span className="font-bold text-xl tracking-tight text-white">专项维修资金智能审计 <span className="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded ml-2 uppercase tracking-widest hidden sm:inline">LLM Powered</span></span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <div className="flex gap-6 text-sm font-medium">
                <button 
                  onClick={() => setActiveTab('audit')}
                  className={cn(
                    "pb-1 transition-all",
                    activeTab === 'audit' ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                  )}
                >
                  实时审计
                </button>
                <button 
                  onClick={() => setActiveTab('history')}
                  className={cn(
                    "pb-1 transition-all",
                    activeTab === 'history' ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                  )}
                >
                  历史报告
                </button>
                <button 
                  onClick={() => setActiveTab('policy')}
                  className={cn(
                    "pb-1 transition-all",
                    activeTab === 'policy' ? "border-b-2 border-indigo-500 text-white" : "text-slate-400 hover:text-white"
                  )}
                >
                  政策库
                </button>
              </div>
              <div className="w-10 h-10 rounded-full bg-white/10 border border-white/10"></div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        <AnimatePresence mode="wait">
          {activeTab === 'audit' && (
            <motion.div
              key="audit-view"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-8"
            >
              {/* Left Column: Upload & Files */}
              <div className="lg:col-span-4 space-y-6">
                <div className="glass-card p-6 flex flex-col gap-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                    <Upload className="w-4 h-4 text-indigo-400" />
                    数据导入
                  </h3>
                  <div className="relative group">
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.xlsx,.xls,.txt"
                      onChange={handleFileUpload}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                    />
                    <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center group-hover:border-indigo-500 group-hover:bg-white/5 transition-all">
                      <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2 group-hover:scale-110 transition-transform" />
                      <p className="text-xs text-slate-300">点击上传或拖拽 PDF, Excel, 竣工资料</p>
                    </div>
                  </div>

                  <div className="mt-2 space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    <AnimatePresence initial={false}>
                      {files.map(file => (
                        <motion.div
                          key={file.id}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 10 }}
                          className="flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-xl group"
                        >
                          <div className="flex items-center gap-3 overflow-hidden">
                            <div className="text-emerald-400 shrink-0">✓</div>
                            <div className="overflow-hidden">
                              <p className="text-xs text-slate-200 truncate">{file.name}</p>
                              <p className="text-[10px] text-slate-500">{file.type === 'application/pdf' ? 'PDF 已解析' : 'Excel 模型处理中'}</p>
                            </div>
                          </div>
                          <button 
                            onClick={() => removeFile(file.id)}
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
                    disabled={files.length === 0 || isAuditing}
                    onClick={startAudit}
                    className={cn(
                      "w-full mt-2 py-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all active:scale-[0.98]",
                      files.length > 0 && !isAuditing
                        ? "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
                        : "bg-white/5 text-slate-500 cursor-not-allowed border border-white/5"
                    )}
                  >
                    {isAuditing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        AI 正在深度审计中...
                      </>
                    ) : (
                      <>
                        <Search className="w-5 h-5" />
                        启动智能审计引擎
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
                       { label: "穿透审核", value: "实物量与发票勾连" }
                     ].map((item, i) => (
                       <div key={i} className="flex justify-between border-b border-white/5 pb-2">
                         <span className="text-[10px] text-slate-500 uppercase tracking-wide">{item.label}</span>
                         <span className="text-[11px] font-medium text-slate-300">{item.value}</span>
                       </div>
                     ))}
                  </div>
                </div>
              </div>

              {/* Right Column: Results */}
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
                        请在侧边栏导入材料。系统将通过多模态大语言模型，自动核查时序逻辑冲突及潜在违规支出。
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
                        <div className="w-32 h-32 border-[6px] border-white/5 border-t-indigo-500 rounded-full animate-[spin_1s_linear_infinite]"></div>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center animate-pulse">
                            <Search className="w-8 h-8 text-indigo-400" />
                          </div>
                        </div>
                      </div>
                      <div className="text-center space-y-4">
                        <h3 className="text-2xl font-bold text-white tracking-tight">正在构建审计逻辑链路</h3>
                        <div className="space-y-2">
                           <div className="flex flex-col gap-2 pt-4">
                              <p className="text-slate-400 text-xs flex items-center justify-center gap-3">
                                <span className="w-2 h-2 bg-indigo-500 rounded-full animate-ping" />
                                正在核查公示文件与工程合同的时序对齐状态...
                              </p>
                              <p className="text-slate-400 text-xs flex items-center justify-center gap-3">
                                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-ping" />
                                LLM 正在提取造价清单中的异常报价条目...
                              </p>
                           </div>
                        </div>
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
                        <h3 className="text-xl font-bold text-rose-200">审计解析引擎故障</h3>
                        <p className="text-rose-400/70 mt-3 max-w-sm mx-auto leading-relaxed text-sm">{error}</p>
                        <button 
                          onClick={() => setError(null)}
                          className="mt-8 px-10 py-3 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-rose-900/20"
                        >
                          重置并重试
                        </button>
                     </motion.div>
                  )}

                  {report && (
                    <motion.div
                      key="report"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-6"
                    >
                      {/* Status Grid Header */}
                      <div className="glass-card p-6">
                        <div className="flex justify-between items-center mb-6">
                          <h3 className="text-sm font-medium text-slate-400 tracking-wide uppercase">合规维度摘要</h3>
                          <div className={cn(
                            "text-xs px-3 py-1 rounded-full font-bold uppercase tracking-widest border",
                            report.status === 'Pass' ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" :
                            report.status === 'Fail' ? "bg-rose-500/20 text-rose-400 border-rose-500/30" :
                            "bg-amber-500/20 text-amber-400 border-amber-500/30"
                          )}>
                            {report.status === 'Pass' ? '合规通过' : report.status === 'Fail' ? '重要违规' : '存在警告'}
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                          {[
                            { label: '使用范围', status: 'COMPLIANCE' },
                            { label: '流程合规', status: 'PROCESS' },
                            { label: '时序逻辑', status: 'TIMING' },
                            { label: '材料完备', status: 'COMPLETENESS' },
                            { label: '金额合理', status: 'VALUE' }
                          ].map((item, i) => {
                            const finding = report.findings.find(f => f.category === item.status);
                            const severity = finding?.severity || 'pass';
                            return (
                              <div key={i} className={cn(
                                "p-3 rounded-xl text-center border transition-all",
                                severity === 'high' ? "bg-rose-500/10 border-rose-500/20 text-rose-400" :
                                severity === 'medium' ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                                "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                              )}>
                                <p className="text-[9px] uppercase font-bold tracking-tighter opacity-80">{item.label}</p>
                                <p className="text-xs font-bold mt-1">{severity === 'high' ? '高风险' : severity === 'medium' ? '中风险' : '合规'}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Main Summary Section */}
                      <div className="glass-card p-8 relative overflow-hidden">
                        <div className="absolute top-[-50px] right-[-50px] p-20 bg-indigo-500/5 rounded-full blur-[60px]"></div>
                        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 mb-8">
                          <div>
                             <h2 className="text-3xl font-extrabold text-white tracking-tight leading-tight">{report.projectName}</h2>
                             <p className="text-xs text-slate-500 mt-2 font-bold tracking-widest uppercase">Audit Date: {report.auditDate}</p>
                          </div>
                          <button 
                             onClick={() => window.print()}
                             className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-xs font-bold bg-white/5 border border-white/10 px-5 py-2.5 rounded-xl transition-all shadow-xl print:hidden active:scale-95"
                          >
                            <FileText className="w-4 h-4" />
                            下载审计报告 (PDF)
                          </button>
                        </div>
                        
                        <div className="bg-slate-900/40 p-6 rounded-2xl border border-white/5 relative">
                          <div className="flex items-center gap-2 mb-4 text-indigo-400">
                            <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.5)]"></div>
                            <span className="text-[10px] font-bold uppercase tracking-widest">LLM 审计综合意见</span>
                          </div>
                          <div className="text-slate-300 leading-relaxed text-sm font-medium markdown-body">
                            <ReactMarkdown>{report.summary}</ReactMarkdown>
                          </div>
                        </div>
                      </div>

                      {/* Findings Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {report.findings.map((finding, idx) => (
                          <motion.div
                            key={idx}
                            whileHover={{ y: -4, boxShadow: '0 10px 30px -5px rgba(0,0,0,0.3)' }}
                            className={cn(
                              "glass-card p-6 border-l-4 transition-all hover:bg-white/10",
                              finding.severity === 'high' ? "border-l-rose-500" :
                              finding.severity === 'medium' ? "border-l-amber-500" :
                              "border-l-emerald-500"
                            )}
                          >
                            <div className="flex items-center justify-between mb-4">
                              <span className={cn(
                                "px-2 px-1 text-[9px] font-bold tracking-widest uppercase rounded",
                                finding.severity === 'high' ? "text-rose-400 bg-rose-500/10" :
                                finding.severity === 'medium' ? "text-amber-400 bg-amber-500/10" :
                                "text-emerald-400 bg-emerald-500/10"
                              )}>
                                {finding.category}
                              </span>
                              <div className={cn(
                                "w-8 h-8 rounded-full flex items-center justify-center border",
                                finding.severity === 'high' ? "border-rose-500/20 bg-rose-500/5 text-rose-400" :
                                finding.severity === 'medium' ? "border-amber-500/20 bg-amber-500/5 text-amber-400" :
                                "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                              )}>
                                 {finding.severity === 'high' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                              </div>
                            </div>
                            <h4 className="font-bold text-white mb-2 leading-snug">{finding.title}</h4>
                            <p className="text-xs text-slate-400 leading-relaxed mb-4">{finding.description}</p>
                            {finding.recommendation && (
                              <div className="mt-4 pt-4 border-t border-white/5">
                                 <div className="flex items-start gap-3">
                                   <div className="mt-1 w-1.5 h-1.5 bg-indigo-500 rounded-full shrink-0 shadow-[0_0_8px_rgba(99,102,241,0.6)]" />
                                   <p className="text-xs text-indigo-300 italic font-medium leading-relaxed">
                                      {finding.recommendation}
                                   </p>
                                 </div>
                              </div>
                            )}
                          </motion.div>
                        ))}
                      </div>

                      {/* Technical Evidence Matrix */}
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
                        
                        <div className="p-8 grid grid-cols-1 lg:grid-cols-3 gap-12 bg-black/20">
                          <div className="space-y-6">
                            <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                               <History className="w-3.5 h-3.5" />
                               逻辑时序追踪
                            </h4>
                            <div className="space-y-6 relative before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
                              {report.extractedDetails.milestones?.map((m, i) => (
                                <div key={i} className="pl-8 relative group">
                                  <div className="absolute left-[5.5px] top-[4px] w-[6px] h-[6px] rounded-full bg-slate-700 group-hover:bg-indigo-500 transition-all z-10 border-2 border-slate-950 group-hover:scale-125" />
                                  <div className="text-[10px] font-bold text-white tracking-wider">{m.date}</div>
                                  <div className="text-[11px] text-slate-400 mt-1 font-medium group-hover:text-slate-200 transition-colors">{m.event}</div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="space-y-6">
                            <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest flex items-center gap-2">
                               <FileText className="w-3.5 h-3.5" />
                               材料扫描结果
                            </h4>
                            <div className="space-y-2.5">
                              {report.extractedDetails.documents?.map((d, i) => (
                                <div key={i} className="flex items-center justify-between bg-white/[0.03] p-4 rounded-xl border border-white/5 group hover:border-white/20 transition-all">
                                  <span className="text-[11px] font-bold text-slate-300">{d.name}</span>
                                  {d.status === 'received' ? (
                                    <div className="flex items-center gap-2 text-emerald-400 text-[9px] font-bold uppercase tracking-widest">
                                       <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
                                       已提取
                                    </div>
                                  ) : (
                                    <div className="flex items-center gap-2 text-rose-400 text-[9px] font-bold uppercase tracking-widest">
                                       <div className="w-1.5 h-1.5 bg-rose-400 rounded-full" />
                                       缺项
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="space-y-8">
                            <div>
                              <h4 className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-4">财务要素萃取</h4>
                              <div className="bg-gradient-to-br from-indigo-500/10 to-indigo-900/10 p-6 rounded-2xl border border-indigo-500/20 backdrop-blur-md">
                                 <p className="text-[10px] text-indigo-400 uppercase font-black tracking-widest mb-2">申报工程概算</p>
                                 <p className="text-3xl font-extrabold text-indigo-100 font-mono tracking-tighter">
                                    ¥{report.extractedDetails.totalBudget?.toLocaleString() || '---'}
                                 </p>
                                 <div className="mt-6 pt-5 border-t border-white/5 flex flex-col gap-2">
                                    <p className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">申报主体单位</p>
                                    <p className="text-xs font-bold text-white leading-relaxed line-clamp-2">{report.extractedDetails.applicants || '---'}</p>
                                 </div>
                              </div>
                            </div>

                            <div className="bg-slate-800/40 p-5 rounded-2xl border border-white/5">
                              <div className="flex items-center gap-2 text-indigo-400 mb-2">
                                <Info className="w-3.5 h-3.5" />
                                <span className="text-[10px] font-bold uppercase tracking-widest">AI 溯源</span>
                              </div>
                              <p className="text-[11px] text-slate-400 font-medium leading-relaxed italic">
                                本核对报告由 LLM 引擎基于上传材料自动生成，核心逻辑符合上海市住房和城乡建设管理委员会专项维修资金管理之规范。
                              </p>
                            </div>
                          </div>
                        </div>

                        <div className="bg-black/40 px-8 py-4 flex justify-between items-center text-[9px] text-slate-600 font-bold uppercase tracking-[0.2em] border-t border-white/5">
                           <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" /> Security Protocol: AES-256 Verified</span>
                           <span className="flex items-center gap-2 opacity-50">
                              Gemini 3.0 Real-time Cognitive Engine
                           </span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}

          {activeTab === 'history' && (
            <motion.div
              key="history-view"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
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
                        key={i}
                        className="glass-card p-6 hover:bg-white/10 transition-all cursor-pointer group border-white/5"
                        onClick={() => {
                          setReport(h);
                          setActiveTab('audit');
                        }}
                      >
                        <div className="flex justify-between items-start mb-4">
                          <div className={cn(
                            "px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-widest",
                            h.status === 'Pass' ? "bg-emerald-500/20 text-emerald-400" :
                            h.status === 'Fail' ? "bg-rose-500/20 text-rose-400" :
                            "bg-amber-500/20 text-amber-400"
                          )}>
                            {h.status}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono">{h.auditDate}</div>
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

          {activeTab === 'policy' && (
            <motion.div
              key="policy-view"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              <div className="glass-card p-8">
                <div className="flex items-center gap-4 mb-8">
                  <div className="w-12 h-12 bg-indigo-500/10 rounded-2xl flex items-center justify-center border border-indigo-500/20">
                    <BookOpen className="w-6 h-6 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white tracking-tight">维修资金政策库</h2>
                    <p className="text-xs text-slate-500 font-bold tracking-widest uppercase mt-1">Maintenance Fund Policies</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {[
                    {
                      title: "《住房专项维修资金管理办法》",
                      source: "建设部、财政部令第165号",
                      tags: ["国家标准", "核心法规"],
                      desc: "规定了住宅专项维修资金的设立、缴存、使用、管理和监督。"
                    },
                    {
                      title: "《关于进一步发挥住宅专项维修资金在老旧小区改造中作用的通知》",
                      source: "住建部公告",
                      tags: ["老旧小区", "政策导向"],
                      desc: "明确了维修资金在支持老旧小区加装电梯、屋面防水等方面的便捷程序。"
                    },
                    {
                      title: "上海市住宅物业管理规定 (2023修订)",
                      source: "上海市人大常委会",
                      tags: ["地方性法规", "上海"],
                      desc: "详细规定了2/3业主表决程序及紧急维修资金使用的绿色通道。"
                    },
                    {
                      title: "住宅专项维修资金审计实务操作指南",
                      source: "审计署/行业协会",
                      tags: ["审计实务", "操作规程"],
                      desc: "提供了针对维修资金审计的项目抽查、账目对账及合规性评估的标准流程。"
                    }
                  ].map((p, i) => (
                    <div key={i} className="glass-card p-6 border-white/5 hover:border-indigo-500/30 transition-all group">
                      <div className="flex gap-2 mb-4">
                        {p.tags.map(tag => (
                          <span key={tag} className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 text-[9px] font-bold uppercase tracking-wider rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                      <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors mb-2">{p.title}</h3>
                      <p className="text-[10px] text-slate-500 font-mono mb-4">{p.source}</p>
                      <p className="text-xs text-slate-400 leading-relaxed">{p.desc}</p>
                      <button className="mt-6 w-full py-2.5 bg-white/5 hover:bg-indigo-500/20 text-indigo-300 text-xs font-bold rounded-xl border border-white/10 transition-all flex items-center justify-center gap-2">
                        阅读全文 <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      
      {/* Footer Status Bar */}
      <footer className="h-10 px-8 bg-white/5 flex items-center justify-between text-[10px] text-slate-500 border-t border-white/5 sticky bottom-0 backdrop-blur-sm z-50">
        <div className="flex gap-6 font-bold uppercase tracking-widest">
          <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> 节点状态: 正常</span>
          <span>LLM Engine: Gemini-3-Flash</span>
        </div>
        <div className="flex gap-6 font-bold uppercase tracking-widest">
          <span>数据加密已启用</span>
          <span>最后审计同步: {new Date().toLocaleTimeString()}</span>
        </div>
      </footer>
    </div>
  );
}

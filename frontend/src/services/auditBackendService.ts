import { BackendAnalyzeResponse } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || "";
const API_URL = `${API_BASE_URL || ""}/api/audit-engine/files/analyze-single`;

export async function analyzeFile(file: File): Promise<BackendAnalyzeResponse> {
  return analyzeFiles([file]);
}

export async function analyzeFiles(files: File[]): Promise<BackendAnalyzeResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  let res: Response;
  try {
    res = await fetch(API_URL, {
      method: "POST",
      body: formData,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "无法连接后端服务。请确认后端已启动（uvicorn app.main:app --reload --port 8000），或检查 VITE_API_BASE_URL/代理配置。"
      );
    }
    throw error;
  }

  const contentType = res.headers.get("content-type") || "";
  let body: BackendAnalyzeResponse | null = null;
  if (contentType.includes("application/json")) {
    body = (await res.json()) as BackendAnalyzeResponse;
  } else {
    const text = await res.text();
    if (!res.ok) {
      throw new Error(`后端服务异常（${res.status}）：${text || "返回非 JSON 响应"}`);
    }
    throw new Error("后端返回格式异常：期望 JSON。");
  }

  if (!res.ok) {
    const summary = body?.audit_view?.display_conclusion?.summary;
    throw new Error(summary || `后端服务请求失败（${res.status}）`);
  }
  return body;
}

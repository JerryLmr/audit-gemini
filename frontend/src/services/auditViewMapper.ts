import { AuditView, BackendAnalyzeResponse } from "../types";

export function extractAuditView(result: BackendAnalyzeResponse): AuditView {
  if (!result.audit_view) {
    throw new Error("响应缺少 audit_view，无法展示新版审计视图。");
  }
  return result.audit_view;
}

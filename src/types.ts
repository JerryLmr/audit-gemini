export type AuditCategory = 'COMPLIANCE' | 'PROCESS' | 'TIMING' | 'COMPLETENESS' | 'VALUE';

export interface AuditFinding {
  category: AuditCategory;
  severity: 'high' | 'medium' | 'low' | 'pass';
  title: string;
  description: string;
  recommendation?: string;
}

export interface ExtractedData {
  projectName?: string;
  totalBudget?: number;
  applicants?: string;
  milestones?: {
    event: string;
    date: string;
  }[];
  documents?: {
    name: string;
    type: string;
    status: 'received' | 'missing';
  }[];
  items?: {
    description: string;
    unitPrice: number;
    quantity: number;
    total: number;
  }[];
}

export interface AuditReport {
  projectName: string;
  auditDate: string;
  status: 'Pass' | 'Fail' | 'Warning';
  summary: string;
  findings: AuditFinding[];
  extractedDetails: ExtractedData;
}

export interface FileData {
  id: string;
  name: string;
  type: string;
  content: string; // Base64 or text
  mimeType: string;
}

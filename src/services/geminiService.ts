import { GoogleGenAI, Type } from "@google/genai";
import { AuditReport, ExtractedData, FileData } from "../types";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export async function extractAndAudit(files: FileData[]): Promise<AuditReport> {
  const model = "gemini-3-flash-preview";

  // Prepare parts for the AI
  const parts = files.map(file => {
    if (file.type === 'application/pdf') {
      return {
        inlineData: {
          mimeType: file.mimeType,
          data: file.content.split(',')[1] || file.content,
        }
      };
    } else {
      // For Excel (converted to text) or other text files
      return { text: `File: ${file.name}\nContent:\n${file.content}` };
    }
  });

  const prompt = `
    你是一位专业的住宅专项维修资金审计专家。
    请分析上传的文件（PDF/Excel），并根据以下维度完成审计：
    1. 使用范围合规性：维修资金仅限用于住宅共用部位、共用设施设备保修期满后的维修、更新和改造。
    2. 流程合规性：是否包含申报、公示、表决、审核、施工、验收等关键环节。
    3. 时序逻辑：各环节日期是否合理（如：表决应在中标前，施工应在合同签订后）。
    4. 材料完备性：查核是否包含 申请表、公示证明、表决结果、工程预算、施工合同、验收报告、发票等。
    5. 金额合理性：单价和总价是否在合理范围内。

    请提供结构化的JSON输出，包含项目名称、审计日期、状态（通过/不通过/警告）、摘要总结、详细发现（Finding）以及抽取的关键数据详情。
  `;

  const response = await ai.models.generateContent({
    model,
    contents: { parts: [...parts, { text: prompt }] },
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.OBJECT,
        properties: {
          projectName: { type: Type.STRING },
          auditDate: { type: Type.STRING },
          status: { type: Type.STRING, enum: ["Pass", "Fail", "Warning"] },
          summary: { type: Type.STRING },
          findings: {
            type: Type.ARRAY,
            items: {
              type: Type.OBJECT,
              properties: {
                category: { type: Type.STRING, enum: ["COMPLIANCE", "PROCESS", "TIMING", "COMPLETENESS", "VALUE"] },
                severity: { type: Type.STRING, enum: ["high", "medium", "low", "pass"] },
                title: { type: Type.STRING },
                description: { type: Type.STRING },
                recommendation: { type: Type.STRING },
              },
              required: ["category", "severity", "title", "description"]
            }
          },
          extractedDetails: {
            type: Type.OBJECT,
            properties: {
              projectName: { type: Type.STRING },
              totalBudget: { type: Type.NUMBER },
              applicants: { type: Type.STRING },
              milestones: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    event: { type: Type.STRING },
                    date: { type: Type.STRING }
                  }
                }
              },
              documents: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    name: { type: Type.STRING },
                    type: { type: Type.STRING },
                    status: { type: Type.STRING, enum: ["received", "missing"] }
                  }
                }
              }
            }
          }
        },
        required: ["projectName", "status", "summary", "findings", "extractedDetails"]
      }
    }
  });

  if (!response.text) {
    throw new Error("AI 响应为空");
  }

  return JSON.parse(response.text) as AuditReport;
}

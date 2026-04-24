# Audit Gemini Demo

一个轻量化全栈 Demo：
- 前端：`frontend/`（React + Vite）
- 后端：`backend/`（FastAPI）
- 无 conda、无数据库、无权限系统、无 RAG

支持多文件上传；本期仅 Excel 参与审计，PDF 作为附件展示。

## 启动方式

### 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

可选 `.env`（`backend/.env`）：

```env
LOCAL_LLM_BASE_URL=http://172.18.0.1:1234/v1
LOCAL_LLM_MODEL=auto
LOCAL_LLM_API_KEY=lm-studio
```

说明：
- Windows + WSL 场景通常使用 Windows 主机 IP（例如 `172.18.0.1`）。
- LM Studio 需要开启 **Serve on local network**。
- `LOCAL_LLM_MODEL=auto` 时会自动选择 `/models` 返回的第一个模型。

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

## Demo 流程

1. 打开前端页面（默认 `http://localhost:3000`）。
2. 上传 Excel（可混合上传 PDF）。
3. 点击“开始审计”。
4. 查看总体结论、分项卡片、问题卡片、证据区和审计人员视图。

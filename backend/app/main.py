from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.audit_engine.api.audit_engine_api import router as audit_engine_router


app = FastAPI(
    title="Audit Engine Demo Backend",
    description="轻量化专项维修资金审计演示服务",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audit_engine_router, prefix="/api/audit-engine")


@app.get("/")
def healthcheck() -> dict[str, object]:
    return {
        "service": "audit-engine-demo-backend",
        "status": "ok",
        "routes": ["/api/audit-engine/files/analyze-single"],
    }


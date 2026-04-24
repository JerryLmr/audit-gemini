from typing import List

from fastapi import APIRouter, File, UploadFile

from modules.audit_engine.services.single_project_analysis_service import analyze_single_project_file


router = APIRouter(tags=["audit-engine"])


@router.post("/files/analyze-single")
async def audit_engine_analyze_single_file(files: List[UploadFile] = File(...)):
    return await analyze_single_project_file(files)

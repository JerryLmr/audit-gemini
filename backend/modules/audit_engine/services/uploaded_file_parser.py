from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from fastapi import UploadFile

from modules.audit_engine.services.audit_pipeline_service import run_audit_pipeline
from modules.audit_engine.services.excel_upload_service import parse_xlsx_bytes


UNSUPPORTED_MESSAGE = "当前版本仅支持 .xlsx，PDF/OCR 解析入口已预留。"


def _file_type(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".xlsx":
        return "xlsx"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        return "image"
    if suffix in {".doc", ".docx"}:
        return "doc"
    if suffix == ".xls":
        return "xls"
    return "unsupported"


def _unsupported_file(filename: str, file_type: str) -> Dict[str, Any]:
    return {
        "filename": filename,
        "file_type": file_type,
        "status": "unsupported",
        "message": UNSUPPORTED_MESSAGE,
        "rows": [],
        "documents": [],
        "warnings": [UNSUPPORTED_MESSAGE],
    }


async def parse_uploaded_file(file: UploadFile) -> Dict[str, Any]:
    filename = file.filename or ""
    file_type = _file_type(filename)

    if file_type != "xlsx":
        return _unsupported_file(filename, file_type)

    try:
        content = await file.read()
        return parse_xlsx_bytes(content, filename=filename)
    except Exception as exc:  # Keep one bad file from failing the whole batch.
        return {
            "filename": filename,
            "file_type": file_type,
            "status": "failed",
            "message": str(exc),
            "rows": [],
            "documents": [],
            "warnings": [str(exc)],
        }


async def parse_uploaded_files(files: Iterable[UploadFile]) -> Dict[str, Any]:
    parsed_files: List[Dict[str, Any]] = []
    for file in files:
        parsed_files.append(await parse_uploaded_file(file))
    return {"files": parsed_files}


def _should_judge_row(
    file_position: int,
    row: Dict[str, Any],
    file_index: Optional[int],
    row_index: Optional[int],
) -> bool:
    if file_index is not None and file_position != file_index:
        return False
    if row_index is not None and row.get("row_index") != row_index:
        return False
    return True


async def judge_uploaded_files(
    files: Iterable[UploadFile],
    file_index: Optional[int] = None,
    row_index: Optional[int] = None,
) -> Dict[str, Any]:
    parsed = await parse_uploaded_files(files)
    judged_files: List[Dict[str, Any]] = []
    total_items = 0
    success_count = 0
    failed_count = 0

    for file_position, file_result in enumerate(parsed["files"]):
        judged_file = {
            key: value
            for key, value in file_result.items()
            if key not in {"rows"}
        }
        items: List[Dict[str, Any]] = []

        if file_result.get("status") == "parsed":
            for row in file_result.get("rows", []):
                if not _should_judge_row(file_position, row, file_index, row_index):
                    continue
                item = {
                    "row_index": row.get("row_index"),
                    "project_key": row.get("project_key"),
                    "project_name": row.get("project_name") or "",
                    "standard_fields": row.get("standard_fields") or {},
                    "missing_fields": row.get("missing_fields") or [],
                    "conflicting_fields": row.get("conflicting_fields") or [],
                    "audit_ready": row.get("audit_ready", False),
                    "audit_request": row.get("audit_request") or {},
                    "source_sheets": row.get("source_sheets") or [],
                    "business_summary": row.get("business_summary") or [],
                    "warnings": row.get("warnings") or [],
                    "mapped_objects": row.get("mapped_objects") or [],
                    "matched_object_ids": row.get("matched_object_ids") or [],
                    "debug": row.get("debug") or {},
                    "audit_result": None,
                    "error": None,
                }
                total_items += 1
                try:
                    item["audit_result"] = run_audit_pipeline(item["audit_request"])
                    item["project_name"] = item["audit_result"].get("project_name") or item["project_name"]
                    success_count += 1
                except Exception as exc:  # Row-level failure should not stop the batch.
                    item["error"] = str(exc)
                    failed_count += 1
                items.append(item)

        judged_file["status"] = "judged" if file_result.get("status") == "parsed" else file_result.get("status")
        judged_file["items"] = items
        judged_files.append(judged_file)

    return {
        "total_items": total_items,
        "success_count": success_count,
        "failed_count": failed_count,
        "files": judged_files,
    }

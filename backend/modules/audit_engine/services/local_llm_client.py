from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests import Response

from app.config import LOCAL_LLM_API_KEY, LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL, LOCAL_LLM_TIMEOUT


def _empty_failure(
    error_type: str,
    error_message: str,
    models_response: Any = None,
    *,
    requested_model: Optional[str] = None,
    selected_model: Optional[str] = None,
    warnings: Optional[List[str]] = None,
    models_ok: bool = False,
    chat_ok: bool = False,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "available": False,
        "model": selected_model or requested_model or LOCAL_LLM_MODEL,
        "requested_model": requested_model or LOCAL_LLM_MODEL,
        "selected_model": selected_model,
        "raw_content": "",
        "error": error_message,
        "error_type": error_type,
        "error_message": error_message,
        "warnings": warnings or [],
        "models_response": models_response or {},
        "models_ok": models_ok,
        "chat_ok": chat_ok,
        "timeout_seconds": timeout_seconds if timeout_seconds is not None else LOCAL_LLM_TIMEOUT,
    }


def _classify_request_error(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        return "timeout"
    if isinstance(exc, (requests.ConnectionError, requests.RequestException)):
        message = str(exc).lower()
        refused_markers = (
            "connection refused",
            "failed to establish a new connection",
            "network is unreachable",
            "no route to host",
            "operation not permitted",
            "max retries exceeded",
        )
        if any(marker in message for marker in refused_markers):
            return "refused"
    return "invalid_response"


def _response_json(response: Response) -> Dict[str, Any] | None:
    try:
        data = response.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _pick_model(model_ids: List[str], requested_model: str) -> Tuple[str, Optional[str]]:
    requested = (requested_model or "").strip()
    if not requested or requested.lower() == "auto":
        return model_ids[0], None
    if requested in model_ids:
        return requested, None
    return (
        model_ids[0],
        f"LOCAL_LLM_MODEL={requested!r} 未在 /models 返回中找到，已自动回退到 {model_ids[0]!r}。",
    )


def check_local_llm_models(*, timeout: int = 5) -> Dict[str, Any]:
    url = f"{LOCAL_LLM_BASE_URL}/models"
    headers = {"Authorization": f"Bearer {LOCAL_LLM_API_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        models_response = _response_json(response)
        print(
            "[audit_engine.local_llm] GET /v1/models",
            json.dumps(
                {
                    "url": url,
                    "status_code": response.status_code,
                    "body": models_response if models_response is not None else response.text[:1000],
                },
                ensure_ascii=False,
            ),
        )
        if not response.ok:
            return _empty_failure(
                "invalid_response",
                f"/models returned HTTP {response.status_code}: {response.text[:500]}",
                models_response,
                requested_model=LOCAL_LLM_MODEL,
                models_ok=False,
                chat_ok=False,
            )
        if not isinstance(models_response, dict) or not isinstance(models_response.get("data"), list):
            return _empty_failure(
                "invalid_response",
                "/models response missing data list",
                models_response,
                requested_model=LOCAL_LLM_MODEL,
                models_ok=False,
                chat_ok=False,
            )
        model_ids = [
            item.get("id")
            for item in models_response.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id")
        ]
        if not model_ids:
            return _empty_failure(
                "model_not_found",
                "/models response has empty model id list",
                models_response,
                requested_model=LOCAL_LLM_MODEL,
                models_ok=False,
                chat_ok=False,
            )
        selected_model, selection_warning = _pick_model(model_ids, LOCAL_LLM_MODEL)
        warnings: List[str] = []
        if selection_warning:
            warnings.append(selection_warning)
        return {
            "available": True,
            "model": selected_model,
            "requested_model": LOCAL_LLM_MODEL,
            "selected_model": selected_model,
            "model_selection_warning": selection_warning,
            "warnings": warnings,
            "models_response": models_response,
            "error": None,
            "error_type": None,
            "error_message": None,
            "models_ok": True,
            "chat_ok": False,
        }
    except Exception as exc:
        error_type = _classify_request_error(exc)
        print(
            "[audit_engine.local_llm] GET /v1/models failed",
            json.dumps(
                {
                    "url": url,
                    "error_type": error_type,
                    "error_message": str(exc),
                },
                ensure_ascii=False,
            ),
        )
        return _empty_failure(
            error_type,
            str(exc),
            requested_model=LOCAL_LLM_MODEL,
            models_ok=False,
            chat_ok=False,
        )


def call_local_llm_json(prompt: str, *, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Call LM Studio's OpenAI-compatible chat completions endpoint.

    The audit pipeline must keep running when the local model is unavailable.
    This function therefore returns an availability marker instead of raising
    network or response-shape exceptions.
    """
    request_timeout = timeout if timeout is not None else LOCAL_LLM_TIMEOUT
    models_check = check_local_llm_models()
    if models_check.get("available") is not True:
        return models_check

    selected_model = str(models_check.get("selected_model") or models_check.get("model") or LOCAL_LLM_MODEL)
    url = f"{LOCAL_LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LOCAL_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": selected_model,
        "messages": [
            {
                "role": "system",
                "content": "你只做字段归类，不做审计判断。必须只输出严格 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "text"},
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=request_timeout)
        data = _response_json(response)
        if not response.ok:
            warnings = list(models_check.get("warnings") or [])
            warnings.append("本地 LLM /chat/completions 调用失败，已回退为仅规则审计结果。")
            return _empty_failure(
                "invalid_response",
                f"/chat/completions returned HTTP {response.status_code}: {response.text[:500]}",
                models_check.get("models_response"),
                requested_model=models_check.get("requested_model"),
                selected_model=selected_model,
                warnings=warnings,
                models_ok=True,
                chat_ok=False,
                timeout_seconds=request_timeout,
            )
        if data is None:
            warnings = list(models_check.get("warnings") or [])
            warnings.append("本地 LLM /chat/completions 返回异常，已回退为仅规则审计结果。")
            return _empty_failure(
                "invalid_response",
                "/chat/completions returned non-JSON response",
                models_check.get("models_response"),
                requested_model=models_check.get("requested_model"),
                selected_model=selected_model,
                warnings=warnings,
                models_ok=True,
                chat_ok=False,
                timeout_seconds=request_timeout,
            )
        content: Optional[str] = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if content is None:
            warnings = list(models_check.get("warnings") or [])
            warnings.append("本地 LLM /chat/completions 返回缺少内容，已回退为仅规则审计结果。")
            return _empty_failure(
                "invalid_response",
                "/chat/completions response missing choices[0].message.content",
                models_check.get("models_response"),
                requested_model=models_check.get("requested_model"),
                selected_model=selected_model,
                warnings=warnings,
                models_ok=True,
                chat_ok=False,
                timeout_seconds=request_timeout,
            )
        return {
            "available": True,
            "model": selected_model,
            "requested_model": models_check.get("requested_model"),
            "selected_model": selected_model,
            "model_selection_warning": models_check.get("model_selection_warning"),
            "warnings": list(models_check.get("warnings") or []),
            "raw_content": content or "{}",
            "error": None,
            "error_type": None,
            "error_message": None,
            "models_response": models_check.get("models_response") or {},
            "models_ok": True,
            "chat_ok": True,
            "timeout_seconds": request_timeout,
        }
    except Exception as exc:
        warnings = list(models_check.get("warnings") or [])
        warnings.append("本地 LLM /chat/completions 调用失败，已回退为仅规则审计结果。")
        return _empty_failure(
            _classify_request_error(exc),
            str(exc),
            models_check.get("models_response"),
            requested_model=models_check.get("requested_model"),
            selected_model=selected_model,
            warnings=warnings,
            models_ok=True,
            chat_ok=False,
            timeout_seconds=request_timeout,
        )

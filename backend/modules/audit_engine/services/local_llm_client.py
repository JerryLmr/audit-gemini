from __future__ import annotations

import json
from typing import Any, Dict, Optional

import requests
from requests import Response

from app.config import LOCAL_LLM_API_KEY, LOCAL_LLM_BASE_URL, LOCAL_LLM_MODEL


def _empty_failure(error_type: str, error_message: str, models_response: Any = None) -> Dict[str, Any]:
    return {
        "available": False,
        "model": LOCAL_LLM_MODEL,
        "raw_content": "{}",
        "error": error_message,
        "error_type": error_type,
        "error_message": error_message,
        "models_response": models_response or {},
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
            )
        if not isinstance(models_response, dict) or not isinstance(models_response.get("data"), list):
            return _empty_failure("invalid_response", "/models response missing data list", models_response)
        model_ids = [
            item.get("id")
            for item in models_response.get("data", [])
            if isinstance(item, dict)
        ]
        if LOCAL_LLM_MODEL not in model_ids:
            return _empty_failure(
                "model_not_found",
                f"model {LOCAL_LLM_MODEL!r} not found in /models response",
                models_response,
            )
        return {
            "available": True,
            "model": LOCAL_LLM_MODEL,
            "models_response": models_response,
            "error": None,
            "error_type": None,
            "error_message": None,
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
        return _empty_failure(error_type, str(exc))


def call_local_llm_json(prompt: str, *, timeout: int = 120) -> Dict[str, Any]:
    """Call LM Studio's OpenAI-compatible chat completions endpoint.

    The audit pipeline must keep running when the local model is unavailable.
    This function therefore returns an availability marker instead of raising
    network or response-shape exceptions.
    """
    models_check = check_local_llm_models()
    if models_check.get("available") is not True:
        return models_check

    url = f"{LOCAL_LLM_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LOCAL_LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LOCAL_LLM_MODEL,
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
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        data = _response_json(response)
        if not response.ok:
            return _empty_failure(
                "invalid_response",
                f"/chat/completions returned HTTP {response.status_code}: {response.text[:500]}",
                models_check.get("models_response"),
            )
        if data is None:
            return _empty_failure(
                "invalid_response",
                "/chat/completions returned non-JSON response",
                models_check.get("models_response"),
            )
        content: Optional[str] = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )
        if content is None:
            return _empty_failure(
                "invalid_response",
                "/chat/completions response missing choices[0].message.content",
                models_check.get("models_response"),
            )
        return {
            "available": True,
            "model": LOCAL_LLM_MODEL,
            "raw_content": content or "{}",
            "error": None,
            "error_type": None,
            "error_message": None,
            "models_response": models_check.get("models_response") or {},
        }
    except Exception as exc:
        return _empty_failure(_classify_request_error(exc), str(exc), models_check.get("models_response"))

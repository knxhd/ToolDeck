"""HTTP 请求转发服务：用 httpx.AsyncClient 转发，30 秒超时，返回完整响应。"""
from __future__ import annotations

import time
from typing import Any

import httpx

from backend.app.schemas.http import (
    BodyType,
    HttpRequest,
    HttpResponse,
    KeyValue,
    HttpMethod,
)
from backend.app.services.form_data import FormDataError, build_form_data, drop_content_type


def _kv_to_dict(items: list[KeyValue]) -> dict[str, str]:
    """把 KeyValue 列表转为 dict，仅保留 enabled 项。"""
    return {item.key: item.value for item in items if item.enabled and item.key}


async def send_request(req: HttpRequest) -> HttpResponse:
    """转发 HTTP 请求，返回完整响应（含耗时与字节数）。"""
    headers = _kv_to_dict(req.headers)
    params = _kv_to_dict(req.params)
    content: Any = None
    form_data: Any = None
    form_files: Any = None

    if req.body_type == BodyType.JSON:
        headers.setdefault("Content-Type", "application/json")
        content = req.body
    elif req.body_type == BodyType.RAW:
        content = req.body
    elif req.body_type == BodyType.FORM_DATA:
        try:
            fields, files = build_form_data(req.body)
        except FormDataError as exc:
            return HttpResponse(status_code=0, status_text="Error", error=str(exc))
        form_data = fields or None
        if files:
            form_files = files
            headers = drop_content_type(headers)

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await client.request(
                method=req.method.value,
                url=req.url,
                headers=headers,
                params=params,
                content=content,
                data=form_data,
                files=form_files,
            )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        body_bytes = response.content
        size_bytes = len(body_bytes)
        try:
            body_text = body_bytes.decode("utf-8")
        except UnicodeDecodeError:
            body_text = body_bytes.decode("utf-8", errors="replace")
        return HttpResponse(
            status_code=response.status_code,
            status_text=response.reason_phrase,
            headers=dict(response.headers),
            body=body_text,
            elapsed_ms=elapsed_ms,
            size_bytes=size_bytes,
        )
    except httpx.TimeoutException:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return HttpResponse(
            status_code=504,
            status_text="Gateway Timeout",
            headers={},
            body="",
            elapsed_ms=elapsed_ms,
            size_bytes=0,
            error="请求超时（30 秒未响应）",
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return HttpResponse(
            status_code=0,
            status_text="Error",
            headers={},
            body="",
            elapsed_ms=elapsed_ms,
            size_bytes=0,
            error=str(exc),
        )


__all__ = ["send_request"]

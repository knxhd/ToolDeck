"""HTTP 请求工作台路由。

- POST /api/http/send       转发请求（一次性返回完整响应）
- POST /api/http/stream      转发请求（流式下发，NDJSON：meta/chunk/done/error）
- GET  /api/http/history     返回历史列表
- DELETE /api/http/history   清空历史
"""
from __future__ import annotations

import json
import time

import httpx
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.schemas.http import BodyType, HttpRequest, KeyValue
from backend.app.services import history_store, users
from backend.app.services.form_data import FormDataError, build_form_data, drop_content_type
from backend.app.services.http_client import send_request

router = APIRouter()


def _kv_to_dict(items: list[KeyValue]) -> dict[str, str]:
    return {item.key: item.value for item in items if item.enabled and item.key}


def _user(x_user: str | None) -> str:
    try:
        return users.sanitize_username(x_user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/send")
async def send(req: HttpRequest, x_user: str | None = Header(default=None)) -> dict:
    """转发 HTTP 请求并返回完整响应；成功后追加历史记录。"""
    user = _user(x_user)
    response = await send_request(req)
    history_store.append_http_call(
        user,
        {
            "method": req.method.value,
            "url": req.url,
            "headers": [h.model_dump() for h in req.headers],
            "body_type": req.body_type.value,
            "body": req.body,
            "status_code": response.status_code,
            "elapsed_ms": response.elapsed_ms,
        },
    )
    return response.model_dump()


@router.post("/stream")
async def stream(req: HttpRequest, x_user: str | None = Header(default=None)) -> StreamingResponse:
    """流式转发请求：先发响应头 meta，再逐块下发 body，最后 done。

    普通接口会在一次或少数几块内收齐；SSE/分块接口则逐块实时推送。
    """
    user = _user(x_user)
    headers = _kv_to_dict(req.headers)
    params = _kv_to_dict(req.params)
    content = None
    form_data = None
    form_files = None
    form_error = ""

    if req.body_type == BodyType.JSON:
        headers.setdefault("Content-Type", "application/json")
        content = req.body
    elif req.body_type == BodyType.RAW:
        content = req.body
    elif req.body_type == BodyType.FORM_DATA:
        try:
            fields, files = build_form_data(req.body)
        except FormDataError as exc:
            form_error = str(exc)
        else:
            form_data = fields or None
            if files:
                # 含文件：multipart/form-data，Content-Type（含 boundary）交给 httpx 生成
                form_files = files
                headers = drop_content_type(headers)

    async def gen():
        start = time.perf_counter()
        size = 0
        if form_error:
            yield json.dumps({"type": "error", "message": form_error}, ensure_ascii=False) + "\n"
            return
        try:
            timeout = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                async with client.stream(
                    method=req.method.value,
                    url=req.url,
                    headers=headers,
                    params=params,
                    content=content,
                    data=form_data,
                    files=form_files,
                ) as resp:
                    meta = {
                        "type": "meta",
                        "status_code": resp.status_code,
                        "status_text": resp.reason_phrase,
                        "headers": dict(resp.headers),
                    }
                    yield json.dumps(meta, ensure_ascii=False) + "\n"
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        chunk_content = chunk.decode("utf-8", errors="replace")
                        frame_content = chunk_content.replace("data:", "")
                        if frame_content:
                            yield json.dumps({"type": "chunk", "data": frame_content}, ensure_ascii=False) + "\n"
                    elapsed_ms = int((time.perf_counter() - start) * 1000)
                    yield json.dumps({"type": "done", "elapsed_ms": elapsed_ms, "size_bytes": size}, ensure_ascii=False) + "\n"
                    history_store.append_http_call(
                        user,
                        {
                            "method": req.method.value,
                            "url": req.url,
                            "headers": [h.model_dump() for h in req.headers],
                            "body_type": req.body_type.value,
                            "body": req.body,
                            "status_code": resp.status_code,
                            "elapsed_ms": elapsed_ms,
                        },
                    )
        except httpx.TimeoutException:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            yield json.dumps(
                {"type": "error", "message": f"请求超时（已用 {elapsed_ms} ms）"},
                ensure_ascii=False,
            ) + "\n"
        except Exception as exc:  # noqa: BLE001
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@router.get("/history")
async def get_history(x_user: str | None = Header(default=None)) -> list[dict]:
    calls = history_store.get_http_calls(_user(x_user))
    return list(reversed(calls))


@router.delete("/history")
async def clear_history(x_user: str | None = Header(default=None)) -> dict:
    history_store.clear_http_calls(_user(x_user))
    return {"cleared": True}

"""LLM Provider Adapter 路由。

- GET    /api/llm/providers                     列出 Provider
- POST   /api/llm/providers                      添加 Provider
- PUT    /api/llm/providers/{name}                更新 Provider
- DELETE /api/llm/providers/{name}                删除 Provider
- POST   /api/llm/chat                            同步调用
- POST   /api/llm/chat/stream                     流式调用（SSE）
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.schemas.llm import ChatRequest, ChatResponse, LlmProvider
from backend.app.services import history_store
from backend.app.services import llm_store
from backend.app.services import users
from backend.app.services.llm import get_adapter

router = APIRouter()


def _user(x_user: str | None) -> str:
    try:
        return users.sanitize_username(x_user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


def _resolve_provider(name: str) -> tuple[LlmProvider, object]:
    """根据 name 取 Provider 配置 + 对应 Adapter。"""
    p = llm_store.get_provider(name)
    if p is None:
        raise HTTPException(status_code=404, detail=f"LLM Provider '{name}' 不存在")
    provider = LlmProvider(**p)
    try:
        adapter = get_adapter(provider.provider_type.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return provider, adapter


@router.get("/providers")
async def list_providers() -> list[dict]:
    return llm_store.list_providers()


@router.post("/providers", response_model=dict)
async def add_provider(provider: LlmProvider) -> dict:
    try:
        return llm_store.add_provider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/providers/{name}", response_model=dict)
async def update_provider(name: str, provider: LlmProvider) -> dict:
    try:
        return llm_store.update_provider(name, provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/providers/{name}")
async def delete_provider(name: str) -> dict:
    try:
        return llm_store.delete_provider(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


def _sse(delta: str = "", finish_reason: str | None = None, error: str | None = None) -> str:
    """构造 SSE data 行。"""
    payload: dict[str, object] = {"delta": delta}
    if finish_reason is not None:
        payload["finish_reason"] = finish_reason
    if error is not None:
        payload["error"] = error
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_user: str | None = Header(default=None)) -> ChatResponse:
    """同步调用 LLM。"""
    user = _user(x_user)
    provider, adapter = _resolve_provider(req.provider_name)
    options = {"temperature": req.temperature, **provider.options}
    request = adapter.build_request(
        provider.base_url,
        provider.api_key,
        provider.model,
        req.messages,
        stream=False,
        options=options,
    )
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.send(request)
            response.raise_for_status()
        content, finish_reason, usage = adapter.parse_sync_response(response)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"上游错误：{exc.response.text}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"调用失败：{exc}")

    history_store.append_llm_call(
        user,
        {
            "provider": provider.name,
            "model": provider.model,
            "messages": [m.model_dump() for m in req.messages],
            "content": content,
            "finish_reason": finish_reason,
            "usage": usage,
        },
    )
    return ChatResponse(content=content, finish_reason=finish_reason, usage=usage, model=provider.model)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, x_user: str | None = Header(default=None)) -> StreamingResponse:
    """流式调用 LLM，SSE 推送。"""
    user = _user(x_user)
    provider, adapter = _resolve_provider(req.provider_name)
    options = {"temperature": req.temperature, **provider.options}
    request = adapter.build_request(
        provider.base_url,
        provider.api_key,
        provider.model,
        req.messages,
        stream=True,
        options=options,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        full_content = ""
        finish_reason = ""
        usage: dict = {}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", request.url, headers=request.headers, json=json.loads(request.content)) as response:
                    if response.status_code >= 400:
                        body = await response.aread()
                        yield _sse(error=f"上游错误 {response.status_code}: {body.decode('utf-8', 'replace')}")
                        return
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        delta, fr = adapter.parse_stream_chunk(line.encode("utf-8"))
                        if delta:
                            full_content += delta
                            yield _sse(delta=delta)
                        if fr:
                            finish_reason = fr
                            yield _sse(delta="", finish_reason=fr)
                            break
            yield _sse(delta="", finish_reason="stop")
        except Exception as exc:
            yield _sse(error=f"已中断：{exc}")
        finally:
            history_store.append_llm_call(
                user,
                {
                    "provider": provider.name,
                    "model": provider.model,
                    "messages": [m.model_dump() for m in req.messages],
                    "content": full_content,
                    "finish_reason": finish_reason,
                    "usage": usage,
                    "stream": True,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
async def get_llm_history(x_user: str | None = Header(default=None)) -> list[dict]:
    """返回 LLM 调用历史（按时间倒序）。"""
    calls = history_store.get_llm_calls(_user(x_user))
    return list(reversed(calls))


@router.delete("/history")
async def clear_llm_history(x_user: str | None = Header(default=None)) -> dict:
    history_store.clear_llm_calls(_user(x_user))
    return {"cleared": True}

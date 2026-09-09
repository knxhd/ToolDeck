import json
import time
import base64
import io
import os
from pathlib import Path
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import sys
sys.path.append(os.path.dirname(__file__))
from dto.models import RequestPayload, ResponsePayload, AuthConfig

app = FastAPI(title="Postman Tool", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ── Auth 注入 ──────────────────────────────────────────────

def apply_auth(headers: Dict[str, str], query_params: Dict[str, str], auth: Optional[AuthConfig]):
    """将 AuthConfig 注入到 headers 或 query_params"""
    if not auth or auth.type == "none":
        return headers, query_params

    headers = dict(headers)
    query_params = dict(query_params)

    if auth.type == "bearer" and auth.token:
        headers["Authorization"] = f"Bearer {auth.token}"
    elif auth.type == "basic" and auth.username is not None:
        pwd = auth.password or ""
        creds = base64.b64encode(f"{auth.username}:{pwd}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
    elif auth.type == "apikey" and auth.key_name and auth.key_value:
        if auth.key_in == "query":
            query_params[auth.key_name] = auth.key_value
        else:
            headers[auth.key_name] = auth.key_value

    return headers, query_params


# ── Body 编码 ──────────────────────────────────────────────

def build_httpx_kwargs(payload: RequestPayload) -> dict:
    """根据 body_type 构造 httpx 请求参数"""
    kwargs = {}

    if payload.body_type == "none":
        return kwargs

    if payload.body_type == "raw":
        # 检测是否是 JSON
        ct = payload.headers.get("Content-Type", "")
        if "application/json" in ct.lower():
            try:
                kwargs["json"] = json.loads(payload.body or "{}")
            except (json.JSONDecodeError, TypeError):
                kwargs["content"] = payload.body
        else:
            kwargs["content"] = payload.body

    elif payload.body_type == "x-www-urlencoded":
        # 解析 body 中的 key=value 对
        data = {}
        if payload.body:
            for pair in payload.body.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    data[k] = v
        kwargs["data"] = data

    elif payload.body_type == "form-data":
        files = []
        data = {}
        for field in payload.form_fields:
            if field.type == "file" and field.content:
                file_bytes = base64.b64decode(field.content)
                filename = field.filename or field.name
                files.append((field.name, (filename, file_bytes)))
            elif field.type == "text":
                data[field.name] = field.value or ""
        if files:
            kwargs["files"] = files
        if data:
            kwargs["data"] = data

    elif payload.body_type == "binary":
        if payload.body:
            kwargs["content"] = base64.b64decode(payload.body)

    return kwargs


# ── 工具函数 ───────────────────────────────────────────────

def parse_headers(headers: httpx.Headers) -> Dict[str, str]:
    return {k: v for k, v in headers.items()}


# ── HTTP 请求代理 ───────────────────────────────────────────

@app.post("/api/request")
async def proxy_request(payload: RequestPayload):
    """普通 HTTP 请求代理"""
    headers, query_params = apply_auth(payload.headers, payload.query_params, payload.auth)
    httpx_kwargs = build_httpx_kwargs(payload)

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=payload.timeout, follow_redirects=True) as client:
            resp = await client.request(
                method=payload.method,
                url=payload.url,
                headers=headers,
                params=query_params,
                **httpx_kwargs,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except httpx.ConnectError as e:
        raise HTTPException(status_code=502, detail=f"Connection error: {e}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"HTTP error: {e}")

    elapsed_ms = (time.time() - start) * 1000
    body_bytes = resp.content
    content_type = resp.headers.get("content-type", "")

    # 尝试解码 body
    try:
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        body_text = base64.b64encode(body_bytes).decode()

    return ResponsePayload(
        status=resp.status_code,
        status_text=resp.reason_phrase,
        headers=parse_headers(resp.headers),
        body=body_text,
        time_ms=round(elapsed_ms, 1),
        size_bytes=len(body_bytes),
        content_type=content_type.split(";")[0].strip(),
    )


# ── SSE 流式透传 ────────────────────────────────────────────

def sse_wrap(payload_str: str) -> str:
    """包装为 SSE 帧"""
    frame = {"type": "frame", "data": payload_str}
    return f"data: {json.dumps(frame, ensure_ascii=False)}\n\n"


def sse_done() -> str:
    """SSE 结束帧"""
    return f"data: {json.dumps({'type': 'done'})}\n\n"


@app.post("/api/request/stream")
async def proxy_request_stream(payload: RequestPayload):
    """流式 HTTP 请求代理（统一 SSE 通道）"""
    headers, query_params = apply_auth(payload.headers, payload.query_params, payload.auth)
    httpx_kwargs = build_httpx_kwargs(payload)

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=payload.timeout, follow_redirects=True) as client:
                async with client.stream(
                    method=payload.method,
                    url=payload.url,
                    headers=headers,
                    params=query_params,
                    **httpx_kwargs,
                ) as resp:
                    upstream_is_sse = "text/event-stream" in resp.headers.get("content-type", "").lower()

                    if upstream_is_sse:
                        # 上游是 SSE → 逐帧透传原始帧
                        async for chunk in resp.aiter_lines():
                            if chunk.startswith("data:"):
                                # 提取原始 payload（data: 后面的内容）
                                payload_str = chunk[5:].strip()
                                yield sse_wrap(payload_str)
                    else:
                        # 上游不是 SSE → 收集完整响应后包装
                        body_chunks = []
                        async for chunk in resp.aiter_bytes():
                            body_chunks.append(chunk)
                        body_bytes = b"".join(body_chunks)
                        try:
                            body_text = body_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            body_text = base64.b64encode(body_bytes).decode()
                        yield sse_wrap(body_text)
        except httpx.TimeoutException:
            yield sse_wrap(json.dumps({"error": "Request timeout"}))
        except httpx.ConnectError as e:
            yield sse_wrap(json.dumps({"error": f"Connection error: {e}"}))
        except Exception as e:
            yield sse_wrap(json.dumps({"error": str(e)}))
        finally:
            yield sse_done()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── WebSocket 代理 ──────────────────────────────────────────

@app.websocket("/api/ws")
async def websocket_proxy(ws: WebSocket, url: str):
    """WebSocket 双向代理"""
    await ws.accept()

    target_ws = None
    try:
        import websockets

        target_ws = await websockets.connect(url)

        import asyncio

        async def forward_client_to_target():
            try:
                while True:
                    data = await ws.receive_text()
                    if target_ws:
                        await target_ws.send(data)
            except WebSocketDisconnect:
                pass
            except Exception:
                pass

        async def forward_target_to_client():
            try:
                while True:
                    if target_ws:
                        data = await target_ws.recv()
                        await ws.send_text(str(data))
            except Exception:
                pass

        await asyncio.gather(
            forward_client_to_target(),
            forward_target_to_client(),
            return_exceptions=True,
        )
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        if target_ws:
            try:
                await target_ws.close()
            except Exception:
                pass
        try:
            await ws.close()
        except Exception:
            pass


# ── 测试端点（方便验证 SSE 解析器） ─────────────────────────

@app.get("/test/sse/openai")
async def test_openai_sse():
    """模拟 OpenAI Chat Completions SSE 端点"""
    chunks = [
        {"choices": [{"delta": {"content": "你好"}}]},
        {"choices": [{"delta": {"content": "，我是"}}]},
        {"choices": [{"delta": {"content": "Postman Tool"}}]},
        {"choices": [{"delta": {"content": "的"}}]},
        {"choices": [{"delta": {"content": "AI"}}]},
        {"choices": [{"delta": {"content": "助手。"}}]},
        {"choices": [{"delta": {"content": "有什么"}}]},
        {"choices": [{"delta": {"content": "可以"}}]},
        {"choices": [{"delta": {"content": "帮你"}}]},
        {"choices": [{"delta": {"content": "的吗？"}}]},
        "[DONE]",
    ]

    async def gen():
        import asyncio
        for chunk in chunks:
            if isinstance(chunk, str):
                yield f"data: {chunk}\n\n"
            else:
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/test/sse/echo")
async def test_echo_sse():
    """简单 SSE echo 测试"""
    import asyncio

    async def gen():
        for i in range(5):
            yield f"data: chunk-{i}\n\n"
            await asyncio.sleep(0.3)
        yield f"data: done\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.websocket("/test/ws/echo")
async def test_ws_echo(ws: WebSocket):
    """WebSocket echo 测试"""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            await ws.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


# ── 静态文件 serve ──────────────────────────────────────────

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html not found"}, status_code=404)


# Mount static files if frontend directory exists
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=58000)

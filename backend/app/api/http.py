"""HTTP 请求工作台路由。

- POST /api/http/send       转发请求
- GET  /api/http/history    返回历史列表
- DELETE /api/http/history  清空历史
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.http import HttpRequest, HttpResponse, HttpCallRecord
from backend.app.services import history_store
from backend.app.services.http_client import send_request

router = APIRouter()


@router.post("/send", response_model=HttpResponse)
async def send(req: HttpRequest) -> HttpResponse:
    """转发 HTTP 请求并返回响应；成功后追加历史记录。"""
    response = await send_request(req)
    # 记录历史（即使出错也保留请求信息）
    history_store.append_http_call(
        {
            "method": req.method.value,
            "url": req.url,
            "headers": [h.model_dump() for h in req.headers],
            "body_type": req.body_type.value,
            "body": req.body,
            "status_code": response.status_code,
            "elapsed_ms": response.elapsed_ms,
        }
    )
    return response


@router.get("/history")
async def get_history() -> list[dict]:
    """返回 HTTP 调用历史（按时间倒序）。"""
    calls = history_store.get_http_calls()
    return list(reversed(calls))


@router.delete("/history")
async def clear_history() -> dict:
    """清空 HTTP 调用历史。"""
    history_store.clear_http_calls()
    return {"cleared": True}

"""网络辅助路由：给前端提供"调用方真实地址"，用于把 URL 里的 127.0.0.1 解析成可达地址。"""
from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.services.net_util import client_ip_from_request, host_from_request

router = APIRouter()


@router.get("/host")
async def net_host(request: Request) -> dict:
    """返回调用方视角的地址信息。

    - client_ip：这次请求的来源 IP（浏览器所在机器的内网 IP，服务端可见的那个）；
    - browser_host：浏览器访问本工具时用的 host（反代场景取 X-Forwarded-Host）。

    两者都可能为空/不可达，前端按设置里的策略决定用哪个。
    """
    return {
        "client_ip": client_ip_from_request(request),
        "browser_host": host_from_request(request),
    }

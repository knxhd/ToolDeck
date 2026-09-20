"""MCP Streamable 客户端路由。

- GET    /api/mcp/servers                      列出所有 Server
- POST   /api/mcp/servers                       添加 Server
- PUT    /api/mcp/servers/{name}                更新 Server
- DELETE /api/mcp/servers/{name}                删除 Server
- POST   /api/mcp/servers/{name}/test           测试连接
- GET    /api/mcp/servers/{name}/tools          列出工具
- POST   /api/mcp/servers/{name}/tools/{tool}/call  调用工具
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.schemas.mcp import (
    McpCallResult,
    McpServer,
    McpTestResult,
    McpTool,
)
from backend.app.services import history_store
from backend.app.services import mcp_client
from backend.app.services import mcp_store

router = APIRouter()


def _get_server_or_404(name: str) -> dict:
    s = mcp_store.get_server(name)
    if s is None:
        raise HTTPException(status_code=404, detail=f"MCP Server '{name}' 不存在")
    return s


@router.get("/servers")
async def list_servers() -> list[dict]:
    return mcp_store.list_servers()


@router.post("/servers", response_model=dict)
async def add_server(server: McpServer) -> dict:
    try:
        return mcp_store.add_server(server)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/servers/{name}", response_model=dict)
async def update_server(name: str, server: McpServer) -> dict:
    try:
        return mcp_store.update_server(name, server)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/servers/{name}")
async def delete_server(name: str) -> dict:
    try:
        return mcp_store.delete_server(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/servers/{name}/test", response_model=McpTestResult)
async def test_server(name: str) -> McpTestResult:
    s = _get_server_or_404(name)
    server = McpServer(**s)
    ok, message, info = await mcp_client.test_connection(server)
    return McpTestResult(ok=ok, message=message, server_info=info)


@router.get("/servers/{name}/tools", response_model=list[McpTool])
async def list_tools(name: str) -> list[McpTool]:
    s = _get_server_or_404(name)
    server = McpServer(**s)
    try:
        return await mcp_client.list_tools(server)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"列出工具失败：{exc}")


@router.post("/servers/{name}/tools/{tool}/call", response_model=McpCallResult)
async def call_tool(name: str, tool: str, args: dict) -> McpCallResult:
    s = _get_server_or_404(name)
    server = McpServer(**s)
    try:
        result = await mcp_client.call_tool(server, tool, args)
    except Exception as exc:
        result = McpCallResult(
            server=name, tool=tool, is_error=True, error=str(exc)
        )
    # 记录历史
    history_store.append_mcp_call(
        {
            "server": name,
            "tool": tool,
            "args": args,
            "is_error": result.is_error,
            "content": result.content,
            "error": result.error,
        }
    )
    return result


@router.get("/history")
async def get_mcp_history() -> list[dict]:
    """返回 MCP 调用历史（按时间倒序）。"""
    calls = history_store.get_mcp_calls()
    return list(reversed(calls))


@router.delete("/history")
async def clear_mcp_history() -> dict:
    history_store.clear_mcp_calls()
    return {"cleared": True}

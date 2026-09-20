"""MCP Streamable HTTP 客户端：封装 Python MCP SDK。

仅支持 Streamable HTTP 传输方式，提供 initialize / list_tools / call_tool 三个方法。
"""
from __future__ import annotations

from typing import Any

import httpx2

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from backend.app.schemas.mcp import McpCallResult, McpServer, McpServerInfo, McpTool


def _build_http_client(server: McpServer) -> httpx2.AsyncClient:
    """构造带 headers 的 httpx2.AsyncClient（供 MCP transport 使用）。"""
    return httpx2.AsyncClient(headers=server.headers or None)


async def initialize(server: McpServer) -> McpServerInfo:
    """与 MCP Server 执行 initialize 握手，返回 server 信息。

    Raises:
        Exception: 连接或握手失败时抛出，由调用方捕获。
    """
    async with _build_http_client(server) as http_client:
        async with streamable_http_client(server.url, http_client=http_client) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                info = session.server_info
                return McpServerInfo(
                    name=getattr(info, "name", "") or server.name,
                    version=getattr(info, "version", "") or "",
                    protocol_version=getattr(info, "protocolVersion", "") or "",
                )


async def test_connection(server: McpServer) -> tuple[bool, str, McpServerInfo | None]:
    """探测连通性，返回 (ok, message, info)。"""
    try:
        info = await initialize(server)
        return True, f"连接成功：{info.name}", info
    except Exception as exc:
        return False, f"无法连接：{exc}", None


async def list_tools(server: McpServer) -> list[McpTool]:
    """调用 tools/list，返回工具列表。"""
    async with _build_http_client(server) as http_client:
        async with streamable_http_client(server.url, http_client=http_client) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    McpTool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema or {},
                    )
                    for tool in result.tools
                ]


async def call_tool(server: McpServer, tool_name: str, args: dict[str, Any]) -> McpCallResult:
    """调用 tools/call，返回结果。"""
    async with _build_http_client(server) as http_client:
        async with streamable_http_client(server.url, http_client=http_client) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                content = []
                for item in result.content:
                    # 逐项转为可序列化 dict
                    if hasattr(item, "model_dump"):
                        content.append(item.model_dump(mode="json"))
                    else:
                        content.append({"type": "text", "text": str(item)})
                return McpCallResult(
                    server=server.name,
                    tool=tool_name,
                    is_error=bool(result.isError),
                    content=content,
                )


__all__ = ["initialize", "test_connection", "list_tools", "call_tool"]

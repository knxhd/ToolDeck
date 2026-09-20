"""MCP 客户端 Pydantic 模型。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class McpServer(BaseModel):
    """MCP Server 连接配置。"""
    name: str
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


class McpTool(BaseModel):
    """MCP 工具描述。"""
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class McpCallResult(BaseModel):
    """MCP 工具调用结果。"""
    server: str
    tool: str
    is_error: bool = False
    content: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class McpServerInfo(BaseModel):
    """MCP Server initialize 返回的握手信息。"""
    name: str
    version: str = ""
    protocol_version: str = ""


class McpTestResult(BaseModel):
    """连接测试结果。"""
    ok: bool
    message: str = ""
    server_info: McpServerInfo | None = None


__all__ = [
    "McpServer",
    "McpTool",
    "McpCallResult",
    "McpServerInfo",
    "McpTestResult",
]

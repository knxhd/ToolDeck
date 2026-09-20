"""MCP Server 配置存储：读写 config.json 的 mcp_servers 字段。"""
from __future__ import annotations

from typing import Any

from backend.app.config import load_config, save_config
from backend.app.schemas.mcp import McpServer


def list_servers() -> list[dict[str, Any]]:
    """返回所有 MCP Server 配置。"""
    return load_config().get("mcp_servers", [])


def get_server(name: str) -> dict[str, Any] | None:
    """按 name 查找单个 Server。"""
    for s in list_servers():
        if s.get("name") == name:
            return s
    return None


def add_server(server: McpServer) -> dict[str, Any]:
    """添加 Server，name 重复则抛 ValueError。"""
    if get_server(server.name) is not None:
        raise ValueError(f"MCP Server '{server.name}' 已存在")
    data = load_config()
    data.setdefault("mcp_servers", []).append(server.model_dump())
    save_config(data)
    return server.model_dump()


def update_server(name: str, server: McpServer) -> dict[str, Any]:
    """更新 Server 配置。"""
    data = load_config()
    servers = data.setdefault("mcp_servers", [])
    for i, s in enumerate(servers):
        if s.get("name") == name:
            servers[i] = server.model_dump()
            save_config(data)
            return server.model_dump()
    raise ValueError(f"MCP Server '{name}' 不存在")


def delete_server(name: str) -> dict[str, Any]:
    """删除 Server。"""
    data = load_config()
    servers = data.get("mcp_servers", [])
    new_servers = [s for s in servers if s.get("name") != name]
    if len(new_servers) == len(servers):
        raise ValueError(f"MCP Server '{name}' 不存在")
    data["mcp_servers"] = new_servers
    save_config(data)
    return {"deleted": name}


__all__ = [
    "list_servers",
    "get_server",
    "add_server",
    "update_server",
    "delete_server",
]

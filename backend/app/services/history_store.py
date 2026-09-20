"""历史持久化：读写 ~/.api-tool/history.json 的三个调用数组。

- http_calls: 最多 200 条
- mcp_calls: 最多 100 条
- llm_calls: 最多 100 条

按时间倒序淘汰最旧记录。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.config import load_history, save_history

MAX_HTTP_CALLS = 200
MAX_MCP_CALLS = 100
MAX_LLM_CALLS = 100


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def append_http_call(record: dict[str, Any]) -> None:
    """追加一条 HTTP 调用历史，自动加时间戳，超过上限淘汰最旧。"""
    data = load_history()
    record.setdefault("timestamp", _now())
    calls = data.setdefault("http_calls", [])
    calls.append(record)
    if len(calls) > MAX_HTTP_CALLS:
        data["http_calls"] = calls[-MAX_HTTP_CALLS:]
    save_history(data)


def append_mcp_call(record: dict[str, Any]) -> None:
    """追加一条 MCP 调用历史。"""
    data = load_history()
    record.setdefault("timestamp", _now())
    calls = data.setdefault("mcp_calls", [])
    calls.append(record)
    if len(calls) > MAX_MCP_CALLS:
        data["mcp_calls"] = calls[-MAX_MCP_CALLS:]
    save_history(data)


def append_llm_call(record: dict[str, Any]) -> None:
    """追加一条 LLM 调用历史。"""
    data = load_history()
    record.setdefault("timestamp", _now())
    calls = data.setdefault("llm_calls", [])
    calls.append(record)
    if len(calls) > MAX_LLM_CALLS:
        data["llm_calls"] = calls[-MAX_LLM_CALLS:]
    save_history(data)


def get_http_calls() -> list[dict[str, Any]]:
    return load_history().get("http_calls", [])


def get_mcp_calls() -> list[dict[str, Any]]:
    return load_history().get("mcp_calls", [])


def get_llm_calls() -> list[dict[str, Any]]:
    return load_history().get("llm_calls", [])


def clear_http_calls() -> None:
    data = load_history()
    data["http_calls"] = []
    save_history(data)


def clear_mcp_calls() -> None:
    data = load_history()
    data["mcp_calls"] = []
    save_history(data)


def clear_llm_calls() -> None:
    data = load_history()
    data["llm_calls"] = []
    save_history(data)


__all__ = [
    "append_http_call",
    "append_mcp_call",
    "append_llm_call",
    "get_http_calls",
    "get_mcp_calls",
    "get_llm_calls",
    "clear_http_calls",
    "clear_mcp_calls",
    "clear_llm_calls",
]

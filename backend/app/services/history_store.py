"""历史持久化：按用户读写 ~/.api-tool/users/<user>/history.json。

- http_calls: 最多 200 条
- mcp_calls: 最多 100 条
- llm_calls: 最多 100 条

按时间倒序淘汰最旧记录。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from backend.app.services.users import sanitize_username, user_history_path

MAX_HTTP_CALLS = 200
MAX_MCP_CALLS = 100
MAX_LLM_CALLS = 100

DEFAULT_HISTORY = {"http_calls": [], "mcp_calls": [], "llm_calls": []}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load(username: str) -> dict:
    u = sanitize_username(username)
    path = user_history_path(u)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_HISTORY, ensure_ascii=False), encoding="utf-8")
        return dict(DEFAULT_HISTORY)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(DEFAULT_HISTORY)


def _save(username: str, data: dict) -> None:
    u = sanitize_username(username)
    path = user_history_path(u)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def append_http_call(username: str, record: dict[str, Any]) -> None:
    data = _load(username)
    record.setdefault("timestamp", _now())
    calls = data.setdefault("http_calls", [])
    calls.append(record)
    if len(calls) > MAX_HTTP_CALLS:
        data["http_calls"] = calls[-MAX_HTTP_CALLS:]
    _save(username, data)


def append_mcp_call(username: str, record: dict[str, Any]) -> None:
    data = _load(username)
    record.setdefault("timestamp", _now())
    calls = data.setdefault("mcp_calls", [])
    calls.append(record)
    if len(calls) > MAX_MCP_CALLS:
        data["mcp_calls"] = calls[-MAX_MCP_CALLS:]
    _save(username, data)


def append_llm_call(username: str, record: dict[str, Any]) -> None:
    data = _load(username)
    record.setdefault("timestamp", _now())
    calls = data.setdefault("llm_calls", [])
    calls.append(record)
    if len(calls) > MAX_LLM_CALLS:
        data["llm_calls"] = calls[-MAX_LLM_CALLS:]
    _save(username, data)


def get_http_calls(username: str) -> list[dict[str, Any]]:
    return _load(username).get("http_calls", [])


def get_mcp_calls(username: str) -> list[dict[str, Any]]:
    return _load(username).get("mcp_calls", [])


def get_llm_calls(username: str) -> list[dict[str, Any]]:
    return _load(username).get("llm_calls", [])


def clear_http_calls(username: str) -> None:
    data = _load(username)
    data["http_calls"] = []
    _save(username, data)


def clear_mcp_calls(username: str) -> None:
    data = _load(username)
    data["mcp_calls"] = []
    _save(username, data)


def clear_llm_calls(username: str) -> None:
    data = _load(username)
    data["llm_calls"] = []
    _save(username, data)


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

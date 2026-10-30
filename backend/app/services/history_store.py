"""历史持久化：按 user_id 存 SQLite。"""
from __future__ import annotations

import json
from typing import Any

MAX_HTTP_CALLS = 200
MAX_MCP_CALLS = 100
MAX_LLM_CALLS = 100


def _trim(table: str, user_id: int, max_n: int) -> None:
    """超过上限时删除最旧记录。"""
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute(
            f"""DELETE FROM {table} WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM {table} WHERE user_id = ? ORDER BY id DESC LIMIT ?
                )""",
            (user_id, user_id, max_n),
        )


def append_http_call(user_id: int, record: dict[str, Any]) -> None:
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute(
            """INSERT INTO http_history
               (user_id, method, url, headers_json, body_type, body, status_code, elapsed_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                record.get("method", ""),
                record.get("url", ""),
                json.dumps(record.get("headers", []), ensure_ascii=False),
                record.get("body_type", "json"),
                record.get("body"),
                record.get("status_code"),
                record.get("elapsed_ms"),
            ),
        )
    _trim("http_history", user_id, MAX_HTTP_CALLS)


def append_mcp_call(user_id: int, record: dict[str, Any]) -> None:
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute(
            """INSERT INTO mcp_history
               (user_id, server, tool, args_json, is_error, content, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                record.get("server", ""),
                record.get("tool", ""),
                json.dumps(record.get("args", {}), ensure_ascii=False),
                1 if record.get("is_error") else 0,
                record.get("content"),
                record.get("error"),
            ),
        )
    _trim("mcp_history", user_id, MAX_MCP_CALLS)


def append_llm_call(user_id: int, record: dict[str, Any]) -> None:
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute(
            """INSERT INTO llm_history
               (user_id, provider, model, messages_json, content, finish_reason, usage_json, stream)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                record.get("provider", ""),
                record.get("model", ""),
                json.dumps(record.get("messages", []), ensure_ascii=False),
                record.get("content"),
                record.get("finish_reason"),
                json.dumps(record.get("usage", {}), ensure_ascii=False),
                1 if record.get("stream") else 0,
            ),
        )
    _trim("llm_history", user_id, MAX_LLM_CALLS)


def get_http_calls(user_id: int) -> list[dict[str, Any]]:
    from backend.app.services.db import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, method, url, headers_json, body_type, body, status_code, elapsed_ms,
                      created_at AS timestamp
               FROM http_history WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, MAX_HTTP_CALLS),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["headers"] = json.loads(d.pop("headers_json"))
        except Exception:
            d["headers"] = []
        out.append(d)
    return out


def get_mcp_calls(user_id: int) -> list[dict[str, Any]]:
    from backend.app.services.db import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, server, tool, args_json, is_error, content, error,
                      created_at AS timestamp
               FROM mcp_history WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, MAX_MCP_CALLS),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["args"] = json.loads(d.pop("args_json"))
        except Exception:
            d["args"] = {}
        d["is_error"] = bool(d["is_error"])
        out.append(d)
    return out


def get_llm_calls(user_id: int) -> list[dict[str, Any]]:
    from backend.app.services.db import get_db
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, provider, model, messages_json, content, finish_reason, usage_json,
                      stream, created_at AS timestamp
               FROM llm_history WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
            (user_id, MAX_LLM_CALLS),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["messages"] = json.loads(d.pop("messages_json"))
        except Exception:
            d["messages"] = []
        try:
            d["usage"] = json.loads(d.pop("usage_json"))
        except Exception:
            d["usage"] = {}
        d["stream"] = bool(d["stream"])
        out.append(d)
    return out


def clear_http_calls(user_id: int) -> None:
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM http_history WHERE user_id = ?", (user_id,))


def clear_mcp_calls(user_id: int) -> None:
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM mcp_history WHERE user_id = ?", (user_id,))


def clear_llm_calls(user_id: int) -> None:
    from backend.app.services.db import get_db
    with get_db() as conn:
        conn.execute("DELETE FROM llm_history WHERE user_id = ?", (user_id,))


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

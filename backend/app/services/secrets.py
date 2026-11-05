"""敏感值存储：用户级 key-value，内存缓存 + SQLite 持久化。"""
from __future__ import annotations

import threading
import uuid

from backend.app.services import db

# 内存缓存：{(user_id, name): value}，写时刷新
_cache: dict[tuple[int, str], str] = {}
_lock = threading.Lock()


def _ref(name: str) -> str:
    return f"__secret:{name}"


def _load_user(user_id: int) -> None:
    """从 DB 加载该用户的所有 secret 到缓存。"""
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT name, value FROM secrets WHERE user_id=?", (user_id,)
        ).fetchall()
    with _lock:
        for row in rows:
            _cache[(user_id, row["name"])] = row["value"]


def set_secret(user_id: int, name: str, value: str) -> str:
    """保存/更新一个敏感值，返回引用字符串。"""
    sid = uuid.uuid4().hex[:16]
    with db.get_db() as conn:
        conn.execute(
            """INSERT INTO secrets (id, user_id, name, value)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, name) DO UPDATE SET value=excluded.value, id=excluded.id""",
            (sid, user_id, name, value),
        )
    with _lock:
        _cache[(user_id, name)] = value
    return _ref(name)


def get_secret(user_id: int, name: str) -> str | None:
    key = (user_id, name)
    with _lock:
        if key in _cache:
            return _cache[key]
    # 缓存未命中，从 DB 加载
    _load_user(user_id)
    with _lock:
        return _cache.get(key)


def resolve_refs(user_id: int, text: str) -> str:
    """把 text 里的 __secret:<name> 替换为真实值。"""
    if not text or "__secret:" not in text:
        return text
    import re
    names = re.findall(r"__secret:([a-zA-Z0-9_]+)", text)
    if not names:
        return text
    # 确保缓存命中
    for name in names:
        val = get_secret(user_id, name)
        if val is not None:
            text = text.replace(_ref(name), val)
    return text


def delete_secret(user_id: int, name: str) -> None:
    with db.get_db() as conn:
        conn.execute("DELETE FROM secrets WHERE user_id=? AND name=?", (user_id, name))
    with _lock:
        _cache.pop((user_id, name), None)

"""用户数据分区：每个用户一个子目录 ~/.api-tool/users/<username>/。

- collections.json / history.json 都按用户隔离
- 用户名为空时拒绝访问（401）
"""
from __future__ import annotations

import re
from pathlib import Path

from backend.app.config import CONFIG_DIR

USERS_DIR = CONFIG_DIR / "users"

# 用户名只允许字母数字下划线短横点，1-32 字符，避免路径穿越
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")


def sanitize_username(username: str | None) -> str:
    """校验并返回合法用户名；非法抛 ValueError。"""
    if not username:
        raise ValueError("缺少 X-User 请求头")
    u = username.strip()
    if not _USERNAME_RE.match(u):
        raise ValueError("用户名只能包含字母数字下划线短横点，长度 1-32")
    return u


def user_dir(username: str) -> Path:
    """返回该用户的数据目录，不存在则创建。"""
    u = sanitize_username(username)
    d = USERS_DIR / u
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_collections_path(username: str) -> Path:
    return user_dir(username) / "collections.json"


def user_history_path(username: str) -> Path:
    return user_dir(username) / "history.json"


def user_exists(username: str) -> bool:
    """该用户是否已有数据（collections.json 存在且非空，或历史文件存在）。"""
    u = sanitize_username(username)
    c = user_collections_path(u)
    h = user_history_path(u)
    if c.exists():
        try:
            import json
            data = json.loads(c.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                return True
        except Exception:
            pass
    return h.exists() and h.stat().st_size > 10


__all__ = [
    "USERS_DIR",
    "sanitize_username",
    "user_dir",
    "user_collections_path",
    "user_history_path",
    "user_exists",
]

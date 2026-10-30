"""认证：密码哈希、token 签发与校验、用户注册/登录。"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from backend.app.services.db import get_db

# 密码强度：至少 10 位，包含字母、数字、特殊字符
_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}$")
_TOKEN_TTL = timedelta(days=30)


def validate_password(pw: str) -> Optional[str]:
    """返回 None 表示通过，否则返回错误提示。"""
    if len(pw) < 10:
        return "密码至少 10 位"
    if not _PASSWORD_RE.match(pw):
        return "密码必须同时包含字母、数字和特殊字符"
    return None


def _hash_password(pw: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + dk.hex()


def _verify_password(pw: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 200_000)
        return secrets.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def create_user(username: str, password: str, display_name: str) -> int:
    """创建用户，返回 user_id。用户名已存在抛 ValueError。"""
    username = username.strip()
    if not re.match(r"^[A-Za-z0-9_.-]{1,32}$", username):
        raise ValueError("用户名只能包含字母数字下划线短横点，长度 1-32")
    err = validate_password(password)
    if err:
        raise ValueError(err)
    salt = os.urandom(16)
    pw_hash = _hash_password(password, salt)
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username, pw_hash, display_name or username),
            )
        except Exception as e:
            if "UNIQUE" in str(e):
                raise ValueError("用户名已被注册")
            raise
        uid = cur.lastrowid
        # 初始化空集合行（个人空间）
        conn.execute("INSERT INTO collections (user_id, team_id, tree_json) VALUES (?, NULL, '[]')", (uid,))
        return uid


def verify_login(username: str, password: str) -> Optional[dict]:
    """校验登录，返回 {id, username, display_name} 或 None。"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, display_name FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if not row:
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}


def issue_token(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = (datetime.now() + _TOKEN_TTL).isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires),
        )
    return token


def resolve_token(token: str) -> Optional[dict]:
    """根据 token 返回 {id, username, display_name}，无效或过期返回 None。"""
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            """SELECT u.id, u.username, u.display_name
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > datetime('now')""",
            (token,),
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}


def revoke_token(token: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, display_name FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}


__all__ = [
    "validate_password",
    "create_user",
    "verify_login",
    "issue_token",
    "resolve_token",
    "revoke_token",
    "get_user_by_id",
]

"""团队服务：创建团队、成员管理、权限校验。"""
from __future__ import annotations

import re
from typing import Optional

from backend.app.services.db import get_db


_TEAM_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\u4e00-\u9fa5 ]{2,32}$")


def create_team(name: str, owner_id: int) -> int:
    name = name.strip()
    if not _TEAM_NAME_RE.match(name):
        raise ValueError("团队名 2-32 位，支持中英文、数字、下划线、短横")
    with get_db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO teams (name, owner_id) VALUES (?, ?)", (name, owner_id)
            )
        except Exception as e:
            if "UNIQUE" in str(e):
                raise ValueError("团队名已被占用")
            raise
        team_id = cur.lastrowid
        # 创建者自动成为 admin
        conn.execute(
            "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'admin')",
            (team_id, owner_id),
        )
        # 初始化团队空集合
        conn.execute(
            "INSERT INTO collections (user_id, team_id, tree_json) VALUES (NULL, ?, '[]')",
            (team_id,),
        )
        return team_id


def list_my_teams(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT t.id, t.name, t.owner_id, tm.role
               FROM teams t JOIN team_members tm ON tm.team_id = t.id
               WHERE tm.user_id = ? ORDER BY t.name""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def is_member(team_id: int, user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        ).fetchone()
    return row is not None


def is_admin(team_id: int, user_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ? AND role = 'admin'",
            (team_id, user_id),
        ).fetchone()
    return row is not None


def list_members(team_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT u.id, u.username, u.display_name, tm.role
               FROM team_members tm JOIN users u ON u.id = tm.user_id
               WHERE tm.team_id = ? ORDER BY tm.role DESC, u.username""",
            (team_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_member(team_id: int, admin_id: int, username: str) -> dict:
    """管理员邀请用户加入团队，按用户名查找。"""
    if not is_admin(team_id, admin_id):
        raise PermissionError("仅管理员可邀请成员")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, display_name FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
        if not row:
            raise ValueError("用户不存在")
        if is_member(team_id, row["id"]):
            raise ValueError("该用户已在团队中")
        conn.execute(
            "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'member')",
            (team_id, row["id"]),
        )
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "role": "member"}


def remove_member(team_id: int, admin_id: int, user_id: int) -> None:
    if not is_admin(team_id, admin_id):
        raise PermissionError("仅管理员可移除成员")
    if user_id == admin_id:
        raise ValueError("不能移除自己（请先转让团队或解散）")
    with get_db() as conn:
        conn.execute(
            "DELETE FROM team_members WHERE team_id = ? AND user_id = ?",
            (team_id, user_id),
        )


def get_team(team_id: int) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, owner_id FROM teams WHERE id = ?", (team_id,)
        ).fetchone()
    return dict(row) if row else None


__all__ = [
    "create_team",
    "list_my_teams",
    "is_member",
    "is_admin",
    "list_members",
    "add_member",
    "remove_member",
    "get_team",
]

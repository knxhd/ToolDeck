"""Collections 持久化：个人空间按 user_id，团队空间按 team_id。"""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.services.db import get_db


def load_collections(scope: str, scope_id: int) -> list[dict[str, Any]]:
    """scope: 'user' 或 'team'。"""
    col = "user_id" if scope == "user" else "team_id"
    with get_db() as conn:
        row = conn.execute(
            f"SELECT tree_json FROM collections WHERE {col} = ?", (scope_id,)
        ).fetchone()
    if not row:
        return []
    try:
        data = json.loads(row["tree_json"])
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_collections(scope: str, scope_id: int, tree: list[dict[str, Any]]) -> None:
    payload = json.dumps(tree, ensure_ascii=False)
    col = "user_id" if scope == "user" else "team_id"
    with get_db() as conn:
        cur = conn.execute(
            f"UPDATE collections SET tree_json = ?, updated_at = datetime('now') WHERE {col} = ?",
            (payload, scope_id),
        )
        if cur.rowcount == 0:
            other = "team_id" if scope == "user" else "user_id"
            conn.execute(
                f"INSERT INTO collections ({col}, {other}, tree_json) VALUES (?, NULL, ?)",
                (scope_id, payload),
            )


def find_node(tree: list[dict[str, Any]], node_id: str) -> Optional[dict[str, Any]]:
    for node in tree:
        if node.get("id") == node_id:
            return node
        children = node.get("children")
        if isinstance(children, list):
            found = find_node(children, node_id)
            if found is not None:
                return found
    return None


def delete_node(tree: list[dict[str, Any]], node_id: str) -> bool:
    for i, node in enumerate(tree):
        if node.get("id") == node_id:
            tree.pop(i)
            return True
        children = node.get("children")
        if isinstance(children, list) and delete_node(children, node_id):
            return True
    return False


__all__ = [
    "load_collections",
    "save_collections",
    "find_node",
    "delete_node",
]

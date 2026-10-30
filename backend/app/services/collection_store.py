"""Collections 持久化：按 user_id 存 SQLite。"""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.services.db import get_db


def load_collections(user_id: int) -> list[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT tree_json FROM collections WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return []
    try:
        data = json.loads(row["tree_json"])
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_collections(user_id: int, tree: list[dict[str, Any]]) -> None:
    payload = json.dumps(tree, ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO collections (user_id, tree_json, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET tree_json = excluded.tree_json, updated_at = excluded.updated_at""",
            (user_id, payload),
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

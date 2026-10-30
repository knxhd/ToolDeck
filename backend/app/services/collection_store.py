"""Collections 持久化：按用户读写 ~/.api-tool/users/<user>/collections.json。

树节点类型：
- collection：根集合
- folder：子集合
- request：请求（kind=http | websocket）

整棵树由前端持有并整体回写；这里只负责存取。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.services.users import sanitize_username, user_collections_path


def _ensure(path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")


def load_collections(username: str) -> list[dict[str, Any]]:
    u = sanitize_username(username)
    path = user_collections_path(u)
    _ensure(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_collections(username: str, tree: list[dict[str, Any]]) -> None:
    u = sanitize_username(username)
    path = user_collections_path(u)
    _ensure(path)
    path.write_text(
        json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def find_node(tree: list[dict[str, Any]], node_id: str) -> Optional[dict[str, Any]]:
    """在树中按 id 查找节点（深度优先）。"""
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
    """从树中删除指定节点，返回是否删除成功。"""
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

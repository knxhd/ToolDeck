"""Collections 持久化：读写 ~/.api-tool/collections.json 的节点树。

树节点类型：
- collection：根集合
- folder：子集合
- request：请求（kind=http | websocket）

整棵树由前端持有并整体回写；这里只负责存取与按 id 查找/删除。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from backend.app.config import CONFIG_DIR, init_config_dir

COLLECTIONS_PATH = CONFIG_DIR / "collections.json"


def _ensure() -> None:
    init_config_dir()
    if not COLLECTIONS_PATH.exists():
        COLLECTIONS_PATH.write_text("[]", encoding="utf-8")


def load_collections() -> list[dict[str, Any]]:
    _ensure()
    try:
        data = json.loads(COLLECTIONS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_collections(tree: list[dict[str, Any]]) -> None:
    _ensure()
    COLLECTIONS_PATH.write_text(
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
    "COLLECTIONS_PATH",
    "load_collections",
    "save_collections",
    "find_node",
    "delete_node",
]

"""Collections 持久化：个人空间按 user_id，团队空间按 team_id。

敏感字段（请求节点里的 headers / mcp_headers，可能含 api-key、Authorization 等）落盘前加密，
读取后解密，避免直接 cat SQLite 泄露明文。加密复用 crypto（Windows DPAPI / 非 Win Fernet）。
"""
from __future__ import annotations

import copy
import json
from typing import Any, Optional

from backend.app.services import crypto
from backend.app.services.db import get_db


def _encrypt_headers(headers: Any) -> Any:
    """把请求头整体加密为一个密文字符串；已加密（幂等）或为空时原样返回。"""
    if isinstance(headers, str) and crypto.is_encrypted(headers):
        return headers  # 已是密文，避免二次加密
    if isinstance(headers, (list, dict)) and headers:
        return crypto.encrypt(json.dumps(headers, ensure_ascii=False))
    return headers


def _decrypt_headers(headers: Any) -> Any:
    """把加密的请求头还原为原始结构；非密文（历史明文/空）原样返回，兼容迁移。"""
    if isinstance(headers, str) and crypto.is_encrypted(headers):
        try:
            return json.loads(crypto.decrypt(headers))
        except Exception:
            return headers
    return headers


def _walk(tree: list[dict[str, Any]], fn) -> None:
    """递归遍历树节点，对每个节点执行 fn。"""
    for node in tree:
        if isinstance(node, dict):
            fn(node)
            children = node.get("children")
            if isinstance(children, list):
                _walk(children, fn)


def _encrypt_node(node: dict[str, Any]) -> None:
    req = node.get("request")
    if isinstance(req, dict) and "headers" in req:
        req["headers"] = _encrypt_headers(req["headers"])
    if "mcp_headers" in node:
        node["mcp_headers"] = _encrypt_headers(node["mcp_headers"])


def _decrypt_node(node: dict[str, Any]) -> None:
    req = node.get("request")
    if isinstance(req, dict) and "headers" in req:
        req["headers"] = _decrypt_headers(req["headers"])
    if "mcp_headers" in node:
        node["mcp_headers"] = _decrypt_headers(node["mcp_headers"])


def _encrypt_tree(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    work = copy.deepcopy(tree)
    _walk(work, _encrypt_node)
    return work


def _decrypt_tree(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    work = copy.deepcopy(tree)
    _walk(work, _decrypt_node)
    return work


def load_collections(scope: str, scope_id: int) -> list[dict[str, Any]]:
    """scope: 'user' 或 'team'。返回的请求头已解密为明文结构。"""
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
    if not isinstance(data, list):
        return []
    return _decrypt_tree(data)


def save_collections(scope: str, scope_id: int, tree: list[dict[str, Any]]) -> None:
    """保存前加密请求头；传入的 tree 不被原地修改（内部深拷贝）。"""
    payload = json.dumps(_encrypt_tree(tree), ensure_ascii=False)
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


def migrate_collections_secrets() -> None:
    """把 collections 表中仍是明文的请求头原地迁移为密文（幂等，可在启动时调用）。"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, user_id, team_id, tree_json FROM collections"
        ).fetchall()
        for row in rows:
            try:
                data = json.loads(row["tree_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(data, list):
                continue
            enc = _encrypt_tree(data)
            if enc != data:
                conn.execute(
                    "UPDATE collections SET tree_json = ? WHERE id = ?",
                    (json.dumps(enc, ensure_ascii=False), row["id"]),
                )


__all__ = [
    "load_collections",
    "save_collections",
    "find_node",
    "delete_node",
    "migrate_collections_secrets",
]

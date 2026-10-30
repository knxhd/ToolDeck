"""Collections 树 CRUD：整棵树由前端持有并整体回写。

- GET  /api/collections        返回当前用户的节点树
- PUT  /api/collections        整体替换节点树
"""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from backend.app.services import collection_store, users

router = APIRouter()


def _user(x_user: str | None) -> str:
    try:
        return users.sanitize_username(x_user)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("")
async def get_collections(x_user: str | None = Header(default=None)) -> list[dict]:
    return collection_store.load_collections(_user(x_user))


@router.put("")
async def put_collections(tree: list[dict], x_user: str | None = Header(default=None)) -> dict:
    collection_store.save_collections(_user(x_user), tree)
    return {"saved": True, "count": len(tree)}

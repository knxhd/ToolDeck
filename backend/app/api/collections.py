"""Collections 树 CRUD：整棵树由前端持有并整体回写。

- GET  /api/collections        返回节点树
- PUT  /api/collections        整体替换节点树
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.services import collection_store

router = APIRouter()


@router.get("")
async def get_collections() -> list[dict]:
    return collection_store.load_collections()


@router.put("")
async def put_collections(tree: list[dict]) -> dict:
    collection_store.save_collections(tree)
    return {"saved": True, "count": len(tree)}

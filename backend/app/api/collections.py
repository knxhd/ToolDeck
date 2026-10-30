"""Collections 树 CRUD：整棵树由前端持有并整体回写。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.auth import current_user
from backend.app.services import collection_store

router = APIRouter()


@router.get("")
async def get_collections(user: dict = Depends(current_user)) -> list[dict]:
    return collection_store.load_collections(user["id"])


@router.put("")
async def put_collections(tree: list[dict], user: dict = Depends(current_user)) -> dict:
    collection_store.save_collections(user["id"], tree)
    return {"saved": True, "count": len(tree)}

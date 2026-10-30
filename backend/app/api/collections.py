"""Collections 树 CRUD：个人空间 + 团队空间。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.auth import current_user
from backend.app.services import collection_store, teams

router = APIRouter()


def _resolve_scope(user: dict, scope: str, team_id: int | None) -> tuple[str, int]:
    """返回 (scope, scope_id)。校验团队成员身份。"""
    if scope == "personal":
        return "user", user["id"]
    if scope == "team":
        if team_id is None:
            raise HTTPException(status_code=400, detail="缺少 team_id")
        if not teams.is_member(team_id, user["id"]):
            raise HTTPException(status_code=403, detail="不是该团队成员")
        return "team", team_id
    raise HTTPException(status_code=400, detail="scope 必须是 personal 或 team")


@router.get("")
async def get_collections(
    user: dict = Depends(current_user),
    scope: str = Query(default="personal"),
    team_id: int | None = Query(default=None),
) -> list[dict]:
    s, sid = _resolve_scope(user, scope, team_id)
    return collection_store.load_collections(s, sid)


@router.put("")
async def put_collections(
    tree: list[dict],
    user: dict = Depends(current_user),
    scope: str = Query(default="personal"),
    team_id: int | None = Query(default=None),
) -> dict:
    s, sid = _resolve_scope(user, scope, team_id)
    collection_store.save_collections(s, sid, tree)
    return {"saved": True, "count": len(tree)}

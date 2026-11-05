"""Collections 树 CRUD：个人空间 + 团队空间。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from backend.app.api.auth import current_user
from backend.app.services import collection_store, postman_io, teams

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


@router.get("/export")
async def export_postman(
    user: dict = Depends(current_user),
    scope: str = Query(default="personal"),
    team_id: int | None = Query(default=None),
    collection_name: str = Query(default="api-tool"),
) -> Response:
    s, sid = _resolve_scope(user, scope, team_id)
    tree = collection_store.load_collections(s, sid)
    payload = postman_io.export_collection(tree, collection_name)
    import json
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="postman-collection-{collection_name}.json"'},
    )


@router.post("/import")
async def import_postman(
    payload: dict,
    user: dict = Depends(current_user),
    scope: str = Query(default="personal"),
    team_id: int | None = Query(default=None),
) -> dict:
    s, sid = _resolve_scope(user, scope, team_id)
    name, tree = postman_io.import_collection(payload)
    # 合并到现有树：作为一个新的顶级 folder 追加
    existing = collection_store.load_collections(s, sid)
    wrapper = {
        "id": f"n_{__import__('uuid').uuid4().hex[:12]}",
        "type": "folder",
        "name": name,
        "children": tree,
    }
    existing.append(wrapper)
    collection_store.save_collections(s, sid, existing)
    return {"imported": True, "name": name, "count": len(tree)}

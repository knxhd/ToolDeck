"""团队路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.auth import current_user
from backend.app.services import teams

router = APIRouter()


class CreateTeamBody(BaseModel):
    name: str


class InviteBody(BaseModel):
    username: str


class RenameTeamBody(BaseModel):
    name: str


@router.get("")
async def list_teams(user: dict = Depends(current_user)) -> list[dict]:
    return teams.list_my_teams(user["id"])


@router.post("")
async def create_team(body: CreateTeamBody, user: dict = Depends(current_user)) -> dict:
    try:
        tid = teams.create_team(body.name, user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": tid, "name": body.name.strip(), "owner_id": user["id"], "role": "admin"}


@router.put("/{team_id}")
async def rename_team(team_id: int, body: RenameTeamBody, user: dict = Depends(current_user)) -> dict:
    try:
        return teams.rename_team(team_id, user["id"], body.name)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}")
async def delete_team(team_id: int, user: dict = Depends(current_user)) -> dict:
    try:
        teams.delete_team(team_id, user["id"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": True}


@router.post("/{team_id}/leave")
async def leave_team(team_id: int, user: dict = Depends(current_user)) -> dict:
    try:
        teams.leave_team(team_id, user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"left": True}


@router.get("/{team_id}/members")
async def list_members(team_id: int, user: dict = Depends(current_user)) -> list[dict]:
    if not teams.is_member(team_id, user["id"]):
        raise HTTPException(status_code=403, detail="不是该团队成员")
    return teams.list_members(team_id)


@router.post("/{team_id}/members")
async def invite(team_id: int, body: InviteBody, user: dict = Depends(current_user)) -> dict:
    try:
        return teams.add_member(team_id, user["id"], body.username)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(team_id: int, user_id: int, user: dict = Depends(current_user)) -> dict:
    try:
        teams.remove_member(team_id, user["id"], user_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"removed": True}

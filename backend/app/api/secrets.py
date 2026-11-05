"""敏感值 API：保存/获取/删除用户级 secret。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.auth import current_user
from backend.app.services import secrets

router = APIRouter()


class SecretBody(BaseModel):
    name: str
    value: str


@router.post("")
async def set_secret(body: SecretBody, user: dict = Depends(current_user)) -> dict:
    ref = secrets.set_secret(user["id"], body.name, body.value)
    return {"ref": ref}


@router.get("/{name}")
async def get_secret(name: str, user: dict = Depends(current_user)) -> dict:
    val = secrets.get_secret(user["id"], name)
    if val is None:
        raise HTTPException(status_code=404, detail="不存在")
    return {"value": val}


@router.delete("/{name}")
async def delete_secret(name: str, user: dict = Depends(current_user)) -> dict:
    secrets.delete_secret(user["id"], name)
    return {"deleted": True}

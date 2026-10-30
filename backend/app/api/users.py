"""用户相关 API：检查用户名是否已存在数据。

- POST /api/user/check   body: {"username": "xxx"}  ->  {"exists": true/false}
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services import users

router = APIRouter()


class CheckBody(BaseModel):
    username: str


@router.post("/check")
async def check_user(body: CheckBody) -> dict:
    try:
        u = users.sanitize_username(body.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"exists": users.user_exists(u), "username": u}

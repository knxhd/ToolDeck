"""认证路由：注册、登录、当前用户、登出。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.app.services import auth, db

router = APIRouter()


class RegisterBody(BaseModel):
    username: str
    password: str
    display_name: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


async def current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI 依赖：从 Authorization: Bearer <token> 解析当前用户。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.split(" ", 1)[1].strip()
    user = auth.resolve_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user


@router.post("/register")
async def register(body: RegisterBody) -> dict:
    try:
        uid = auth.create_user(body.username, body.password, body.display_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 自动登录
    token = auth.issue_token(uid)
    return {"token": token, "user": auth.get_user_by_id(uid)}


@router.post("/login")
async def login(body: LoginBody) -> dict:
    user = auth.verify_login(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = auth.issue_token(user["id"])
    return {"token": token, "user": user}


@router.get("/me")
async def me(user: dict = Depends(current_user)) -> dict:
    return {"user": user}


@router.post("/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        auth.revoke_token(token)
    return {"ok": True}


__all__ = ["router", "current_user"]

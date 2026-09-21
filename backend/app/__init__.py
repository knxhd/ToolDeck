"""应用外壳：构造 FastAPI 实例，协调 CORS、路由注册、静态资源托管。"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.config import init_config_dir
from backend.app.resources import resolve_static_path


def get_env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def is_dev() -> bool:
    return get_env("APP_ENV", "production") == "development"


def create_app() -> FastAPI:
    """构造 FastAPI 实例：CORS（仅 dev）、API 路由、静态资源托管（仅 prod）。"""
    init_config_dir()
    app = FastAPI(title="API Tool", version="0.1.0")

    if is_dev():
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok", "env": get_env("APP_ENV", "production")})

    # 注册各业务路由
    from backend.app.api import http as http_api
    from backend.app.api import llm as llm_api
    from backend.app.api import mcp as mcp_api

    app.include_router(http_api.router, prefix="/api/http")
    app.include_router(mcp_api.router, prefix="/api/mcp")
    app.include_router(llm_api.router, prefix="/api/llm")

    # 生产模式托管前端静态资源 + SPA fallback
    if not is_dev():
        static_dir = resolve_static_path()
        if static_dir.exists():
            app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

            index_file = static_dir / "index.html"

            @app.get("/{full_path:path}", response_model=None)
            async def spa_fallback(full_path: str) -> HTMLResponse | JSONResponse:
                # 非 API/SSE 路径返回 index.html，交给前端路由
                if full_path.startswith(("api/", "sse/")):
                    return JSONResponse({"detail": "Not Found"}, status_code=404)
                if index_file.exists():
                    return HTMLResponse(index_file.read_text(encoding="utf-8"))
                return JSONResponse({"detail": "frontend not built"}, status_code=500)

    return app

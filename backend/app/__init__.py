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

    # 初始化 SQLite
    from backend.app.services.db import init_db
    init_db()

    # 迁移历史明文敏感数据为密文（幂等；新建库无影响）
    try:
        from backend.app.config import migrate_config_secrets
        from backend.app.services import collection_store, history_store

        migrate_config_secrets()
        history_store.migrate_history_secrets()
        collection_store.migrate_collections_secrets()
    except Exception:  # noqa: BLE001 —— 迁移失败不应阻断启动，后续写入仍会加密
        import logging

        logging.getLogger("api-tool").exception("敏感数据迁移失败，忽略（新写入仍会加密）")

    app = FastAPI(title="API Tool", version="0.2.0")

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
    from backend.app.api import auth as auth_api
    from backend.app.api import collections as collections_api
    from backend.app.api import files as files_api
    from backend.app.api import http as http_api
    from backend.app.api import llm as llm_api
    from backend.app.api import mcp as mcp_api
    from backend.app.api import teams as teams_api

    app.include_router(auth_api.router, prefix="/api/auth")
    app.include_router(collections_api.router, prefix="/api/collections")
    app.include_router(files_api.router, prefix="/api/files")
    app.include_router(http_api.router, prefix="/api/http")
    app.include_router(mcp_api.router, prefix="/api/mcp")
    app.include_router(llm_api.router, prefix="/api/llm")
    app.include_router(teams_api.router, prefix="/api/teams")

    # 生产模式托管前端静态资源 + SPA fallback
    if not is_dev():
        static_dir = resolve_static_path()
        if static_dir.exists():
            app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

            # favicon / 根目录静态文件
            @app.get("/favicon.svg", include_in_schema=False)
            async def favicon() -> HTMLResponse:
                f = static_dir / "favicon.svg"
                return HTMLResponse(
                    content=f.read_bytes(),
                    media_type="image/svg+xml",
                ) if f.exists() else HTMLResponse(status_code=404)

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

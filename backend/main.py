"""应用入口：解析 APP_ENV，构造 FastAPI，启动 uvicorn 并打开浏览器。

开发模式：APP_ENV=development uvicorn backend.main:app --reload --port 8765
生产模式：直接 python backend/main.py（自动选端口 + 打开浏览器）
"""
from __future__ import annotations

import os

import uvicorn
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import create_app
from backend.app.launcher import open_browser_after_delay
from backend.app.port import find_available_port


def main() -> None:
    env = os.environ.get("APP_ENV", "production")
    host = os.environ.get("APP_HOST", "127.0.0.1")

    if env == "production":
        # 生产模式：自动探测端口并打开浏览器
        port = find_available_port(
            int(os.environ.get("APP_PORT", "8765")),
            int(os.environ.get("APP_PORT", "8765")) + 10,
        )
        open_browser_after_delay(f"http://{host}:{port}")
    else:
        port = int(os.environ.get("APP_PORT", "8765"))

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


# FastAPI 实例供 uvicorn import 使用
app = create_app()


if __name__ == "__main__":
    main()

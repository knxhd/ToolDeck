"""静态资源路径解析：开发期使用 frontend/dist，PyInstaller 打包后使用 _MEIPASS。"""
from __future__ import annotations

import sys
from pathlib import Path


def resolve_static_path() -> Path:
    """返回前端静态资源目录。

    - PyInstaller onefile 模式：资源解压到 sys._MEIPASS/frontend/dist
    - 开发/普通运行：项目根目录下的 frontend/dist
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "frontend" / "dist"
    # backend/app/resources.py -> 项目根目录
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


__all__ = ["resolve_static_path"]

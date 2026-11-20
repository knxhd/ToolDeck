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


def resolve_asset_path(name: str) -> Path | None:
    """返回随包分发的图片等资源文件路径，找不到返回 None。

    - PyInstaller 打包后：sys._MEIPASS/assets/<name>
    - 开发/普通运行：项目根 image/ 或 backend/build/ 下查找

    托盘版 exe 以 assets/tray.ico 是否存在作为「本次构建带托盘」的标记，
    非托盘构建不会打进该文件，因此运行时天然降级为无托盘。
    """
    for directory in _asset_dirs():
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def _asset_dirs() -> list[Path]:
    if hasattr(sys, "_MEIPASS"):
        return [Path(sys._MEIPASS) / "assets"]
    root = Path(__file__).resolve().parents[2]
    return [root / "image", root / "backend" / "build"]


__all__ = ["resolve_static_path", "resolve_asset_path"]

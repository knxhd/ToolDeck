"""文件相关路由（Form Data 文件上传字段使用）。

- POST /api/files/pick                  弹出本机原生「选择文件」对话框，返回真实文件路径
- POST /api/files/upload?filename=xxx   兜底：浏览器选择文件后上传副本到数据目录，返回副本路径

工具运行在本机时优先使用原生对话框，Form Data 中保存的就是文件的原始路径；
Docker / 无桌面环境下原生对话框不可用（返回 501），前端改走上传副本。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool

from backend.app.config import CONFIG_DIR

router = APIRouter()

UPLOAD_DIR = CONFIG_DIR / "files"

# 同一时间只允许弹出一个对话框
_pick_lock = threading.Lock()


class PickerUnavailable(RuntimeError):
    """当前环境没有可用的原生文件对话框。"""


def _pick_macos() -> str | None:
    script = 'POSIX path of (choose file with prompt "选择要上传的文件")'
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if proc.returncode != 0:
        # 用户取消时 osascript 返回非 0（-128）
        if "-128" in proc.stderr:
            return None
        raise PickerUnavailable(proc.stderr.strip() or "osascript 执行失败")
    return proc.stdout.strip() or None


def _pick_tk() -> str | None:
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        raise PickerUnavailable("无桌面环境")
    try:
        import tkinter
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001
        raise PickerUnavailable(f"tkinter 不可用：{exc}") from exc

    try:
        root = tkinter.Tk()
    except Exception as exc:  # noqa: BLE001
        raise PickerUnavailable(f"无法创建对话框：{exc}") from exc
    try:
        root.withdraw()
        # 置顶，避免对话框被浏览器窗口遮挡
        root.attributes("-topmost", True)
        root.update()
        path = filedialog.askopenfilename(parent=root, title="选择要上传的文件")
    finally:
        root.destroy()
    return os.path.normpath(path) if path else None


def _native_pick() -> str | None:
    if not _pick_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="已有文件选择对话框打开")
    try:
        if sys.platform == "darwin":
            return _pick_macos()
        return _pick_tk()
    finally:
        _pick_lock.release()


@router.post("/pick")
async def pick_file(request: Request) -> dict:
    """弹出本机文件选择对话框；取消时 path 为 null，环境不支持时返回 501。"""
    # 非本机访问（如局域网其它电脑打开页面）时，对话框会弹在服务端桌面上，改走上传副本
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=501, detail="非本机访问，不支持原生文件对话框")
    try:
        path = await run_in_threadpool(_native_pick)
    except PickerUnavailable as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return {"path": path}


def _safe_name(filename: str) -> str:
    name = Path(filename).name or "file"
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name)


@router.post("/upload")
async def upload_file(request: Request, filename: str = Query(..., min_length=1)) -> dict:
    """请求体为文件原始字节；保存到 <数据目录>/files/ 下并返回绝对路径。"""
    data = await request.body()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / f"{time.strftime('%Y%m%d%H%M%S')}_{_safe_name(filename)}"
    target.write_bytes(data)
    return {"path": str(target.resolve()), "size": len(data)}


__all__ = ["router"]

"""Windows 系统托盘（可选，仅打包时显式启用）。

设计原则：默认行为与旧版完全一致（headless，无托盘）。
只有同时满足下面三条才会走托盘路径：

1. 运行平台是 Windows；
2. exe 是带托盘构建的（PyInstaller 把 assets/tray.ico 打进了包，这里用它当构建标记）；
3. 启动参数没有显式 `--no-tray`。

非 Windows 平台（Linux/Docker/macOS）不会 import pystray，
构建时也会把 pystray/PIL 排除在外，完全不增加体积。
"""
from __future__ import annotations

import ctypes
import os
import sys
import threading
import webbrowser
from pathlib import Path

TRAY_ICON_NAME = "tray.ico"


def tray_icon_path() -> Path | None:
    from backend.app.resources import resolve_asset_path

    return resolve_asset_path(TRAY_ICON_NAME)


def tray_build_enabled() -> bool:
    """本次构建是否带托盘：只有打包后的 Windows exe 才会自动启用托盘。

    开发态（python backend/main.py）默认不启用，保持与原 headless 行为一致；
    调试托盘可显式加 --tray（此时用 tray_runtime_available 判断）。
    """
    if not getattr(sys, "frozen", False):
        return False
    return tray_runtime_available()


def tray_runtime_status() -> tuple[bool, str]:
    """返回 (是否可用, 原因说明)，原因写进 server.log 便于排查托盘不出现的问题。"""
    if sys.platform != "win32":
        return False, f"平台不是 Windows（platform={sys.platform}）"
    try:
        import pystray  # noqa: F401
    except Exception as exc:
        return False, f"pystray 导入失败：{exc!r}"
    icon = tray_icon_path()
    if icon is None:
        return False, "未找到托盘图标 assets/tray.ico（本次不是带托盘的构建）"
    return True, f"图标 {icon}"


def tray_runtime_available() -> bool:
    """当前环境是否具备托盘运行条件（Windows + pystray + 图标文件）。"""
    return tray_runtime_status()[0]


def copy_to_clipboard(text: str) -> bool:
    """把文本写入 Windows 剪贴板（不依赖 pywin32）。"""
    if sys.platform != "win32":
        return False
    try:
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p

        payload = text.encode("utf-16-le") + b"\x00\x00"
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
        if not handle:
            return False
        locked = kernel32.GlobalLock(handle)
        if not locked:
            return False
        ctypes.memmove(locked, payload, len(payload))
        kernel32.GlobalUnlock(handle)

        if not user32.OpenClipboard(None):
            return False
        try:
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_UNICODETEXT, handle)
        finally:
            user32.CloseClipboard()
        return True
    except Exception:
        return False


def serve_with_tray(
    app,
    *,
    host: str,
    port: int,
    url: str,
    open_browser: bool = True,
    log_path: Path | None = None,
) -> None:
    """后台线程跑 uvicorn，主线程跑托盘图标；退出菜单会优雅关闭服务。"""
    import pystray
    from PIL import Image

    import uvicorn

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        log_config=None,
        access_log=True,
    )
    server = uvicorn.Server(config)

    server_thread = threading.Thread(target=server.run, name="tooldeck-server")
    server_thread.start()

    icon_path = tray_icon_path()
    image = Image.open(icon_path)
    image = image.resize((64, 64))

    def open_ui(*_args) -> None:
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            pass

    def copy_url(icon, _item) -> None:
        ok = copy_to_clipboard(url)
        if ok:
            notify(icon, "地址已复制到剪贴板")
        else:
            notify(icon, "复制失败，请手动访问 " + url)

    def notify(icon, message: str) -> None:
        try:
            icon.notify(message, "ToolDeck")
        except Exception:
            pass

    def open_log(icon=None, _item=None) -> None:
        if log_path and Path(log_path).exists():
            try:
                os.startfile(str(log_path))  # 仅 Windows
            except Exception:
                pass

    def quit_app(icon, _item) -> None:
        server.should_exit = True
        icon.stop()

    entries: list = [
        pystray.MenuItem("打开 ToolDeck", open_ui, default=True),
        pystray.MenuItem("复制访问地址", copy_url),
    ]
    if log_path:
        entries.append(pystray.MenuItem("查看日志", open_log))
    entries.append(pystray.Menu.SEPARATOR)
    entries.append(pystray.MenuItem("退出", quit_app))

    icon = pystray.Icon(
        "tooldeck",
        icon=image,
        title=f"ToolDeck · {url}",
        menu=pystray.Menu(*entries),
    )

    def setup(icon: pystray.Icon) -> None:
        icon.visible = True
        if open_browser:
            # 图标就绪后再延时打开浏览器，避免服务尚未监听时报连接错误
            threading.Timer(1.5, open_ui).start()
            notify(icon, "ToolDeck 已启动，双击图标可打开界面")

    try:
        icon.run(setup=setup)
    finally:
        server.should_exit = True
        server_thread.join(timeout=5)


__all__ = [
    "TRAY_ICON_NAME",
    "copy_to_clipboard",
    "serve_with_tray",
    "tray_build_enabled",
    "tray_icon_path",
    "tray_runtime_available",
    "tray_runtime_status",
]

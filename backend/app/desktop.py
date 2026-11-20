"""Windows 桌面窗口模式：pywebview + WebView2 内嵌 ToolDeck 界面。

只在「Windows + 打包的窗口版 exe」下启用；Linux / Docker / macOS 一律不加载
pywebview，保持原有的纯 headless 行为，不会引入任何额外的运行时依赖。

窗口与托盘的关系：
    - 窗口版自带托盘（关闭窗口 = 收进托盘，托盘菜单可再次唤出）
    - 托盘不可用（缺少 pystray 等）时窗口照常工作，关闭即退出
    - WebView2 初始化失败时弹窗说明并退出，不会静默变成"点了没反应"
"""
from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

# 窗口版构建标记：spec 在 APP_WINDOW=1 时把它打进 assets/
DESKTOP_MARKER = "window.mode"

# WebView2 Runtime 的 EdgeUpdate 产品 GUID
_WEBVIEW2_GUID = r"{F3017226-FE2A-4295-8BDF-00C3A9A7E4B2}"

_SPLASH_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>ToolDeck</title>
<style>
  :root { color-scheme: dark; }
  html, body { height: 100%; margin: 0; }
  body {
    display: grid; place-items: center; background: #0F1115; color: #E5E7EB;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  }
  .wrap { display: flex; flex-direction: column; align-items: center; gap: 20px; }
  .logo { width: 76px; height: 76px; filter: drop-shadow(0 8px 20px rgba(22,93,255,.28)); }
  h1 { margin: 0; font-size: 17px; font-weight: 600; letter-spacing: .3px; }
  p  { margin: 0; font-size: 12.5px; color: #98A2B3; }
  .bar { width: 184px; height: 3px; border-radius: 3px; background: #1C2230; overflow: hidden; }
  .bar i {
    display: block; height: 100%; width: 40%; border-radius: 3px;
    background: linear-gradient(90deg, #165DFF, #0FC6C2);
    animation: slide 1.25s ease-in-out infinite;
  }
  @keyframes slide { 0% { transform: translateX(-105%); } 100% { transform: translateX(275%); } }
</style></head>
<body><div class="wrap">
  <svg class="logo" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#165dff"/><stop offset="100%" stop-color="#0fc6c2"/>
    </linearGradient></defs>
    <rect width="32" height="32" rx="7" fill="url(#g)"/>
    <path d="M7 17.5 L24 8 L18.5 25 L15.5 18.5 L7 17.5 Z" fill="#fff" stroke="#fff"
          stroke-width="1.2" stroke-linejoin="round" fill-opacity="0.95"/>
    <circle cx="24" cy="24" r="3" fill="#fff"/>
  </svg>
  <h1>ToolDeck</h1>
  <p>正在启动本地服务…</p>
  <div class="bar"><i></i></div>
</div></body></html>"""


def _message_box(text: str, title: str = "ToolDeck") -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x00000040)
    except Exception:
        pass


def webview2_installed() -> bool:
    """检测 WebView2 Runtime 是否安装（注册表 + 目录兜底）。"""
    try:
        import winreg
    except ImportError:
        return False

    locations = (
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_GUID}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_GUID}"),
        (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_GUID}"),
    )
    for root, key in locations:
        try:
            with winreg.OpenKey(root, key) as handle:
                version = winreg.QueryValueEx(handle, "pv")[0]
                if version:
                    return True
        except OSError:
            continue

    for base in (
        r"C:\Program Files (x86)\Microsoft\EdgeWebView\Application",
        r"C:\Program Files\Microsoft\EdgeWebView\Application",
    ):
        folder = Path(base)
        if folder.exists() and any(folder.iterdir()):
            return True
    return False


def desktop_runtime_status() -> tuple[bool, str]:
    """返回 (是否可以启动桌面窗口, 原因说明)。"""
    if sys.platform != "win32":
        return False, f"非 Windows 平台（{sys.platform}），桌面窗口不可用"
    try:
        import webview  # noqa: F401
    except Exception as exc:
        return False, f"pywebview 导入失败：{exc!r}"
    if not webview2_installed():
        return False, "未检测到 WebView2 Runtime（需安装 Microsoft Edge WebView2 Evergreen Runtime）"
    return True, "pywebview + WebView2 可用"


def desktop_marker_path() -> Path | None:
    from backend.app.resources import resolve_asset_path

    return resolve_asset_path(DESKTOP_MARKER)


def desktop_build_enabled() -> bool:
    """本次构建是否带桌面窗口：只有打包的窗口版 exe 才自动启用。"""
    if not getattr(sys, "frozen", False):
        return False
    if desktop_marker_path() is None:
        return False
    return desktop_runtime_status()[0]


def _wait_ready(url: str, timeout: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}api/health", timeout=1.0) as resp:
                if getattr(resp, "status", 200) == 200:
                    return True
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(0.4)
    return False


def run_desktop(
    app,
    *,
    host: str,
    port: int,
    url: str,
    log_path: Path | None = None,
    open_browser: bool = False,
    storage_path: Path | None = None,
) -> None:
    """启动本地服务并在 WebView2 窗口里打开 ToolDeck；关闭窗口收进托盘。"""
    import uvicorn
    import webview

    config = uvicorn.Config(
        app, host=host, port=port, log_level="info", log_config=None, access_log=True
    )
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, name="tooldeck-server", daemon=True)
    server_thread.start()

    window = webview.create_window(
        "ToolDeck",
        html=_SPLASH_HTML,
        width=1280,
        height=860,
        min_size=(960, 640),
        background_color="#0F1115",
    )

    state = {"loaded": False, "quitting": False, "tray": None}

    def on_loaded() -> None:
        state["loaded"] = True

    window.events.loaded += on_loaded

    def on_closing():
        """点右上角关闭 → 收进托盘；正在退出时才真正关闭。"""
        if state["quitting"] or state["tray"] is None:
            return True
        window.hide()
        return False

    window.events.closing += on_closing

    def show_window() -> None:
        try:
            window.show()
            window.restore()
        except Exception:
            pass

    def load_ui() -> None:
        if not _wait_ready(url):
            return
        try:
            window.load_url(url)
        except Exception:
            pass

    def build_tray():
        """窗口版托盘：菜单与窗口联动。失败时返回 None（窗口照常可用）。"""
        try:
            import pystray
            from PIL import Image

            from backend.app.tray import copy_to_clipboard, tray_icon_path

            icon_path = tray_icon_path()
            if icon_path is None:
                return None

            def copy_url(icon, _item) -> None:
                if copy_to_clipboard(url):
                    try:
                        icon.notify("地址已复制到剪贴板", "ToolDeck")
                    except Exception:
                        pass

            def open_log(icon=None, _item=None) -> None:
                import os

                if log_path and Path(log_path).exists():
                    try:
                        os.startfile(str(log_path))
                    except Exception:
                        pass

            def quit_app(icon, _item) -> None:
                state["quitting"] = True
                server.should_exit = True
                try:
                    icon.stop()
                except Exception:
                    pass
                try:
                    window.destroy()
                except Exception:
                    pass

            entries: list = [
                pystray.MenuItem("打开 ToolDeck", lambda i, it: show_window(), default=True),
                pystray.MenuItem("隐藏窗口", lambda i, it: window.hide()),
                pystray.MenuItem("复制访问地址", copy_url),
            ]
            if log_path:
                entries.append(pystray.MenuItem("查看日志", open_log))
            entries.append(pystray.Menu.SEPARATOR)
            entries.append(pystray.MenuItem("退出", quit_app))

            icon = pystray.Icon(
                "tooldeck",
                icon=Image.open(icon_path).resize((64, 64)),
                title=f"ToolDeck · {url}",
                menu=pystray.Menu(*entries),
            )
            threading.Thread(target=icon.run, name="tooldeck-tray", daemon=True).start()
            return icon
        except Exception:
            return None

    def on_start() -> None:
        state["tray"] = build_tray()
        threading.Thread(target=load_ui, name="tooldeck-ready", daemon=True).start()
        if open_browser:
            threading.Timer(1.5, lambda: __import__("webbrowser").open_new_tab(url)).start()

    try:
        webview.start(
            on_start,
            gui="edgechromium",
            private_mode=False,
            storage_path=str(storage_path) if storage_path else None,
        )
    finally:
        state["quitting"] = True
        server.should_exit = True
        server_thread.join(timeout=5)

    if not state["loaded"]:
        _message_box(
            "WebView2 窗口没能初始化（界面未加载）。\n\n"
            "请确认已安装 Microsoft Edge WebView2 Runtime，然后重试；\n"
            "也可以先用 api-tool.exe --no-window 以托盘/无界面方式运行。"
        )


__all__ = [
    "DESKTOP_MARKER",
    "desktop_build_enabled",
    "desktop_marker_path",
    "desktop_runtime_status",
    "run_desktop",
    "webview2_installed",
]

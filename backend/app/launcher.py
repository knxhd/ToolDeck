"""启动器：uvicorn 启动后异步打开浏览器。"""
from __future__ import annotations

import threading
import time
import webbrowser


def open_browser_after_delay(url: str, delay: float = 2.0) -> None:
    """在后台线程中延迟打开浏览器，避免阻塞 uvicorn 启动。"""
    def _open() -> None:
        time.sleep(delay)
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            pass

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


__all__ = ["open_browser_after_delay"]

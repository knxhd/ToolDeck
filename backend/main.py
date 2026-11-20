"""应用入口：解析 APP_ENV，构造 FastAPI，启动 uvicorn（无界面 headless 服务）。

支持命令行参数（headless 服务器）：
    python backend/main.py --host 0.0.0.0 --port 9000 --data-dir /srv/api-tool

参数与环境变量优先级：命令行 > 环境变量 > 默认值
    --host      默认 127.0.0.1（对应环境变量 APP_HOST）
    --port      默认 8765（对应环境变量 APP_PORT）
    --data-dir  数据目录，默认 ~/.api-tool（对应环境变量 APP_CONFIG_DIR）

托盘（仅 Windows，且需带托盘构建的 exe）：
    api-tool.exe --no-tray     强制不使用托盘，与原 headless 行为一致
    api-tool.exe --tray        强制启用托盘（非托盘构建会忽略并提示）
    api-tool.exe --no-open     托盘模式启动时不自动打开浏览器

开发模式：APP_ENV=development uvicorn backend.main:app --reload --port 8765
生产模式（Docker）：uvicorn backend.main:app --host 0.0.0.0 --port 8765
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import uvicorn


def _ensure_streams() -> None:
    """Windowed exe（托盘版无控制台）里 sys.stdout/stderr 为 None，
    替换成最小可写对象，避免 print / argparse 报错时静默崩溃。"""

    class _Null:
        def write(self, *_args):
            return None

        def flush(self):
            return None

        def isatty(self):
            return False

    if sys.stdout is None:
        sys.stdout = _Null()  # type: ignore[assignment]
    if sys.stderr is None:
        sys.stderr = _Null()  # type: ignore[assignment]


_ensure_streams()


def _apply_data_dir_early() -> None:
    """在导入 backend.app 之前把 --data-dir 落成 APP_CONFIG_DIR。

    config 模块的 CONFIG_DIR / CONFIG_PATH 是模块级常量，首次 import 即固定，
    若等到 parse_args 之后再设置环境变量就为时已晚（--data-dir 会失效）。
    """
    argv = sys.argv[1:]
    for index, token in enumerate(argv):
        if token == "--data-dir" and index + 1 < len(argv):
            os.environ["APP_CONFIG_DIR"] = argv[index + 1]
        elif token.startswith("--data-dir="):
            os.environ["APP_CONFIG_DIR"] = token.split("=", 1)[1]


_apply_data_dir_early()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import create_app

# FastAPI 实例供 uvicorn import 使用（Docker / uvicorn 直接加载）
app = create_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ToolDeck server")
    parser.add_argument(
        "--host",
        default=os.environ.get("APP_HOST", "127.0.0.1"),
        help="监听地址，默认 127.0.0.1（对外服务请用 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("APP_PORT", "8765")),
        help="监听端口，默认 8765",
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("APP_CONFIG_DIR", ""),
        help="数据目录（collections.json / history.json / config.json），默认 ~/.api-tool",
    )
    tray_group = parser.add_mutually_exclusive_group()
    tray_group.add_argument(
        "--tray",
        dest="tray",
        action="store_true",
        default=None,
        help="启用系统托盘（仅 Windows 的托盘版构建有效）",
    )
    tray_group.add_argument(
        "--no-tray",
        dest="tray",
        action="store_false",
        help="禁用系统托盘，按 headless 方式运行",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="托盘模式启动时不自动打开浏览器",
    )
    return parser.parse_args()


def _setup_logging(stream, log_file=None) -> None:
    """日志：有控制台就输出到终端；托盘模式额外落盘，便于排查。"""
    handlers: list[logging.Handler] = []
    if stream is not None:
        handlers.append(logging.StreamHandler(stream))
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(
                RotatingFileHandler(
                    log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
                )
            )
        except Exception:
            pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers or [logging.NullHandler()],
    )


def _local_url(host: str, port: int) -> str:
    if host in ("0.0.0.0", "::", "127.0.0.1", "localhost"):
        return f"http://localhost:{port}/"
    return f"http://{host}:{port}/"


def _is_windowed_frozen() -> bool:
    """无控制台的打包 exe：错误信息没有任何输出通道，必须弹窗提示。"""
    return getattr(sys, "frozen", False) and sys.platform == "win32"


def _probe_running_instance(host: str, port: int) -> bool:
    """本机是否已有 ToolDeck 实例在跑（/api/health 可达即视为已运行）。

    统一用 127.0.0.1 探测：Windows 上 localhost 可能先解析成 ::1，
    而服务通常只监听 IPv4，会出现"端口在占但探测失败"的假阴性。
    """
    import urllib.error
    import urllib.request

    probe_host = "127.0.0.1" if host in ("0.0.0.0", "::", "localhost") else host
    try:
        with urllib.request.urlopen(
            f"http://{probe_host}:{port}/api/health", timeout=1.5
        ) as resp:
            return getattr(resp, "status", 200) == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _port_in_use(host: str, port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return False
        except OSError:
            return True


def _message_box(text: str, title: str = "ToolDeck") -> None:
    """Windows 消息框（无控制台时唯一的可见提示手段）。"""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, title, 0x00000040)
    except Exception:
        pass


def main() -> None:
    global app
    args = parse_args()

    if args.data_dir:
        # 自定义数据目录：必须在 create_app（初始化配置目录）之前设置环境变量
        os.environ["APP_CONFIG_DIR"] = args.data_dir
        app = create_app()

    use_tray = False
    tray_reason = "未启用"
    if args.tray is True:
        # 显式 --tray：开发态也能调试托盘
        try:
            from backend.app.tray import tray_runtime_status

            use_tray, tray_reason = tray_runtime_status()
        except Exception as exc:
            tray_reason = f"托盘模块不可用：{exc!r}"
        if not use_tray:
            print(f"[提示] 托盘不可用（{tray_reason}），已按 headless 模式启动。")
    elif args.tray is None:
        # 默认：只有带托盘的 exe 才启用，开发/源码运行完全是旧行为
        try:
            from backend.app.tray import tray_build_enabled, tray_runtime_status

            ok, tray_reason = tray_runtime_status()
            use_tray = ok and tray_build_enabled()
            if ok and not getattr(sys, "frozen", False):
                tray_reason = "源码运行（非打包 exe），默认不开托盘"
        except Exception as exc:
            tray_reason = f"托盘模块不可用：{exc!r}"

    stream = sys.stderr if sys.stderr is not None else sys.stdout
    url = _local_url(args.host, args.port)

    # 无控制台 exe 没有任何输出通道：一律落盘日志，托盘问题才可诊断
    log_file = None
    if _is_windowed_frozen():
        data_dir = Path(os.environ.get("APP_CONFIG_DIR") or (Path.home() / ".api-tool"))
        log_file = data_dir / "server.log"
    _setup_logging(stream, log_file)
    logging.getLogger(__name__).info(
        "启动：tray=%s（%s） url=%s", use_tray, tray_reason, url
    )

    if _is_windowed_frozen():
        # 双击场景：先分辨"已经在跑"和"端口被别的程序占了"，避免毫无反馈地退出
        if _probe_running_instance(args.host, args.port):
            import webbrowser

            webbrowser.open_new_tab(url)
            return
        if _port_in_use(args.host, args.port):
            _message_box(
                f"端口 {args.port} 已被其他程序占用，ToolDeck 无法启动。\n\n"
                "解决办法：\n"
                f"1. 关闭占用 {args.port} 端口的程序后重试；\n"
                "2. 或换个端口启动，例如：api-tool.exe --port 9000"
            )
            return

    if use_tray:
        from backend.app.tray import serve_with_tray

        logging.getLogger(__name__).info("托盘模式启动：%s", url)
        try:
            serve_with_tray(
                app,
                host=args.host,
                port=args.port,
                url=url,
                open_browser=not args.no_open,
                log_path=log_file,
            )
            return
        except Exception as exc:  # 托盘不可用（缺少桌面会话等）时降级，别静默退出
            logging.getLogger(__name__).exception("托盘启动失败，降级为无界面模式")
            _message_box(
                f"托盘图标启动失败：{exc}\n\n"
                f"已改用无界面模式继续运行，访问 {url}\n"
                f"日志：{log_file}"
            )
            if not args.no_open:
                from backend.app.launcher import open_browser_after_delay

                open_browser_after_delay(url, 2.0)

    if _is_windowed_frozen() and not args.no_open:
        # 无托盘的双击场景：服务起来后自动开浏览器，避免"点了没反应"的错觉
        from backend.app.launcher import open_browser_after_delay

        open_browser_after_delay(url, 2.0)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        log_config=None,
        access_log=True,
    )


if __name__ == "__main__":
    main()

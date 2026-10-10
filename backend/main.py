"""应用入口：解析 APP_ENV，构造 FastAPI，启动 uvicorn（无界面 headless 服务）。

支持命令行参数（headless 服务器）：
    python backend/main.py --host 0.0.0.0 --port 9000 --data-dir /srv/api-tool

参数与环境变量优先级：命令行 > 环境变量 > 默认值
    --host      默认 127.0.0.1（对应环境变量 APP_HOST）
    --port      默认 8765（对应环境变量 APP_PORT）
    --data-dir  数据目录，默认 ~/.api-tool（对应环境变量 APP_CONFIG_DIR）

开发模式：APP_ENV=development uvicorn backend.main:app --reload --port 8765
生产模式（Docker）：uvicorn backend.main:app --host 0.0.0.0 --port 8765
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.app import create_app

# FastAPI 实例供 uvicorn import 使用（Docker / uvicorn 直接加载）
app = create_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="API Tool headless server")
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
    return parser.parse_args()


def main() -> None:
    global app
    args = parse_args()

    if args.data_dir:
        # 自定义数据目录：必须在 create_app（初始化配置目录）之前设置环境变量
        os.environ["APP_CONFIG_DIR"] = args.data_dir
        app = create_app()
    _stream = sys.stderr if sys.stderr is not None else sys.stdout
    if _stream is not None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=_stream,
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            handlers=[logging.NullHandler()],
        )
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

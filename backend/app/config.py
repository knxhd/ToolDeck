"""配置目录初始化：首次启动创建配置目录与默认配置文件。

默认目录为 ~/.api-tool/（符合规范）。开发/沙箱环境可通过 APP_CONFIG_DIR
环境变量覆盖为项目本地路径，便于在受限环境下运行。
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def _resolve_config_dir() -> Path:
    """解析配置目录：优先 APP_CONFIG_DIR，否则 ~/.api-tool/。"""
    override = os.environ.get("APP_CONFIG_DIR")
    if override:
        return Path(override)
    return Path.home() / ".api-tool"


CONFIG_DIR = _resolve_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"
HISTORY_PATH = CONFIG_DIR / "history.json"

DEFAULT_CONFIG = {"version": 1, "mcp_servers": [], "llm_providers": []}
DEFAULT_HISTORY = {"http_calls": [], "mcp_calls": [], "llm_calls": []}


def init_config_dir() -> None:
    """首次启动检测 ~/.api-tool/，不存在则创建并写入默认配置文件。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, ensure_ascii=False), encoding="utf-8"
        )
    if not HISTORY_PATH.exists():
        HISTORY_PATH.write_text(
            json.dumps(DEFAULT_HISTORY, ensure_ascii=False), encoding="utf-8"
        )


def load_config() -> dict:
    """读取 config.json，缺失则初始化后返回默认值。"""
    init_config_dir()
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(data: dict) -> None:
    """写入 config.json。"""
    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_history() -> dict:
    """读取 history.json。"""
    init_config_dir()
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def save_history(data: dict) -> None:
    """写入 history.json。"""
    HISTORY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


__all__ = [
    "CONFIG_DIR",
    "CONFIG_PATH",
    "HISTORY_PATH",
    "init_config_dir",
    "load_config",
    "save_config",
    "load_history",
    "save_history",
]

"""配置目录初始化：首次启动创建配置目录与默认配置文件。

默认目录为 ~/.api-tool/（符合规范）。开发/沙箱环境可通过 APP_CONFIG_DIR
环境变量覆盖为项目本地路径，便于在受限环境下运行。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from backend.app.services import crypto


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


def _encrypt_sensitive(data: dict) -> dict:
    """落盘前加密：llm_providers[].api_key、mcp_servers[].headers 各值。幂等（已加密跳过）。"""
    for p in data.get("llm_providers", []):
        if isinstance(p.get("api_key"), str) and p["api_key"] and not crypto.is_encrypted(p["api_key"]):
            p["api_key"] = crypto.encrypt(p["api_key"])
    for s in data.get("mcp_servers", []):
        hdrs = s.get("headers") or {}
        if isinstance(hdrs, dict):
            s["headers"] = {
                k: (v if crypto.is_encrypted(v) else crypto.encrypt(v))
                for k, v in hdrs.items()
                if v
            }
    return data


def _decrypt_sensitive(data: dict) -> dict:
    """读取后解密：与 _encrypt_sensitive 对称。历史明文（无前缀）原样返回，兼容迁移。"""
    for p in data.get("llm_providers", []):
        if isinstance(p.get("api_key"), str) and p["api_key"]:
            p["api_key"] = crypto.decrypt(p["api_key"])
    for s in data.get("mcp_servers", []):
        hdrs = s.get("headers") or {}
        if isinstance(hdrs, dict):
            s["headers"] = {k: crypto.decrypt(v) for k, v in hdrs.items()}
    return data


def load_config() -> dict:
    """读取 config.json（敏感字段自动解密）。"""
    init_config_dir()
    return _decrypt_sensitive(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))


def save_config(data: dict) -> None:
    """写入 config.json（敏感字段自动加密）。"""
    CONFIG_PATH.write_text(
        json.dumps(_encrypt_sensitive(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def migrate_config_secrets() -> None:
    """把历史明文 config.json 迁移为密文（幂等）。"""
    data = load_config()   # 解密读取（历史明文仍为明文）
    save_config(data)      # 再落盘时统一加密


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
    "migrate_config_secrets",
]

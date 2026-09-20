"""LLM Provider 配置存储：读写 config.json 的 llm_providers 字段。"""
from __future__ import annotations

from typing import Any

from backend.app.config import load_config, save_config
from backend.app.schemas.llm import LlmProvider


def list_providers() -> list[dict[str, Any]]:
    return load_config().get("llm_providers", [])


def get_provider(name: str) -> dict[str, Any] | None:
    for p in list_providers():
        if p.get("name") == name:
            return p
    return None


def add_provider(provider: LlmProvider) -> dict[str, Any]:
    if get_provider(provider.name) is not None:
        raise ValueError(f"LLM Provider '{provider.name}' 已存在")
    data = load_config()
    data.setdefault("llm_providers", []).append(provider.model_dump())
    save_config(data)
    return provider.model_dump()


def update_provider(name: str, provider: LlmProvider) -> dict[str, Any]:
    data = load_config()
    providers = data.setdefault("llm_providers", [])
    for i, p in enumerate(providers):
        if p.get("name") == name:
            providers[i] = provider.model_dump()
            save_config(data)
            return provider.model_dump()
    raise ValueError(f"LLM Provider '{name}' 不存在")


def delete_provider(name: str) -> dict[str, Any]:
    data = load_config()
    providers = data.get("llm_providers", [])
    new_providers = [p for p in providers if p.get("name") != name]
    if len(new_providers) == len(providers):
        raise ValueError(f"LLM Provider '{name}' 不存在")
    data["llm_providers"] = new_providers
    save_config(data)
    return {"deleted": name}


__all__ = [
    "list_providers",
    "get_provider",
    "add_provider",
    "update_provider",
    "delete_provider",
]

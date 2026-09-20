"""Provider Adapter 工厂：根据 provider_type 返回对应 Adapter。

注册 openai -> OpenAICompatibleAdapter，未知 type 抛 ValueError。
"""
from __future__ import annotations

from backend.app.schemas.llm import ProviderType
from backend.app.services.llm.base_adapter import LLMProviderAdapter
from backend.app.services.llm.openai_adapter import OpenAICompatibleAdapter

_REGISTRY: dict[str, type[LLMProviderAdapter]] = {
    ProviderType.OPENAI.value: OpenAICompatibleAdapter,
}


def register_adapter(provider_type: str, adapter_cls: type[LLMProviderAdapter]) -> None:
    """注册新 Adapter。"""
    _REGISTRY[provider_type] = adapter_cls


def get_adapter(provider_type: str) -> LLMProviderAdapter:
    """获取 Adapter 实例。

    Raises:
        ValueError: 未注册的 provider_type。
    """
    cls = _REGISTRY.get(provider_type)
    if cls is None:
        raise ValueError(
            f"未注册的 provider_type '{provider_type}'，"
            f"可选：{list(_REGISTRY.keys())}"
        )
    return cls()


__all__ = ["register_adapter", "get_adapter"]

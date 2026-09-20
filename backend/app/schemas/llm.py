"""LLM Provider 与 Chat 调用 Pydantic 模型。"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class LlmProvider(BaseModel):
    """LLM Provider 配置。"""
    name: str
    base_url: str
    api_key: str
    model: str
    provider_type: ProviderType = ProviderType.OPENAI
    options: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str  # user / assistant / system
    content: str


class ChatRequest(BaseModel):
    """LLM 聊天请求。"""
    provider_name: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float = 0.7


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """同步调用响应。"""
    content: str
    finish_reason: str = ""
    usage: ChatUsage = Field(default_factory=ChatUsage)
    model: str = ""


__all__ = [
    "ProviderType",
    "LlmProvider",
    "ChatMessage",
    "ChatRequest",
    "ChatUsage",
    "ChatResponse",
]

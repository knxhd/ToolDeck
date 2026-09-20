"""LLM Provider Adapter 抽象基类。

所有 Provider 必须把请求/响应统一为内部 OpenAI 格式：
- build_request 构造 httpx.Request
- parse_stream_chunk 解析单行 SSE chunk，返回 (delta, finish_reason)
"""
from __future__ import annotations

import abc
from typing import Any

import httpx

from backend.app.schemas.llm import ChatMessage


class LLMProviderAdapter(abc.ABC):
    """Provider 适配器抽象基类。"""

    @abc.abstractmethod
    def build_request(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[ChatMessage],
        stream: bool,
        options: dict[str, Any],
    ) -> httpx.Request:
        """构造发往上游的 httpx.Request。"""
        raise NotImplementedError

    @abc.abstractmethod
    def parse_stream_chunk(self, line: bytes) -> tuple[str, str | None]:
        """解析单行流式 chunk，返回 (delta 文本, finish_reason 或 None)。

        空行或非数据行返回 ("", None)。
        """
        raise NotImplementedError

    @abc.abstractmethod
    def parse_sync_response(self, response: httpx.Response) -> tuple[str, str, dict]:
        """解析同步响应，返回 (content, finish_reason, usage_dict)。"""
        raise NotImplementedError


__all__ = ["LLMProviderAdapter"]

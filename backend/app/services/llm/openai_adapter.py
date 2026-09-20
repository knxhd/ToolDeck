"""OpenAI Compatible Adapter：直接以 OpenAI 格式调用 /v1/chat/completions。

OpenAI Compatible Provider（DeepSeek、智谱、Moonshot、通义等）直接 passthrough。
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from backend.app.schemas.llm import ChatMessage
from backend.app.services.llm.base_adapter import LLMProviderAdapter


class OpenAICompatibleAdapter(LLMProviderAdapter):
    """OpenAI Compatible 协议适配器。"""

    def build_request(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[ChatMessage],
        stream: bool,
        options: dict[str, Any],
    ) -> httpx.Request:
        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }
        if "temperature" in options:
            payload["temperature"] = options["temperature"]
        # 合并其余 options
        for k, v in options.items():
            if k != "temperature":
                payload.setdefault(k, v)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        }
        return httpx.Request("POST", url, json=payload, headers=headers)

    def parse_stream_chunk(self, line: bytes) -> tuple[str, str | None]:
        text = line.decode("utf-8", errors="replace").strip()
        if not text or not text.startswith("data:"):
            return "", None
        data_str = text[len("data:"):].strip()
        if data_str == "[DONE]":
            return "", "stop"
        try:
            obj = json.loads(data_str)
        except json.JSONDecodeError:
            return "", None
        choices = obj.get("choices") or []
        if not choices:
            return "", None
        delta = choices[0].get("delta", {}).get("content") or ""
        finish_reason = choices[0].get("finish_reason")
        return delta, finish_reason

    def parse_sync_response(self, response: httpx.Response) -> tuple[str, str, dict]:
        obj = response.json()
        choices = obj.get("choices") or []
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        finish_reason = choices[0].get("finish_reason", "") if choices else ""
        usage = obj.get("usage", {}) or {}
        return content, finish_reason, usage


__all__ = ["OpenAICompatibleAdapter"]

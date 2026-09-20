"""HTTP 请求/响应 Pydantic 模型。"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class BodyType(str, Enum):
    NONE = "none"
    JSON = "json"
    RAW = "raw"
    FORM_DATA = "form-data"


class KeyValue(BaseModel):
    key: str = ""
    value: str = ""
    enabled: bool = True


class HttpRequest(BaseModel):
    method: HttpMethod = HttpMethod.GET
    url: str
    headers: list[KeyValue] = Field(default_factory=list)
    params: list[KeyValue] = Field(default_factory=list)
    body_type: BodyType = BodyType.NONE
    body: str = ""


class HttpResponse(BaseModel):
    status_code: int
    status_text: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = ""
    elapsed_ms: int = 0
    size_bytes: int = 0
    error: str | None = None


class HttpCallRecord(BaseModel):
    """历史记录单条。"""
    method: str
    url: str
    headers: list[KeyValue] = Field(default_factory=list)
    body_type: str = "none"
    body: str = ""
    status_code: int = 0
    elapsed_ms: int = 0
    timestamp: str = ""


__all__ = [
    "HttpMethod",
    "BodyType",
    "KeyValue",
    "HttpRequest",
    "HttpResponse",
    "HttpCallRecord",
]

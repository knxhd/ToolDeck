from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """认证快捷注入配置"""
    type: Literal["none", "bearer", "basic", "apikey"] = "none"
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    key_name: Optional[str] = None
    key_value: Optional[str] = None
    key_in: Optional[Literal["header", "query"]] = "header"


class FormField(BaseModel):
    """form-data 字段"""
    name: str
    type: Literal["text", "file"] = "text"
    value: Optional[str] = None
    content: Optional[str] = None  # base64 编码的文件内容
    filename: Optional[str] = None


class RequestPayload(BaseModel):
    """HTTP 请求体"""
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"] = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    query_params: Dict[str, str] = Field(default_factory=dict)
    body: Optional[str] = None
    body_type: Literal["none", "raw", "form-data", "x-www-urlencoded", "binary"] = "none"
    form_fields: List[FormField] = Field(default_factory=list)
    auth: Optional[AuthConfig] = None
    timeout: int = 30


class ResponsePayload(BaseModel):
    """HTTP 响应体"""
    status: int
    status_text: str
    headers: Dict[str, str]
    body: str
    time_ms: float
    size_bytes: int
    content_type: str


class ErrorPayload(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None

"""批量/压测任务的 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class BenchRequestTemplate(BaseModel):
    """模板请求：与前端 HttpRequestData 对应，占位符保持 {{var}} 原样，由后端逐行替换。"""

    method: str = "GET"
    url: str = ""
    headers: list[dict] = Field(default_factory=list)
    params: list[dict] = Field(default_factory=list)
    body_type: str = "none"
    body: str = ""


class BenchRunBody(BaseModel):
    """发起一次批量测试。"""

    name: str = "批量测试"
    upload_id: str
    concurrency: int = Field(default=10, ge=1, le=100)
    streaming: bool = False
    request: BenchRequestTemplate
    # 当前环境/集合变量：CSV 列没覆盖的占位符用它兜底（如 {{host}}）
    env_vars: dict[str, str] = Field(default_factory=dict)


class JobSummary(BaseModel):
    avg_ms: float = 0
    p95_ms: float = 0
    ttft_avg_ms: float = 0


class BenchJob(BaseModel):
    id: str
    name: str
    user_id: int
    created_at: str
    status: str = "running"  # running / done / failed
    total: int = 0
    done: int = 0
    success: int = 0
    fail: int = 0
    concurrency: int = 10
    streaming: bool = False
    upload_name: str = ""
    result_csv: str = ""
    error: str = ""
    columns: list[str] = Field(default_factory=list)
    stats: JobSummary = Field(default_factory=JobSummary)

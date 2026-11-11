"""批量/压测任务的 Pydantic 模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class BenchColumn(BaseModel):
    """自定义结果列：CSV 表头 + 取值路径。

    path 支持 `response.data`、`response.data[0].name`、`data.items.0.id` 等写法，
    解析时忽略 `response.` / `body.` / `$` 前缀，按点号与下标逐层取值。
    """

    title: str = Field(min_length=1, max_length=64, description="CSV 表头文字")
    path: str = Field(min_length=1, max_length=200, description="取值路径")

    @model_validator(mode="after")
    def _trim(self) -> "BenchColumn":
        self.title = self.title.strip()
        self.path = self.path.strip()
        if not self.title or not self.path:
            raise ValueError("表头名与取值路径都不能为空")
        return self


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
    # 自定义结果列：在固定指标列之后追加；流式模式下 content 为系统默认列
    columns: list[BenchColumn] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _unique_titles(self) -> "BenchRunBody":
        seen: set[str] = set()
        for c in self.columns:
            if c.title in seen:
                raise ValueError(f"自定义表头重复：{c.title}")
            seen.add(c.title)
        return self


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

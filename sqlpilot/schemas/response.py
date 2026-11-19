"""HTTP 出参模型（doc §11.2）。"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

FinalStatus = Literal["success", "refused", "failed"]


class ResultTable(BaseModel):
    columns: list[str]
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    truncated: bool = False


class Metrics(BaseModel):
    retry_count: int = 0
    step_count: int = 0
    sql_attempts: int = 0
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


class TraceStep(BaseModel):
    step: int
    node: str
    ts_ms: int
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None


class QueryResponse(BaseModel):
    run_id: str
    final_status: FinalStatus
    answer: str | None = None
    sql: str | None = None
    result: ResultTable | None = None
    failure_reason: str | None = None
    metrics: Metrics = Field(default_factory=Metrics)
    trace: list[TraceStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    code: str
    message: str
    run_id: str | None = None
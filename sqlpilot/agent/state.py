"""AgentState for the agent loop (doc §2.7). TypedDict, not BaseModel."""
from typing import Literal, TypedDict


class Usage(TypedDict, total=False):
    prompt_tokens: int
    completion_tokens: int
    llm_calls: int


class AgentState(TypedDict, total=False):
    run_id: str
    question: str
    schema_context: str
    selected_tables: list[str]
    sql: str
    sql_history: list[str]
    sql_attempts: int
    exec_result: dict | None
    error: dict | None          # {"errno","message","kind","source"}
    reflect_hint: str | None
    need_relink: bool
    retry_count: int
    step_count: int
    start_ts: float
    usage: Usage
    trace: list[dict]
    final_status: Literal["success", "refused", "failed"]
    answer: str | None
    failure_reason: str | None
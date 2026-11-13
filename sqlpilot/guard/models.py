"""SqlGuard result type (doc §2.11)."""
from typing import Any

from pydantic import BaseModel, Field


class SqlValidation(BaseModel):
    passed: bool
    normalized_sql: str | None = None
    reason: str | None = None
    tables: list[str] = Field(default_factory=list)
    injected_limit: bool = False
    observation: dict[str, Any] | None = None   # {"errno","message","kind","source"}
    blocked: bool = False                        # True => security violation => refuse, no retry
    # Contract: blocked=True implies observation["kind"] == "BLOCKED"